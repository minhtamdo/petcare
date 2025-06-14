from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Appointment, Status
from .serializers import AppointmentSerializer, AppointmentUpdateSerializer

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_appointment(request, appointment_id):
    """
    Approve a pending appointment
    """
    try:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Check if appointment is in pending status
        if appointment.status != Status.PENDING.value:
            return Response({
                'error': 'Chỉ có thể chấp nhận lịch hẹn đang chờ duyệt',
                'current_status': appointment.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update appointment
        appointment.status = Status.APPROVED.value  # Assuming you have APPROVED status
        appointment.approver = request.user
        appointment.updated_at = timezone.now()
        appointment.save()
        
        # Serialize and return updated appointment
        serializer = AppointmentSerializer(appointment)
        
        return Response({
            'message': 'Lịch hẹn đã được chấp nhận thành công',
            'appointment': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Có lỗi xảy ra: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_appointment(request, appointment_id):
    """
    Reject a pending appointment
    """
    try:
        appointment = get_object_or_404(Appointment, id=appointment_id)
        
        # Check if appointment is in pending status
        if appointment.status != Status.PENDING.value:
            return Response({
                'error': 'Chỉ có thể từ chối lịch hẹn đang chờ duyệt',
                'current_status': appointment.status
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Update appointment
        appointment.status = Status.REJECTED.value  # Assuming you have REJECTED status
        appointment.approver = request.user
        appointment.updated_at = timezone.now()
        appointment.save()
        
        # Serialize and return updated appointment
        serializer = AppointmentSerializer(appointment)
        
        return Response({
            'message': 'Lịch hẹn đã được từ chối',
            'appointment': serializer.data
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Có lỗi xảy ra: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_appointments(request):
    """
    Get all appointments with optional filtering
    """
    try:
        appointments = Appointment.objects.select_related('pet', 'owner', 'staff', 'approver').all()
        
        # Optional filtering
        status_filter = request.GET.get('status')
        if status_filter:
            appointments = appointments.filter(status=status_filter)
        
        date_filter = request.GET.get('date')
        if date_filter:
            appointments = appointments.filter(check_in=date_filter)
        
        serializer = AppointmentSerializer(appointments, many=True)
        
        return Response({
            'appointments': serializer.data,
            'count': appointments.count()
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response({
            'error': f'Có lỗi xảy ra: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)