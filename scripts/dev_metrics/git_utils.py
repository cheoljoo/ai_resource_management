"""Shared git helpers for the dev_metrics scripts.

Only relies on the `git` CLI + Python stdlib (subprocess, no third-party deps),
since these scripts target the "로컬 git 저장소만으로 즉시 가능" metrics from
developer_evaluation_metrics.md.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable


@dataclass
class Commit:
    commit_hash: str
    parents: list[str]
    author_name: str
    author_email: str
    author_ts: int  # unix epoch (author date, includes local tz info already applied by git)
    subject: str
    files: list[str] = field(default_factory=list)

    @property
    def dt(self) -> datetime:
        return datetime.fromtimestamp(self.author_ts, tz=timezone.utc).astimezone()

    @property
    def is_merge(self) -> bool:
        return len(self.parents) > 1


def run_git(repo: str, args: list[str]) -> str:
    result = subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


_FIELD_SEP = "\x1f"
_RECORD_SEP = "\x1e"
_LOG_FORMAT = _RECORD_SEP + _FIELD_SEP.join(["%H", "%P", "%an", "%ae", "%at", "%s"])


def iter_commits(
    repo: str,
    rev_range: str = "HEAD",
    with_files: bool = False,
    extra_args: Iterable[str] | None = None,
) -> list[Commit]:
    """Parse `git log` output into Commit objects.

    rev_range follows normal git revision range syntax (e.g. "HEAD", "main",
    "base..tip"). Order matches `git log` (newest first).
    """
    args = ["log", f"--pretty=format:{_LOG_FORMAT}"]
    if with_files:
        args.append("--name-only")
    args.extend(extra_args or [])
    args.append(rev_range)

    output = run_git(repo, args)
    commits: list[Commit] = []
    for record in output.split(_RECORD_SEP):
        record = record.strip("\n")
        if not record:
            continue
        lines = record.split("\n")
        header = lines[0]
        h, parents, an, ae, at, subject = header.split(_FIELD_SEP)
        files = [line for line in lines[1:] if line.strip()] if with_files else []
        commits.append(
            Commit(
                commit_hash=h,
                parents=parents.split() if parents else [],
                author_name=an,
                author_email=ae,
                author_ts=int(at),
                subject=subject,
                files=files,
            )
        )
    return commits


def list_branches(repo: str, include_remote: bool = True) -> list[str]:
    args = ["for-each-ref", "--format=%(refname:short)", "refs/heads/"]
    names = [n for n in run_git(repo, args).splitlines() if n.strip()]
    if include_remote:
        remote_args = ["for-each-ref", "--format=%(refname:short)", "refs/remotes/"]
        names += [
            n for n in run_git(repo, remote_args).splitlines()
            if n.strip() and not n.endswith("/HEAD")
        ]
    return names


def default_branch(repo: str) -> str:
    for candidate in ("origin/main", "origin/master", "main", "master"):
        try:
            run_git(repo, ["rev-parse", "--verify", candidate])
            return candidate
        except subprocess.CalledProcessError:
            continue
    return "HEAD"
