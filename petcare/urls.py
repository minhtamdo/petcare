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
    return render(request, 'vet.html')

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

        return JsonResponse({'message': 'Thông tin đã được cập nhật.'})
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
    context = {
        'pets': pets,
        'total_pets': total_pets,
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
            "updated_at": p.updated_at.strftime("%d/%m/%Y %H:%M")
        }
        for p in plans
    ]
    return JsonResponse({"nutrition_plans": data})

# def vaccination_view(request, pet_id):
#     vaccination = VaccinationHistory.objects.filter(pet__id=pet_id).select_related('created_by')
#     data = [
#         {
#             "food_type": p.food_type,
#             "portion": p.portion,
#             "note": p.note,
#             "created_by": p.created_by.fullname,
#             "updated_at": p.updated_at.strftime("%d/%m/%Y %H:%M")
#         }
#         for p in plans
#     ]
#     return JsonResponse({"nutrition_plans": data})

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

]
