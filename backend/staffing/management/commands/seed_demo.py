import random
from datetime import timedelta

from django.contrib.gis.geos import Point
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from staffing.models import City, Shift, Role, RoleRequirement, StaffMember
from staffing.services.matching import assign_staff

# (name, latitude, longitude)
CITIES = [
    ("Milano", 45.4642, 9.1900),
    ("Monza", 45.5845, 9.2744),
    ("Bergamo", 45.6983, 9.6773),
    ("Brescia", 45.5416, 10.2118),
    ("Como", 45.8081, 9.0852),
    ("Varese", 45.8206, 8.8251),
    ("Pavia", 45.1847, 9.1582),
    ("Lodi", 45.3097, 9.5037),
    ("Novara", 45.4469, 8.6219),
    ("Piacenza", 45.0526, 9.6930),
    ("Torino", 45.0703, 7.6869),
    ("Verona", 45.4384, 10.9916),
    ("Genova", 44.4056, 8.9463),
    ("Bologna", 44.4949, 11.3426),
    ("Firenze", 43.7696, 11.2558),
    ("Roma", 41.9028, 12.4964),
    ("Napoli", 40.8518, 14.2681),
    ("Cosenza", 39.2983, 16.2537),
]

# Most of the staff pool lives around Milan, a few people elsewhere.
CITY_WEIGHTS = {
    "Milano": 10, "Monza": 4, "Bergamo": 4, "Brescia": 3, "Como": 2, "Varese": 2,
    "Pavia": 2, "Lodi": 2, "Novara": 2, "Piacenza": 1, "Torino": 4, "Verona": 2,
    "Genova": 1, "Bologna": 2, "Firenze": 1, "Roma": 2, "Napoli": 1, "Cosenza": 1,
}

ROLE_WEIGHTS = {Role.CARE_ASSISTANT: 40, Role.NURSE: 35, Role.PHYSIOTHERAPIST: 15, Role.DOCTOR: 10}

FIRST_NAMES = [
    "Giulia", "Marco", "Chiara", "Luca", "Sara", "Andrea", "Francesca", "Matteo",
    "Elena", "Davide", "Valentina", "Simone", "Martina", "Federico", "Alessia",
    "Lorenzo", "Silvia", "Paolo", "Laura", "Stefano", "Irene", "Riccardo", "Anna",
    "Tommaso", "Beatrice", "Gabriele", "Marta", "Nicola",
]
LAST_NAMES = [
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo", "Ricci",
    "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini", "Costa",
    "Giordano", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana", "Santoro",
    "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli",
]

STAFF_COUNT = 60

# (title, city, days from today, patients, {role: quantity}, notes)
SHIFTS = [
    ("Night shift · Villa Aurora care home", "Milano", 2, 60,
     {Role.NURSE: 2, Role.CARE_ASSISTANT: 4}, "22:00 to 07:00, two wards."),
    ("Weekend cover · Rehabilitation clinic", "Bergamo", 5, 90,
     {Role.NURSE: 3, Role.CARE_ASSISTANT: 5, Role.PHYSIOTHERAPIST: 2, Role.DOCTOR: 1},
     "Day shift, 08:00 to 20:00."),
    ("Home-care rounds", "Torino", 9, 25,
     {Role.NURSE: 2, Role.PHYSIOTHERAPIST: 2}, "Visits across the city, own car needed."),
    ("Vaccination day · Community health centre", "Roma", 14, 400,
     {Role.DOCTOR: 2, Role.NURSE: 5, Role.CARE_ASSISTANT: 1}, "Walk-in clinic, 09:00 to 17:00."),
]


class Command(BaseCommand):
    help = "Load demo cities, staff and shifts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Do nothing if the database already contains cities.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["if_empty"] and City.objects.exists():
            self.stdout.write("Demo data already present, skipping.")
            return

        rng = random.Random(42)  # deterministic demo data

        cities = {
            name: City.objects.create(name=name, location=Point(lon, lat, srid=4326))
            for name, lat, lon in CITIES
        }

        full_names = rng.sample(
            [f"{first} {last}" for first in FIRST_NAMES for last in LAST_NAMES], STAFF_COUNT
        )
        StaffMember.objects.bulk_create(
            StaffMember(
                full_name=full_name,
                role=rng.choices(list(ROLE_WEIGHTS), weights=list(ROLE_WEIGHTS.values()))[0],
                city=cities[
                    rng.choices(list(CITY_WEIGHTS), weights=list(CITY_WEIGHTS.values()))[0]
                ],
                max_travel_km=rng.choice([30, 50, 80, 120]),
            )
            for full_name in full_names
        )

        today = timezone.localdate()
        shifts = []
        for title, city, days, patients, roles, notes in SHIFTS:
            shift = Shift.objects.create(
                title=title,
                city=cities[city],
                date=today + timedelta(days=days),
                patients=patients,
                notes=notes,
            )
            RoleRequirement.objects.bulk_create(
                RoleRequirement(shift=shift, role=role, quantity=quantity)
                for role, quantity in roles.items()
            )
            shifts.append(shift)

        # Staff the first shift so the demo shows both states.
        assign_staff(shifts[0])

        self.stdout.write(self.style.SUCCESS(
            f"Created {len(cities)} cities, {STAFF_COUNT} staff members, {len(shifts)} shifts."
        ))
