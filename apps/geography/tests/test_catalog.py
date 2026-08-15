import hashlib
from pathlib import Path

import pytest

from apps.geography.models import Department, District, Province
from apps.geography.services import parse_geography_source

SNAPSHOT = (
    Path(__file__).resolve().parent.parent / "data" / "peru_ubigeo_2025-12-31.csv"
)


@pytest.mark.django_db
def test_versioned_snapshot_metadata_counts_and_hierarchy() -> None:
    assert hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest() == (
        "58a2959fa22fd9ff3b515a357f451e26a56f82178dfa363f64499d996fb0fff3"
    )
    snapshot = parse_geography_source(SNAPSHOT)

    assert len(snapshot.departments) == 25
    assert len(snapshot.provinces) == 196
    assert len(snapshot.districts) == 1892
    assert {row.code for row in snapshot.departments} >= {"01", "04", "07", "25"}
    assert next(row for row in snapshot.departments if row.code == "04").name == (
        "Arequipa"
    )
    assert all(isinstance(row.code, str) for row in snapshot.districts)
    assert all(len(row.code) == 6 for row in snapshot.districts)


@pytest.mark.django_db
def test_loaded_catalog_has_no_orphans_and_preserves_active_state() -> None:
    assert Department.objects.count() == 25
    assert Province.objects.count() == 196
    assert District.objects.count() == 1892
    assert not Province.objects.exclude(
        department_id__in=Department.objects.values("code")
    ).exists()
    assert not District.objects.exclude(
        province_id__in=Province.objects.values("code")
    ).exists()
    assert Department.objects.get(code="04").is_active
    assert District.objects.get(code="040101").province.department_id == "04"


@pytest.mark.django_db
def test_catalog_codes_are_primary_string_identifiers() -> None:
    assert Department._meta.pk.name == "code"
    assert Province._meta.pk.name == "code"
    assert District._meta.pk.name == "code"
    assert Department._meta.pk.max_length == 2
    assert Province._meta.pk.max_length == 4
    assert District._meta.pk.max_length == 6
    assert Department.objects.get(pk="01").code == "01"
