from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import json
from core.models import Appointment
from core.models import Status  # if you use Status.choices() or Status.values()
from core.models import User, Pet


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