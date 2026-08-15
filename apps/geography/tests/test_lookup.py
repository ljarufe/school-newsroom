import pytest
from django.test import Client
from django.urls import reverse

from apps.geography.models import District
from apps.geography.views import DISTRICT_RESULT_LIMIT


@pytest.mark.django_db
def test_lookup_requires_active_department_and_three_characters() -> None:
    url = reverse("geography:district_lookup")

    assert Client().get(url).status_code == 400
    assert Client().get(url, {"departamento": "99", "buscar": "san"}).status_code == 400
    response = Client().get(url, {"departamento": "04", "buscar": "sa"})

    assert response.status_code == 200
    assert response.json() == {"results": []}


@pytest.mark.django_db
def test_lookup_is_accent_insensitive_scoped_active_and_bounded() -> None:
    url = reverse("geography:district_lookup")
    accent_response = Client().get(
        url,
        {"departamento": "04", "buscar": "ocona"},
    )
    assert accent_response.status_code == 200
    assert all(
        result.keys() >= {"code", "name"}
        for result in accent_response.json()["results"]
    )
    assert any(
        "Ocoña" == result["name"] for result in accent_response.json()["results"]
    )

    other_department_code = (
        District.objects.filter(
            province__department_id="15", name__unaccent__icontains="san"
        )
        .values_list("code", flat=True)
        .first()
    )
    inactive = District.objects.filter(province__department_id="04").first()
    inactive.is_active = False
    inactive.save(update_fields=["is_active"])
    response = Client().get(url, {"departamento": "04", "buscar": "san"})
    codes = {result["code"] for result in response.json()["results"]}

    assert len(codes) <= DISTRICT_RESULT_LIMIT
    assert other_department_code not in codes
    assert inactive.code not in codes


@pytest.mark.django_db
def test_lookup_only_adds_province_for_ambiguous_names() -> None:
    District.objects.create(
        code="040199",
        name="Arequipa",
        province_id="0401",
    )
    response = Client().get(
        reverse("geography:district_lookup"),
        {"departamento": "04", "buscar": "arequipa"},
    )
    results = response.json()["results"]

    assert len(results) == 2
    assert all(result["province"] == "Arequipa" for result in results)
