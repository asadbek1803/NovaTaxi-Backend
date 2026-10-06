from django.contrib import admin

from shared.models import Region, District, Mfy, Street


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)
    ordering = ('name',)


@admin.register(District)
class DistrictAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'region', 'latitude', 'longitude')
    list_filter = ('region',)
    search_fields = ('name', 'region__name')
    ordering = ('region', 'name')


@admin.register(Mfy)
class MfyAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'district', 'type', 'latitude', 'longitude')
    list_filter = ('district__region', 'type')
    search_fields = ('name', 'district__name')
    ordering = ('district__region', 'district', 'name')


@admin.register(Street)
class StreetAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'mfy', 'latitude', 'longitude')
    search_fields = ('name', 'mfy__name')
    ordering = ('mfy', 'name')
