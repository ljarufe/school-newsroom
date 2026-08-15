from collections import Counter

from django.contrib.postgres.lookups import Unaccent
from django.db.models import CharField
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Department, District

CharField.register_lookup(Unaccent)

DISTRICT_RESULT_LIMIT = 20


@require_GET
def district_lookup(request):
    department_code = request.GET.get("departamento", "").strip()
    search = " ".join(request.GET.get("buscar", "").split())
    if (
        not department_code
        or not Department.objects.filter(code=department_code, is_active=True).exists()
    ):
        return JsonResponse({"results": []}, status=400)
    if len(search) < 3:
        return JsonResponse({"results": []})

    districts = list(
        District.objects.filter(
            is_active=True,
            province__is_active=True,
            province__department_id=department_code,
            name__unaccent__icontains=search,
        )
        .select_related("province")
        .order_by("name", "code")[:DISTRICT_RESULT_LIMIT]
    )
    name_counts = Counter(district.name.casefold() for district in districts)
    results = []
    for district in districts:
        result = {"code": district.code, "name": district.name}
        if name_counts[district.name.casefold()] > 1:
            result["province"] = district.province.name
        results.append(result)
    return JsonResponse({"results": results})
