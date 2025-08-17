from django.contrib import admin
from .models import Course, Enrollment

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'teacher', 'category', 'price', 'is_active', 'created_at')
    list_filter = ('is_active', 'category', 'created_at')
    search_fields = ('name', 'description', 'teacher__email')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('-created_at',)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'course', 'payment_status', 'amount_paid', 'enrolled_at')
    list_filter = ('payment_status', 'enrolled_at')
    search_fields = ('student__email', 'course__name', 'payment_id', 'order_id')
    ordering = ('-enrolled_at',)
