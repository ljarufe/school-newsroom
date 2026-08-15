import datetime as dt

import pytest
from django.core.exceptions import ValidationError

from apps.news.models import NewsPage, School
from apps.news.school_forms import SchoolAdminForm


@pytest.mark.django_db
def test_school_department_required_district_optional_and_compatible() -> None:
    missing_department = School(name="Colegio ficticio sin departamento")
    with pytest.raises(ValidationError) as required_error:
        missing_department.full_clean()
    assert "department" in required_error.value.message_dict

    department_only = School(
        name="Colegio ficticio departamental",
        department_id="04",
    )
    department_only.full_clean()

    compatible = School(
        name="Colegio ficticio distrital",
        department_id="04",
        district_id="040101",
    )
    compatible.full_clean()


@pytest.mark.django_db
def test_school_rejects_manipulated_incompatible_district() -> None:
    school = School(
        name="Colegio ficticio incompatible",
        department_id="04",
        district_id="150101",
    )

    with pytest.raises(ValidationError) as error:
        school.full_clean()

    assert "debe pertenecer al departamento" in str(
        error.value.message_dict["district"]
    )


@pytest.mark.django_db
def test_school_admin_form_uses_bounded_dependent_district_widget() -> None:
    school = School.objects.create(
        name="Colegio ficticio existente",
        department_id="04",
        district_id="040101",
    )
    rendered = str(SchoolAdminForm(instance=school)["district"])

    assert "data-dependent-district" in rendered
    assert 'data-department-field="#id_department"' in rendered
    assert 'value="040101"' in rendered
    assert 'value="Arequipa"' in rendered
    assert "Chachapoyas" not in rendered

    incompatible_form = SchoolAdminForm(
        data={
            "name": school.name,
            "department": "04",
            "district": "150101",
        },
        instance=school,
    )
    assert not incompatible_form.is_valid()
    assert "debe pertenecer al departamento" in str(
        incompatible_form.errors["district"]
    )


@pytest.mark.django_db
def test_news_coverage_department_required_and_district_compatible() -> None:
    department_field = NewsPage._meta.get_field("coverage_department")
    district_field = NewsPage._meta.get_field("coverage_district")
    assert not department_field.blank
    assert district_field.blank and district_field.null

    page = NewsPage(
        title="Cobertura ficticia incompatible",
        slug="cobertura-ficticia-incompatible",
        publication_date=dt.date(2026, 8, 1),
        body=[("paragraph", "<p>Contenido ficticio.</p>")],
        coverage_department_id="04",
        coverage_district_id="150101",
    )
    with pytest.raises(ValidationError) as error:
        page.clean()
    assert "debe pertenecer al departamento" in str(
        error.value.message_dict["coverage_district"]
    )

    page.coverage_district_id = None
    page.clean()
