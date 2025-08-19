from rest_framework import serializers
from .models import CourseSubscription
from courses.models import Course


class CreateOrderSerializer(serializers.Serializer):
    course_id = serializers.IntegerField()

    def validate_course_id(self, value):
        try:
            course = Course.objects.get(id=value, is_active=True)
        except Course.DoesNotExist:
            raise serializers.ValidationError("Course not found or inactive")
        
        # Check if already subscribed
        if CourseSubscription.objects.filter(
            student=self.context['request'].user,
            course=course,
            payment_status='completed'
        ).exists():
            raise serializers.ValidationError("Already subscribed to this course")
        
        return value

    def validate(self, attrs):
        # Ensure user is verified
        if not self.context['request'].user.is_verified:
            errors = []
            if not self.context['request'].user.email_verified:
                errors.append("Email not verified")
            if not self.context['request'].user.phone_verified:
                errors.append("Phone not verified")
            raise serializers.ValidationError(errors)
        
        return attrs


class VerifyPaymentSerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField()
    razorpay_payment_id = serializers.CharField()
    razorpay_signature = serializers.CharField()
    subscription_id = serializers.IntegerField()

    def validate(self, attrs):
        # Verify subscription exists
        try:
            subscription = CourseSubscription.objects.get(
                id=attrs['subscription_id'],
                order_id=attrs['razorpay_order_id'],
                student=self.context['request'].user,
                payment_status='pending'  # Only allow pending subscriptions
            )
        except CourseSubscription.DoesNotExist:
            raise serializers.ValidationError("Subscription not found or already processed")
        
        attrs['subscription'] = subscription
        return attrs