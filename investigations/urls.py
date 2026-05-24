from django.urls import include, path
from rest_framework.routers import DefaultRouter

from investigations.views import InvestigationCaseViewSet, health

router = DefaultRouter()
router.register("cases", InvestigationCaseViewSet, basename="case")

urlpatterns = [
    path("health/", health, name="health"),
    path("", include(router.urls)),
]
