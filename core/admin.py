from django.contrib import admin
from .models import *

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'fullname', 'role', 'gender', 'email', 'phonenumber', 'created_at')
    search_fields = ('username', 'fullname', 'email')
    list_filter = ('role', 'gender')

@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    list_display = ('name', 'species', 'breed', 'gender', 'birth_date', 'owner')
    search_fields = ('name', 'species', 'breed')
    list_filter = ('species', 'gender')

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'pet', 'owner', 'check_in', 'check_out', 'status')
    search_fields = ('id', 'pet__name', 'owner__fullname')
    list_filter = ('type', 'status', 'check_in', 'check_out')

@admin.register(NutritionPlan)
class NutritionPlanAdmin(admin.ModelAdmin):
    list_display = ('id', 'pet', 'created_by', 'created_at')
    search_fields = ('pet__name',)
    list_filter = ('created_at',)

@admin.register(BeautyServiceHistory)
class BeautyServiceHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'service_type')
    search_fields = ('service_type',)

@admin.register(HotelServiceHistory)
class HotelServiceHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'room_type', 'room_number')
    search_fields = ('room_number',)

@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'appointment', 'diagnosis')
    search_fields = ('diagnosis',)

@admin.register(VaccinationHistory)
class VaccinationHistoryAdmin(admin.ModelAdmin):
    list_display = ('vaccine_name', 'vaccination_date', 'pet_name', 'is_completed')
    list_filter = ('is_completed', 'vaccination_date')
    search_fields = ('vaccine_name',)

    def pet_name(self, obj):
        return obj.appointment.pet.name
