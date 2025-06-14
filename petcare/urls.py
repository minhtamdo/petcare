"""
URL configuration for petcare project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from itertools import chain
from django.shortcuts import render, redirect
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponseNotAllowed, HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import render
from django.db import connection
import json
from django.shortcuts import render, redirect
from core.models import *
from django.utils import timezone
from django.db.models import Sum, Q, OuterRef, Exists, F, Value, Min, DecimalField
from django.db.models.functions import Coalesce
from datetime import datetime, time, timedelta, date
from django.http import JsonResponse, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
import calendar
from openpyxl import Workbook 
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, get_object_or_404
import json
from django.db import connection
from django.shortcuts import redirect
from django.conf import settings
import stripe
import traceback
from django.utils.timezone import now
import logging
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_http_methods
import io
from collections import defaultdict
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.db.models import Count
from django.utils.dateparse import parse_date
from django.shortcuts import get_object_or_404
from django.utils import timezone
from datetime import datetime
from django.views.decorators.http import require_http_methods
from django.utils.dateparse import parse_date
from django.utils.timezone import make_aware

@csrf_exempt
def login_view(request):
    if request.method == 'GET':
        return render(request, 'login.html')

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            role_input = data.get('role')  # 'Vet', 'Staff', 'Owner'

            if not all([username, password, role_input]):
                return JsonResponse({'success': False, 'message': 'Vui lòng nhập đầy đủ thông tin.'})

            # Truy vấn từ bảng 'users' (bạn đã custom model)
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT user_id, username, fullname, role
                    FROM users
                    WHERE username = %s
                      AND role = %s
                      AND password_hash = crypt(%s, password_hash)
                """, [username, role_input, password])
                user = cursor.fetchone()

            if user:
                request.session['user_id'] = str(user[0])
                request.session['username'] = user[1]
                request.session['fullname'] = user[2]
                request.session['role'] = user[3]

                return JsonResponse({
                    'success': True,
                    'redirect_url': get_redirect_url(user[3]),
                    'user': {
                        'username': user[1],
                        'fullname': user[2],
                        'role': user[3]
                    }
                })
            else:
                return JsonResponse({'success': False, 'message': 'Sai tài khoản, mật khẩu hoặc vai trò.'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Lỗi hệ thống: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Chỉ hỗ trợ phương thức POST'})


def get_redirect_url(role):
    if role == 'Vet':
        return '/vet/'
    elif role == 'Staff':
        return '/staff/'
    elif role == 'Owner':
        return '/owner/'
    return '/login/'


def vet_dashboard(request):
    if request.session.get('role') != 'Vet':
        return redirect('/login')
    user_id = request.session.get('user_id')
    total_pets = Pet.objects.count()
    today = date.today()
    today_appointments = Appointment.objects.filter(
        type='medical',
        staff_id=user_id,
        check_in=today
    ).count()
    vaccine_count = Appointment.objects.filter(
        staff_id=user_id,
        check_in=today,
        type='vaccine',
        status='pending'
    ).count()
    return render(request, 'vet.html', {
        'total_pets': total_pets,
        'today_appointments': today_appointments,
        'vaccine_count': vaccine_count
        })

def recent_activities(request):
    user_id = request.session.get('user_id')
    today = date.today()

    # Lấy 5 lịch hẹn gần nhất nhưng không bao gồm hôm nay
    appointments = (
        Appointment.objects
        .filter(check_in__lt=today, staff_id=user_id)
        .select_related('pet')
        .order_by('-check_in')[:5]
    )

    data = []
    for a in appointments:
        data.append({
            'check_in': a.check_in.strftime('%d/%m/%Y'),  # ❗ Chỉ ngày
            'pet_name': f"{a.pet.name} ({a.pet.species})",  # ❗ Giống loài
            'type': a.get_type_display(),
            'status': a.status,
        })
    
    return JsonResponse(data, safe=False)

def pet_list(request):
    pets = Pet.objects.select_related('owner').all().order_by('-created_at')

    data = []
    for pet in pets:
        data.append({
            'id': str(pet.id),
            'name': pet.name,
            'species': pet.species,
            'breed': pet.breed,
            'age': pet.age,
            'avatar': pet.image_url,
            'owner': pet.owner.fullname,
            'phone': pet.owner.phonenumber,
        })

    return JsonResponse(data, safe=False)

def owner_dashboard(request):
    if request.session.get('role') != 'Owner':
        return redirect('/login')

    user_id = request.session.get('user_id')
    if not user_id:
        return redirect('/login')

    owner_uuid = uuid.UUID(user_id)
    user = User.objects.get(id=owner_uuid)

    total_pets = Pet.objects.filter(owner_id=owner_uuid).count()
    total_bookings = Appointment.objects.filter(owner_id=owner_uuid).count()
    pets = Pet.objects.filter(owner_id=owner_uuid)

    return render(request, 'owner.html', {
        'total_pets': total_pets,
        'total_bookings': total_bookings,
        'user_fullname': user.fullname,
        'user_email': user.email,
        'user_phone': user.phonenumber,
        'pets': pets,
    })


def get_owner_pets(request):
    owner_id = request.session.get('user_id')
    if not owner_id:
        return JsonResponse({'error': 'Bạn chưa đăng nhập'}, status=401)

    try:
        owner_uuid = uuid.UUID(owner_id)
        pets = Pet.objects.filter(owner_id=owner_uuid).values('id', 'name')
        return JsonResponse(list(pets), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
def create_appointment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            pet_id = data.get('pet_id')
            appointment_type = data.get('type')
            notes = data.get('notes', '')

            if not pet_id or not appointment_type:
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            pet = Pet.objects.get(id=pet_id)
            owner = pet.owner

            if appointment_type == 'hotel':
                check_in = data.get('check_in_date')
                check_out = data.get('check_out_date')
                if not check_in or not check_out:
                    return JsonResponse({'error': 'Missing check-in or check-out date'}, status=400)
            else:
                appointment_date = data.get('appointment_date')
                if not appointment_date:
                    return JsonResponse({'error': 'Missing appointment date'}, status=400)
                check_in = appointment_date
                check_out = appointment_date  # ➕ giống nhau cho các dịch vụ không phải cư trú

            appointment = Appointment.objects.create(
                pet=pet,
                owner=owner,
                type=appointment_type,
                check_in=check_in,
                check_out=check_out,
                notes=notes
            )

            return JsonResponse({'message': 'Appointment created successfully'}, status=200)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    print(f"DATA: {data}")
    return JsonResponse({'error': 'Invalid request method'}, status=405)

def get_current_user(request):
    user_id = request.session.get('user_id')  # Hoặc token/session tùy bạn xử lý
    return User.objects.get(id=user_id)

def get_account_info(request):
    user = get_current_user(request)
    return JsonResponse({
        'fullname': user.fullname,
        'email': user.email,
        'phonenumber': user.phonenumber
    })

@csrf_exempt
def update_account_info(request):
    if request.method == 'POST':
        user = get_current_user(request)
        data = json.loads(request.body)

        user.fullname = data.get('fullname', user.fullname)
        user.email = data.get('email', user.email)
        user.phonenumber = data.get('phonenumber', user.phonenumber)
        user.save()

        return JsonResponse({'success': True, 'message': 'Thông tin đã được cập nhật.'})
    return JsonResponse({'error': 'Phương thức không được hỗ trợ.'}, status=405)

def upcoming_appointments(request):
    user = get_current_user(request)
    if not user:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    now = timezone.now().date()

    appointments = Appointment.objects.filter(
        owner=user,
        status='confirmed',
        check_out__gte=now  # những cuộc hẹn còn hiệu lực
    ).select_related('pet').order_by('check_in')

    data = []
    for appt in appointments:
        time_str = f"{appt.check_in} → {appt.check_out}" if appt.check_in != appt.check_out else str(appt.check_in)
        data.append({
            'id': str(appt.id),
            'type': appt.get_type_display(),
            'pet_name': appt.pet.name,
            'time': time_str,
            'notes': appt.notes
        })

    return JsonResponse(data, safe=False)

def pets_list_view(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    pets = Pet.objects.filter(owner_id=user_id)

    pet_data = []
    for pet in pets:
        pet_data.append({
            'id': str(pet.id),
            'name': pet.name,
            'species': pet.species,
            'breed': pet.breed,
            'gender': pet.gender,
            'gender_vi': pet.gender_vi,
            'age': pet.age,
            'fur_color': pet.fur_color,
            'image_url': pet.image_url
        })

    return JsonResponse(pet_data, safe=False)

def vaccination_schedule_list(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    vaccinations = (
        VaccinationHistory.objects
        .select_related('appointment__pet')
        .filter(appointment__staff_id=user_id)
        .order_by('-vaccination_date')
    )

    data = []
    for v in vaccinations:
        data.append({
            'id': str(v.id),
            'pet_name': v.appointment.pet.name,
            'pet_species': v.appointment.pet.species,
            'vaccine_name': v.vaccine_name,
            'vaccination_date': v.vaccination_date.strftime('%d/%m/%Y'),
            'next_due': v.next_due.strftime('%d/%m/%Y') if v.next_due else '',
            'total_doses': v.total_doses,
            'batch_number': v.batch_number,
            'note': v.note or '',
            'is_completed': v.is_completed,
        })

    return JsonResponse(data, safe=False)


@csrf_exempt 
def update_vaccination(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Chỉ chấp nhận POST'}, status=405)

    try:
        data = json.loads(request.body)
        v = VaccinationHistory.objects.get(id=id)
        v.vaccine_name = data.get('vaccine_name', v.vaccine_name)
        v.batch_number = data.get('batch_number', v.batch_number)
        v.note = data.get('note', v.note)
        v.total_doses = int(data.get('total_doses', v.total_doses))

        # Xử lý ngày (nếu có)
        next_due = data.get('next_due')
        if next_due:
            from datetime import datetime
            v.next_due = datetime.strptime(next_due, "%Y-%m-%d").date()

        # Cập nhật trạng thái tiêm
        if 'is_completed' in data:
            v.is_completed = data['is_completed']

        v.save()

        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


def vaccination_history_all(request):
    histories = (
        VaccinationHistory.objects
        .select_related('appointment__pet', 'appointment__staff')
        .order_by('-vaccination_date')
    )

    data = []
    for v in histories:
        data.append({
            'pet_name': v.appointment.pet.name,
            'pet_species': v.appointment.pet.species,
            'vaccine_name': v.vaccine_name,
            'vaccination_date': v.vaccination_date.strftime('%d/%m/%Y'),
            'batch_number': v.batch_number,
            'note': v.note or '',
            'staff_name': v.appointment.staff.fullname if v.appointment.staff else 'N/A',
        })

    return JsonResponse(data, safe=False)

def user_examinations_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    appointments = Appointment.objects.filter(
        staff_id=user_id,
        type='medical',
    ).select_related('pet', 'owner')

    data = []
    for appt in appointments:
        data.append({
            'id': str(appt.id),
            'check_in': appt.check_in.strftime('%Y-%m-%d'),
            'pet': appt.pet.name,
            'owner': appt.owner.fullname,
            'phonenumber': appt.owner.phonenumber,
            'status': appt.status,
            'type': appt.get_type_display(),
        })

    return JsonResponse(data, safe=False)


@csrf_exempt
def update_status_view(request, appointment_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Phải dùng POST'}, status=405)

    try:
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

        data = json.loads(request.body)
        new_status = data.get('status')

        if new_status not in ['pending', 'confirmed', 'completed', 'cancelled']:
            return JsonResponse({'error': 'Trạng thái không hợp lệ'}, status=400)

        appt = Appointment.objects.get(id=appointment_id, staff_id=user_id)
        appt.status = new_status
        appt.save()

        return JsonResponse({'success': True})
    except Appointment.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy lịch hẹn'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def medical_history_by_staff(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    histories = (
        MedicalHistory.objects
        .select_related('appointment__pet', 'appointment__owner', 'appointment__staff')
        .filter(appointment__staff_id=user_id)
        .order_by('-appointment__check_in')
    )

    data = []
    for record in histories:
        appt = record.appointment
        data.append({
            'id': str(record.id),
            'pet': appt.pet.name,
            'owner_phone': appt.owner.phonenumber,
            'date': appt.check_in.strftime('%Y-%m-%d'),
            'diagnosis': record.diagnosis,
            'treatment': record.treatment,
            'notes': record.notes or '',
        })

    return JsonResponse(data, safe=False)

@csrf_exempt
def update_medical_record(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Chỉ hỗ trợ POST'}, status=405)

    try:
        record = MedicalHistory.objects.select_related('appointment').get(id=id)
        user_id = request.session.get('user_id')

        if str(record.appointment.staff_id) != str(user_id):
            return JsonResponse({'error': 'Không có quyền chỉnh sửa'}, status=403)

        data = json.loads(request.body)
        record.diagnosis = data.get('diagnosis', record.diagnosis)
        record.treatment = data.get('treatment', record.treatment)
        record.notes = data.get('notes', record.notes)
        record.save()

        return JsonResponse({'success': True})
    except MedicalHistory.DoesNotExist:
        return JsonResponse({'error': 'Bệnh án không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def nutrition_plan_by_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    plans = NutritionPlan.objects.filter(created_by_id=user_id).select_related('pet').order_by('-updated_at')

    data = []
    for plan in plans:
        data.append({
            'id': str(plan.id),
            'pet_name': plan.pet.name,
            'species': plan.pet.species,
            'food_type': plan.food_type,
            'portion': plan.portion,
            'note': plan.note or '',
            'created_at': plan.created_at.strftime('%Y-%m-%d %H:%M'),
            'updated_at': plan.updated_at.strftime('%Y-%m-%d %H:%M'),
        })

    return JsonResponse(data, safe=False)

@csrf_exempt
def create_nutrition_plan(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        pet_id = data.get('pet_id')
        food_type = data.get('food_type')
        portion = data.get('portion')
        note = data.get('note', '')

        user_id = request.session.get('user_id')  # Lấy từ session
        if not user_id:
            return JsonResponse({'success': False, 'error': 'User chưa đăng nhập.'})

        try:
            pet = Pet.objects.get(id=pet_id)
            created_by = User.objects.get(id=user_id)  # lấy custom User model

            NutritionPlan.objects.create(
                pet=pet,
                food_type=food_type,
                portion=portion,
                note=note,
                created_by=created_by
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Invalid request'})

@csrf_exempt
def update_nutrition_plan(request, id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Chỉ hỗ trợ POST'}, status=405)

    try:
        plan = NutritionPlan.objects.get(id=id)
        user_id = request.session.get('user_id')

        if str(plan.created_by_id) != str(user_id):
            return JsonResponse({'error': 'Không có quyền sửa'}, status=403)

        data = json.loads(request.body)
        plan.food_type = data.get('food_type', plan.food_type)
        plan.portion = data.get('portion', plan.portion)
        plan.note = data.get('note', plan.note)
        plan.save()

        return JsonResponse({'success': True})
    except NutritionPlan.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy chế độ ăn'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def delete_nutrition_plan(request, id):
    if request.method != 'DELETE':
        return JsonResponse({'error': 'Chỉ hỗ trợ DELETE'}, status=405)

    try:
        plan = NutritionPlan.objects.get(id=id)
        user_id = request.session.get('user_id')

        if str(plan.created_by_id) != str(user_id):
            return JsonResponse({'error': 'Không có quyền xóa'}, status=403)

        plan.delete()
        return JsonResponse({'success': True})
    except NutritionPlan.DoesNotExist:
        return JsonResponse({'error': 'Không tìm thấy bản ghi'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def create_appointment_by_staff(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=405)

    try:
        data = json.loads(request.body)
        staff_id = request.session.get('user_id')
        if not staff_id:
            return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

        pet = Pet.objects.select_related('owner').get(id=data['pet_id'])

        appointment = Appointment.objects.create(
            pet=pet,
            owner=pet.owner,
            staff_id=staff_id,
            approver_id=staff_id,  # hoặc để None nếu cần duyệt
            check_in=data['check_in'],
            check_out=data['check_in'],  # lịch khám trong ngày
            type='medical',
            status='pending',  # hoặc Status.PENDING.value
            notes=data.get('notes', '')
        )

        return JsonResponse({'success': True, 'id': str(appointment.id)})

    except Pet.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Thú cưng không tồn tại'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

def list_all_pets(request):
    pets = Pet.objects.select_related('owner').all()
    data = []

    for pet in pets:
        data.append({
            'id': str(pet.id),
            'name': pet.name,
            'species': pet.species,
            'breed': pet.breed,
            'owner_name': pet.owner.fullname,
            'owner_phone': pet.owner.phonenumber
        })

    return JsonResponse(data, safe=False)

def pet_detail_view(request, pet_id):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    pet = get_object_or_404(Pet, id=pet_id, owner_id=user_id)
    return JsonResponse({
        'id': str(pet.id),
        'name': pet.name,
        'species': pet.species,
        'breed': pet.breed,
        'birth_date': str(pet.birth_date),
        'gender': pet.gender,
        'fur_color': pet.fur_color,
        'image_url': pet.image_url
    })

@csrf_exempt
def delete_pet_view(request, pet_id):
    if request.method == "DELETE":
        try:
            pet = Pet.objects.get(id=pet_id)
            pet.delete()
            return JsonResponse({'success': True})
        except Pet.DoesNotExist:
            return HttpResponseNotFound("Thú cưng không tồn tại.")
    else:
        return HttpResponseNotAllowed(['DELETE'])


@csrf_exempt
def create_pet(request):
    if request.method == 'POST':
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

        data = json.loads(request.body)
        pet = Pet.objects.create(
            owner_id=user_id,
            name=data['name'],
            species=data['species'],
            breed=data.get('breed'),
            birth_date=data['birth_date'],
            gender=data['gender'],
            fur_color=data.get('fur_color'),
            image_url=data.get('image_url')
        )
        return JsonResponse({'success': True, 'id': str(pet.id)})

@csrf_exempt
def update_pet(request, pet_id):
    if request.method == 'PUT':
        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

        try:
            pet = Pet.objects.get(id=pet_id, owner_id=user_id)
        except Pet.DoesNotExist:
            return JsonResponse({'error': 'Không tìm thấy thú cưng'}, status=404)

        data = json.loads(request.body)
        pet.name = data['name']
        pet.species = data['species']
        pet.breed = data.get('breed')
        pet.birth_date = data['birth_date']
        pet.gender = data['gender']
        pet.fur_color = data.get('fur_color')
        pet.image_url = data.get('image_url')
        pet.save()

        return JsonResponse({'success': True})


@csrf_exempt
def register_owner(request):
    if request.method != "POST":
        return JsonResponse({"error": "Phương thức không được hỗ trợ"}, status=405)

    try:
        data = json.loads(request.body.decode("utf-8"))

        required_fields = ["username", "password", "fullname", "gender", "email", "phonenumber"]
        for field in required_fields:
            if not data.get(field):
                return JsonResponse({"error": f"Trường '{field}' là bắt buộc"}, status=400)

        if User.objects.filter(username=data["username"]).exists():
            return JsonResponse({"error": "Tên đăng nhập đã tồn tại"}, status=400)

        user = User.objects.create(
            username=data["username"],
            password_hash=data["password"],  # giữ nguyên mật khẩu gốc
            role=UserRole.OWNER.value,
            gender=data["gender"],
            fullname=data["fullname"],
            email=data["email"],
            phonenumber=data["phonenumber"],
            created_at=now(),
            updated_at=now()
        )

        return JsonResponse({"message": "Đăng ký thành công"}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Dữ liệu không hợp lệ"}, status=400)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def appointment_history_view(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return JsonResponse({'error': 'Chưa đăng nhập'}, status=401)

    appointments = Appointment.objects.filter(owner_id=user_id).order_by('-check_in')
    data = [{
        'id': str(a.id),
        'service_name': a.get_type_display(),     # lấy tên hiển thị từ choices
        'pet_name': a.pet.name,
        'date': str(a.check_in),
        'time': '',  # bạn có thể thêm time nếu model có
        'status_vi': a.get_status_display()
    } for a in appointments]
    return JsonResponse(data, safe=False)

@csrf_exempt
def update_appointment(request, appointment_id):
    if request.method != 'POST':
        return JsonResponse({'error': 'Phải là POST'}, status=405)

    try:
        data = json.loads(request.body)

        appointment = Appointment.objects.get(id=appointment_id)

        # Kiểm tra quyền người dùng
        if str(appointment.owner_id) != str(request.session.get('user_id')):
            return JsonResponse({'error': 'Không có quyền chỉnh sửa'}, status=403)

        # Cập nhật dữ liệu
        appointment.check_in = data['date']
        appointment.pet_id = uuid.UUID(data['pet_id'])
        appointment.type = data['service'].upper()  # <-- nên luôn dùng upper() ở backend
        appointment.save()

        return JsonResponse({'success': True, 'message': 'Cập nhật thành công!'})

    except Appointment.DoesNotExist:
        return JsonResponse({'error': 'Lịch hẹn không tồn tại'}, status=404)

    except Exception as e:
        import traceback
        print(traceback.format_exc())  # In stacktrace vào terminal
        return JsonResponse({'error': f'Lỗi server: {str(e)}'}, status=500)


def logout_view(request):
    request.session.flush()
    return redirect('/login')

def register_page(request):
    return render(request, 'register.html')

def redirect_to_login(request):
    return redirect('/login/')

def staff_dashboard(request):
    if request.session.get('role') != 'Staff':
        return redirect('/login')
    
    pets = Pet.objects.select_related('owner').all().order_by('-created_at')
    total_pets = pets.count()

    pending_appointments = Appointment.objects.filter(status='pending').count()
    appointments = Appointment.objects.all()
    today = timezone.now().date()
    current_month = today.month
    current_year = today.year
    monthly_appointments = Appointment.objects.filter(
        check_in__year=current_year,
        check_in__month=current_month
    ).count()

    context = {
        'appointments' : appointments,
        'pets': pets,
        'total_pets': total_pets,
        'pending_appointments': pending_appointments,
        'monthly_appointments': monthly_appointments,
    }

    return render(request, 'staff.html', context)

def nutrition_view(request, pet_id):
    plans = NutritionPlan.objects.filter(pet__id=pet_id).select_related('created_by')
    data = [
        {
            "food_type": p.food_type,
            "portion": p.portion,
            "note": p.note,
            "created_by": p.created_by.fullname,
            "updated_at": p.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for p in plans
    ]
    return JsonResponse({"nutrition_plans": data})

def vaccination_view(request, pet_id):
    histories = VaccinationHistory.objects.select_related('appointment__pet')\
        .filter(appointment__pet_id=pet_id)

    data = [
        {
            "vaccine_name": h.vaccine_name,
            "vaccination_date": h.vaccination_date.isoformat(),
            "next_due": h.next_due.isoformat(),
            "total_doses": h.total_doses,
            "batch_number": h.batch_number,
            "is_completed": h.is_completed,
            "note": h.note,
        }
        for h in histories
    ]
    return JsonResponse(data, safe=False)

def service_view(request, pet_id):
    appointments = Appointment.objects.filter(pet_id=pet_id)
    beauty_services = BeautyServiceHistory.objects.filter(appointment__in=appointments).select_related('appointment')
    hotel_services = HotelServiceHistory.objects.filter(appointment__in=appointments).select_related('appointment')

    for item in beauty_services:
        item.service_category = 'beauty'
    for item in hotel_services:
        item.service_category = 'hotel'

    combined_services = sorted(
        chain(beauty_services, hotel_services),
        key=lambda x: x.appointment.check_in,
        reverse=True
    )

    data = []
    for service in combined_services:
        base = {
            "type": service.service_category,
            "check_in": service.appointment.check_in.isoformat(),
            "check_out": service.appointment.check_out.isoformat(),
        }

        if service.service_category == "beauty":
            base.update({
                "service_type": service.service_type,
                "notes": service.notes
            })
        else:
            base.update({
                "room_type": service.room_type,
                "room_number": service.room_number,
                "special_needs": service.special_needs
            })

        data.append(base)

    return JsonResponse(data, safe=False)

def medical_view(request, pet_id):
    records = MedicalHistory.objects.filter(appointment__pet_id=pet_id) \
        .select_related('appointment') \
        .order_by('-appointment__check_in')

    data = [
        {
            "diagnosis": record.diagnosis,
            "treatment": record.treatment,
            "notes": record.notes,
            "check_in": record.appointment.check_in.isoformat(),
            "check_out": record.appointment.check_out.isoformat()
        }
        for record in records
    ]

    return JsonResponse(data, safe=False)

@csrf_exempt
def update_appointment(request, appointment_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            action = data.get('action')

            req = Appointment.objects.get(id=appointment_id)

            if action == 'approve':
                req.status = 'confirmed'
            elif action == 'reject':
                req.status = 'cancelled'
            elif action == 'complete':
                req.status = 'completed'
            else:
                return JsonResponse({'success': False, 'message': 'Hành động không hợp lệ'})

            req.save()
            return JsonResponse({'success': True, 'new_status': req.status})

        except Appointment.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Cuộc hẹn không tồn tại'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ'})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('vet/', vet_dashboard, name='vet_dashboard'),
    path('staff/', staff_dashboard, name='staff_dashboard'),
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_page, name='register'),
    path('api/register/owner/', register_owner, name='register_owner'),
    path('nutrition/<uuid:pet_id>/', nutrition_view, name='get_nutrition_plan'),
    path('vaccinations/<uuid:pet_id>/', vaccination_view, name='get_vaccination_history'),
    path('services/<uuid:pet_id>/', service_view, name='get_service_history'),
    path('medical/<uuid:pet_id>/', medical_view, name='get_medical_history'),
    path('update-appointment/<uuid:appointment_id>/', update_appointment, name='update_appointment'),
    path('', redirect_to_login),
    path('api/pets/', get_owner_pets, name='get_owner_pets'),
    path('api/appointments/create/', create_appointment, name='create_appointment'),
    path('account/info/', get_account_info, name='account-info'),
    path('account/update/', update_account_info, name='account-update'),
    path('appointments/upcoming/', upcoming_appointments, name='upcoming-appointments'),
    path('pets/', pets_list_view, name='pets_list'),
    path('pets/<uuid:pet_id>/delete/', delete_pet_view, name='delete_pet'),
    path('pets/create/', create_pet),
    path('pets/<uuid:pet_id>/update/', update_pet),
    path('pets/<uuid:pet_id>/', pet_detail_view),
    path('appointments/history/', appointment_history_view),
    path('appointments/update/<uuid:appointment_id>/', update_appointment, name='update_appointment'),
    path('appointments/recent/', recent_activities, name='recent_activities'),
    path('pets/api/', pet_list, name='pet_list'),
    path('api/vaccinations/', vaccination_schedule_list, name='vaccination_schedule_list'),
    path('api/vaccinations/<uuid:id>/update/', update_vaccination, name='update_vaccination'),
    path('api/vaccinations/history/', vaccination_history_all, name='vaccination_history_all'),
    path('examinations/user/', user_examinations_view, name='user_examinations'),
    path('appointments/update-status/<uuid:appointment_id>/', update_status_view, name='update_status'),
    path('api/medical-history/staff/', medical_history_by_staff, name='medical_history_by_staff'),
    path('api/medical-history/<uuid:id>/update/', update_medical_record, name='update_medical_record'),
    path('api/nutrition-plans/user/', nutrition_plan_by_user, name='nutrition_plan_by_user'),
    path('api/nutrition-plans/create/', create_nutrition_plan, name='create_nutrition_plan'),
    path('api/nutrition-plans/<uuid:id>/update/', update_nutrition_plan, name='update_nutrition_plan'),
    path('api/nutrition-plans/<uuid:id>/delete/', delete_nutrition_plan, name='delete_nutrition_plan'),
    path('api/appointments/staff/create/', create_appointment_by_staff, name='create_appointment_by_staff'),
    path('api/pets/all/', list_all_pets, name='list_all_pets'),

    
]
