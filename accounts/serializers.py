from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User, TeacherProfile, OTP


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'phone_number', 'first_name', 
                  'last_name', 'role', 'email_verified', 'phone_verified', 
                  'date_joined']
        read_only_fields = ['id', 'date_joined', 'email_verified', 'phone_verified']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    phone_number = serializers.CharField(max_length=13)
    password = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value
    
    def validate(self, attrs):
        email = attrs['email']
        phone_number = attrs['phone_number']
        return attrs
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        
        user = User.objects.create_user(
            **validated_data,
            role='student',
            email_verified=True,
            phone_verified=True
        )
        user.set_password(password)
        user.save()
        
        return user

class TeacherCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone_number', 'password', 
                  'first_name', 'last_name']
        
    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered")
        return value
    
    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number already registered")
        return value
    
    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(
            **validated_data,
            role='teacher',
            email_verified=True,  # Teachers are pre-verified by admin
            phone_verified=True
        )
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    
    def validate_old_password(self, value):
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate_new_password(self, value):
        # Add any password strength validation here
        return value
    
    def save(self):
        user = self.context.get('request').user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    password = serializers.CharField()
    
    def validate(self, attrs):
        identifier = attrs.get('identifier')
        password = attrs.get('password')
        
        if not identifier or not password:
            raise serializers.ValidationError('Must include "identifier" and "password".')
        
        user = None
        
        # Check if identifier looks like an email
        if '@' in identifier:
            # Try to authenticate with email (USERNAME_FIELD is email)
            user = authenticate(username=identifier, password=password)
        
        # If not authenticated yet, try with phone number
        if not user:
            try:
                user_obj = User.objects.get(phone_number=identifier)
                # Since USERNAME_FIELD is email, we need to use the user's email to authenticate
                user = authenticate(username=user_obj.email, password=password)
            except User.DoesNotExist:
                pass
        
        # If still not authenticated, try with username
        if not user:
            try:
                user_obj = User.objects.get(username=identifier)
                # Since USERNAME_FIELD is email, we need to use the user's email to authenticate
                user = authenticate(username=user_obj.email, password=password)
            except User.DoesNotExist:
                pass
        
        if not user:
            raise serializers.ValidationError('Invalid credentials.')
        
        if not user.is_active:
            raise serializers.ValidationError('User account is disabled.')
        
        attrs['user'] = user
        return attrs


class SendOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email address or phone number")
    identifier_type = serializers.ChoiceField(choices=['email', 'phone'], required=False, 
                                               help_text="Optional - will be auto-detected if not provided")
    purpose = serializers.ChoiceField(choices=['registration', 'password_reset'])


class VerifyOTPSerializer(serializers.Serializer):
    identifier = serializers.CharField(help_text="Email address or phone number")
    identifier_type = serializers.ChoiceField(choices=['email', 'phone'], required=False,
                                               help_text="Optional - will be auto-detected if not provided")
    otp_code = serializers.CharField(max_length=4)
    purpose = serializers.ChoiceField(choices=['registration', 'password_reset'])


class ForgotPasswordSerializer(serializers.Serializer):
    identifier = serializers.CharField()
    otp_code = serializers.CharField(max_length=4)
    new_password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField(min_length=8)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError("Passwords don't match")
        
        identifier = attrs['identifier']
        
        # Try to find user by email or phone
        user = None
        identifier_type = None
        
        if '@' in identifier:
            # It's an email
            identifier_type = 'email'
            try:
                user = User.objects.get(email=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")
        else:
            # It's a phone number
            identifier_type = 'phone'
            try:
                user = User.objects.get(phone_number=identifier)
            except User.DoesNotExist:
                raise serializers.ValidationError("User not found")
        
        # Verify OTP - Allow both verified (from verify-otp step) and unverified OTPs
        otp = OTP.objects.filter(
            identifier=identifier,
            otp_type=identifier_type,
            purpose='password_reset',
            otp_code=attrs['otp_code']
        ).order_by('-created_at').first()
        
        if not otp or otp.is_expired:
            raise serializers.ValidationError("Invalid or expired OTP")
        
        attrs['user'] = user
        attrs['otp'] = otp
        return attrs


class TeacherProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = ['bio', 'qualifications']


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    
    def validate_old_password(self, value):
        user = self.context.get('request').user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect")
        return value
    
    def validate_new_password(self, value):
        # Add any password strength validation here
        return value
    
    def save(self):
        user = self.context.get('request').user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
