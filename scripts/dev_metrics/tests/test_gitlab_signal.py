"""Offline GitLab metadata regression tests; only synthetic credentials/data."""
import contextlib
import datetime as dt
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gitlab_signal as signal

NOW = dt.datetime(2026, 9, 15, tzinfo=dt.timezone.utc)
RECENT = "2026-09-10T01:02:03Z"
OLD = "2025-01-01T00:00:00Z"
FUTURE = "2027-01-01T00:00:00Z"
PRIVATE = "SYNTHETIC-PRIVATE-BODY"
CONFIG = {"GITLAB_TOKEN": "synthetic-token", "GITLAB_BASE_URL": "https://gitlab.example.test/hub"}
PROJECT = "group/repo"
PREFIX = "projects/group%2Frepo"


def response(data=None, status=200, next_page="", links=None):
    headers = {} if next_page is None else {"X-Next-Page": next_page}
    return Mock(status_code=status, headers=headers, links=links or {}, text=PRIVATE,
                json=Mock(return_value=data))


def actor(username="owner", **extra):
    return {"username": username, "bio": PRIVATE, **extra}


def mr(iid=1, **extra):
    return {"id": iid + 100, "iid": iid, "state": "merged", "author": actor(),
            "merged_by": actor("merger"), "created_at": RECENT, "updated_at": RECENT,
            "merged_at": RECENT, "reviewers": [actor("requested")],
            "title": PRIVATE, "description": PRIVATE, "diff": PRIVATE, **extra}


def note(number=1, username="reviewer", **extra):
    return {"id": number, "author": actor(username), "system": False,
            "created_at": RECENT, "updated_at": RECENT, "body": PRIVATE, **extra}


def record(**extra):
    return {**signal.request_metadata(mr(**extra), PROJECT), "discussions": [], "approvals": None}


