from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, OTP

class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'role', 'email_verified', 'phone_verified', 'is_active')
    list_filter = ('role', 'email_verified', 'phone_verified', 'is_active', 'is_staff')
    search_fields = ('email', 'username', 'first_name', 'last_name', 'phone_number')
    ordering = ('-created_at',)
    
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Info', {'fields': ('role', 'phone_number', 'email_verified', 'phone_verified')}),
    )
    
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Info', {'fields': ('email', 'role', 'phone_number')}),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'otp_type', 'purpose', 'otp_code', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('otp_type', 'purpose', 'is_verified', 'created_at')
    search_fields = ('identifier', 'otp_code')
    ordering = ('-created_at',)
    readonly_fields = ('created_at', 'expires_at')


admin.site.register(User, CustomUserAdmin)
