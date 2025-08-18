from django.contrib import admin
from .models import Course, Enrollment

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'level', 'base_price', 'duration_hours', 'is_active', 'created_at')
    list_filter = ('is_active', 'category','created_at')
    search_fields = ('name', 'description', 'category')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('category', 'name')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'payment_status', 'amount_paid', 'enrolled_at')
    list_filter = ('payment_status', 'enrolled_at')
    search_fields = ('student__email','payment_id', 'order_id')
    ordering = ('-enrolled_at',)
    readonly_fields = ('enrolled_at', 'updated_at')
