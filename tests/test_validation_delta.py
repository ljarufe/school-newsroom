from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import validation_delta
from scripts.validation_delta import (
    DOCUMENTATION_ONLY,
    FULL_VALIDATION,
    ZERO_OBJECT_ID,
    classify_endpoint_refs,
    classify_paths,
    classify_pre_commit_pre_push,
    classify_refs,
    paths_from_name_status,
    resolve_commit,
)


def name_status(*entries: str) -> bytes:
    return "\0".join(entries).encode() + b"\0"


def git_commits(*refs: str) -> dict[str, str]:
    return {f"{ref}^{{commit}}": ref for ref in refs}


def install_git_adapter(
    monkeypatch: pytest.MonkeyPatch,
    *,
    commits: Mapping[str, str],
    merge_bases: Mapping[tuple[str, str], str] | None = None,
    diffs: Mapping[tuple[str, str], bytes] | None = None,
) -> list[tuple[str, ...]]:
    calls: list[tuple[str, ...]] = []
    merge_bases = merge_bases or {}
    diffs = diffs or {}

    def fake_git_output(repository: Path, *args: str) -> bytes:
        del repository
        calls.append(args)
        if args[:2] == ("rev-parse", "--verify") and len(args) == 3:
            commit = commits.get(args[2])
            if commit is not None:
                return f"{commit}\n".encode()
        if args[:1] == ("merge-base",) and len(args) == 3:
            merge_base = merge_bases.get((args[1], args[2]))
            if merge_base is not None:
                return f"{merge_base}\n".encode()
        if args[:4] == ("diff", "--find-renames", "--name-status", "-z"):
            diff = diffs.get((args[-2], args[-1]))
            if diff is not None:
                return diff
        raise subprocess.CalledProcessError(1, ("git", *args))

    monkeypatch.setattr(validation_delta, "git_output", fake_git_output)
    return calls


def pre_commit_push_environment(
    from_ref: str,
    to_ref: str,
    *,
    remote_name: str = "origin",
) -> dict[str, str]:
    return {
        "PRE_COMMIT_FROM_REF": from_ref,
        "PRE_COMMIT_TO_REF": to_ref,
        "PRE_COMMIT_REMOTE_NAME": remote_name,
        "PRE_COMMIT_REMOTE_URL": "https://example.invalid/school-newsroom.git",
        "PRE_COMMIT_REMOTE_BRANCH": "main",
        "PRE_COMMIT_LOCAL_BRANCH": "qa-001-test",
    }


def test_docs_only_paths_take_the_lightweight_route() -> None:
    assert classify_paths(["docs/guide.md", "README.md"]).route == DOCUMENTATION_ONLY


@pytest.mark.parametrize(
    "path",
    [
        "apps/news/models.py",
        ".github/workflows/pr-validation.yml",
        "Makefile",
        "static/news/css/seo_assistant.css",
    ],
)
def test_executable_or_configuration_paths_fail_closed(path: str) -> None:
    assert classify_paths(["docs/guide.md", path]).route == FULL_VALIDATION


def test_deleted_documentation_is_classified_from_its_deleted_path() -> None:
    assert paths_from_name_status(name_status("D", "docs/obsolete.md")) == [
        "docs/obsolete.md"
    ]
    assert (
        classify_paths(
            paths_from_name_status(name_status("D", "apps/news/obsolete.py"))
        ).route
        == FULL_VALIDATION
    )


@pytest.mark.parametrize(
    ("output", "expected_route"),
    [
        (name_status("R100", "docs/old.md", "docs/new.md"), DOCUMENTATION_ONLY),
        (
            name_status("R100", "docs/guide.md", "apps/news/guide.py"),
            FULL_VALIDATION,
        ),
    ],
)
def test_rename_paths_classify_both_source_and_destination(
    output: bytes,
    expected_route: str,
) -> None:
    assert classify_paths(paths_from_name_status(output)).route == expected_route


def test_resolve_commit_uses_git_rev_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = install_git_adapter(monkeypatch, commits=git_commits("base"))

    assert resolve_commit(Path("repository"), "base") == "base"
    assert calls == [("rev-parse", "--verify", "base^{commit}")]


def test_resolve_commit_rejects_an_empty_ref() -> None:
    with pytest.raises(ValueError, match="missing Git ref"):
        resolve_commit(Path("repository"), "")