class FrozenDateTime(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return NOW


class GitLabSignalTests(unittest.TestCase):
    def setUp(self):
        # Any missing mock fails closed rather than making a live call.
        self.network = patch.object(requests.Session, "get", side_effect=AssertionError("No live calls"))
        self.network.start()
        self.addCleanup(self.network.stop)

    def client(self, config=None):
        client = signal.GitLabClient(CONFIG if config is None else config)
        self.addCleanup(client.session.close)
        return client

    def test_dotenv_parsing_and_process_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "test.env"
            path.write_text('GITLAB_TOKEN="file-token"\nGITLAB_BASE_URL="https://file.test/hub"\n'
                            'LGEP_PASSWORD="a=b # literal"\n', encoding="utf-8")
            with patch.dict(os.environ, {"GITLAB_TOKEN": "process-token",
                                         "GITLAB_BASE_URL": CONFIG["GITLAB_BASE_URL"]}, clear=True):
                config = signal.load_env(path)
            self.assertEqual(config["GITLAB_TOKEN"], "process-token")
            self.assertEqual(config["GITLAB_BASE_URL"], CONFIG["GITLAB_BASE_URL"])
            self.assertEqual(config["LGEP_PASSWORD"], "a=b # literal")

    def test_default_env_is_worktree_root_not_cwd(self):
        expected = Path(signal.__file__).resolve().parents[2] / ".env"
        self.assertEqual(signal.DEFAULT_ENV_FILE, expected)
        with patch.object(signal, "dotenv_values", return_value={}) as values, \
                patch.object(os, "getcwd", return_value="/unrelated"), patch.dict(os.environ, CONFIG, clear=True):
            self.assertEqual(signal.load_env()["GITLAB_TOKEN"], "synthetic-token")
        values.assert_called_once_with(expected, interpolate=False)

    def test_missing_env_file_process_configuration_works(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, CONFIG, clear=True):
            self.assertEqual(signal.load_env(Path(directory) / "absent")["GITLAB_TOKEN"], "synthetic-token")

    def test_pat_preferred_to_legacy_auth(self):
        client = self.client({**CONFIG, "LGEP_ID": "legacy", "LGEP_PASSWORD": "legacy-password"})
        self.assertEqual(client.session.headers["PRIVATE-TOKEN"], "synthetic-token")
        self.assertIsNone(client.session.auth)
        self.assertFalse(client.session.trust_env)

    def test_legacy_auth_and_missing_credentials(self):
        client = self.client({"LGEP_ID": "legacy", "LGEP_PASSWORD": "legacy-password"})
        self.assertEqual(client.session.auth, ("legacy", "legacy-password"))
        self.assertNotIn("PRIVATE-TOKEN", client.session.headers)
        for config in ({}, {"LGEP_ID": "legacy"}):
            with self.assertRaises(signal.CollectionError):
                self.client(config)

    def test_base_url_normalization_preserves_hub(self):
        for suffix in ("", "/", "/api/v4", "/api/v4/", "/api/v4/api/v4/"):
            with self.subTest(suffix=suffix):
                self.assertEqual(signal.normalize_base_url(CONFIG["GITLAB_BASE_URL"] + suffix),
                                 CONFIG["GITLAB_BASE_URL"] + "/api/v4")
        self.assertEqual(signal.normalize_base_url("http://gitlab.test/hub"), "http://gitlab.test/hub/api/v4")

    def test_invalid_base_url_is_sanitized(self):
        for url in ("https://user:synthetic-secret@host/hub", "https://host/?token=synthetic-secret",
                    "ftp://host", "https://host:invalid", "https://[invalid"):
            with self.subTest(url=url), self.assertRaises(signal.CollectionError) as error:
                signal.normalize_base_url(url)
            self.assertNotIn("synthetic-secret", str(error.exception))

    def test_request_disallows_redirects_and_verifies_tls(self):
        client = self.client()
        with patch.object(client.session, "get", return_value=response([])) as get:
            client.get(PREFIX)
        self.assertEqual(get.call_args.args[0], CONFIG["GITLAB_BASE_URL"] + "/api/v4/" + PREFIX)
        self.assertIs(get.call_args.kwargs["allow_redirects"], False)
        self.assertIs(get.call_args.kwargs["verify"], True)

    def test_short_pages_follow_actual_next_header(self):
        client = self.client()
        with patch.object(client.session, "get", side_effect=[response([{"id": 1}], next_page="3"),
                                                               response([{"id": 2}])]) as get:
            pages = list(client.pages(PREFIX, {"state": "all"}))
        self.assertEqual([page[0][0]["id"] for page in pages], [1, 2])
        self.assertEqual([call.kwargs["params"]["page"] for call in get.call_args_list], [1, 3])

    def test_full_final_page_needs_no_extra_request(self):
        client = self.client()
        with patch.object(client.session, "get", return_value=response([{"id": i} for i in range(100)])) as get:
            self.assertEqual(len(list(client.pages(PREFIX))), 1)
        get.assert_called_once()

    def test_link_pagination_when_next_header_absent(self):
        client = self.client()
        link = client.url + "/" + PREFIX + "?page=7&per_page=100"
        with patch.object(client.session, "get", side_effect=[
                response([{"id": 1}], next_page=None, links={"next": {"url": link}}),
                response([{"id": 2}], next_page=None)]) as get:
            self.assertEqual(len(list(client.pages(PREFIX))), 2)
        self.assertEqual(get.call_args.kwargs["params"]["page"], 7)

    def test_untrusted_link_never_followed(self):
        client = self.client()
        with patch.object(client.session, "get", return_value=response(
                [{"id": 1}], next_page=None, links={"next": {"url": "https://other.test/?page=2"}})) as get:
            with self.assertRaises(signal.CollectionError):
                list(client.pages(PREFIX))
        get.assert_called_once()

    def test_repeated_ids_or_nonadvancing_headers_fail(self):
        client = self.client()
        cases = ([response([{"id": 1}], next_page="2"), response([{"id": 1}])],
                 [response([{"id": 1}], next_page="1")],
                 [response([{"id": 1}], next_page="invalid")],
                 [response([], next_page="2")])
        for responses in cases:
            with self.subTest(responses=len(responses)), \
                    patch.object(client.session, "get", side_effect=responses), self.assertRaises(signal.CollectionError):
                list(client.pages(PREFIX))

    def test_malformed_list_is_sanitized(self):
        client = self.client()
        for payload in ({"body": PRIVATE}, [PRIVATE], [{"id": {"body": PRIVATE}}]):
            with patch.object(client.session, "get", return_value=response(payload)), \
                    self.assertRaises(signal.CollectionError) as error:
                list(client.pages(PREFIX))
            self.assertNotIn(PRIVATE, str(error.exception))

    def test_projection_drops_bodies_at_every_nested_level(self):
        client = self.client()
        position = {"new_path": "src/file.py", "new_line": 7, "body": PRIVATE,
                    "line_range": {"start": {"new_line": 7, "body": PRIVATE},
                                   "end": {"new_line": 9, "text": PRIVATE}, "diff": PRIVATE},
                    "head_sha": {"description": PRIVATE}}
        raw = mr(reviewers=[actor("requested", description=PRIVATE)],
                 diff_refs={"diff": PRIVATE}, labels=[PRIVATE], pipeline={"body": PRIVATE})
        result = signal.request_metadata(raw, PROJECT)
        discussion = {"id": "d1", "individual_note": False, "body": PRIVATE,
                      "notes": [note(position=position), note(2, system=True)]}
        with patch.object(client.session, "get", side_effect=[response([discussion]), response({
                "approved_by": [{"user": actor("approver"), "body": PRIVATE}],
                "description": PRIVATE, "approvals_required": 1})]):
            result["discussions"] = signal.fetch_discussions(client, PREFIX)
            result["approvals"] = signal.fetch_approvals(client, PREFIX)
        self.assertNotIn(PRIVATE, json.dumps(result))
        projected = result["discussions"][0]["notes"][0]["position"]
        self.assertEqual(projected["line_range"], {"start": {"new_line": 7}, "end": {"new_line": 9}})
        self.assertNotIn("head_sha", projected)
        self.assertTrue(result["discussions"][0]["notes"][1]["system"])
        self.assertEqual(result["requested_reviewers"], [{"username": "requested"}])

    def test_discussion_pagination_includes_all_notes_and_system_notes(self):
        client = self.client()
        with patch.object(client.session, "get", side_effect=[
                response([{"id": "d1", "notes": [note(), note(2, system=True)]}], next_page="2"),
                response([{"id": "d2", "notes": [note(3, created_at=OLD), note(4)]}])]):
            discussions = signal.fetch_discussions(client, PREFIX)
        self.assertEqual(sum(len(item["notes"]) for item in discussions), 4)

    def test_optional_approvals_only_404_405_unavailable(self):
        client = self.client()
        for status in (404, 405):
            with patch.object(client.session, "get", return_value=response(status=status)):
                self.assertIsNone(signal.fetch_approvals(client, PREFIX))
                with self.assertRaises(signal.CollectionError):
                    signal.fetch_discussions(client, PREFIX)
        for status in (301, 302, 401, 403, 429, 500):
            with patch.object(client.session, "get", return_value=response(status=status)), \
                    self.assertRaises(signal.CollectionError):
                signal.fetch_approvals(client, PREFIX)

    def test_empty_approval_snapshot_is_not_unavailable(self):
        client = self.client()
        with patch.object(client.session, "get", return_value=response({"approved_by": []})):
            self.assertEqual(signal.fetch_approvals(client, PREFIX), {"approved_by": []})

    def test_malformed_metadata_fails_closed(self):
        client = self.client()
        for payload in (None, {}, {"approved_by": [PRIVATE]}, {"approved_by": [{"user": PRIVATE}]}):
            with patch.object(client.session, "get", return_value=response(payload)), \
                    self.assertRaises(signal.CollectionError):
                signal.fetch_approvals(client, PREFIX)
        for payload in ({**mr(), "iid": None}, mr(state=None), mr(reviewers=PRIVATE)):
            with self.assertRaises(signal.CollectionError):
                signal.request_metadata(payload, PROJECT)
        with self.assertRaises(signal.CollectionError):
            signal.note_metadata({"id": 1, "body": PRIVATE})

    def test_roles_windows_and_current_approval_deduplication(self):
        item = record(created_at=OLD)
        item["discussions"] = [{"notes": [signal.note_metadata(raw) for raw in (
            note(), note(2), note(3, "owner"), note(4, "system", system=True),
            note(5, "old", created_at=OLD, updated_at=RECENT), note(6, "future", created_at=FUTURE),
            note(7, "bot", author=actor("bot", bot=True)),
        )]}]
        item["approvals"] = {"approved_by": [actor("reviewer"), actor("approver"), actor("approver"), actor("owner")]}
        result = signal.aggregate([item], 30, NOW)
        self.assertEqual(result["request_author_total"], {"owner": 1})
        self.assertEqual(result["merged_author_total"], {"owner": 1})
        self.assertEqual(result["merger_total"], {"merger": 1})
        self.assertEqual(result["comment_total"], {"reviewer": 2, "owner": 1, "bot": 1})
        self.assertEqual(result["review_total"], {"reviewer": 1, "approver": 1, "owner": 1})
        self.assertEqual(result["reviewer_total"], {"reviewer": 1, "approver": 1, "bot": 1})
        self.assertNotIn("requested", result["reviewer_total"])

    def test_reviewer_total_counts_distinct_mrs_not_comments(self):
        items = [record(iid=1), record(iid=2)]
        for item in items:
            item["discussions"] = [{"notes": [signal.note_metadata(note()), signal.note_metadata(note(2))]}]
        self.assertEqual(signal.aggregate(items, 30, NOW)["reviewer_total"], {"reviewer": 2})

    def test_actual_merger_fallback_never_infers_owner(self):
        items = [record(merged_by=None, merge_user=actor("fallback")),
                 record(iid=2, merged_by=None), record(iid=3, merged_at=OLD),
                 record(iid=4, state="closed"), record(iid=5, merged_at=FUTURE)]
        result = signal.aggregate(items, 30, NOW)
        self.assertEqual(result["merger_total"], {"fallback": 1})
        self.assertEqual(result["merged_author_total"], {"owner": 4})
        preferred = signal.request_metadata(mr(merge_user=actor("fallback")), PROJECT)
        self.assertEqual(preferred["merged_by"]["username"], "merger")

    def test_identity_email_fallback_no_display_name_or_id_counting(self):
        self.assertEqual(signal.person_key({"email": "a@example.test"}), "a@example.test")
        self.assertEqual(signal.person_key({"username": "a", "email": "a@example.test"}), "a")
        self.assertIsNone(signal.person_key({"id": 1, "name": "Display Name"}))

    def test_timestamp_boundaries_and_invalid_values(self):
        cutoff = NOW - dt.timedelta(days=30)
        for timestamp in (cutoff.isoformat(), NOW.isoformat(), RECENT, "2026-09-10T01:02:03+02:00"):
            self.assertTrue(signal.in_window(timestamp, cutoff, NOW))
        for timestamp in (None, OLD, FUTURE):
            self.assertFalse(signal.in_window(timestamp, cutoff, NOW))
        with self.assertRaises(signal.CollectionError) as error:
            signal.in_window(PRIVATE, cutoff, NOW)
        self.assertNotIn(PRIVATE, str(error.exception))

    def collect_mocked(self, limit=0, approvals_status=200):
        client = self.client()
        updated = [mr(created_at=OLD), mr(2)]

        def route(url, params=None, **kwargs):
            endpoint = url.removeprefix(client.url + "/")
            if endpoint == PREFIX + "/repository/commits":
                return response([{"id": "sha", "author_email": "commit@example.test", "message": PRIVATE}])
            if endpoint == PREFIX + "/issues":
                return response([{"id": 1, "created_at": RECENT, "author": actor("issue-author"), "description": PRIVATE}])
            if endpoint == PREFIX + "/merge_requests":
                self.assertEqual(params["state"], "all")
                if "created_after" in params:
                    return response([mr(2)])
                self.assertIn("updated_after", params)
                return response(updated)
            if endpoint.endswith("/discussions"):
                return response([{"id": "d1", "notes": [note()]}])
            if endpoint.endswith("/approvals"):
                return response({"approved_by": [{"user": actor("approver")}]}, status=approvals_status)
            if endpoint in (PREFIX + "/merge_requests/1", PREFIX + "/merge_requests/2"):
                return response(updated[int(endpoint.rsplit("/", 1)[1]) - 1])
            self.fail("Unexpected mocked endpoint")

        with patch.object(signal, "load_env", return_value=CONFIG), \
                patch.object(signal, "GitLabClient", return_value=client), \
                patch.object(signal.dt, "datetime", FrozenDateTime), \
                patch.object(client.session, "get", side_effect=route), \
                patch.object(client.session, "close") as close:
            result = signal.collect_signal([PROJECT, PROJECT], 30, limit)
        close.assert_called_once()
        return result

    def test_collection_schema_legacy_created_window_updated_records(self):
        result = self.collect_mocked()
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["window_days"], 30)
        self.assertEqual(result["collected_at"], NOW.isoformat())
        self.assertEqual(result["commits"], {"commit@example.test": 1})
        self.assertEqual(result["mrs"], {"owner": 1})
        self.assertEqual(result["issues"], {"issue-author": 1})
        self.assertEqual(result["request_author_total"], {"owner": 2})
        self.assertEqual(len(result["requests"]), 2)
        self.assertEqual(result["truncated_projects"], [])
        self.assertEqual(result["unavailable"], [])
        self.assertNotIn(PRIVATE, json.dumps(result))

    def test_cap_only_applies_to_records_and_reports_truncation(self):
        result = self.collect_mocked(limit=1)
        self.assertEqual(len(result["requests"]), 1)
        self.assertEqual(result["truncated_projects"], [PROJECT])
        self.assertEqual(result["mrs"], {"owner": 1})
        self.assertEqual(self.collect_mocked(limit=2)["truncated_projects"], [])

    def test_unavailable_is_explicit_not_false_zero(self):
        result = self.collect_mocked(approvals_status=404)
        self.assertEqual(len(result["unavailable"]), 2)
        self.assertIsNone(result["requests"][0]["approvals"])
        self.assertEqual(result["unavailable"][0]["feature"], "approvals")
        self.assertEqual(result["review_total"], {})
        self.assertEqual(result["reviewer_total"], {"reviewer": 2})

    def test_empty_project_success(self):
        client = self.client()
        with patch.object(signal, "load_env", return_value=CONFIG), \
                patch.object(signal, "GitLabClient", return_value=client), \
                patch.object(client.session, "get", return_value=response([])):
            result = signal.collect_signal([PROJECT], 30)
        self.assertEqual(result["requests"], [])
        self.assertEqual(result["mrs"], {})
        self.assertEqual(result["unavailable"], [])
        self.assertEqual(result["projects"], [PROJECT])

    def test_skip_commits_is_unknown_and_does_not_call_commit_api(self):
        client = self.client()
        with patch.object(signal, "load_env", return_value=CONFIG), \
                patch.object(signal, "GitLabClient", return_value=client), \
                patch.object(client.session, "get", return_value=response([])) as get:
            result = signal.collect_signal([PROJECT], 30, skip_commits=True)
        self.assertIsNone(result["commits"])
        self.assertEqual(result["mrs"], {})
        self.assertEqual(result["projects"], [PROJECT])
        self.assertEqual(result["unavailable"][0]["feature"], "commits")
        self.assertEqual(get.call_count, 3)
        self.assertTrue(all("/repository/commits" not in call.args[0] for call in get.call_args_list))

    def test_limit_with_next_header_stops_and_marks_truncation(self):
        client = self.client()
        with patch.object(signal, "load_env", return_value=CONFIG), \
                patch.object(signal, "GitLabClient", return_value=client), \
                patch.object(signal.dt, "datetime", FrozenDateTime), \
                patch.object(client.session, "get", side_effect=[
                    response([]), response([]), response([]),
                    response([mr()], next_page="2"), response(mr()),
                    response([]), response({"approved_by": []}),
                ]) as get:
            result = signal.collect_signal([PROJECT], 30, 1)
        self.assertEqual(result["truncated_projects"], [PROJECT])
        self.assertEqual(get.call_count, 7)

    def test_network_and_json_errors_are_sanitized(self):
        client = self.client()
        for exception in (requests.ConnectionError(PRIVATE), requests.Timeout(PRIVATE), requests.exceptions.SSLError(PRIVATE)):
            with patch.object(client.session, "get", side_effect=exception), \
                    self.assertRaises(signal.CollectionError) as error:
                client.get(PREFIX)
            self.assertNotIn(PRIVATE, str(error.exception))
        invalid = response()
        invalid.json.side_effect = ValueError(PRIVATE)
        with patch.object(client.session, "get", return_value=invalid), \
                self.assertRaises(signal.CollectionError) as error:
            client.get(PREFIX)
        self.assertNotIn(PRIVATE, str(error.exception))

    def test_failed_later_page_preserves_previous_output(self):
        client = self.client()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "signal.json"
            path.write_text("previous", encoding="utf-8")
            stderr = io.StringIO()
            with patch.object(sys, "argv", ["script", "--project", PROJECT, "--json-out", str(path)]), \
                    patch.object(signal, "load_env", return_value=CONFIG), \
                    patch.object(signal, "GitLabClient", return_value=client), \
                    patch.object(client.session, "get", side_effect=[
                        response([{"id": "a", "author_email": "a@test"}], next_page="2"), response(status=500)]), \
                    contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(signal.main(), 1)
            self.assertEqual(path.read_text(encoding="utf-8"), "previous")
            self.assertNotIn(PRIVATE, stderr.getvalue())

    def test_atomic_write_failure_preserves_output_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "signal.json"
            path.write_text("previous", encoding="utf-8")
            with patch.object(signal.os, "replace", side_effect=OSError(PRIVATE)), self.assertRaises(OSError):
                signal.write_json(path, {"schema_version": 2})
            self.assertEqual(path.read_text(encoding="utf-8"), "previous")
            self.assertEqual(list(Path(directory).iterdir()), [path])

    def test_cli_write_failure_message_is_sanitized(self):
        result = self.collect_mocked()
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["script", "--project", PROJECT, "--json-out", "unused.json"]), \
                patch.object(signal, "collect_signal", return_value=result), \
                patch.object(signal, "write_json", side_effect=OSError(PRIVATE)), \
                contextlib.redirect_stderr(stderr):
            self.assertEqual(signal.main(), 1)
        self.assertNotIn(PRIVATE, stderr.getvalue())

    def test_cli_flags_success_output_and_defaults(self):
        result = self.collect_mocked()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "signal.json"
            env = Path(directory) / "custom.env"
            output = io.StringIO()
            with patch.object(sys, "argv", ["script", "--project", PROJECT, "--project", "second",
                                           "--since-days", "30", "--env-file", str(env), "--json-out", str(path)]), \
                    patch.object(signal, "collect_signal", return_value=result) as collect, \
                    contextlib.redirect_stdout(output):
                self.assertEqual(signal.main(), 0)
            collect.assert_called_once_with([PROJECT, "second"], 30, 0, env, skip_commits=False)
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), result)
            self.assertNotIn(PRIVATE, output.getvalue())

    def test_cli_rejects_invalid_limits(self):
        for flag, value in (("--since-days", "0"), ("--limit-per-project", "-1")):
            with patch.object(sys, "argv", ["script", "--project", PROJECT, flag, value]), \
                    contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                signal.main()
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()