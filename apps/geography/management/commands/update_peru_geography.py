from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.geography.models import Department, District, Province
from apps.geography.services import (
    OFFICIAL_RESOURCE_URL,
    GeographySnapshot,
    GeographySourceError,
    parse_geography_bytes,
    parse_geography_source,
)


@dataclass(frozen=True)
class CatalogDiff:
    created_departments: tuple[str, ...]
    created_provinces: tuple[str, ...]
    created_districts: tuple[str, ...]
    renamed_departments: tuple[str, ...]
    renamed_provinces: tuple[str, ...]
    renamed_districts: tuple[str, ...]
    reactivated_departments: tuple[str, ...]
    reactivated_provinces: tuple[str, ...]
    reactivated_districts: tuple[str, ...]
    inactive_departments: tuple[str, ...]
    inactive_provinces: tuple[str, ...]
    inactive_districts: tuple[str, ...]

    @property
    def has_changes(self) -> bool:
        return any(getattr(self, field) for field in self.__dataclass_fields__)


class Command(BaseCommand):
    help = (
        "Check the selected official INEI geography source against the local "
        "catalog. Use --apply to apply a reviewed diff."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            help="Controlled local XLSX or normalized CSV path (remote URLs rejected).",
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Apply the fully validated diff transactionally.",
        )

    def handle(self, *args, **options):
        try:
            snapshot, source_label, checksum = self._load_source(options["source"])
            catalog_diff = self._build_diff(snapshot)
        except (GeographySourceError, OSError, URLError) as error:
            raise CommandError(str(error)) from error

        self.stdout.write(f"Source: {source_label}")
        self.stdout.write(f"SHA-256: {checksum}")
        self.stdout.write(
            "Validated: "
            f"{len(snapshot.departments)} departments, "
            f"{len(snapshot.provinces)} provinces, "
            f"{len(snapshot.districts)} districts"
        )
        self._write_diff(catalog_diff)

        if not options["apply"]:
            self.stdout.write("Dry run: database unchanged. Use --apply to mutate.")
            return

        with transaction.atomic():
            self._apply_snapshot(snapshot)
        self.stdout.write(
            self.style.SUCCESS("Geography catalog updated transactionally.")
        )

    def _load_source(self, local_source):
        if local_source:
            local_source = str(local_source)
            if "://" in local_source:
                raise GeographySourceError(
                    "--source accepts local files only; remote URLs are not allowed."
                )
            path = Path(local_source).expanduser()
            raw = path.read_bytes()
            snapshot = parse_geography_source(path)
            return snapshot, str(path), hashlib.sha256(raw).hexdigest()

        try:
            with urlopen(OFFICIAL_RESOURCE_URL, timeout=30) as response:
                raw = response.read()
        except (OSError, URLError) as error:
            raise GeographySourceError(
                f"The official INEI resource could not be downloaded: {error}"
            ) from error
        return (
            parse_geography_bytes(raw),
            OFFICIAL_RESOURCE_URL,
            hashlib.sha256(raw).hexdigest(),
        )

    @staticmethod
    def _build_diff(snapshot: GeographySnapshot) -> CatalogDiff:
        departments = Department.objects.in_bulk()
        provinces = Province.objects.in_bulk()
        districts = District.objects.in_bulk()

        source_departments = {row.code: row for row in snapshot.departments}
        source_provinces = {row.code: row for row in snapshot.provinces}
        source_districts = {row.code: row for row in snapshot.districts}

        parent_conflicts = [
            f"province {code}: {provinces[code].department_id} -> {row.department_code}"
            for code, row in source_provinces.items()
            if code in provinces
            and provinces[code].department_id != row.department_code
        ]
        parent_conflicts.extend(
            f"district {code}: {districts[code].province_id} -> {row.province_code}"
            for code, row in source_districts.items()
            if code in districts and districts[code].province_id != row.province_code
        )
        if parent_conflicts:
            raise GeographySourceError(
                "Unexpected administrative parent changes: "
                + "; ".join(sorted(parent_conflicts))
            )

        return CatalogDiff(
            created_departments=tuple(
                sorted(source_departments.keys() - departments.keys())
            ),
            created_provinces=tuple(sorted(source_provinces.keys() - provinces.keys())),
            created_districts=tuple(sorted(source_districts.keys() - districts.keys())),
            renamed_departments=tuple(
                sorted(
                    code
                    for code, row in source_departments.items()
                    if code in departments and departments[code].name != row.name
                )
            ),
            renamed_provinces=tuple(
                sorted(
                    code
                    for code, row in source_provinces.items()
                    if code in provinces and provinces[code].name != row.name
                )
            ),
            renamed_districts=tuple(
                sorted(
                    code
                    for code, row in source_districts.items()
                    if code in districts and districts[code].name != row.name
                )
            ),
            reactivated_departments=tuple(
                sorted(
                    code
                    for code in source_departments
                    if code in departments and not departments[code].is_active
                )
            ),
            reactivated_provinces=tuple(
                sorted(
                    code
                    for code in source_provinces
                    if code in provinces and not provinces[code].is_active
                )
            ),
            reactivated_districts=tuple(
                sorted(
                    code
                    for code in source_districts
                    if code in districts and not districts[code].is_active
                )
            ),
            inactive_departments=tuple(
                sorted(
                    code
                    for code in departments.keys() - source_departments.keys()
                    if departments[code].is_active
                )
            ),
            inactive_provinces=tuple(
                sorted(
                    code
                    for code in provinces.keys() - source_provinces.keys()
                    if provinces[code].is_active
                )
            ),
            inactive_districts=tuple(
                sorted(
                    code
                    for code in districts.keys() - source_districts.keys()
                    if districts[code].is_active
                )
            ),
        )

    def _write_diff(self, catalog_diff: CatalogDiff) -> None:
        for field_name in catalog_diff.__dataclass_fields__:
            codes = getattr(catalog_diff, field_name)
            label = field_name.replace("_", " ").capitalize()
            self.stdout.write(f"{label}: {len(codes)}")
            if codes:
                visible_codes = codes[:20]
                suffix = f" (+{len(codes) - 20} more)" if len(codes) > 20 else ""
                self.stdout.write("  " + ", ".join(visible_codes) + suffix)
        if not catalog_diff.has_changes:
            self.stdout.write("No catalog changes detected.")

    @staticmethod
    def _apply_snapshot(snapshot: GeographySnapshot) -> None:
        department_codes = [row.code for row in snapshot.departments]
        province_codes = [row.code for row in snapshot.provinces]
        district_codes = [row.code for row in snapshot.districts]

        for row in snapshot.departments:
            Department.objects.update_or_create(
                code=row.code,
                defaults={"name": row.name, "is_active": True},
            )
        for row in snapshot.provinces:
            Province.objects.update_or_create(
                code=row.code,
                defaults={
                    "name": row.name,
                    "department_id": row.department_code,
                    "is_active": True,
                },
            )
        for row in snapshot.districts:
            District.objects.update_or_create(
                code=row.code,
                defaults={
                    "name": row.name,
                    "province_id": row.province_code,
                    "is_active": True,
                },
            )

        District.objects.exclude(code__in=district_codes).update(is_active=False)
        Province.objects.exclude(code__in=province_codes).update(is_active=False)
        Department.objects.exclude(code__in=department_codes).update(is_active=False)
