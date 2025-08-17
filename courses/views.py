from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi

from .models import Course, Enrollment
from .serializers import (
    CourseSerializer, CourseCreateSerializer,
    EnrollmentSerializer, EnrollmentCreateSerializer
)
from accounts.permissions import IsTeacher, IsStudent, IsTeacherOrAdmin

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
            
        # Filter by teacher
        teacher_id = self.request.query_params.get('teacher', None)
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
            
        return queryset

class CourseDetailView(generics.RetrieveAPIView):
    queryset = Course.objects.filter(is_active=True)
    serializer_class = CourseSerializer
    permission_classes = [AllowAny]
    lookup_field = 'slug'

class CourseCreateView(generics.CreateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseCreateSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    
    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user)

class CourseUpdateView(generics.UpdateAPIView):
    queryset = Course.objects.all()
    serializer_class = CourseCreateSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Teachers can only update their own courses
        if self.request.user.is_teacher:
            return Course.objects.filter(teacher=self.request.user)
        # Admins can update any course
        return Course.objects.all()

class CourseDeleteView(generics.DestroyAPIView):
    queryset = Course.objects.all()
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    lookup_field = 'slug'
    
    def get_queryset(self):
        # Teachers can only delete their own courses
        if self.request.user.is_teacher:
            return Course.objects.filter(teacher=self.request.user)
        # Admins can delete any course
        return Course.objects.all()
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        # Soft delete - just mark as inactive
        instance.is_active = False
        instance.save()
        return Response(
            {"message": "Course deleted successfully"},
            status=status.HTTP_204_NO_CONTENT
        )

class TeacherCoursesView(generics.ListAPIView):
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated, IsTeacher]
    
    def get_queryset(self):
        return Course.objects.filter(teacher=self.request.user)

class StudentEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsStudent]
    
    def get_queryset(self):
        return Enrollment.objects.filter(
            student=self.request.user,
            payment_status='completed'
        )

class CourseEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    permission_classes = [IsAuthenticated, IsTeacherOrAdmin]
    
    def get_queryset(self):
        course_slug = self.kwargs.get('slug')
        queryset = Enrollment.objects.filter(
            course__slug=course_slug,
            payment_status='completed'
        )
        
        # Teachers can only see enrollments for their courses
        if self.request.user.is_teacher:
            queryset = queryset.filter(course__teacher=self.request.user)
            
        return queryset
