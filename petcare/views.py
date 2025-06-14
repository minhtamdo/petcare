from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json
from core.models import Appointment
from core.models import Status  # if you use Status.choices() or Status.values()
from core.models import User, Pet,Service
from django.db import connection
from itertools import chain
from django.shortcuts import render, redirect
from django.contrib import admin
from django.urls import path
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
from collections import defaultdict
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.db.models import Count
from django.utils.dateparse import parse_date
from . import views


@csrf_exempt
def update_appointment_status(request, appointment_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            new_status = data.get('status', '').lower()  # Force lowercase
            reason = data.get('reason', '')

            print("Received status:", new_status)
            print("Valid statuses:", [s.value for s in Status])

            if new_status not in [s.value for s in Status]:
                return JsonResponse({'error': 'Invalid status'}, status=400)

            appointment = get_object_or_404(Appointment, id=appointment_id)
            appointment.status = new_status
            if reason:
                appointment.notes = reason
            if request.user.is_authenticated:
                appointment.approver = request.user
            appointment.save()

            return JsonResponse({'success': True})

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)


def get_pets_by_owner_phone(request):
    phone = request.GET.get('phone')
    if not phone:
        return JsonResponse({'error': 'Phone number required'}, status=400)

    try:
        owner = User.objects.get(phonenumber=phone)
        pets = Pet.objects.filter(owner=owner).values('id', 'name')
        return JsonResponse({'pets': list(pets)}, status=200)
    except User.DoesNotExist:
        return JsonResponse({'pets': []}, status=200)
    

def get_users_by_role(request):
    role = request.GET.get('role')
    if role not in ['Staff', 'Vet']:
        return JsonResponse({'users': []}, status=200)
    
    users = User.objects.filter(role=role).values('id', 'fullname')
    return JsonResponse({'users': list(users)}, status=200)

@csrf_exempt
def create_appointment(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            pet = Pet.objects.get(id=data['pet_id'])
            owner = User.objects.get(phonenumber=data['owner_phone'])
            status = data['status'].lower()

            # Assign staff only if status is not pending
            staff = None
            if status != Status.PENDING.value.lower():
                staff = User.objects.get(id=data['staff_id'])

            appointment = Appointment.objects.create(
                pet=pet,
                owner=owner,
                type=data['type'].lower(),
                check_in=data['check_in'],
                check_out=data['check_out'],
                staff=staff,
                status=status,
                notes=data.get('notes', '')
            )

            return JsonResponse({'message': 'Appointment created successfully'}, status=201)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)

    return JsonResponse({'error': 'Invalid request method'}, status=405)

def get_services(request):
    services = Service.objects.all()
    data = [
        {
            'type': service.type,
            'description': service.description,
            'duration': service.duration,
            'price': service.price
        }
        for service in services
    ]
    return JsonResponse({'services': data})
@csrf_exempt
def update_service_price(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            service_type = data.get('type')
            new_price = data.get('price')

            service = Service.objects.get(type=service_type)
            service.price = int(new_price)
            service.save()

            return JsonResponse({'success': True, 'message': 'Cập nhật giá thành công!'})
        except Service.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Không tìm thấy dịch vụ.'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Chỉ hỗ trợ phương thức POST'}, status=405)

def monthly_revenue_chart_data(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                EXTRACT(MONTH FROM a.check_in) AS month,
                SUM(
                    CASE 
                        WHEN a.type = 'hotel' THEN s.price * GREATEST((a.check_out - a.check_in), 1)
                        ELSE s.price
                    END
                ) AS revenue
            FROM appointments a
            JOIN services s ON a.type = s.type
            WHERE a.status = 'completed'
              AND EXTRACT(YEAR FROM a.check_in) = EXTRACT(YEAR FROM CURRENT_DATE)
            GROUP BY month
            ORDER BY month
        """)
        results = cursor.fetchall()

    # Create a list of 12 months initialized to 0
    revenues = [0] * 12
    for month, revenue in results:
        revenues[int(month) - 1] = float(revenue)

    return JsonResponse({'monthly_revenue': revenues})



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

def pet_species_stats(request):
    data = (
        Pet.objects
        .values('species')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    stats = {item['species']: item['count'] for item in data}
    print('_-------------------------------------------------------------------------------------')
    return JsonResponse(stats)


def calculate_monthly_revenue_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT
                SUM(
                    CASE 
                        WHEN a.type = 'hotel' THEN s.price * GREATEST((a.check_out - a.check_in), 1)
                        ELSE s.price
                    END
                ) AS total_revenue
            FROM appointments a
            JOIN services s ON a.type = s.type
            WHERE a.status = 'completed'
              AND EXTRACT(MONTH FROM a.check_in) = EXTRACT(MONTH FROM CURRENT_DATE)
              AND EXTRACT(YEAR FROM a.check_in) = EXTRACT(YEAR FROM CURRENT_DATE);
        """)
        row = cursor.fetchone()
    
    total_revenue = row[0] if row[0] is not None else 0

    return JsonResponse({'total_revenue': int(total_revenue)})


