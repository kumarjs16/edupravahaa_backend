from django.urls import path
from .views import (
    CourseListView, CourseDetailView, CourseCreateView,
    CourseUpdateView, CourseDeleteView, TeacherCoursesView,
    StudentEnrollmentsView, CourseEnrollmentsView
)

app_name = 'courses'

urlpatterns = [
    # Public course endpoints
    path('', CourseListView.as_view(), name='course_list'),
    path('<slug:slug>/', CourseDetailView.as_view(), name='course_detail'),
    
    # Teacher course management
    path('create/', CourseCreateView.as_view(), name='course_create'),
    path('<slug:slug>/update/', CourseUpdateView.as_view(), name='course_update'),
    path('<slug:slug>/delete/', CourseDeleteView.as_view(), name='course_delete'),
    path('teacher/my-courses/', TeacherCoursesView.as_view(), name='teacher_courses'),
    
    # Enrollment endpoints
    path('student/enrollments/', StudentEnrollmentsView.as_view(), name='student_enrollments'),
    path('<slug:slug>/enrollments/', CourseEnrollmentsView.as_view(), name='course_enrollments'),
]