def test_pre_push_command_uses_pre_commit_refs_for_existing_docs_delta(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = install_git_adapter(
        monkeypatch,
        commits=git_commits("old", "new"),
        diffs={("old", "new"): name_status("M", "docs/guide.md")},
    )
    for name, value in pre_commit_push_environment("old", "new").items():
        monkeypatch.setenv(name, value)

    assert validation_delta.pre_push_command(argparse.Namespace(repository=".")) == 0
    assert "validation route: documentation-only" in capsys.readouterr().out
    assert calls[-1] == (
        "diff",
        "--find-renames",
        "--name-status",
        "-z",
        "old",
        "new",
    )


def test_pre_push_command_runs_make_check_for_full_validation(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        validation_delta,
        "classify_pre_commit_pre_push",
        lambda environment, repository: validation_delta.Classification(
            FULL_VALIDATION,
            "executable delta",
        ),
    )
    monkeypatch.setattr(
        validation_delta.subprocess,
        "run",
        lambda command, **kwargs: SimpleNamespace(returncode=17),
    )

    assert validation_delta.pre_push_command(argparse.Namespace(repository=".")) == 17
    assert "Full validation selected: running make check." in capsys.readouterr().out


def test_existing_branch_executable_endpoint_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_git_adapter(
        monkeypatch,
        commits=git_commits("old", "new"),
        diffs={("old", "new"): name_status("M", "apps/news/views.py")},
    )

    assert (
        classify_pre_commit_pre_push(pre_commit_push_environment("old", "new")).route
        == FULL_VALIDATION
    )


@pytest.mark.parametrize(
    ("diff", "expected_route"),
    [
        (name_status("R100", "docs/old.md", "docs/new.md"), DOCUMENTATION_ONLY),
        (
            name_status("R100", "docs/old.md", "apps/news/new.py"),
            FULL_VALIDATION,
        ),
    ],
)
def test_existing_branch_rename_delta_is_rename_aware(
    monkeypatch: pytest.MonkeyPatch,
    diff: bytes,
    expected_route: str,
) -> None:
    install_git_adapter(
        monkeypatch,
        commits=git_commits("old", "new"),
        diffs={("old", "new"): diff},
    )

    assert (
        classify_pre_commit_pre_push(pre_commit_push_environment("old", "new")).route
        == expected_route
    )


def test_existing_endpoint_and_pr_classification_use_different_bases(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_git_adapter(
        monkeypatch,
        commits=git_commits("remote-old", "local-new"),
        merge_bases={("remote-old", "local-new"): "merge-base"},
        diffs={
            ("remote-old", "local-new"): name_status(
                "D", "apps/news/remote_only.py", "A", "docs/guide.md"
            ),
            ("merge-base", "local-new"): name_status("A", "docs/guide.md"),
        },
    )

    assert classify_endpoint_refs("remote-old", "local-new").route == FULL_VALIDATION
    assert classify_refs("remote-old", "local-new").route == DOCUMENTATION_ONLY


def test_uat_b_new_branch_readme_delta_is_documentation_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_git_adapter(
        monkeypatch,
        commits=git_commits("origin/main", "local-head"),
        merge_bases={("origin/main", "local-head"): "main-base"},
        diffs={("main-base", "local-head"): name_status("M", "README.md")},
    )

    assert (
        classify_pre_commit_pre_push(
            pre_commit_push_environment(ZERO_OBJECT_ID, "local-head")
        ).route
        == DOCUMENTATION_ONLY
    )


def test_new_branch_executable_delta_requires_full_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_git_adapter(
        monkeypatch,
        commits=git_commits("origin/main", "local-head"),
        merge_bases={("origin/main", "local-head"): "main-base"},
        diffs={("main-base", "local-head"): name_status("M", "apps/news/views.py")},
    )

    assert (
        classify_pre_commit_pre_push(
            pre_commit_push_environment(ZERO_OBJECT_ID, "local-head")
        ).route
        == FULL_VALIDATION
    )


def test_new_branch_without_resolvable_remote_main_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_git_adapter(monkeypatch, commits=git_commits("local-head"))

    assert (
        classify_pre_commit_pre_push(
            pre_commit_push_environment(ZERO_OBJECT_ID, "local-head")
        ).route
        == FULL_VALIDATION
    )


def test_deleted_ref_fails_closed() -> None:
    assert (
        classify_pre_commit_pre_push(
            pre_commit_push_environment("remote-old", ZERO_OBJECT_ID)
        ).route
        == FULL_VALIDATION
    )


def test_new_branch_without_remote_name_fails_closed() -> None:
    environment = pre_commit_push_environment(ZERO_OBJECT_ID, "local-head")
    environment.pop("PRE_COMMIT_REMOTE_NAME")

    assert classify_pre_commit_pre_push(environment).route == FULL_VALIDATION


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {"PRE_COMMIT_FROM_REF": "missing", "PRE_COMMIT_TO_REF": "head"},
        {"PRE_COMMIT_FROM_REF": "base", "PRE_COMMIT_TO_REF": "missing"},
    ],
)
def test_missing_or_invalid_pre_commit_refs_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
    environment: dict[str, str],
) -> None:
    install_git_adapter(monkeypatch, commits={})

    assert classify_pre_commit_pre_push(environment).route == FULL_VALIDATION


def test_subprocess_errors_fail_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def git_error(repository: Path, *args: str) -> bytes:
        del repository, args
        raise subprocess.CalledProcessError(1, "git")

    monkeypatch.setattr(validation_delta, "git_output", git_error)

    assert classify_refs("base", "head").route == FULL_VALIDATION


def test_main_dispatches_the_pr_classifier_command(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    install_git_adapter(
        monkeypatch,
        commits=git_commits("base", "head"),
        merge_bases={("base", "head"): "merge-base"},
        diffs={("merge-base", "head"): name_status("M", "docs/guide.md")},
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "validation_delta.py",
            "classify",
            "--base-ref",
            "base",
            "--head-ref",
            "head",
        ],
    )

    assert validation_delta.main() == 0
    assert "validation route: documentation-only" in capsys.readouterr().out
