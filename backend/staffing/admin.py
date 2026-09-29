from django.contrib.gis import admin

from staffing.models import Assignment, City, Shift, RoleRequirement, StaffMember


@admin.register(City)
class CityAdmin(admin.GISModelAdmin):
    search_fields = ["name"]


@admin.register(StaffMember)
class StaffMemberAdmin(admin.ModelAdmin):
    list_display = ["full_name", "role", "city", "max_travel_km", "active"]
    list_filter = ["role", "active", "city"]
    search_fields = ["full_name"]


class RoleRequirementInline(admin.TabularInline):
    model = RoleRequirement
    extra = 0


class AssignmentInline(admin.TabularInline):
    model = Assignment
    extra = 0
    readonly_fields = ["distance_km"]


@admin.register(Shift)
class ShiftAdmin(admin.ModelAdmin):
    list_display = ["title", "date", "city", "patients"]
    list_filter = ["city"]
    inlines = [RoleRequirementInline, AssignmentInline]
