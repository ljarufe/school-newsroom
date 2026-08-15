import csv
import io
from pathlib import Path
from urllib.error import URLError

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import DataError

from apps.geography.models import Department, District, Province
from apps.geography.services import NORMALIZED_COLUMNS

VERSIONED_SNAPSHOT = (
    Path(__file__).resolve().parent.parent / "data" / "peru_ubigeo_2025-12-31.csv"
)


def write_source(tmp_path, rows, name="source.csv"):
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=NORMALIZED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    return path


def geography_row(
    *,
    department_code="99",
    department_name="Departamento Ficticio",
    province_code="9901",
    province_name="Provincia Ficticia",
    district_code="990101",
    district_name="Distrito Ficticio",
):
    return {
        "department_code": department_code,
        "department_name": department_name,
        "province_code": province_code,
        "province_name": province_name,
        "district_code": district_code,
        "district_name": district_name,
    }


@pytest.mark.django_db
def test_updater_is_dry_run_by_default(tmp_path) -> None:
    source = write_source(tmp_path, [geography_row()])
    stdout = io.StringIO()

    call_command("update_peru_geography", source=source, stdout=stdout)

    assert not Department.objects.filter(code="99").exists()
    assert Department.objects.get(code="04").is_active
    assert "Dry run: database unchanged" in stdout.getvalue()
    assert "Created departments: 1" in stdout.getvalue()


@pytest.mark.django_db
def test_updater_apply_creates_renames_deactivates_and_is_idempotent(tmp_path) -> None:
    source = write_source(
        tmp_path,
        [
            geography_row(
                department_code="04",
                department_name="Arequipa Actualizada",
                province_code="0401",
                province_name="Arequipa",
                district_code="040101",
                district_name="Arequipa",
            ),
            geography_row(),
        ],
    )

    call_command("update_peru_geography", source=source, apply=True, verbosity=0)
    assert Department.objects.get(code="04").name == "Arequipa Actualizada"
    assert Department.objects.get(code="99").is_active
    assert District.objects.get(code="990101").province_id == "9901"
    assert not Department.objects.get(code="01").is_active
    assert not District.objects.get(code="010101").is_active

    second_stdout = io.StringIO()
    call_command(
        "update_peru_geography",
        source=source,
        apply=True,
        stdout=second_stdout,
        verbosity=0,
    )
    assert "No catalog changes detected" in second_stdout.getvalue()


@pytest.mark.django_db
def test_updater_reactivates_codes_that_reappear() -> None:
    Department.objects.filter(code="04").update(is_active=False)
    Province.objects.filter(code="0401").update(is_active=False)
    District.objects.filter(code="040101").update(is_active=False)

    call_command(
        "update_peru_geography",
        source=VERSIONED_SNAPSHOT,
        apply=True,
        verbosity=0,
    )

    assert Department.objects.get(code="04").is_active
    assert Province.objects.get(code="0401").is_active
    assert District.objects.get(code="040101").is_active


@pytest.mark.django_db
@pytest.mark.parametrize(
    "rows, expected_error",
    [
        ([geography_row(), geography_row()], "Duplicate district code"),
        (
            [
                geography_row(
                    department_code="04",
                    province_code="1501",
                    district_code="150101",
                )
            ],
            "Orphan provinces",
        ),
    ],
)
def test_updater_rejects_duplicate_and_malformed_hierarchy(
    tmp_path, rows, expected_error
) -> None:
    source = write_source(tmp_path, rows)

    with pytest.raises(CommandError, match=expected_error):
        call_command("update_peru_geography", source=source, apply=True)

    assert not Department.objects.filter(code="99").exists()


@pytest.mark.django_db
def test_updater_rejects_bad_file_and_remote_source(tmp_path) -> None:
    malformed = tmp_path / "malformed.csv"
    malformed.write_text("wrong,columns\nvalue,value\n", encoding="utf-8")

    with pytest.raises(CommandError, match="columns must be exactly"):
        call_command("update_peru_geography", source=malformed, apply=True)
    with pytest.raises(CommandError, match="local files only"):
        call_command(
            "update_peru_geography",
            source="https://attacker.invalid/source.xlsx",
        )


@pytest.mark.django_db
def test_updater_rejects_unexpected_parent_change(tmp_path) -> None:
    Province.objects.filter(code="0401").update(department_id="15")

    with pytest.raises(CommandError, match="administrative parent changes"):
        call_command("update_peru_geography", source=VERSIONED_SNAPSHOT, apply=True)

    assert Province.objects.get(code="0401").department_id == "15"


@pytest.mark.django_db
def test_updater_rolls_back_every_write_on_apply_failure(tmp_path) -> None:
    source = write_source(
        tmp_path,
        [geography_row(district_name="X" * 101)],
    )

    with pytest.raises(DataError):
        call_command("update_peru_geography", source=source, apply=True)

    assert not Department.objects.filter(code="99").exists()
    assert Department.objects.get(code="04").is_active


@pytest.mark.django_db
def test_default_remote_failure_does_not_mutate(monkeypatch) -> None:
    def fail_download(*args, **kwargs):
        raise URLError("offline in test")

    monkeypatch.setattr(
        "apps.geography.management.commands.update_peru_geography.urlopen",
        fail_download,
    )

    with pytest.raises(CommandError, match="could not be downloaded"):
        call_command("update_peru_geography", apply=True)

    assert Department.objects.get(code="04").is_active
