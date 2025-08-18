from rest_framework import serializers
from .models import Course, Enrollment
from accounts.serializers import UserSerializer
from django.utils import timezone
from datetime import datetime, timedelta

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = [
            'id', 'name', 'slug', 'description', 'category',
            'thumbnail', 'duration_hours', 'base_price', 'advantages', 
            'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
        
