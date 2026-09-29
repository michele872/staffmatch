from django.contrib.gis.db import models
from django.core.validators import MinValueValidator


class Role(models.TextChoices):
    NURSE = "NURSE", "Nurse"
    CARE_ASSISTANT = "CARE_ASSISTANT", "Care assistant"
    PHYSIOTHERAPIST = "PHYSIOTHERAPIST", "Physiotherapist"
    DOCTOR = "DOCTOR", "Doctor"


class City(models.Model):
    name = models.CharField(max_length=100, unique=True)
    # geography=True makes PostGIS compute distances in metres on the spheroid.
    location = models.PointField(geography=True, srid=4326)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "cities"

    def __str__(self) -> str:
        return self.name


class StaffMember(models.Model):
    full_name = models.CharField(max_length=150)
    role = models.CharField(max_length=20, choices=Role.choices)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="staff")
    max_travel_km = models.PositiveIntegerField(
        default=50,
        validators=[MinValueValidator(1)],
        help_text="Maximum distance this person is willing to travel for a shift.",
    )
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} ({self.get_role_display()})"


class Shift(models.Model):
    title = models.CharField(max_length=200)
    date = models.DateField()
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="shifts")
    patients = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["date", "title"]

    def __str__(self) -> str:
        return f"{self.title} ({self.date})"


class RoleRequirement(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="requirements")
    role = models.CharField(max_length=20, choices=Role.choices)
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        ordering = ["role"]
        constraints = [
            models.UniqueConstraint(fields=["shift", "role"], name="unique_role_per_shift"),
        ]

    def __str__(self) -> str:
        return f"{self.quantity} x {self.get_role_display()}"


class Assignment(models.Model):
    shift = models.ForeignKey(Shift, on_delete=models.CASCADE, related_name="assignments")
    staff = models.ForeignKey(StaffMember, on_delete=models.CASCADE, related_name="assignments")
    role = models.CharField(max_length=20, choices=Role.choices)
    distance_km = models.DecimalField(max_digits=7, decimal_places=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["role", "distance_km"]
        constraints = [
            models.UniqueConstraint(fields=["shift", "staff"], name="unique_staff_per_shift"),
        ]

    def __str__(self) -> str:
        return f"{self.staff} -> {self.shift}"
