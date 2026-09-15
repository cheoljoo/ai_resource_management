"""Offline GitHub metadata/privacy regression tests; gh is always mocked."""
import contextlib
import datetime as dt
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import github_signal as signal


NOW = dt.datetime(2026, 9, 15, tzinfo=dt.timezone.utc)
RECENT = "2026-09-10T01:02:03Z"
OLD = "2025-01-01T00:00:00Z"
FUTURE = "2027-01-01T00:00:00Z"
SECRET = "PRIVATE BODY MUST NEVER ESCAPE"
REPO = "example/project"
ROOT = f"repos/{REPO}"


def user(login):
    return {"id": 42, "login": login, "body": SECRET, "profile": {"description": SECRET}}


def pr(number=1, **extra):
    return {"id": number, "number": number, "state": "closed", "created_at": RECENT,
            "updated_at": RECENT, "merged": True, "merged_at": RECENT,
            "merged_by": user("merger"), "user": user("owner"), "title": SECRET,
            "body": SECRET, "description": SECRET,
            "requested_reviewers": [user("requested-only")], **extra}


def review(identity, login="reviewer", **extra):
    return {"id": identity, "user": user(login), "state": "APPROVED",
            "submitted_at": RECENT, "body": SECRET, **extra}


def comment(identity, login="reviewer", **extra):
    return {"id": identity, "user": user(login), "created_at": RECENT,
            "updated_at": RECENT, "body": SECRET, "diff_hunk": SECRET, **extra}


