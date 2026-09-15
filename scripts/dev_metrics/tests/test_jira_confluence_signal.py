"""실제 자격증명/네트워크 없이 수집 계약과 실패 처리를 검증한다."""
import contextlib
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
import jira_confluence_signal as signal


SETTINGS = {
    "JIRA_URL": "https://jira.example.test/jira/",
    "JIRA_PERSONAL_TOKEN": "test-jira-secret",
    "CONFLUENCE_URL": "https://wiki.example.test/main",
    "CONFLUENCE_PERSONAL_TOKEN": "test-wiki-secret",
}


class JiraConfluenceTests(unittest.TestCase):
    def test_env_parsing_and_environment_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text('export JIRA_PERSONAL_TOKEN="abc=${TOKEN}#def"\nJIRA_URL=file\n', encoding="utf-8")
            with patch.dict(os.environ, {"JIRA_URL": "environment"}, clear=True):
                settings = signal.load_settings(path)
        self.assertEqual(settings["JIRA_PERSONAL_TOKEN"], "abc=${TOKEN}#def")
        self.assertEqual(settings["JIRA_URL"], "environment")

    def test_missing_env_can_use_process_environment(self):
        with patch.dict(os.environ, SETTINGS, clear=True):
            self.assertEqual(signal.load_settings(Path("/missing/env")), SETTINGS)

    def test_roster_snapshot_and_service_specific_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roster.json"
            path.write_text(json.dumps({"people": {
                "one@example.test": {"jira_total_180d": 100},
                "two@example.test": {"jira_user": "jira-two", "confluence_user": "wiki-two"},
            }}), encoding="utf-8")
            roster = signal.load_roster(path, None)
        self.assertEqual(roster["one@example.test"], {"jira_user": "one", "confluence_user": "one"})
        self.assertEqual(roster["two@example.test"]["confluence_user"], "wiki-two")

    def test_person_replaces_roster_and_deduplicates(self):
        roster = signal.load_roster(Path("/missing/roster"), ["one@example.test", "one@example.test"])
        self.assertEqual(list(roster), ["one@example.test"])

    def test_invalid_roster_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roster.json"
            for data in ({"people": {}}, {"people": {"one": {"jira_user": None}}}, []):
                with self.subTest(data=data):
                    path.write_text(json.dumps(data), encoding="utf-8")
                    with self.assertRaises(signal.CollectionError):
                        signal.load_roster(path, None)

    def test_pat_context_path_timeout_and_tls(self):
        client = signal.AtlassianClient("JIRA", SETTINGS)
        self.addCleanup(client.session.close)
        with patch.object(client.session, "get", return_value=Mock(status_code=200, json=lambda: {"total": 7})) as get:
            self.assertEqual(signal.jira_count(client, "query"), 7)
        self.assertEqual(client.session.headers["Authorization"], "Bearer test-jira-secret")
        get.assert_called_once_with(
            "https://jira.example.test/jira/rest/api/2/search",
            params={"jql": "query", "maxResults": 0, "fields": "key"},
            timeout=30, verify=True, allow_redirects=False,
        )

    def test_ssl_verify_explicit_false_and_invalid(self):
        self.assertFalse(signal.ssl_verify({"JIRA_SSL_VERIFY": "false"}, "JIRA"))
        with self.assertRaises(signal.CollectionError):
            signal.ssl_verify({"JIRA_SSL_VERIFY": "typo"}, "JIRA")

    def test_missing_credentials_fail_without_network(self):
        with self.assertRaisesRegex(signal.CollectionError, "JIRA_PERSONAL_TOKEN"):
            signal.AtlassianClient("JIRA", {"JIRA_URL": SETTINGS["JIRA_URL"]})

    def test_http_failures_and_redirects_never_echo_response(self):
        client = signal.AtlassianClient("JIRA", SETTINGS)
        self.addCleanup(client.session.close)
        for status in (301, 401, 403, 429, 500):
            with self.subTest(status=status), patch.object(
                client.session, "get", return_value=Mock(status_code=status, text="test-jira-secret")
            ):
                with self.assertRaises(signal.CollectionError) as error:
                    client.get("/rest/api/2/search", {})
                self.assertIn(str(status), str(error.exception))
                self.assertNotIn("test-jira-secret", str(error.exception))

    def test_network_errors_are_sanitized(self):
        client = signal.AtlassianClient("JIRA", SETTINGS)
        self.addCleanup(client.session.close)
        with patch.object(client.session, "get", side_effect=requests.ConnectionError("test-jira-secret")):
            with self.assertRaises(signal.CollectionError) as error:
                client.get("/rest/api/2/search", {})
        self.assertNotIn("test-jira-secret", str(error.exception))

    def test_invalid_json_is_rejected(self):
        client = signal.AtlassianClient("JIRA", SETTINGS)
        self.addCleanup(client.session.close)
        response = Mock(status_code=200)
        response.json.side_effect = ValueError("test-jira-secret")
        with patch.object(client.session, "get", return_value=response):
            with self.assertRaisesRegex(signal.CollectionError, "JSON"):
                client.get("/rest/api/2/search", {})

    def test_jira_total_zero_and_invalid(self):
        client = Mock()
        client.get.return_value = {"total": 0}
        self.assertEqual(signal.jira_count(client, "query"), 0)
        for total in (None, -1, "3", True):
            client.get.return_value = {"total": total}
            with self.assertRaises(signal.CollectionError):
                signal.jira_count(client, "query")

    def test_confluence_paginates_even_when_server_caps_page_size(self):
        client = Mock()
        client.get.side_effect = [
            {"results": [{"id": str(i)} for i in range(50)], "_links": {"next": "https://untrusted.test/?start=50"}},
            {"results": [{"id": "49"}, {"id": "50"}], "_links": {}},
        ]
        self.assertEqual(signal.confluence_count(client, "query"), 51)
        self.assertEqual(client.get.call_args_list[1].args, (
            "/rest/api/content/search", {"cql": "query", "start": 50, "limit": 100},
        ))

    def test_confluence_zero_invalid_and_stalled_pages(self):
        client = Mock()
        client.get.return_value = {"results": [], "_links": {}}
        self.assertEqual(signal.confluence_count(client, "query"), 0)
        for response in ({}, {"results": [{}]}, {"results": [], "_links": {"next": "next"}}):
            client.get.return_value = response
            with self.assertRaises(signal.CollectionError):
                signal.confluence_count(client, "query")
        client.get.return_value = {"results": [{"id": "one"}], "_links": {"next": "next"}}
        with self.assertRaises(signal.CollectionError):
            signal.confluence_count(client, "query")

    def test_collection_schema_window_and_query_escaping(self):
        jira, confluence = Mock(), Mock()
        jira.get.return_value = {"total": 12}
        confluence.get.return_value = {"results": [{"id": "1"}], "_links": {}}
        roster = {"person@example.test": {"jira_user": 'a"b\\c', "confluence_user": "wiki-person"}}
        with patch.object(signal, "AtlassianClient", side_effect=[jira, confluence]), contextlib.redirect_stdout(io.StringIO()):
            result = signal.collect(roster, SETTINGS, 90)
        person = result["people"]["person@example.test"]
        self.assertEqual(result["window_days"], 90)
        self.assertEqual(person["jira_total_180d"], 12)
        self.assertEqual(person["confluence_hits"], 1)
        self.assertEqual(person["jql"], '(assignee = "a\\"b\\\\c" OR reporter = "a\\"b\\\\c") AND updated >= -90d')
        self.assertEqual(person["cql"], 'contributor = "wiki-person" AND lastmodified >= now("-90d")')
        self.assertNotIn("test-jira-secret", json.dumps(result))
        jira.session.close.assert_called_once()
        confluence.session.close.assert_called_once()

    def test_failed_collection_does_not_overwrite_existing_result(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "result.json"
            output.write_text("previous result", encoding="utf-8")
            args = ["script", "--person", "one", "--json-out", str(output)]
            with patch.object(sys, "argv", args), patch.object(signal, "load_settings", return_value=SETTINGS), \
                    patch.object(signal, "collect", side_effect=signal.CollectionError("JIRA: HTTP 401")), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(signal.main(), 1)
            self.assertEqual(output.read_text(encoding="utf-8"), "previous result")

    def test_cli_rejects_nonpositive_window(self):
        with patch.object(sys, "argv", ["script", "--since-days", "0"]), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                signal.main()
        self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()