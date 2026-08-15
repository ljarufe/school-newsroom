from django.urls import path

from .views import district_lookup

app_name = "geography"

urlpatterns = [
    path("distritos/", district_lookup, name="district_lookup"),
]
