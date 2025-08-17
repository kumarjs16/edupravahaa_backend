from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import razorpay
import hmac
import hashlib
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from courses.models import Course, Enrollment
from accounts.permissions import IsStudent

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class CreateOrderView(views.APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['course_id'],
            properties={
                'course_id': openapi.Schema(type=openapi.TYPE_INTEGER, description='Course ID')
            }
        ),
        responses={
            200: openapi.Response(
                description="Order created successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'order_id': openapi.Schema(type=openapi.TYPE_STRING),
                        'amount': openapi.Schema(type=openapi.TYPE_NUMBER),
                        'currency': openapi.Schema(type=openapi.TYPE_STRING),
                        'key': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    def post(self, request):
        course_id = request.data.get('course_id')
        
        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            return Response(
                {"error": "Course not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Check if already enrolled
        existing_enrollment = Enrollment.objects.filter(
            student=request.user,
            course=course
        ).first()
        
        if existing_enrollment and existing_enrollment.payment_status == 'completed':
            return Response(
                {"error": "Already enrolled in this course"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create Razorpay order
        amount = int(course.price * 100)  # Convert to paise
        
        try:
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'notes': {
                    'course_id': course.id,
                    'student_id': request.user.id,
                    'student_email': request.user.email
                }
            }
            
            order = client.order.create(data=order_data)
            
            # Create or update enrollment
            enrollment, created = Enrollment.objects.update_or_create(
                student=request.user,
                course=course,
                defaults={
                    'order_id': order['id'],
                    'payment_status': 'pending'
                }
            )
            
            return Response({
                'order_id': order['id'],
                'amount': order['amount'],
                'currency': order['currency'],
                'key': settings.RAZORPAY_KEY_ID
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class VerifyPaymentView(views.APIView):
    permission_classes = [IsAuthenticated, IsStudent]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature'],
            properties={
                'razorpay_order_id': openapi.Schema(type=openapi.TYPE_STRING),
                'razorpay_payment_id': openapi.Schema(type=openapi.TYPE_STRING),
                'razorpay_signature': openapi.Schema(type=openapi.TYPE_STRING),
            }
        )
    )
    def post(self, request):
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')
        
        if not all([payment_id, order_id, signature]):
            return Response(
                {"error": "Missing payment details"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verify signature
        try:
            generated_signature = hmac.new(
                settings.RAZORPAY_KEY_SECRET.encode('utf-8'),
                f"{order_id}|{payment_id}".encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            if generated_signature != signature:
                return Response(
                    {"error": "Invalid signature"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Update enrollment
            enrollment = Enrollment.objects.filter(
                order_id=order_id,
                student=request.user
            ).first()
            
            if not enrollment:
                return Response(
                    {"error": "Enrollment not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            enrollment.payment_id = payment_id
            enrollment.payment_status = 'completed'
            enrollment.amount_paid = enrollment.course.price
            enrollment.save()
            
            return Response({
                "message": "Payment verified successfully",
                "enrollment_id": enrollment.id
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
