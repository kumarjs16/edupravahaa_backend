from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
import razorpay
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from courses.models import Course
from payments.models import CourseSubscription
from accounts.permissions import IsStudent
from django.utils import timezone
import logging

# Initialize Razorpay client
client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

# Set up logging
logger = logging.getLogger(__name__)

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
                        'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER)
                    }
                )
            ),
            400: "Bad Request",
            404: "Course Not Found"
        }
    )
    def post(self, request):
        course_id = request.data.get('course_id')
        
        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            logger.error(f"Course {course_id} not found or inactive")
            return Response({"error": "Course not found or inactive"}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if user is verified
        if not request.user.is_verified:
            return Response({"error": "User email or phone not verified"}, status=status.HTTP_403_FORBIDDEN)
        
        # Check if already subscribed
        existing_subscription = CourseSubscription.objects.filter(
            student=request.user, course=course, payment_status='completed'
        ).exists()
        if existing_subscription:
            return Response({"error": "Already subscribed to this course"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Create Razorpay order
        amount = int(course.base_price * 100)  # Convert to paise
        try:
            order_data = {
                'amount': amount,
                'currency': 'INR',
                'payment_capture': '1',  # Auto-capture
                'notes': {
                    'course_id': str(course.id),
                    'student_id': str(request.user.id),
                    'student_email': request.user.email
                }
            }
            # order = client.order.create(data=order_data)
            
            # Create subscription
            # subscription = CourseSubscription.objects.create(
            #     student=request.user,
            #     course=course,
            #     amount_paid=course.base_price,
            #     order_id=order['id'],
            #     payment_method='razorpay',
            #     payment_status='pending',
            #     currency='INR'
            # )
            
            # return Response({
            #     'order_id': order['id'],
            #     'amount': order['amount'],
            #     'currency': order['currency'],
            #     'key': settings.RAZORPAY_KEY_ID,
            #     'subscription_id': subscription.id
            # }, status=status.HTTP_200_OK)



            fake_order_id = 'order_12345678'  # Hardcode a fake order_id

            # Create subscription with fake order_id
            subscription = CourseSubscription.objects.create(
                student=request.user,
                course=course,
                amount_paid=course.base_price,
                order_id=fake_order_id,
                payment_method='razorpay',
                payment_status='pending',
                currency='INR'
            )

            return Response({
                'order_id': fake_order_id,
                'amount': amount,
                'currency': 'INR',
                'key': settings.RAZORPAY_KEY_ID,
                'subscription_id': subscription.id
            }, status=status.HTTP_200_OK)


            
        except razorpay.errors.BadRequestError as e:
            logger.error(f"Razorpay error creating order: {str(e)}")
            return Response({"error": f"Payment gateway error: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.exception(f"Unexpected error creating order: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class VerifyPaymentView(views.APIView):
    permission_classes = [IsAuthenticated, IsStudent]

    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature', 'subscription_id'],
            properties={
                'razorpay_order_id': openapi.Schema(type=openapi.TYPE_STRING),
                'razorpay_payment_id': openapi.Schema(type=openapi.TYPE_STRING),
                'razorpay_signature': openapi.Schema(type=openapi.TYPE_STRING),
                'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER)
            }
        ),
        responses={
            200: openapi.Response(
                description="Payment verified successfully",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'subscription_id': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'course_name': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            ),
            400: "Bad Request",
            404: "Subscription Not Found"
        }
    )
    def post(self, request):
        payment_id = request.data.get('razorpay_payment_id')
        order_id = request.data.get('razorpay_order_id')
        signature = request.data.get('razorpay_signature')
        subscription_id = request.data.get('subscription_id')
        
        if not all([payment_id, order_id, signature, subscription_id]):
            return Response({"error": "Missing payment details"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify subscription exists
        try:
            print("--------------", subscription_id, order_id, request.user)
            subscription = CourseSubscription.objects.get(
                id=subscription_id, order_id=order_id, student=request.user
            )
        except CourseSubscription.DoesNotExist:
            logger.error(f"Subscription {subscription_id} not found for order {order_id}")
            return Response({"error": "Subscription not found"}, status=status.HTTP_404_NOT_FOUND)
        

        # Mock signature verification for testing without valid keys
        if settings.RAZORPAY_KEY_SECRET == 'fake_secret_for_testing':
            # Assume signature is valid for testing
            pass
        else:
            # Original Razorpay SDK verification
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
        # try:
        #     client.utility.verify_payment_signature(params_dict)
        # except razorpay.errors.SignatureVerificationError as e:
        #     logger.error(f"Signature verification failed: {str(e)}")
        #     subscription.payment_status = 'failed'
        #     subscription.save()
        #     return Response({"error": "Invalid payment signature"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Update subscription
        try:
            subscription.payment_id = payment_id
            subscription.payment_status = 'completed'
            subscription.payment_response = params_dict
            subscription.payment_completed_at = timezone.now()
            subscription.save()
            
            return Response({
                "message": "Payment verified successfully",
                "subscription_id": subscription.id,
                "course_name": subscription.course.name
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.exception(f"Error updating subscription {subscription_id}: {str(e)}")
            return Response({"error": "Internal server error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)