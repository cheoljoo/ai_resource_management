"""Offline schema-2/legacy MR and PR report contracts; no git or API calls."""
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


NOW = "2026-09-15T00:00:00Z"
MAIN_COLUMNS = [
    "person", "git_EA", "g_owner", "g_review", "g_comment", "g_message",
    "g_merged", "g_submit", "gitlab_c", "gitlab_mr", "jira", "confluence",
]
METADATA_COLUMNS = [
    "provider", "person", "created", "selected_author", "reviewed", "comments",
    "reviews", "merged_owner", "merger", "commits_legacy",
]


def schema(created_field, prefix):
    return {
        "schema_version": 2, "window_days": 30, "collected_at": NOW,
        "commits": {f"{prefix}-commit@example.test": 2},
        created_field: {f"{prefix}-created": 3}, "issues": {f"{prefix}-issue": 4},
        "request_author_total": {f"{prefix}-author": 5},
        "reviewer_total": {f"{prefix}-reviewer": 600},
        "comment_total": {f"{prefix}-commenter": 7},
        "review_total": {f"{prefix}-review-event": 8},
        "merged_author_total": {f"{prefix}-merged-owner": 9},
        "merger_total": {f"{prefix}-merger": 10},
        "requests": [], "unavailable": [],
        "truncated_projects": [], "truncated_repos": [],
    }


