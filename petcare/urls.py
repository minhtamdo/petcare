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
from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import render
from django.db import connection
import json
from django.shortcuts import render, redirect
from core.models import *
from django.utils.timezone import now
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
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

            # Truy vấn từ bảng 'users'
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


def medical_history_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT mh.record_id, 
                    u.fullname, 
                    p.name,
                    mh.diagnosis, 
                    mh.treatment, 
                    mh.notes
            FROM medical_history mh
            JOIN appointments a ON mh.appointment_id = a.appointment_id
            JOIN users u ON a.owner_id = u.user_id
            JOIN pets p ON a.pet_id = p.pet_id;

        """)
        results = cursor.fetchall()

    histories = []
    for row in results:
        histories.append({
            'record_id': row[0],
            'owner_name': row[1],
            'pet_name': row[2],
            'diagnosis': row[3],
            'treatment': row[4],
            'notes': row[5],
        })


    return render(request, 'vet.html', {
        'medical_history': histories
    })


@csrf_exempt
@require_POST
def add_medical_history_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            fullname = data.get('fullname')
            pet_id = data.get('pet_id')
            diagnosis = data.get('diagnosis')
            treatment = data.get('treatment')
            notes = data.get('notes')

            # if not user_id or not pet_id:
            #     return JsonResponse({'success': False, 'error': 'Thiếu user_id hoặc pet_id'})

            print("Hello")
            print(fullname)
            print(pet_id)
            # Lấy appointment_id mới nhất theo user_id và pet_id
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT appointment_id
                    FROM appointments 
                    JOIN users ON appointments.owner_id = users.user_id
                    WHERE appointments.pet_id = %s AND users.fullname = %s
                    LIMIT 1
                """, [pet_id, fullname])

                result = cursor.fetchone()

                if not result:
                    return JsonResponse({'success': False, 'error': 'Không tìm thấy lịch hẹn phù hợp'})

                appointment_id = result[0]  # Lúc này mới an toàn

            print("app_id " + str(appointment_id))

            record_id = str(uuid.uuid4())  # Sinh UUID cho record_id

            # Thêm bệnh án
            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE medical_history
                    SET diagnosis = %s,
                        treatment = %s,
                        notes = %s
                    WHERE appointment_id = %s
                """, [diagnosis, treatment, notes, appointment_id])

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Phương thức không hợp lệ'})

@csrf_exempt
def add_vaccination_history_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            appointment_id = data.get('appointment_id')
            vaccine_name = data.get('vaccine_name')
            vaccination_date = data.get('vaccination_date')  # dạng: '2025-06-12'
            next_due = data.get('next_due')                  # dạng: '2025-07-12'
            total_doses = data.get('total_doses')
            batch_number = data.get('batch_number')
            is_completed = data.get('is_completed', False)
            note = data.get('note', '')

            # Tìm appointment_id dựa trên fullname và pet_id
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT appointment_id
                    FROM appointments 
                    WHERE appointments.type = 'vaccine'
                    ORDER BY appointments.updated_at DESC
                    LIMIT 1
                """)

                result = cursor.fetchone()
                if not result:
                    return JsonResponse({'success': False, 'error': 'Không tìm thấy lịch hẹn phù hợp'})

                appointment_id = result[0]

            vaccination_id = str(uuid.uuid4())

            # Thêm lịch tiêm phòng
            with connection.cursor() as cursor:
                cursor.execute("""
                        UPDATE vaccination_history
                        SET
                            vaccine_name = %s,
                            vaccination_date = %s,
                            next_due = %s,
                            total_doses = %s,
                            batch_number = %s,
                            is_completed = %s,
                            note = %s
                        WHERE vaccination_id = %s AND appointment_id = %s
                    """, [
                        vaccine_name,
                        vaccination_date,
                        next_due,
                        total_doses,
                        batch_number,
                        is_completed,
                        note,
                        vaccination_id,
                        appointment_id
                    ])


            return JsonResponse({'success': True, 'vaccination_id': vaccination_id})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'Phương thức không hợp lệ'})


@require_GET
def get_users(request):
    query = request.GET.get('q', '')
    users = User.objects.filter(fullname__icontains=query)[:10]
    results = [{'id': user.id, 'fullname': user.fullname} for user in users]
    return JsonResponse(results, safe=False)

@require_GET
def get_pets_by_owner(request):
    owner_id = request.GET.get('owner_id')
    if not owner_id:
        return JsonResponse([], safe=False)

    pets = Pet.objects.filter(owner_id=owner_id)[:10]
    results = [{'id': pet.id, 'name': pet.name} for pet in pets]
    return JsonResponse(results, safe=False)




def staff_dashboard(request):
    if request.session.get('role') != 'Staff':
        return redirect('/login')
    return render(request, 'staff.html')

def owner_dashboard(request):
    if request.session.get('role') != 'Owner':
        return redirect('/login')
    return render(request, 'owner.html')

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
    


