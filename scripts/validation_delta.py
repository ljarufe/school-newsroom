#!/usr/bin/env python3
"""Classify Git deltas for proportional repository validation.

Only the paths in ``DOCUMENTATION_ONLY_PATHS`` are eligible for the lightweight
validation route.  Every Git or input error intentionally selects full
validation so local pre-push and Pull Request Validation fail closed together.
"""

from __future__ import annotations

import argparse
import os
import subprocess
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path

DOCUMENTATION_ONLY_PATHS = frozenset(
    {
        "README.md",
        "AGENTS.md",
        "THIRD_PARTY_NOTICES.md",
        ".github/pull_request_template.md",
    }
)
DOCUMENTATION_ONLY_PREFIXES = ("docs/",)
FULL_VALIDATION = "full-validation"
DOCUMENTATION_ONLY = "documentation-only"
ZERO_OBJECT_ID = "0" * 40


@dataclass(frozen=True)
class Classification:
    route: str
    reason: str


def is_documentation_path(path: str) -> bool:
    """Return whether one changed path belongs to the explicit allowlist."""
    return path in DOCUMENTATION_ONLY_PATHS or path.startswith(
        DOCUMENTATION_ONLY_PREFIXES
    )


def classify_paths(paths: Iterable[str]) -> Classification:
    """Classify changed paths; any non-allowlisted path requires full validation."""
    changed_paths = list(paths)
    if not changed_paths:
        return Classification(FULL_VALIDATION, "no changed paths were available")

    non_documentation_paths = [
        path for path in changed_paths if not is_documentation_path(path)
    ]
    if non_documentation_paths:
        return Classification(
            FULL_VALIDATION,
            f"non-documentation path: {non_documentation_paths[0]}",
        )
    return Classification(DOCUMENTATION_ONLY, "all changed paths are documentation")


def paths_from_name_status(output: bytes) -> list[str]:
    """Extract every path from NUL-delimited ``git diff --name-status`` output."""
    fields = output.decode("utf-8", errors="surrogateescape").split("\0")
    if fields and fields[-1] == "":
        fields.pop()

    paths: list[str] = []
    position = 0
    while position < len(fields):
        status = fields[position]
        position += 1
        if not status:
            raise ValueError("empty Git name-status entry")
        if position >= len(fields):
            raise ValueError(f"missing path for Git status {status!r}")
        paths.append(fields[position])
        position += 1
        if status[0] in {"R", "C"}:
            if position >= len(fields):
                raise ValueError(f"missing destination for Git status {status!r}")
            paths.append(fields[position])
            position += 1
    return paths


def git_output(repository: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args],
        cwd=repository,
        check=True,
        capture_output=True,
    ).stdout


def resolve_commit(repository: Path, ref: str) -> str:
    if not ref:
        raise ValueError("missing Git ref")
    return (
        git_output(repository, "rev-parse", "--verify", f"{ref}^{{commit}}")
        .decode("ascii")
        .strip()
    )


def classify_commit_delta(
    base_commit: str,
    head_commit: str,
    repository: Path,
) -> Classification:
    """Classify a direct changed-path delta between two resolved commits."""
    paths = paths_from_name_status(
        git_output(
            repository,
            "diff",
            "--find-renames",
            "--name-status",
            "-z",
            base_commit,
            head_commit,
        )
    )
    return classify_paths(paths)


def classify_refs(
    base_ref: str, head_ref: str, repository: Path = Path(".")
) -> Classification:
    """Classify a Pull Request delta from merge base to the proposed head."""
    try:
        base_commit = resolve_commit(repository, base_ref)
        head_commit = resolve_commit(repository, head_ref)
        merge_base = (
            git_output(repository, "merge-base", base_commit, head_commit)
            .decode("ascii")
            .strip()
        )
        return classify_commit_delta(merge_base, head_commit, repository)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        return Classification(FULL_VALIDATION, f"could not compare Git refs: {error}")


def classify_endpoint_refs(
    from_ref: str,
    to_ref: str,
    repository: Path = Path("."),
) -> Classification:
    """Classify an existing branch push from its remote endpoint to local endpoint."""
    try:
        from_commit = resolve_commit(repository, from_ref)
        to_commit = resolve_commit(repository, to_ref)
        return classify_commit_delta(from_commit, to_commit, repository)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        return Classification(FULL_VALIDATION, f"could not compare Git refs: {error}")


def classify_pre_commit_pre_push(
    environment: Mapping[str, str],
    repository: Path = Path("."),
) -> Classification:
    """Classify a pre-commit managed pre-push hook using its documented refs."""
    from_ref = environment.get("PRE_COMMIT_FROM_REF", "")
    to_ref = environment.get("PRE_COMMIT_TO_REF", "")
    if not from_ref or not to_ref:
        return Classification(FULL_VALIDATION, "missing pre-commit push refs")
    if to_ref == ZERO_OBJECT_ID:
        return Classification(FULL_VALIDATION, "ref deletion requires full validation")
    if from_ref != ZERO_OBJECT_ID:
        return classify_endpoint_refs(from_ref, to_ref, repository)

    remote_name = environment.get("PRE_COMMIT_REMOTE_NAME", "")
    if not remote_name:
        return Classification(FULL_VALIDATION, "missing remote name for a new branch")
    return classify_refs(f"{remote_name}/main", to_ref, repository)


def print_classification(classification: Classification) -> None:
    print(f"validation route: {classification.route}")
    print(f"reason: {classification.reason}")


def classify_command(args: argparse.Namespace) -> int:
    classification = classify_refs(args.base_ref, args.head_ref, Path(args.repository))
    print_classification(classification)
    return 0


def pre_push_command(args: argparse.Namespace) -> int:
    classification = classify_pre_commit_pre_push(os.environ, Path(args.repository))
    print_classification(classification)
    if classification.route == DOCUMENTATION_ONLY:
        print("Documentation-only push: make check was intentionally not run.")
        return 0

    print("Full validation selected: running make check.")
    return subprocess.run(
        ["make", "check"], cwd=args.repository, check=False
    ).returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    classify_parser = subparsers.add_parser("classify")
    classify_parser.add_argument("--base-ref", required=True)
    classify_parser.add_argument("--head-ref", required=True)
    classify_parser.add_argument("--repository", default=".")
    classify_parser.set_defaults(handler=classify_command)

    pre_push_parser = subparsers.add_parser("pre-push")
    pre_push_parser.add_argument("--repository", default=".")
    pre_push_parser.set_defaults(handler=pre_push_command)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
