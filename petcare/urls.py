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

def staff_dashboard(request):
    if request.session.get('role') != 'Staff':
        return redirect('/login')
    return render(request, 'staff.html')

def owner_dashboard(request):
    if request.session.get('role') != 'Owner':
        return redirect('/login')
    return render(request, 'owner.html')


def logout_view(request):
    request.session.flush()
    return redirect('/login')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', login_view, name='login'),
    path('vet/', vet_dashboard, name='vet_dashboard'),
    path('staff/', staff_dashboard, name='staff_dashboard'),
    path('owner/', owner_dashboard, name='owner_dashboard'),
    path('logout/', logout_view, name='logout'),

]
