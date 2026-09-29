from django.db.models import Count, OuterRef, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from staffing.models import Assignment, City, Shift, StaffMember
from staffing.serializers import (
    AssignmentSerializer,
    CitySerializer,
    ShiftDetailSerializer,
    ShiftListSerializer,
    IntakeRequestSerializer,
    RolePlanSerializer,
    StaffMemberSerializer,
)
from staffing.services import ai_intake, matching


@api_view(["GET"])
def meta(request):
    """Feature flags the frontend needs at startup."""
    return Response({"ai_intake_enabled": ai_intake.is_enabled()})


class CityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    pagination_class = None


class StaffMemberViewSet(viewsets.ModelViewSet):
    serializer_class = StaffMemberSerializer
    pagination_class = None

    def get_queryset(self):
        queryset = StaffMember.objects.select_related("city")
        role = self.request.query_params.get("role")
        city = self.request.query_params.get("city")
        if role:
            queryset = queryset.filter(role=role)
        if city:
            queryset = queryset.filter(city_id=city)
        return queryset


class ShiftViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    pagination_class = None

    def get_queryset(self):
        if self.action == "list":
            # Two separate aggregates on different relations would multiply
            # each other in a single JOIN, so they are computed as subqueries.
            required = (
                Shift.objects.filter(pk=OuterRef("pk"))
                .annotate(total=Sum("requirements__quantity"))
                .values("total")
            )
            assigned = (
                Shift.objects.filter(pk=OuterRef("pk"))
                .annotate(total=Count("assignments"))
                .values("total")
            )
            return Shift.objects.select_related("city").annotate(
                required_staff=Coalesce(Subquery(required), 0),
                assigned_staff=Coalesce(Subquery(assigned), 0),
            )
        return Shift.objects.select_related("city").prefetch_related(
            "requirements", "assignments__staff__city"
        )

    def get_serializer_class(self):
        return ShiftListSerializer if self.action == "list" else ShiftDetailSerializer

    @action(detail=True, methods=["get"])
    def plan(self, request, pk=None):
        """Preview: the closest available people for every open position."""
        plans = matching.build_plan(self.get_object())
        return Response(RolePlanSerializer(plans, many=True).data)

    @action(detail=True, methods=["post"])
    def assign(self, request, pk=None):
        """Fill the open positions with the proposed people and save them."""
        shift = self.get_object()
        matching.assign_staff(shift)
        shift = self.get_queryset().get(pk=shift.pk)
        return Response(ShiftDetailSerializer(shift).data)

    @action(detail=False, methods=["post"], url_path="draft-from-text")
    def draft_from_text(self, request):
        """Turn a free-text staffing request into a shift draft (not saved)."""
        serializer = IntakeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cities = {city.name: city.id for city in City.objects.all()}
        try:
            draft = ai_intake.draft_shift(
                serializer.validated_data["text"],
                known_cities=list(cities),
                today=timezone.localdate(),
            )
        except ai_intake.AIIntakeDisabled as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except ai_intake.AIIntakeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        data = draft.model_dump()
        data["city"] = cities.get(draft.city)
        return Response(data)


class AssignmentViewSet(mixins.DestroyModelMixin, viewsets.GenericViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
