from datetime import date
from django.db import models
import uuid
from enum import Enum

# Enum types
class AppointmentType(Enum):
    MEDICAL = 'medical'
    BEAUTY = 'beauty'
    HOTEL = 'hotel'
    VACCINE = 'vaccine'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class Gender(Enum):
    MALE = 'Male'
    FEMALE = 'Female'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class Status(Enum):
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

class UserRole(Enum):
    ADMIN = 'Admin'
    OWNER = 'Owner'
    STAFF = 'Staff'
    VET = 'Vet'

    @classmethod
    def choices(cls):
        return [(key.value, key.name) for key in cls]

# Models
class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="user_id")
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.TextField()
    role = models.CharField(max_length=20, choices=UserRole.choices())
    gender = models.CharField(max_length=10, choices=Gender.choices())
    fullname = models.CharField(max_length=100)
    email = models.CharField(max_length=100)
    phonenumber = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'users'

    def __str__(self):
        return f"{self.fullname} ({self.username})"

class Pet(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="pet_id")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pets', db_column="owner_id")
    name = models.CharField(max_length=50)
    species = models.CharField(max_length=30)
    breed = models.CharField(max_length=30)
    gender = models.CharField(max_length=10)
    birth_date = models.DateField()
    fur_color = models.CharField(max_length=30)
    image_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        db_table = 'pets'

    def __str__(self):
        return f"{self.name} ({self.species})"
    @property
    def gender_vi(self):
        if self.gender == "Male":
            return "Đực"
        else:
            return "Cái"

    @property
    def age(self):
        if not self.birth_date:
            return "Không rõ"
        
        today = date.today()
        years = today.year - self.birth_date.year
        months = today.month - self.birth_date.month
        days = today.day - self.birth_date.day

        if days < 0:
            months -= 1
        if months < 0:
            years -= 1
            months += 12

        if years >= 1:
            return f"{years} tuổi"
        else:
            return f"{months} tháng"

class Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="appointment_id")
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name='appointments', db_column="pet_id")
    owner = models.ForeignKey(User, on_delete=models.CASCADE, db_column="owner_id")
    type = models.CharField(max_length=20, choices=AppointmentType.choices())
    check_in = models.DateField()
    check_out = models.DateField()
    staff = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='staff_appointments', db_column="staff_id")
    status = models.CharField(max_length=20, choices=Status.choices(), default=Status.PENDING.value)
    approver = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='approved_appointments', db_column="approver_id")
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'appointments'

    def __str__(self):
        return f"Appointment {self.id} - {self.get_type_display()}"
    @property
    def status_display(self):
        return self.get_status_display()

    @property
    def type_display(self):
        return self.get_type_display()


class NutritionPlan(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="plan_id")
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, db_column="pet_id")
    food_type = models.TextField()
    portion = models.TextField()
    note = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, db_column='created_by')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'nutrition_plans'

    def __str__(self):
        return f"Nutrition Plan for {self.pet.name}"

class BeautyServiceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="beauty_id")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, db_column="appointment_id")
    service_type = models.CharField(max_length=50)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'beauty_service_history'

    def __str__(self):
        return f"Beauty Service {self.service_type}"

class HotelServiceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="hotel_id")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, db_column="appointment_id")
    room_type = models.CharField(max_length=30)
    room_number = models.CharField(max_length=20)
    special_needs = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'hotel_service_history'

    def __str__(self):
        return f"Hotel Service {self.room_type}"

class MedicalHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="record_id")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, db_column="appointment_id")
    diagnosis = models.TextField()
    treatment = models.TextField()
    notes = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'medical_history'

    def __str__(self):
        return f"Medical Record {self.id}"

class VaccinationHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, db_column="vaccination_id")
    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, db_column="appointment_id")
    vaccine_name = models.TextField()
    vaccination_date = models.DateField()
    next_due = models.DateField()
    total_doses = models.IntegerField()
    batch_number = models.CharField(max_length=50)
    is_completed = models.BooleanField(default=False)
    note = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'vaccination_history'

    def __str__(self):
        return f"{self.vaccine_name} on {self.vaccination_date}"
    
class Service(models.Model):
    type = models.CharField(max_length=20, primary_key=True)
    description = models.TextField()
    duration = models.CharField(max_length=100)
    price = models.IntegerField()

    class Meta:
        db_table = 'services'

    def __str__(self):
        return f"{self.type} - {self.price} VNĐ"