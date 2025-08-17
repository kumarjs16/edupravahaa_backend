from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import serializers
from django.contrib.auth import login
from django.core.mail import send_mail
from django.conf import settings
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
import logging

logger = logging.getLogger(__name__)

from .models import User, OTP
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer,
    TeacherCreateSerializer, ChangePasswordSerializer,
    SendOTPSerializer, VerifyOTPSerializer,
    ForgotPasswordSerializer
)
from .permissions import IsAdmin, IsTeacher, IsStudent


class SendOTPView(views.APIView):
    permission_classes = [AllowAny]
    serializer_class = SendOTPSerializer
    
    @swagger_auto_schema(
        request_body=SendOTPSerializer,
        operation_description="Send OTP to email or phone (auto-detects type)"
    )
    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        identifier = serializer.validated_data['identifier']
        purpose = serializer.validated_data['purpose']
        
        # Auto-detect identifier type based on the identifier value
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        phone_pattern = r'^[\+]?[0-9]{10,15}$'
        
        if re.match(email_pattern, identifier):
            identifier_type = 'email'
        elif re.match(phone_pattern, identifier):
            identifier_type = 'phone'
        else:
            return Response({
                "error": "Invalid identifier. Please provide a valid email or phone number."
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create OTP
        otp = OTP.objects.create(
            identifier=identifier,
            otp_type=identifier_type,
            purpose=purpose
        )
        
        # Send OTP
        if identifier_type == 'email':
            # Use Twilio SendGrid for email
            from .email_services import send_otp_email
            
            email_sent = send_otp_email(identifier, otp.otp_code, purpose)
            
            if not email_sent and not settings.DEBUG:
                return Response({
                    "error": "Failed to send email. Please try again."
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            return Response({
                "message": f"OTP sent to email {identifier}",
                "otp_expires_in_seconds": 600
            }, status=status.HTTP_200_OK)
            
        else:  # phone
            # Send SMS using configured service
            sms_sent = False
            using_console = False
            
            try:
                # Import here to avoid circular imports
                from .sms_services import get_sms_service, ConsoleSMSService
                
                sms_service = get_sms_service()
                message = f'Your OTP for {purpose.replace("_", " ").title()} is: {otp.otp_code}\nValid for 10 minutes.'
                
                # Check if using console service
                using_console = isinstance(sms_service, ConsoleSMSService)
                
                # Send SMS
                sms_sent = sms_service.send_sms(identifier, message)
                
                if not sms_sent and not settings.DEBUG:
                    return Response({
                        "error": "Failed to send SMS. Please try again."
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                
            except Exception as e:
                logger.error(f"SMS sending error: {str(e)}")
                if not settings.DEBUG:
                    return Response({
                        "error": "SMS service unavailable"
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
                using_console = True  # Fallback to console behavior
            
            response_data = {
                "message": f"OTP sent to phone {identifier}",
                "otp_expires_in_seconds": 600
            }
            
            # Only return OTP in debug mode if using console service
            if settings.DEBUG and using_console:
                response_data["debug_otp"] = otp.otp_code
                
            return Response(response_data, status=status.HTTP_200_OK)


class VerifyOTPView(views.APIView):
    permission_classes = [AllowAny]
    serializer_class = VerifyOTPSerializer
    
    @swagger_auto_schema(
        request_body=VerifyOTPSerializer,
        operation_description="Verify OTP (auto-detects identifier type)"
    )
    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        identifier = serializer.validated_data['identifier']
        otp_code = serializer.validated_data['otp_code']
        purpose = serializer.validated_data['purpose']
        
        # Auto-detect identifier type if not provided
        identifier_type = serializer.validated_data.get('identifier_type')
        if not identifier_type:
            import re
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            phone_pattern = r'^[\+]?[0-9]{10,15}$'
            
            if re.match(email_pattern, identifier):
                identifier_type = 'email'
            elif re.match(phone_pattern, identifier):
                identifier_type = 'phone'
            else:
                return Response({
                    "error": "Invalid identifier. Please provide a valid email or phone number."
                }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify OTP
        otp = OTP.objects.filter(
            identifier=identifier,
            otp_type=identifier_type,
            purpose=purpose,
            otp_code=otp_code,
            is_verified=False
        ).order_by('-created_at').first()
        
        if not otp:
            return Response({
                "error": "Invalid OTP"
            }, status=status.HTTP_400_BAD_REQUEST)
            
        if otp.is_expired:
            return Response({
                "error": "OTP has expired"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as verified
        otp.is_verified = True
        otp.save()
        
        return Response({
            "message": f"{identifier_type.capitalize()} verified successfully",
            "identifier": identifier,
            "identifier_type": identifier_type,
            "verified": True
        }, status=status.HTTP_200_OK)


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    @swagger_auto_schema(
        operation_description="Register a new student (requires email and phone OTP verification)",
        responses={
            201: openapi.Response(
                description="Registration successful",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            )
        }
    )
    
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        response_data = {
            'message': 'Registration successful! Please login to continue.'
        }        

        # Add trial info for students
        if user.role == 'student' and user.trial_end_date:
            response_data['trial_info'] = {
                'trial_ends_at': user.trial_end_date.isoformat(),
                'trial_duration_seconds': user.trial_remaining_seconds
            }
        
        return Response(response_data, status=status.HTTP_201_CREATED)




class LoginView(views.APIView):
    permission_classes = [AllowAny]
    serializer_class = LoginSerializer
    
    @swagger_auto_schema(
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="Successful login",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'access': openapi.Schema(type=openapi.TYPE_STRING),
                        'refresh': openapi.Schema(type=openapi.TYPE_STRING),
                        'user_type': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            400: openapi.Response(
                description="Invalid input or credentials",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
            403: openapi.Response(
                description="Account disabled",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'error': openapi.Schema(type=openapi.TYPE_STRING),
                    }
                )
            ),
        }
    )
    def post(self, request):
        try:
            serializer = LoginSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user = serializer.validated_data['user']
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            response_data = {
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'user_type': user.role,
                'message': 'Login successful'
            }

            # Add trial info for students
            if user.role == 'student':
                response_data['is_trial'] = not user.has_purchased_courses
                response_data['has_purchased'] = user.has_purchased_courses
                
                if not user.has_purchased_courses and user.trial_end_date:
                    response_data['trial_ends_at'] = user.trial_end_date.isoformat()
                    response_data['trial_remaining_seconds'] = user.trial_remaining_seconds

            return Response(response_data)
        
        except serializers.ValidationError as e:
            # Handle validation errors from serializer (e.g., invalid credentials, missing fields)
            return Response({
                'error': 'Invalid credentials' if 'Invalid credentials' in str(e) else str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            # Catch any unexpected errors for robustness
            logger.error(f"Login error: {str(e)}")
            return Response({
                'error': 'An unexpected error occurred. Please try again.'
            }, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['refresh'],
            properties={
                'refresh': openapi.Schema(type=openapi.TYPE_STRING, description='Refresh token')
            }
        ),
        responses={205: 'Logout successful'}
    )
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({"detail": "Logout successful"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user

class CreateTeacherView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = TeacherCreateSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        operation_description="Create a new teacher account with profile (Admin only)",
        responses={201: UserSerializer}
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Teacher account and profile created successfully'
        }, status=status.HTTP_201_CREATED)

class ListTeachersView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        return User.objects.filter(role='teacher')

class ListStudentsView(generics.ListAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    def get_queryset(self):
        return User.objects.filter(role='student')

class ChangePasswordView(generics.UpdateAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = self.get_object()
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)


class ForgotPasswordView(views.APIView):
    permission_classes = [AllowAny]
    serializer_class = ForgotPasswordSerializer
    
    @swagger_auto_schema(
        request_body=ForgotPasswordSerializer,
        operation_description="Reset password using OTP"
    )
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        otp = serializer.validated_data['otp']
        new_password = serializer.validated_data['new_password']
        
        # Update password
        user.set_password(new_password)
        user.save()
        
        # Mark OTP as used
        otp.is_verified = True
        otp.save()
        
        return Response({
            'message': 'Password reset successfully'
        }, status=status.HTTP_200_OK)


class TrialStatusView(views.APIView):
    permission_classes = [IsAuthenticated]
    
    @swagger_auto_schema(
        operation_description="Get trial status for frontend display",
        responses={
            200: openapi.Response(
                description="Trial status information",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'is_trial': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'trial_ends_at': openapi.Schema(type=openapi.TYPE_STRING, format='date-time'),
                        'remaining_seconds': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'has_purchased': openapi.Schema(type=openapi.TYPE_BOOLEAN),
                        'purchased_courses_count': openapi.Schema(type=openapi.TYPE_INTEGER),
                    }
                )
            )
        }
    )
    def get(self, request):
        user = request.user
        
        # Non-students don't have trials
        if user.role != 'student':
            return Response({
                'is_trial': False,
                'has_purchased': False,
                'purchased_courses_count': 0
            })
        
        # Get purchased courses count
        from payments.models import CourseSubscription
        purchased_count = CourseSubscription.objects.filter(
            student=user,
            payment_status='completed'
        ).count()
        
        response_data = {
            'is_trial': not user.has_purchased_courses,
            'has_purchased': user.has_purchased_courses,
            'purchased_courses_count': purchased_count
        }
        
        # Add trial info only if user is on trial
        if not user.has_purchased_courses and user.trial_end_date:
            response_data['trial_ends_at'] = user.trial_end_date.isoformat()
            response_data['remaining_seconds'] = user.trial_remaining_seconds
        
        return Response(response_data)