@csrf_exempt
def delete_medical_record(request, record_id):
    if request.method == 'POST':
        record = get_object_or_404(MedicalHistory, pk=record_id)
        record.delete()
        return JsonResponse({'message': 'Xóa bệnh án thành công'})
    else:
        return HttpResponseNotAllowed(['POST'])

def get_medical_record_detail(request, record_id):
    if request.method == 'GET':
        record = get_object_or_404(MedicalHistory, pk=record_id)
        data = {
            'diagnosis': record.diagnosis,
            'treatment': record.treatment,
            'notes': record.notes,
            # nếu có các trường khác thì thêm ở đây
        }
        return JsonResponse(data)
    else:
        return HttpResponseNotAllowed(['GET'])


def logout_view(request):
    request.session.flush()
    return redirect('/login')

def register_page(request):
    return render(request, 'register.html')

def vaccination_history_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT v.vaccination_id,
                   a.appointment_id,
                   v.vaccine_name,
                   v.next_due,
                   v.total_doses,
                   v.batch_number,
                   v.is_completed,
                   v.note
            FROM vaccination_history v
            JOIN appointments a ON v.appointment_id = a.appointment_id
        """)
        results = cursor.fetchall()

    vaccinations = []
    for row in results:
        vaccinations.append({
            'vaccination_id': row[0],
            'appointment_id': row[1],
            'vaccine_name': row[2],
            'next_due': row[3],
            'total_doses': row[4],
            'batch_number': row[5],
            'is_completed': row[6],
            'note': row[7],
        })

    return render(request, 'lichsutiemphong.html', {
        'vaccinations': vaccinations
    })

# @csrf_exempt
# def add_vaccination_record(request):
#     try:
#         if request.method != 'POST':
#             return JsonResponse({"error": "Phương thức không hợp lệ."}, status=405)

#         data = json.loads(request.body)

#         # Lấy appointment từ ID
#         appointment_id = data.get("appointment_id")
#         appointment = get_object_or_404(Appointment, id=appointment_id)

#         VaccinationHistory.objects.create(

#             vaccine_name=data.get("vaccine_name"),
#             vaccination_date=now().date(),
#             next_due=data.get("next_due"),
#             total_doses=data.get("total_doses"),
#             batch_number=data.get("batch_number"),
#             is_completed=data.get("is_completed") == True or data.get("is_completed") == "true",
#             note=data.get("note", "")
#         )

#         return JsonResponse({"message": "Đã thêm lịch tiêm phòng thành công."})

#     except Exception as e:
#         return JsonResponse({"error": str(e)}, status=400)

def delete_vaccination_api(request, id):
    if request.method == 'POST':
        try:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM vaccination_history WHERE vaccination_id = %s", [str(id)])
            return JsonResponse({'success': True, 'message': 'Đã xóa lịch tiêm phòng'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Phương thức không hợp lệ'})


@csrf_exempt
def update_vaccination(request, vaccination_id):
    if request.method == "PUT":
        try:
            data = json.loads(request.body)

            vaccination = VaccinationHistory.objects.get(pk=vaccination_id)
            vaccination.appointment_id = data.get("appointment_id")
            vaccination.vaccine_name = data.get("vaccine_name")
            vaccination.next_due = data.get("next_due")
            vaccination.total_doses = data.get("total_doses")
            vaccination.batch_number = data.get("batch_number")
            vaccination.is_completed = data.get("is_completed", False)
            vaccination.note = data.get("note", "")
            vaccination.save()

            return JsonResponse({"success": True})
        except VaccinationHistory.DoesNotExist:
            return JsonResponse({"success": False, "message": "Không tìm thấy lịch tiêm phòng"}, status=404)
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=400)

    return JsonResponse({"success": False, "message": "Phương thức không hỗ trợ"}, status=405)


def get_vaccination_detail(request, vaccination_id):
    try:
        vaccination = VaccinationHistory.objects.get(pk=vaccination_id)
        return JsonResponse({
            "vaccination_id": str(vaccination.id),
            "appointment_id": str(vaccination.appointment_id),
            "vaccine_name": vaccination.vaccine_name,
            "next_due": vaccination.next_due.strftime('%Y-%m-%d'),
            "total_doses": vaccination.total_doses,
            "batch_number": vaccination.batch_number,
            "is_completed": vaccination.is_completed,
            "note": vaccination.note
        })
    except VaccinationHistory.DoesNotExist:
        return JsonResponse({"error": "Không tìm thấy lịch tiêm phòng"}, status=404)

# @csrf_exempt
# def vaccination_detail(request, id):
#     if request.method == 'GET':
#         try:
#             v = VaccinationHistory.objects.get(id=id)
#             data = {
#                 'vaccination_id': str(v.id),  # UUID nên convert thành str
#                 'appointment_id': v.appointment_id,
#                 'vaccine_name': v.vaccine_name,
#                 'next_due': v.next_due.strftime('%Y-%m-%d'),
#                 'total_doses': v.total_doses,
#                 'batch_number': v.batch_number,
#                 'is_completed': v.is_completed,
#                 'note': v.note
#             }
#             return JsonResponse(data)
#         except VaccinationHistory.DoesNotExist:
#             return JsonResponse({'error': 'Không tìm thấy lịch tiêm phòng'}, status=404)

#     elif request.method == 'PUT':


#         try:
#             data = json.loads(request.body)

#               # ✅ In ra các trường sau khi người dùng gửi PUT
#             print("Dữ liệu PUT nhận được:")
#             print("appointment_id:", data['appointment_id'])
#             print("vaccine_name:", data['vaccine_name'])
#             print("next_due:", data['next_due'])
#             print("total_doses:", data['total_doses'])
#             print("batch_number:", data['batch_number'])
#             print("is_completed:", data['is_completed'])
#             print("note:", data.get('note', ''))
#             print("vaccination_id:", str(id))

#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     UPDATE vaccination_history
#                     SET 
#                         appointment_id = %s,
#                         vaccine_name = %s,
#                         next_due = %s,
#                         total_doses = %s,
#                         batch_number = %s,
#                         is_completed = 'Đã hoàn thành',
#                         note = %s
#                     WHERE vaccination_id = %s
#                 """, [
#                     data['appointment_id'],
#                     data['vaccine_name'],
#                     data['next_due'],
#                     data['total_doses'],
#                     data['batch_number'],
#                     data['is_completed'],
#                     data.get('note', ''),
#                     str(id)  # đảm bảo là chuỗi nếu UUID
#                 ])

#                 if cursor.rowcount == 0:
#                     return JsonResponse({'success': False, 'message': 'Không tìm thấy bản ghi cần cập nhật.'})

#             return JsonResponse({'success': True, 'message': 'Cập nhật thành công!'})

#         except Exception as e:
#             return HttpResponseBadRequest(str(e))

#     else:
#         return HttpResponseNotAllowed(['GET', 'PUT'])
    


def giao_dien_lich(request):
        return render(request, 'giaodienlich.html')

@csrf_exempt
def update_medical_record_api(request, record_id):
    if request.method != 'PUT':
        return JsonResponse({'error': 'Chỉ chấp nhận phương thức PUT'}, status=405)

    try:
        data = json.loads(request.body)
        record = get_object_or_404(MedicalHistory, pk=record_id)

        record.diagnosis = data.get('diagnosis', record.diagnosis)
        record.treatment = data.get('treatment', record.treatment)
        record.notes = data.get('notes', record.notes)
        record.save()

        return JsonResponse({'message': 'Cập nhật thành công'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_page, name='register'),
    path('api/register/owner/', register_owner, name='register_owner'),

    # Dashboard
    path('vet/', medical_history_view, name='medical_history_view'),  # bạn
    path('vet/vaccination_history/', vaccination_history_view, name='vaccination_history'),
    path('staff/', staff_dashboard, name='staff_dashboard'),
    path('owner/', owner_dashboard, name='owner_dashboard'),

    # Account API
    path('account/info/', get_account_info, name='account-info'),
    path('account/update/', update_account_info, name='account-update'),

    # Appointment
    path('api/appointments/create/', create_appointment, name='create_appointment'),
    path('appointments/upcoming/', upcoming_appointments, name='upcoming-appointments'),
    path('appointments/history/', appointment_history_view),

    # Pet API
    path('api/pets/', get_owner_pets, name='get_owner_pets'),
    path('pets/', pets_list_view, name='pets_list'),  # nếu bạn có
    path('pets/create/', create_pet),
    path('pets/<uuid:pet_id>/', pet_detail_view),
    path('pets/<uuid:pet_id>/update/', update_pet),
    path('pets/<uuid:pet_id>/delete/', delete_pet_view, name='delete_pet'),

    # Medical History
    path('api/add-medical-history/', add_medical_history_api, name='add_medical_history_api'),
    path('medical_history/<uuid:record_id>/delete/', delete_medical_record, name='delete_medical_record'),
    path('api/medical_history/<uuid:record_id>/', get_medical_record_detail, name='get_medical_record_detail'),
    path('api/medical_history/<uuid:record_id>/update/', update_medical_record_api, name='update_medical_record'),

    # Vaccination
    path('api/add-vaccination/', add_vaccination_history_api, name='add_vaccination'),
    path('vaccination_history/<uuid:id>/delete/', delete_vaccination_api, name='delete_vaccination'),
    path('api/vaccination/<uuid:vaccination_id>/', get_vaccination_detail, name='get_vaccination_detail'),
    path('api/vaccination/<uuid:vaccination_id>/update/', update_vaccination, name='update_vaccination'),

    # Extra
    path('giao-dien-lich/', giao_dien_lich, name='giao_dien_lich'),
    path('', redirect_to_login),
]
