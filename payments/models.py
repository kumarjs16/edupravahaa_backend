from django.db import models
from django.conf import settings
from django.utils import timezone
from courses.models import Course


class CourseSubscription(models.Model):
    """
    Tracks individual course purchases by students.
    Each purchase grants lifetime access to that specific course.
    """
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded'),
    )
    
    PAYMENT_METHOD_CHOICES = (
        ('razorpay', 'Razorpay'),
        ('stripe', 'Stripe'),
        ('paypal', 'PayPal'),
        ('bank_transfer', 'Bank Transfer'),
        ('free', 'Free'),
        ('other', 'Other'),
    )
    
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='course_subscriptions'
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,  # Protect course from deletion if subscriptions exist
        related_name='subscriptions'
    )
    
    # Payment details
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    payment_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    order_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHOD_CHOICES, default='other')
    
    # Additional payment info
    currency = models.CharField(max_length=3, default='INR')
    payment_response = models.JSONField(null=True, blank=True)  # Store full payment gateway response
    
    # Timestamps
    purchased_at = models.DateTimeField(auto_now_add=True)
    payment_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Access control
    is_active = models.BooleanField(default=True)  # For manual access control if needed
    
    class Meta:
        db_table = 'course_subscriptions'
        unique_together = ['student', 'course']  # One subscription per student per course
        ordering = ['-purchased_at']
        indexes = [
            models.Index(fields=['student', 'payment_status']),
            models.Index(fields=['course', 'payment_status']),
        ]
    
    def __str__(self):
        return f"{self.student.email} - {self.course.name} ({self.payment_status})"
    
    def save(self, *args, **kwargs):
        # When a payment is completed, update user's purchase status
        if self.payment_status == 'completed':
            # Update user's purchase status
            if not self.student.has_purchased_courses:
                self.student.has_purchased_courses = True
                self.student.save(update_fields=['has_purchased_courses'])
            
            # Set payment completion time
            if not self.payment_completed_at:
                self.payment_completed_at = timezone.now()
        
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        """Check if subscription is expired - always False for lifetime access"""
        return False  # Lifetime access
    
    @property
    def has_access(self):
        """Check if student has access to the course"""
        return self.payment_status == 'completed' and self.is_active