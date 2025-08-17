from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
from django.core.exceptions import ValidationError
import random


class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('teacher', 'Teacher'),
        ('student', 'Student'),
    )
    
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False, max_length=13)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    trial_end_date = models.DateTimeField(null=True, blank=True)
    has_purchased_courses = models.BooleanField(default=False)

    USERNAME_FIELD = 'email'
    # REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        
    def __str__(self):
        return f"{self.email} - {self.role}"

    def save(self, *args, **kwargs):
        if not self.pk and not self.trial_end_date and self.role == 'student':
            # Set trial end date only for students on registration
            trial_settings = getattr(settings, 'TRIAL_SETTINGS', {})
            if trial_settings.get('TEST_MODE', True):
                # Use minutes for testing
                duration = timedelta(minutes=trial_settings.get('TRIAL_DURATION_MINUTES', 5))
            else:
                # Use days for production
                duration = timedelta(days=trial_settings.get('TRIAL_DURATION_MINUTES', 5))
            
            self.trial_end_date = timezone.now() + duration
        
        super().save(*args, **kwargs)
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_teacher(self):
        return self.role == 'teacher'
    
    @property
    def is_student(self):
        return self.role == 'student'
    
    @property
    def is_verified(self):
        return self.email_verified and self.phone_verified

    @property
    def is_trial_expired(self):
        """Check if trial period has expired"""
        if self.has_purchased_courses or self.role != 'student':
            return False  # Never expires if user has purchased courses or not a student
        
        if not self.trial_end_date:
            return False
        
        return timezone.now() > self.trial_end_date

    @property
    def trial_remaining_seconds(self):
        """Calculate seconds remaining in trial"""
        if self.has_purchased_courses or self.role != 'student':
            return None  # No trial limit for users with purchases or non-students
        
        if not self.trial_end_date:
            return 0
        
        time_remaining = self.trial_end_date - timezone.now()
        
        if time_remaining.total_seconds() <= 0:
            return 0
        
        return int(time_remaining.total_seconds())


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
        limit_choices_to={'role': 'teacher'}
    )
    bio = models.TextField(blank=True, help_text="Teacher's biography or description")
    qualifications = models.JSONField(default=list, blank=True, help_text="List of qualifications, e.g., ['PhD', '10 years experience']")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'teacher_profiles'
        indexes = [
            models.Index(fields=['user']),
        ]
    
    def __str__(self):
        return f"Profile for {self.user.email}"
    
    def save(self, *args, **kwargs):
        if self.user.role != 'teacher':
            raise ValidationError("TeacherProfile can only be created for users with role 'teacher'.")
        super().save(*args, **kwargs)

        
class OTP(models.Model):
    OTP_TYPE_CHOICES = (
        ('email', 'Email'),
        ('phone', 'Phone'),
    )
    
    PURPOSE_CHOICES = (
        ('registration', 'Registration'),
        ('password_reset', 'Password Reset'),
    )
    
    identifier = models.CharField(max_length=255)  # email or phone number
    otp_type = models.CharField(max_length=10, choices=OTP_TYPE_CHOICES)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES)
    otp_code = models.CharField(max_length=4)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        db_table = 'otps'
        indexes = [
            models.Index(fields=['identifier', 'otp_type', 'purpose']),
        ]
    
    def save(self, *args, **kwargs):
        if not self.otp_code:
            self.otp_code = str(random.randint(1000, 9999))
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def __str__(self):
        return f"{self.identifier} - {self.otp_type} - {self.purpose}"
