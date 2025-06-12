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
from django.http import HttpResponseNotAllowed, HttpResponseBadRequest
from django.shortcuts import get_object_or_404



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
def vaccination_detail(request, id):
    if request.method == 'GET':
        try:
            v = VaccinationHistory.objects.get(id=id)
            data = {
                'vaccination_id': str(v.id),  # UUID nên convert thành str
                'appointment_id': v.appointment_id,
                'vaccine_name': v.vaccine_name,
                'next_due': v.next_due.strftime('%Y-%m-%d'),
                'total_doses': v.total_doses,
                'batch_number': v.batch_number,
                'is_completed': v.is_completed,
                'note': v.note
            }
            return JsonResponse(data)
        except VaccinationHistory.DoesNotExist:
            return JsonResponse({'error': 'Không tìm thấy lịch tiêm phòng'}, status=404)

    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)

            with connection.cursor() as cursor:
                cursor.execute("""
                    UPDATE vaccination_history
                    SET 
                        appointment_id = %s,
                        vaccine_name = %s,
                        next_due = %s,
                        total_doses = %s,
                        batch_number = %s,
                        is_completed = %s,
                        note = %s
                    WHERE vaccination_id = %s
                """, [
                    data['appointment_id'],
                    data['vaccine_name'],
                    data['next_due'],
                    data['total_doses'],
                    data['batch_number'],
                    data['is_completed'],
                    data.get('note', ''),
                    str(id)  # đảm bảo là chuỗi nếu UUID
                ])

                if cursor.rowcount == 0:
                    return JsonResponse({'success': False, 'message': 'Không tìm thấy bản ghi cần cập nhật.'})

            return JsonResponse({'success': True, 'message': 'Cập nhật thành công!'})

        except Exception as e:
            return HttpResponseBadRequest(str(e))

    else:
        return HttpResponseNotAllowed(['GET', 'PUT'])
    

def giao_dien_lich(request):
        return render(request, 'giaodienlich.html')

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('vet/', medical_history_view, name='medical_history_view'),
    path('staff/', staff_dashboard, name='staff_dashboard'),
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('logout/', logout_view, name='logout'),
    path('register/', register_page, name='register'),
    path('api/register/owner/', register_owner, name='register_owner'),
    path('api/add-medical-history/', add_medical_history_api, name='add_medical_history_api'),
    path("api/add-medical-history/", add_medical_history_api, name="add_medical_history"),
    path('medical_history/<uuid:record_id>/delete/', delete_medical_record, name='delete_medical_record'),
    path('api/medical_history/<uuid:record_id>/', get_medical_record_detail, name='get_medical_record_detail'),
    path('vet/vaccination_history/', vaccination_history_view, name='vaccination_history'),
    path('api/add-vaccination/', add_vaccination_history_api, name='add_vaccination'),
    path('vaccination_history/<uuid:id>/delete/', delete_vaccination_api, name='delete_vaccination'),
    path('api/vaccinations/<uuid:id>', vaccination_detail, name='vaccination_detail'),
    path('giao-dien-lich/', giao_dien_lich, name='giao_dien_lich'),


]
