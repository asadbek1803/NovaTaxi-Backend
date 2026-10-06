from rest_framework.permissions import BasePermission


class IsDriver(BasePermission):
    message = "Faqat haydovchilar uchun ruxsat berilgan"

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_driver', False)
        )


class IsDriverVerified(BasePermission):
    message = "Haydovchi hali tasdiqlanmagan"

    def has_permission(self, request, view):
        if not (
            request.user
            and request.user.is_authenticated
            and getattr(request.user, 'is_driver', False)
        ):
            return False
        driver = getattr(request.user, 'driver_profile', None)
        if not driver:
            return False
        return bool(driver.is_verified and driver.is_active)
