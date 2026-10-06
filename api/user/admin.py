from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import OTPCode, RefreshToken, User, UserSettings


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ['id', 'phone', 'full_name', 'is_verified', 'is_driver', 'is_staff', 'is_superuser', 'rating', 'created_at']
    search_fields = ['phone', 'full_name']
    list_filter = ['is_verified', 'is_driver', 'is_staff', 'is_active']

    fieldsets = (
        (None, {'fields': ('phone', 'password')}),
        ('Shaxsiy ma\'lumotlar', {'fields': ('full_name', 'avatar_url')}),
        ('Ruxsatlar', {'fields': ('is_active', 'is_staff', 'is_superuser', 'is_verified', 'is_driver', 'groups', 'user_permissions')}),
        ('Statistika', {'fields': ('rating', 'total_rides')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('phone', 'password1', 'password2', 'is_staff', 'is_superuser', 'is_active'),
        }),
    )

    ordering = ['-created_at']
    readonly_fields = ['id', 'created_at', 'updated_at']
    list_per_page = 25


@admin.register(OTPCode)
class OTPCodeAdmin(admin.ModelAdmin):
    list_display = ['phone', 'code', 'is_used', 'created_at']
    list_filter = ['is_used']


@admin.register(UserSettings)
class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ['user', 'language', 'notifications_enabled', 'dark_mode']


@admin.register(RefreshToken)
class RefreshTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'is_revoked', 'created_at']
    list_filter = ['is_revoked']
