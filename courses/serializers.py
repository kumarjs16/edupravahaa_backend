from rest_framework import serializers
from .models import Course, Enrollment
from accounts.serializers import UserSerializer

class CourseSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.get_full_name', read_only=True)
    enrolled_students_count = serializers.IntegerField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'description', 'price', 'teacher',
            'teacher_name', 'category', 'thumbnail', 'duration_weeks',
            'is_active', 'enrolled_students_count', 'is_enrolled',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
        
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Enrollment.objects.filter(
                student=request.user,
                course=obj,
                payment_status='completed'
            ).exists()
        return False

class CourseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'name', 'description', 'price', 'category',
            'thumbnail', 'duration_weeks'
        ]
        
    def create(self, validated_data):
        # Teacher is set from the request user in the view
        return Course.objects.create(**validated_data)

class EnrollmentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)
    student = UserSerializer(read_only=True)
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'student', 'course', 'payment_status',
            'payment_id', 'order_id', 'amount_paid',
            'enrolled_at', 'updated_at'
        ]
        read_only_fields = ['id', 'enrolled_at', 'updated_at']

class EnrollmentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Enrollment
        fields = ['course']
        
    def validate_course(self, value):
        # Check if course is active
        if not value.is_active:
            raise serializers.ValidationError("This course is not active.")
        
        # Check if student is already enrolled
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            existing_enrollment = Enrollment.objects.filter(
                student=request.user,
                course=value
            ).first()
            
            if existing_enrollment:
                if existing_enrollment.payment_status == 'completed':
                    raise serializers.ValidationError("You are already enrolled in this course.")
                elif existing_enrollment.payment_status == 'pending':
                    raise serializers.ValidationError("You have a pending enrollment for this course.")
        
        return value