class GitHubSignalTests(unittest.TestCase):
    def setUp(self):
        self.routes = {}
        self.calls = []
        self.runner = patch.object(signal.subprocess, "run", side_effect=self.fake_gh).start()
        self.addCleanup(patch.stopall)

    def fake_gh(self, command, **kwargs):
        self.assertEqual(command[:2], ["gh", "api"])
        self.assertTrue(kwargs["capture_output"])
        self.assertTrue(kwargs["text"])
        self.assertEqual(kwargs["env"]["GH_PROMPT_DISABLED"], "1")
        endpoint = urlsplit(command[2])
        query = parse_qs(endpoint.query)
        self.calls.append((endpoint.path, query))
        page = int(query.get("page", [1])[0])
        key = (endpoint.path, page)
        if key not in self.routes:
            self.fail(f"Unexpected mocked API endpoint: {key}")
        return Mock(returncode=0, stdout=json.dumps(self.routes[key]), stderr=SECRET)

    def setup_repo(self, prs=None, repo=REPO):
        root = f"repos/{repo}"
        self.routes[(f"{root}/commits", 1)] = []
        self.routes[(f"{root}/issues", 1)] = []
        self.routes[(f"{root}/pulls", 1)] = prs if prs is not None else [pr()]
        for raw in prs if prs is not None else [pr()]:
            self.detail(raw, repo)

    def detail(self, raw, repo=REPO):
        root = f"repos/{repo}"
        number = raw["number"]
        self.routes[(f"{root}/pulls/{number}", 1)] = raw
        for path in (f"pulls/{number}/reviews", f"pulls/{number}/comments", f"issues/{number}/comments"):
            self.routes[(f"{root}/{path}", 1)] = []

    def collect(self, **kwargs):
        return signal.collect_signal(REPO, now=NOW, **kwargs)

    def run_main(self, argv):
        with patch.object(signal.dt, "datetime", wraps=dt.datetime) as clock:
            clock.now.return_value = NOW
            return signal.main(argv)

    def test_roles_history_and_individual_event_windows(self):
        self.setup_repo([pr(created_at=OLD)])
        self.routes[(f"{ROOT}/pulls/1/reviews", 1)] = [
            review(1), review(2, state="CHANGES_REQUESTED"),
            review(3, "dismissed", state="DISMISSED"),
            review(4, "old", submitted_at=OLD),
            review(5, "pending", state="PENDING", submitted_at=None),
            review(6, "owner", state="COMMENTED"),
            review(7, "future", submitted_at=FUTURE),
        ]
        self.routes[(f"{ROOT}/pulls/1/comments", 1)] = [
            comment(1), comment(2), comment(3, "owner"),
            comment(4, "old", created_at=OLD), comment(5, "deleted", user=None),
        ]
        self.routes[(f"{ROOT}/issues/1/comments", 1)] = [
            comment(1, "discussion"), comment(2), comment(3, "future", created_at=FUTURE),
        ]
        result = self.collect()
        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["window_days"], 180)
        self.assertTrue(result["metadata_only"])
        self.assertEqual(result["collected_at"], "2026-09-15T00:00:00Z")
        self.assertEqual(result["prs"], {})
        self.assertEqual(result["request_author_total"], {"owner": 1})
        self.assertEqual(result["reviewer_total"], {"reviewer": 1, "dismissed": 1, "discussion": 1})
        self.assertEqual(result["review_total"], {"reviewer": 2, "dismissed": 1, "owner": 1})
        self.assertEqual(result["comment_total"], {"reviewer": 3, "owner": 1, "discussion": 1})
        self.assertEqual(result["merged_author_total"], {"owner": 1})
        self.assertEqual(result["merger_total"], {"merger": 1})
        request = result["requests"][0]
        self.assertEqual([r["state"] for r in request["reviews"]][:3],
                         ["APPROVED", "CHANGES_REQUESTED", "DISMISSED"])
        self.assertEqual(request["requested_reviewers"][0]["login"], "requested-only")
        self.assertNotIn(SECRET, json.dumps(result))

    def test_unknown_and_unmerged_never_infer_merger(self):
        self.setup_repo([pr(1, merged_by=None), pr(2, merged=False, merged_at=None),
                         pr(3, merged_at=OLD), pr(4, merged=None)])
        result = self.collect()
        self.assertEqual(result["merged_author_total"], {"owner": 2})
        self.assertEqual(result["merger_total"], {})
        self.assertFalse(result["requests"][0]["merger_known"])
        self.assertIsNone(result["requests"][3]["merged"])

    def test_nested_body_exclusion_and_comment_coordinates(self):
        raw = comment(9, path="src/file.c", line=12, start_line=10, side="RIGHT",
                      in_reply_to_id=8, pull_request_review_id=7, resolved=True,
                      resolved_by=user("resolver"),
                      resolution={"resolved": True, "resolved_by": user("resolver"), "body": SECRET},
                      reactions={"body": SECRET})
        metadata = signal.comment_metadata(raw)
        self.assertEqual(metadata["in_reply_to_id"], 8)
        self.assertEqual(metadata["line"], 12)
        self.assertTrue(metadata["resolution"]["resolved"])
        self.assertNotIn(SECRET, json.dumps(metadata))
        self.assertNotIn("resolved", signal.comment_metadata(comment(1)))
        malicious = signal.comment_metadata(comment(2, path={"body": SECRET}, line=[SECRET]))
        self.assertNotIn("path", malicious)
        self.assertNotIn("line", malicious)

    def test_legacy_counters_have_explicit_window_and_issues_exclude_prs(self):
        self.setup_repo([pr(1), pr(2, created_at=OLD)])
        self.routes[(f"{ROOT}/commits", 1)] = [
            {"sha": "a", "commit": {"author": {"email": "one@example.test"}, "message": SECRET}},
            {"sha": "b", "commit": {"author": {"email": "one@example.test"}}},
        ]
        self.routes[(f"{ROOT}/issues", 1)] = [
            {"id": 1, "created_at": RECENT, "user": user("issue-author"), "body": SECRET},
            {"id": 2, "created_at": OLD, "updated_at": RECENT, "user": user("old")},
            {"id": 3, "created_at": RECENT, "user": user("pr-owner"), "pull_request": {}},
        ]
        result = self.collect()
        self.assertEqual(result["commits"], {"one@example.test": 2})
        self.assertEqual(result["prs"], {"owner": 1})
        self.assertEqual(result["issues"], {"issue-author": 1})
        cutoff = signal._iso(NOW - dt.timedelta(days=180))
        for path, query in self.calls:
            if path.endswith(("/commits", "/issues")):
                self.assertEqual(query["since"], [cutoff])
            if path.endswith("/commits"):
                self.assertEqual(query["until"], [signal._iso(NOW)])

    def test_manual_pagination_every_list_endpoint(self):
        for path, identity in (("commits", "sha"), ("pulls", "number"),
                               ("issues", "id"), ("pulls/1/reviews", "id"),
                               ("pulls/1/comments", "id"), ("issues/1/comments", "id")):
            with self.subTest(path=path):
                self.routes[(f"{ROOT}/{path}", 1)] = [{identity: n} for n in range(100)]
                self.routes[(f"{ROOT}/{path}", 2)] = [{identity: 100}]
                self.assertEqual(len(list(signal._items(f"{ROOT}/{path}", identity))), 101)
                self.assertEqual(self.calls[-1][1], {"per_page": ["100"], "page": ["2"]})

    def test_full_page_then_empty_and_repeated_page(self):
        endpoint = f"{ROOT}/issues"
        self.routes[(endpoint, 1)] = [{"id": n} for n in range(100)]
        self.routes[(endpoint, 2)] = []
        self.assertEqual(len(list(signal._items(endpoint))), 100)
        self.routes[(endpoint, 2)] = self.routes[(endpoint, 1)]
        with self.assertRaisesRegex(signal.CollectionError, "pagination"):
            list(signal._items(endpoint))

    def test_updated_window_stops_and_default_selects_beyond_first_page(self):
        first = [pr(n) for n in range(1, 101)]
        self.setup_repo(first)
        self.routes[(f"{ROOT}/pulls", 2)] = [pr(101), pr(102, updated_at=OLD), pr(103)]
        self.detail(pr(101))
        result = self.collect()
        self.assertEqual(len(result["requests"]), 101)
        self.assertEqual(result["truncated_repos"], [])
        query = next(query for path, query in self.calls if path == f"{ROOT}/pulls")
        self.assertEqual(query["sort"], ["updated"])
        self.assertEqual(query["direction"], ["desc"])
        self.assertEqual(query["state"], ["all"])
        self.assertFalse(any(path.endswith("/102") or path.endswith("/103") for path, _ in self.calls))

    def test_explicit_cap_preserves_legacy_pr_count_and_reports_actual_truncation(self):
        self.setup_repo([pr(1), pr(2)])
        result = self.collect(limit_per_repo=1)
        self.assertEqual(len(result["requests"]), 1)
        self.assertEqual(result["prs"], {"owner": 2})
        self.assertEqual(result["truncated_repos"], [REPO])
        self.assertFalse(any(path.endswith("/2") for path, _ in self.calls))
        self.setup_repo([pr(1)])
        self.assertEqual(self.collect(limit_per_repo=1)["truncated_repos"], [])

    def test_inclusive_cutoff_and_future_exclusion(self):
        cutoff = NOW - dt.timedelta(days=180)
        self.assertTrue(signal.in_window(signal._iso(cutoff), cutoff, NOW))
        self.assertTrue(signal.in_window(signal._iso(NOW), cutoff, NOW))
        self.assertFalse(signal.in_window(FUTURE, cutoff, NOW))
        self.assertFalse(signal.in_window(None, cutoff, NOW))
        with self.assertRaises(signal.CollectionError):
            signal.in_window(SECRET, cutoff, NOW)

    def test_subprocess_errors_and_invalid_json_are_sanitized(self):
        errors = [FileNotFoundError(SECRET), OSError(SECRET),
                  subprocess.TimeoutExpired("gh", 60, output=SECRET, stderr=SECRET),
                  UnicodeError(SECRET)]
        for error in errors:
            with self.subTest(error=type(error).__name__):
                self.runner.side_effect = error
                with self.assertRaises(signal.CollectionError) as raised:
                    signal._gh_json("endpoint")
                self.assertNotIn(SECRET, str(raised.exception))
        self.runner.side_effect = None
        for response in (Mock(returncode=1, stdout=SECRET, stderr=SECRET),
                         Mock(returncode=0, stdout=SECRET, stderr=SECRET),
                         Mock(returncode=0, stdout="", stderr=SECRET)):
            self.runner.return_value = response
            with self.assertRaises(signal.CollectionError) as raised:
                signal._gh_json("endpoint")
            self.assertNotIn(SECRET, str(raised.exception))

    def test_invalid_response_shapes_fail_closed(self):
        for rows in ({"body": SECRET}, [None], [{"body": SECRET}], [{"id": {"body": SECRET}}]):
            self.routes[("endpoint", 1)] = rows
            with self.subTest(rows=type(rows).__name__):
                with self.assertRaises(signal.CollectionError):
                    list(signal._items("endpoint"))
        for raw in (None, [], pr(number=2), pr(state="invalid"), pr(merged="false")):
            with self.assertRaises(signal.CollectionError):
                signal.request_metadata(raw, REPO, 1)

    def test_cli_multi_repo_atomic_metadata_output(self):
        self.setup_repo()
        self.setup_repo(repo="example/second")
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "signal.json"
            output.write_text("previous", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = self.run_main(["--repo", REPO, "--repo", "example/second",
                                        "--repo", REPO, "--json-out", str(output)])
            self.assertEqual(status, 0)
            result = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(result["requests"]), 2)
            self.assertEqual(result["prs"], {"owner": 2})
            self.assertEqual(result["request_author_total"], {"owner": 2})
            self.assertNotIn(SECRET, output.read_text() + stdout.getvalue() + stderr.getvalue())
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_cli_late_failure_keeps_existing_output(self):
        self.setup_repo()
        self.routes[(f"{ROOT}/pulls/1/reviews", 1)] = {"body": SECRET}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "signal.json"
            output.write_text("previous", encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                status = self.run_main(["--repo", REPO, "--json-out", str(output)])
            self.assertEqual(status, 1)
            self.assertEqual(output.read_text(), "previous")
            self.assertNotIn(SECRET, stdout.getvalue() + stderr.getvalue())

    def test_cli_subprocess_and_json_failures_do_not_overwrite_output(self):
        for response in (FileNotFoundError(SECRET),
                         subprocess.TimeoutExpired("gh", 60, output=SECRET, stderr=SECRET),
                         Mock(returncode=1, stdout=SECRET, stderr=SECRET),
                         Mock(returncode=0, stdout=SECRET, stderr=SECRET)):
            with self.subTest(response=type(response).__name__), tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / "signal.json"
                output.write_text("previous", encoding="utf-8")
                self.runner.side_effect = response if isinstance(response, Exception) else None
                self.runner.return_value = response
                stdout, stderr = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    status = self.run_main(["--repo", REPO, "--json-out", str(output)])
                self.assertEqual(status, 1)
                self.assertEqual(output.read_text(), "previous")
                self.assertNotIn(SECRET, stdout.getvalue() + stderr.getvalue())
                self.assertNotIn("Traceback", stderr.getvalue())

    def test_second_repository_failure_does_not_publish_partial_results(self):
        self.setup_repo()
        self.routes[("repos/example/second/commits", 1)] = {"message": SECRET}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "signal.json"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                status = self.run_main(["--repo", REPO, "--repo", "example/second", "--json-out", str(output)])
            self.assertEqual(status, 1)
            self.assertFalse(output.exists())

    def test_reviewer_counts_distinct_prs_not_events_or_requested_membership(self):
        self.setup_repo([pr(1), pr(2)])
        for number in (1, 2):
            self.routes[(f"{ROOT}/pulls/{number}/reviews", 1)] = [review(1), review(2)]
            self.routes[(f"{ROOT}/issues/{number}/comments", 1)] = [comment(1), comment(2, "OWNER")]
        result = self.collect()
        self.assertEqual(result["reviewer_total"], {"reviewer": 2})
        self.assertEqual(result["review_total"], {"reviewer": 4})

    def test_atomic_replace_failure_preserves_output_and_cleans_temp(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "signal.json"
            output.write_text("previous", encoding="utf-8")
            with patch.object(signal.os, "replace", side_effect=OSError(SECRET)):
                with self.assertRaises(signal.CollectionError) as raised:
                    signal._write_json(output, {"metadata_only": True})
            self.assertNotIn(SECRET, str(raised.exception))
            self.assertEqual(output.read_text(), "previous")
            self.assertEqual(len(list(Path(directory).iterdir())), 1)

    def test_invalid_arguments_do_not_call_gh(self):
        for kwargs in ({"since_days": 0}, {"limit_per_repo": -1}, {"since_days": 10**20}):
            with self.assertRaises(signal.CollectionError):
                self.collect(**kwargs)
        with self.assertRaises(signal.CollectionError):
            signal.collect_signal("invalid?token=" + SECRET)
        self.runner.assert_not_called()


if __name__ == "__main__":
    unittest.main()