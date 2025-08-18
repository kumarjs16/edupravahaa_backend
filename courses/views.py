from rest_framework import generics, status, views
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Course, Enrollment
from .serializers import (
    CourseSerializer
)
from accounts.permissions import IsTeacher, IsStudent, IsTeacherOrAdmin, IsAdmin
from payments.models import CourseSubscription

class CourseListView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_active=True)
        
        # Filter by search query
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(category__icontains=search)
            )
        
        # Filter by category
        category = self.request.query_params.get('category', None)
        if category:
            queryset = queryset.filter(category__iexact=category)

            
        return queryset




# Admin Course Management Views
class AdminCourseCreateView(generics.CreateAPIView):
    """Admin-only API to create new courses"""
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    
    @swagger_auto_schema(
        operation_description="Create a new course with all details (Admin only)",
        request_body=CourseSerializer
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.save()
        
        return Response({
            'message': 'Course created successfully',
            'course': CourseSerializer(course, context={'request': request}).data
        }, status=status.HTTP_201_CREATED)


class AdminCourseUpdateView(generics.UpdateAPIView):
    """Admin-only API to update course details"""
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
    lookup_field = 'id'

