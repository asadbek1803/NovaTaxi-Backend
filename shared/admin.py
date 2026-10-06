from django.contrib import admin

from .models import (
    CarCategory, SurgePricing, Driver, Ride,
    Location, SavedLocation,
    ChatThread, ChatMessage,
    PaymentMethod,
    Notification, FCMToken, ScheduledNotification,
    SupportTicket,
)


@admin.register(CarCategory)
class CarCategoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'base_fare', 'price_per_km', 'price_per_minute',
                    'estimated_arrival_time', 'is_cargo', 'is_active']
    list_filter = ['is_active', 'is_cargo']
    search_fields = ['name', 'id']


@admin.register(SurgePricing)
class SurgePricingAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'reason', 'multiplier', 'is_active', 'created_at']
    list_filter = ['is_active', 'reason']
    search_fields = ['name']


@admin.register(Driver)
class DriverAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'phone', 'car_model', 'license_plate', 'rating',
                    'is_available', 'is_cargo', 'category']
    list_filter = ['is_available', 'is_cargo', 'category']


@admin.register(Ride)
class RideAdmin(admin.ModelAdmin):
    list_display = ['id', 'passenger', 'driver', 'status', 'price', 'created_at']
    list_filter = ['status']


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'type', 'lat', 'lng']


@admin.register(SavedLocation)
class SavedLocationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'name']


@admin.register(ChatThread)
class ChatThreadAdmin(admin.ModelAdmin):
    list_display = ['id', 'ride', 'driver', 'passenger', 'unread_count', 'created_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'thread', 'sender', 'text', 'is_read', 'created_at']


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'type', 'holder_name', 'expiry', 'is_default']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'is_read', 'created_at']


@admin.register(FCMToken)
class FCMTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'token', 'created_at']


@admin.register(ScheduledNotification)
class ScheduledNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'target', 'frequency', 'send_time', 'is_active', 'last_sent_at']
    list_filter = ['is_active', 'frequency', 'target']


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'subject', 'status', 'created_at']
    list_filter = ['status']