class CombineMrPrTests(unittest.TestCase):
    def report(self, gitlab=None, github=None, top_people=100):
        git_data = {("/repos/example", "src/core"): Counter({"Git@example.test": 4})}
        gerrit = {field: {} for field in (
            "person_total", "reviewer_total", "comment_total", "message_total",
            "merged_owner_total", "submitter_total",
        )}
        with tempfile.TemporaryDirectory() as directory:
            argv = ["combine_expert_signals.py", "--repo", "/repos/example",
                    "--since-days", "30", "--top-people", str(top_people)]
            for provider, data in (("gerrit", gerrit), ("gitlab", gitlab), ("github", github)):
                if data is not None:
                    path = Path(directory) / f"{provider}.json"
                    path.write_text(json.dumps(data), encoding="utf-8")
                    argv.extend([f"--{provider}-json", str(path)])
            output = io.StringIO()
            with patch.object(sys, "argv", argv), patch.object(
                combine, "collect_module_contributor_ea", return_value=git_data,
            ) as collect, contextlib.redirect_stdout(output):
                combine.main()
            collect.assert_called_once_with(["/repos/example"], 30, 2)
        return output.getvalue()

    def table(self, output, start):
        lines = output.splitlines()
        index = next(i for i, line in enumerate(lines) if line.startswith(start + " "))
        header = lines[index].split()
        rows = []
        for line in lines[index + 1:]:
            if not line.strip() or line.startswith("#"):
                break
            values = line.split()
            self.assertEqual(len(values), len(header))
            rows.append(dict(zip(header, values)))
        return header, rows

    def test_both_providers_union_all_roles_without_widening_or_scoring(self):
        output = self.report(schema("mrs", "gl"), schema("prs", "gh"))
        header, main = self.table(output, "person")
        self.assertEqual(header, MAIN_COLUMNS)
        self.assertEqual(main[0]["person"], "git")
        self.assertEqual(main[0]["git_EA"], "4")
        expected = {f"{prefix}-{role}" for prefix in ("gl", "gh") for role in (
            "commit", "created", "issue", "author", "reviewer", "commenter",
            "review-event", "merged-owner", "merger",
        )}
        self.assertEqual({row["person"] for row in main}, expected | {"git"})
        self.assertEqual([row["person"] for row in main[1:]], sorted(expected))
        self.assertTrue(all(row["git_EA"] == "0" for row in main[1:]))
        self.assertIn("고유 인원: 19명", output)
        self.assertIn("6개 소스", output)
        header, metadata = self.table(output, "provider")
        self.assertEqual(header, METADATA_COLUMNS)
        for provider, prefix in (("GitLab", "gl"), ("GitHub", "gh")):
            rows = {row["person"]: row for row in metadata if row["provider"] == provider}
            self.assertEqual(list(rows), sorted(rows))
            for role, column, count in (
                ("created", "created", "3"), ("author", "selected_author", "5"),
                ("reviewer", "reviewed", "600"), ("commenter", "comments", "7"),
                ("review-event", "reviews", "8"), ("merged-owner", "merged_owner", "9"),
                ("merger", "merger", "10"), ("commit", "commits_legacy", "2"),
            ):
                self.assertEqual(rows[f"{prefix}-{role}"][column], count)
            self.assertEqual(rows[f"{prefix}-author"]["created"], "0")
            self.assertEqual(rows[f"{prefix}-merged-owner"]["merger"], "0")
        self.assertNotIn("WARNING", output)

    def test_normalization_within_provider_but_no_cross_provider_count_sum(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        gitlab["reviewer_total"] = {"Shared@lge.com": 2, "shared@lgepartner.com": 3}
        github["reviewer_total"] = {"SHARED": 11}
        output = self.report(gitlab, github)
        _, main = self.table(output, "person")
        self.assertEqual(sum(row["person"] == "shared" for row in main), 1)
        _, rows = self.table(output, "provider")
        shared = {row["provider"]: row for row in rows if row["person"] == "shared"}
        self.assertEqual(shared["GitLab"]["reviewed"], "5")
        self.assertEqual(shared["GitHub"]["reviewed"], "11")

    def test_legacy_maps_preserve_counts_but_metadata_is_na(self):
        output = self.report({"commits": {"Legacy": 2}, "mrs": {"Legacy": 3}},
                             {"commits": {"Legacy": 4}, "prs": {"Legacy": 5}})
        _, rows = self.table(output, "provider")
        self.assertEqual(len(rows), 2)
        for row, created, commits in zip(rows, ("3", "5"), ("2", "4")):
            self.assertEqual(row["created"], created)
            self.assertEqual(row["commits_legacy"], commits)
            for column in combine.MR_PR_FIELDS:
                self.assertEqual(row[column], "N/A")
        _, main = self.table(output, "person")
        legacy = next(row for row in main if row["person"] == "legacy")
        self.assertEqual((legacy["gitlab_c"], legacy["gitlab_mr"]), ("2", "3"))
        self.assertIn("metadata window unknown", output)
        self.assertIn("collected_at=N/A, window_days=N/A", output)

    def test_empty_maps_are_zero_missing_or_null_maps_are_na(self):
        for provider in ("GitLab", "GitHub"):
            with self.subTest(provider=provider):
                data = schema("mrs" if provider == "GitLab" else "prs", "actor")
                data["reviewer_total"] = {}
                data["comment_total"] = None
                del data["review_total"]
                del data["commits"]
                del data["mrs" if provider == "GitLab" else "prs"]
                output = self.report(**{provider.lower(): data})
                _, rows = self.table(output, "provider")
                for row in rows:
                    self.assertEqual(row["reviewed"], "0")
                    for column in ("created", "comments", "reviews", "commits_legacy"):
                        self.assertEqual(row[column], "N/A")
                _, main = self.table(output, "person")
                self.assertTrue(all(row["gitlab_c"] == row["gitlab_mr"] == "N/A" for row in main))

    def test_absent_github_omits_rows_and_explains_not_collected(self):
        output = self.report(schema("mrs", "gl"))
        _, rows = self.table(output, "provider")
        self.assertEqual({row["provider"] for row in rows}, {"GitLab"})
        self.assertIn("GitHub PR metadata not collected", output)
        self.assertNotIn("# GitHub: schema_version", output)
        self.assertIn("5개 소스", output)
        self.assertNotIn("WARNING", output)

    def test_scope_includes_empty_repos_and_skipped_commits_are_na(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        gitlab["projects"] = ["org/collected", "org/empty"]
        github["repos"] = ["org/github-empty"]
        gitlab["commits"] = None
        output = self.report(gitlab, github)
        self.assertIn("GitLab collected scope: org/collected, org/empty", output)
        self.assertIn("GitHub collected scope: org/github-empty", output)
        self.assertIn("범위 밖 활동은 미수집", output)
        _, rows = self.table(output, "provider")
        self.assertTrue(all(row["commits_legacy"] == "N/A" for row in rows if row["provider"] == "GitLab"))

    def test_explicit_empty_github_input_is_not_treated_as_absent(self):
        output = self.report(github={})
        self.assertNotIn("GitHub PR metadata not collected", output)
        self.assertIn("# GitHub: schema_version=legacy", output)
        self.assertIn("WARNING: GitHub unavailable maps", output)

    def test_no_provider_input_has_no_metadata_table_or_extra_warnings(self):
        output = self.report()
        self.assertNotIn("## MR/PR metadata", output)
        self.assertNotIn("WARNING", output)
        self.assertIn("GitHub PR metadata not collected", output)

    def test_gitlab_unavailable_approvals_warn_partial_not_complete_zero(self):
        for source in ("unavailable", "requests"):
            with self.subTest(source=source):
                data = schema("mrs", "gl")
                data["review_total"] = {}
                data[source] = ([{"project": "org/repo", "iid": 42, "feature": "approvals",
                                 "reason": "unsupported_or_not_visible (HTTP 404/405)"}]
                                if source == "unavailable" else [{"approvals": None}])
                output = self.report(data)
                self.assertIn("WARNING: GitLab approvals unavailable", output)
                self.assertIn("reviewer_total/review_total (reviewed/reviews) are partial lower bounds", output)
                self.assertIn("not complete zeros", output)

    def test_both_truncation_warnings_and_legacy_independence(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        gitlab["truncated_projects"] = ["org/gl"]
        github["truncated_repos"] = ["org/gh"]
        output = self.report(gitlab, github)
        for provider, project in (("GitLab", "org/gl"), ("GitHub", "org/gh")):
            self.assertIn(f"WARNING: {provider} cap reached", output)
            self.assertIn(f"legacy created/commits counters independent: {project}", output)

    def test_windows_show_collection_endpoint_and_warn_on_day_mismatch(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        github["window_days"] = 180
        output = self.report(gitlab, github)
        self.assertIn(f"collected_at={NOW}, window_days=30", output)
        self.assertIn(f"collected_at={NOW}, window_days=180", output)
        self.assertIn("GitHub metadata window_days=180 differs from --since-days=30", output)
        self.assertIn("GitLab/GitHub metadata windows differ", output)

    def test_equal_days_but_different_collection_endpoints_warn(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        github["collected_at"] = "2026-09-14T00:00:00Z"
        output = self.report(gitlab, github)
        self.assertIn("GitLab/GitHub metadata windows differ", output)

    def test_equivalent_iso_endpoints_do_not_warn(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        github["collected_at"] = "2026-09-15T09:00:00+09:00"
        self.assertNotIn("WARNING", self.report(gitlab, github))

    def test_unknown_or_invalid_endpoints_are_not_assumed_equal(self):
        for value in (None, "invalid", "2026-09-15T00:00:00"):
            with self.subTest(value=value):
                github = schema("prs", "gh")
                github["collected_at"] = value
                self.assertIn("GitHub metadata window unknown", self.report(github=github))

    def test_metadata_not_ranked_or_hidden_by_main_top_people(self):
        output = self.report(schema("mrs", "gl"), schema("prs", "gh"), top_people=1)
        _, main = self.table(output, "person")
        self.assertEqual([row["person"] for row in main], ["git"])
        _, metadata = self.table(output, "provider")
        self.assertEqual(len(metadata), 18)
        self.assertIn("고유 인원: 19명", output)

    def test_legends_keep_provider_semantics_and_avoid_raw_content(self):
        gitlab, github = schema("mrs", "gl"), schema("prs", "gh")
        for data in (gitlab, github):
            data["requests"] = [{"body": "PRIVATE_SENTINEL", "title": "PRIVATE_SENTINEL",
                                 "requested_reviewers": [{"login": "requested-only"}]}]
        output = self.report(gitlab, github)
        for text in (
            "GitLab mrs / GitHub prs legacy", "created_at", "updated_at",
            "request_author_total", "reviewer_total", "comment_total", "review_total",
            "distinct MR/PR", "owner 자신의 feedback 제외", "current approved_by approval snapshot",
            "historical review events 아님", "submitted_at", "non-PENDING review events",
            "DISMISSED", "merged_author_total", "merge 시각 창이 아님", "merger_total",
            "merged_at", "actual merged_by/merge_user", "author와 별개", "unknown merger",
            "requested_reviewers는 참여 아님", "users/bots", "human-only 보장 없음",
            "git_EA와 합산하지 않음", "개인별 성과 비교·평가로 전용하지 않는다",
        ):
            with self.subTest(text=text):
                self.assertIn(text, output)
        self.assertNotIn("PRIVATE_SENTINEL", output)
        self.assertNotIn("requested-only", output)


if __name__ == "__main__":
    unittest.main()