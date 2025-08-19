from django.contrib import admin
from .models import Course

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'level', 'base_price', 'duration_hours', 'is_active', 'created_at')
    list_filter = ('is_active', 'category','created_at')
    search_fields = ('name', 'description', 'category')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('category', 'name')
    readonly_fields = ('created_at', 'updated_at')


