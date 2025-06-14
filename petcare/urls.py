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



urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('vet/', views.vet_dashboard, name='vet_dashboard'),
    path('staff/', views.staff_dashboard, name='staff_dashboard'),
    path('owner/', views.owner_dashboard, name='owner_dashboard'),
    path('logout/', views.logout_view, name='logout_view'),
    path('register/', views.register_page, name='register'),
    path('api/register/owner/', views.register_owner, name='register_owner'),
    path('nutrition/<uuid:pet_id>/', views.nutrition_view, name='get_nutrition_plan'),
    path('vaccinations/<uuid:pet_id>/', views.vaccination_view, name='get_vaccination_history'),
    path('services/<uuid:pet_id>/', views.service_view, name='get_service_history'),
    path('medical/<uuid:pet_id>/', views.medical_view, name='get_medical_history'),
    path('appointment/<uuid:appointment_id>/update/', views.update_appointment_status, name='update_status'),
    path('', views.redirect_to_login),
    path('api/get-pets/', views.get_pets_by_owner_phone, name='get_pets_by_phone'),
    path('api/get-users/', views.get_users_by_role, name='get_users_by_role'),
    path('api/create-appointment/', views.create_appointment, name='create_appointment'),
    path('api/services/', views.get_services, name='get_services'),
    path('api/update-service-price/', views.update_service_price, name='update_service_price'),
    path('api/monthly-revenue/', views.calculate_monthly_revenue_view, name='monthly-revenue'),
    path('api/monthly-revenue-chart/', views.monthly_revenue_chart_data),
    path('api/pet-species-stats/', views.pet_species_stats, name='pet_species_stats'),
]
