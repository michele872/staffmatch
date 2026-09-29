from django.urls import include, path
from rest_framework.routers import DefaultRouter

from staffing import views

router = DefaultRouter()
router.register("cities", views.CityViewSet)
router.register("staff", views.StaffMemberViewSet, basename="staff")
router.register("shifts", views.ShiftViewSet, basename="shift")
router.register("assignments", views.AssignmentViewSet)

urlpatterns = [
    path("meta/", views.meta),
    path("", include(router.urls)),
]
