from django.urls import path
from .views import (
    CourseListView, AdminCourseCreateView, AdminCourseUpdateView
)

app_name = 'courses'

urlpatterns = [
    # Public course endpoints
    path('', CourseListView.as_view(), name='course_list'),
    
    # Admin endpoints
    path('admin/create/course/', AdminCourseCreateView.as_view(), name='admin_course_create'),
    path('admin/update/<int:id>/', AdminCourseUpdateView.as_view(), name='admin_course_update'),

]