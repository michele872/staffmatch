from django.db import transaction
from rest_framework import serializers

from staffing.models import Assignment, City, Shift, Role, RoleRequirement, StaffMember


class CitySerializer(serializers.ModelSerializer):
    latitude = serializers.FloatField(source="location.y", read_only=True)
    longitude = serializers.FloatField(source="location.x", read_only=True)

    class Meta:
        model = City
        fields = ["id", "name", "latitude", "longitude"]


class StaffMemberSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)

    class Meta:
        model = StaffMember
        fields = ["id", "full_name", "role", "city", "city_name", "max_travel_km", "active"]


class RoleRequirementSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleRequirement
        fields = ["role", "quantity"]


class AssignmentSerializer(serializers.ModelSerializer):
    staff_name = serializers.CharField(source="staff.full_name", read_only=True)
    staff_city = serializers.CharField(source="staff.city.name", read_only=True)

    class Meta:
        model = Assignment
        fields = ["id", "staff", "staff_name", "staff_city", "role", "distance_km"]


class ShiftListSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    required_staff = serializers.IntegerField(read_only=True)
    assigned_staff = serializers.IntegerField(read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id", "title", "date", "city", "city_name", "patients",
            "required_staff", "assigned_staff",
        ]


class ShiftDetailSerializer(serializers.ModelSerializer):
    city_name = serializers.CharField(source="city.name", read_only=True)
    requirements = RoleRequirementSerializer(many=True)
    assignments = AssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = Shift
        fields = [
            "id", "title", "date", "city", "city_name", "patients", "notes",
            "requirements", "assignments", "created_at",
        ]
        read_only_fields = ["created_at"]

    def validate_requirements(self, value):
        if not value:
            raise serializers.ValidationError("Add at least one role.")
        roles = [item["role"] for item in value]
        if len(roles) != len(set(roles)):
            raise serializers.ValidationError("Each role can appear only once.")
        return value

    @transaction.atomic
    def create(self, validated_data):
        requirements = validated_data.pop("requirements")
        shift = Shift.objects.create(**validated_data)
        RoleRequirement.objects.bulk_create(
            RoleRequirement(shift=shift, **item) for item in requirements
        )
        return shift


class RolePlanSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=Role.choices)
    required = serializers.IntegerField()
    already_assigned = serializers.IntegerField()
    missing = serializers.IntegerField()
    candidates = serializers.SerializerMethodField()

    def get_candidates(self, plan):
        return [
            {
                "staff": candidate.staff.id,
                "staff_name": candidate.staff.full_name,
                "staff_city": candidate.staff.city.name,
                # Same representation as Assignment.distance_km (DRF DecimalField).
                "distance_km": str(candidate.distance_km),
            }
            for candidate in plan.candidates
        ]


class IntakeRequestSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=5000, trim_whitespace=True)
