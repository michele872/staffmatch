from datetime import date

from django.contrib.gis.geos import Point

from staffing.models import City, Shift, Role, RoleRequirement, StaffMember

# Real coordinates, so distances in tests match what users would see.
MILANO = (45.4642, 9.1900)
MONZA = (45.5845, 9.2744)  # ~15 km from Milano
BERGAMO = (45.6983, 9.6773)  # ~45 km from Milano
ROMA = (41.9028, 12.4964)  # ~480 km from Milano


def make_city(name: str, lat_lon: tuple[float, float]) -> City:
    lat, lon = lat_lon
    return City.objects.create(name=name, location=Point(lon, lat, srid=4326))


def make_staff(name: str, city: City, role: str = Role.CARE_ASSISTANT, max_travel_km: int = 50,
               active: bool = True) -> StaffMember:
    return StaffMember.objects.create(
        full_name=name, city=city, role=role, max_travel_km=max_travel_km, active=active
    )


def make_shift(city: City, requirements: dict[str, int], on: date = date(2030, 6, 14),
               title: str = "Night shift") -> Shift:
    shift = Shift.objects.create(title=title, city=city, date=on, patients=100)
    for role, quantity in requirements.items():
        RoleRequirement.objects.create(shift=shift, role=role, quantity=quantity)
    return shift
