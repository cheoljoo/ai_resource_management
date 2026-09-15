"""Gerrit JSON 결합 계약을 네트워크/git 조회 없이 검증한다."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import combine_expert_signals as combine


class CombineGerritTests(unittest.TestCase):
    def report(self, gerrit):
        git_data = {("/repos/example", "src/core"): Counter({"Git@example.test": 4})}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gerrit.json"
            path.write_text(json.dumps(gerrit), encoding="utf-8")
            output = io.StringIO()
            with patch.object(sys, "argv", [
                "combine_expert_signals.py", "--repo", "/repos/example",
                "--since-days", "30", "--gerrit-json", str(path),
            ]), patch.object(combine, "collect_module_contributor_ea", return_value=git_data) as collect:
                with contextlib.redirect_stdout(output):
                    combine.main()
            collect.assert_called_once_with(["/repos/example"], 30, 2)
        return output.getvalue()

    def rows(self, output):
        lines = output.splitlines()
        header_index = next(i for i, line in enumerate(lines) if line.startswith("person "))
        header = lines[header_index].split()
        rows = []
        for line in lines[header_index + 1:]:
            if not line.strip() or line.startswith("#"):
                break
            rows.append(dict(zip(header, line.split())))
        return rows

    def new_schema(self):
        return {
            "person_total": {"Owner@example.test": 2},
            "reviewer_total": {"Reviewer@example.test": 100, "reviewer@partner.test": 3},
            "comment_total": {"Commenter@example.test": 5},
            "message_total": {"System@example.test": 6},
            "merged_owner_total": {"Merger@example.test": 7},
            "submitter_total": {"Submitter@example.test": 8},
        }

    def test_new_contributors_normalization_and_git_only_sort(self):
        output = self.report(self.new_schema())
        rows = self.rows(output)
        self.assertEqual(rows[0]["person"], "git")
        people = {row["person"]: row for row in rows}
        self.assertEqual(set(people), {"git", "owner", "reviewer", "commenter", "system", "merger", "submitter"})
        for person, column, value in (
            ("owner", "g_owner", "2"), ("reviewer", "g_review", "103"),
            ("commenter", "g_comment", "5"), ("system", "g_message", "6"),
            ("merger", "g_merged", "7"), ("submitter", "g_submit", "8"),
        ):
            self.assertEqual(people[person][column], value)
        self.assertEqual(people["reviewer"]["g_owner"], "0")
        self.assertEqual(people["commenter"]["g_message"], "0")
        self.assertIn("고유 인원: 7명", output)
        self.assertIn("[example] src/core: git(4)", output)
        self.assertNotIn("WARNING", output)

    def test_legacy_person_total_is_accepted_as_owner_only(self):
        output = self.report({"person_total": {"Owner@example.test": 2}})
        people = {row["person"]: row for row in self.rows(output)}
        self.assertEqual(people["owner"]["g_owner"], "2")
        for row in people.values():
            for column in ("g_review", "g_comment", "g_message", "g_merged", "g_submit"):
                self.assertEqual(row[column], "N/A")
        self.assertIn("WARNING", output)
        self.assertIn("unavailable (N/A, 실제 0이 아님)", output)

    def test_present_empty_map_is_zero_but_missing_maps_are_unavailable(self):
        output = self.report({"person_total": {}, "reviewer_total": {}})
        row = self.rows(output)[0]
        self.assertEqual(row["g_review"], "0")
        self.assertEqual(row["g_comment"], "N/A")
        warning = next(line for line in output.splitlines() if "WARNING" in line)
        self.assertNotIn("g_review", warning)
        self.assertIn("g_comment", warning)

    def test_truncated_servers_warns_about_cap(self):
        data = self.new_schema()
        data["truncated_servers"] = ["na", "lamp"]
        output = self.report(data)
        self.assertIn("WARNING: Gerrit cap reached", output)
        self.assertIn("na, lamp", output)
        data["truncated_servers"] = []
        self.assertNotIn("cap reached", self.report(data))

    def test_legend_explains_semantics_and_routing_limits(self):
        output = self.report(self.new_schema())
        for text in (
            "기존 gerrit/person_total", "distinct reviewed changes", "owner 자신의 feedback 제외",
            "current vote snapshot", "historic vote event count가 아님",
            "published comments", "inline/patch-set-level", "사람 여부를 검증한 지표가 아님",
            "auto/system 포함", "comments와 별개",
            "comments/messages/submits는 각각 timestamp가 since-days 창 안",
            "현재 상태가 MERGED", "merge 시각 창이 아님", "actual submitter",
            "라우팅(누구에게 물어볼지)", "개인별 성과 비교·평가로 전용하지 않는다",
        ):
            with self.subTest(text=text):
                self.assertIn(text, output)


if __name__ == "__main__":
    unittest.main()