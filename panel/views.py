import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Q
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from shared.models import Region, District, Mfy, Street, Driver, Ride, DriverProfile, Vehicle, CarCategory, SurgePricing, SupportTicket, Notification
from api.user.models import User


def staff_required(view_func):
    decorated = login_required(view_func, login_url='/panel/login/')
    return user_passes_test(
        lambda u: u.is_staff or u.is_superuser,
        login_url='/panel/login/'
    )(decorated)


def login_view(request):
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return redirect('panel:dashboard')

    if request.method == 'POST':
        phone = request.POST.get('phone', '')
        password = request.POST.get('password', '')
        user = authenticate(request, username=phone, password=password)
        if user and (user.is_staff or user.is_superuser):
            login(request, user)
            return redirect('panel:dashboard')
        messages.error(request, "Telefon raqam yoki parol noto'g'ri")

    return render(request, 'panel/login.html')


def logout_view(request):
    logout(request)
    return redirect('panel:login')


@staff_required
def dashboard_view(request):
    today = timezone.now().date()
    today_start = timezone.make_aware(timezone.datetime.combine(today, timezone.datetime.min.time()))
    yesterday = today - timedelta(days=1)
    yesterday_start = timezone.make_aware(timezone.datetime.combine(yesterday, timezone.datetime.min.time()))

    total_drivers = Driver.objects.filter(is_active=True).count()
    online_drivers = Driver.objects.filter(is_active=True, is_available=True).count()
    total_users = User.objects.filter(is_driver=False, is_active=True).count()
    total_users_yesterday = User.objects.filter(is_driver=False, is_active=True, created_at__lt=today_start).count()

    today_rides = Ride.objects.filter(created_at__gte=today_start)
    yesterday_rides = Ride.objects.filter(created_at__gte=yesterday_start, created_at__lt=today_start)
    completed_today = today_rides.filter(status='completed').count()
    completed_yesterday = yesterday_rides.filter(status='completed').count()
    cancelled_today = today_rides.filter(status='cancelled').count()
    pending_today = today_rides.filter(status='pending').count()
    active_rides = Ride.objects.filter(status__in=['accepted', 'arriving', 'in_progress']).count()

    today_revenue = today_rides.filter(status='completed').aggregate(total=Sum('price'))['total'] or 0
    yesterday_revenue = yesterday_rides.filter(status='completed').aggregate(total=Sum('price'))['total'] or 0
    total_revenue = Ride.objects.filter(status='completed').aggregate(total=Sum('price'))['total'] or 0
    total_rides_all = Ride.objects.filter(status='completed').count()

    revenue_change = 0
    if yesterday_revenue > 0:
        revenue_change = round(((today_revenue - yesterday_revenue) / yesterday_revenue) * 100, 1)
    rides_change = 0
    if completed_yesterday > 0:
        rides_change = round(((completed_today - completed_yesterday) / completed_yesterday) * 100, 1)
    users_change = 0
    if total_users_yesterday > 0:
        users_change = round(((total_users - total_users_yesterday) / total_users_yesterday) * 100, 1)

    weekly_data = []
    for i in range(6, -1, -1):
        day = today - timedelta(days=i)
        day_start = timezone.make_aware(timezone.datetime.combine(day, timezone.datetime.min.time()))
        day_end = timezone.make_aware(timezone.datetime.combine(day + timedelta(days=1), timezone.datetime.min.time()))
        revenue = Ride.objects.filter(
            status='completed', created_at__gte=day_start, created_at__lt=day_end
        ).aggregate(t=Sum('price'))['t'] or 0
        ride_count = Ride.objects.filter(
            created_at__gte=day_start, created_at__lt=day_end
        ).count()
        weekly_data.append({
            'day': day.strftime('%a'),
            'date': day.strftime('%d.%m'),
            'revenue': revenue,
            'rides': ride_count,
        })

    status_counts = {
        'completed': Ride.objects.filter(status='completed').count(),
        'cancelled': Ride.objects.filter(status='cancelled').count(),
        'pending': Ride.objects.filter(status='pending').count(),
        'active': Ride.objects.filter(status__in=['accepted', 'arriving', 'in_progress']).count(),
    }

    recent_rides = Ride.objects.select_related('passenger', 'driver', 'category').order_by('-created_at')[:10]
    pending_kyc = DriverProfile.objects.filter(is_submitted=True, is_verified=False).select_related('user').count()
    open_support_count = SupportTicket.objects.filter(status='open').count()

    context = {
        'total_drivers': total_drivers,
        'online_drivers': online_drivers,
        'total_users': total_users,
        'completed_today': completed_today,
        'cancelled_today': cancelled_today,
        'pending_today': pending_today,
        'active_rides': active_rides,
        'today_revenue': today_revenue,
        'yesterday_revenue': yesterday_revenue,
        'total_revenue': total_revenue,
        'total_rides_all': total_rides_all,
        'revenue_change': revenue_change,
        'rides_change': rides_change,
        'users_change': users_change,
        'weekly_data_json': json.dumps(weekly_data),
        'status_counts_json': json.dumps(status_counts),
        'recent_rides': recent_rides,
        'pending_kyc': pending_kyc,
        'open_support_count': open_support_count,
    }
    return render(request, 'panel/dashboard.html', context)


@staff_required
def map_view(request):
    return render(request, 'panel/map.html')


@staff_required
def api_drivers_locations(request):
    drivers = Driver.objects.filter(is_active=True).select_related('user').prefetch_related('rides').values(
        'id', 'name', 'phone', 'current_lat', 'current_lng',
        'heading', 'is_available', 'car_model', 'license_plate', 'rating'
    )
    driver_list = list(drivers)
    driver_map = {d['id']: d for d in driver_list}

    active_rides = Ride.objects.filter(
        status__in=['accepted', 'arriving', 'in_progress']
    ).select_related('passenger').only(
        'id', 'driver_id', 'passenger_id', 'from_lat', 'from_lng',
        'from_address', 'status', 'price', 'category_id'
    )

    for ride in active_rides:
        did = ride.driver_id
        if did in driver_map:
            if 'rides' not in driver_map[did]:
                driver_map[did]['rides'] = []
            driver_map[did]['rides'].append({
                'id': ride.id,
                'passenger_name': ride.passenger.full_name or ride.passenger.phone,
                'passenger_id': ride.passenger.id,
                'from_address': ride.from_address,
                'from_lat': ride.from_lat,
                'from_lng': ride.from_lng,
                'status': ride.status,
                'price': ride.price,
                'category': ride.category_id,
            })

    return JsonResponse({'drivers': driver_list})


@staff_required
def api_active_rides(request):
    rides = Ride.objects.filter(
        status__in=['pending', 'accepted', 'arriving', 'in_progress']
    ).select_related('passenger', 'driver').order_by('-created_at')

    data = []
    for ride in rides:
        item = {
            'id': ride.id,
            'passenger': {
                'id': ride.passenger.id,
                'name': ride.passenger.full_name or ride.passenger.phone,
                'phone': ride.passenger.phone,
                'avatar_url': ride.passenger.avatar_url or '',
            },
            'from_lat': ride.from_lat,
            'from_lng': ride.from_lng,
            'from_address': ride.from_address,
            'to_lat': ride.to_lat,
            'to_lng': ride.to_lng,
            'to_address': ride.to_address,
            'status': ride.status,
            'price': ride.price,
            'category': ride.category_id or '',
            'driver_id': ride.driver_id or '',
        }
        if ride.driver_id:
            item['driver'] = {
                'id': ride.driver.id,
                'name': ride.driver.name,
                'phone': ride.driver.phone,
                'car_model': ride.driver.car_model,
                'license_plate': ride.driver.license_plate,
            }
        data.append(item)

    return JsonResponse({'rides': data})


@staff_required
def drivers_list_view(request):
    drivers = Driver.objects.select_related('user').order_by('-created_at')
    total = drivers.count()
    active = drivers.filter(is_active=True).count()
    verified = drivers.filter(is_verified=True).count()
    context = {
        'drivers': drivers,
        'total': total,
        'active': active,
        'verified': verified,
    }
    return render(request, 'panel/drivers.html', context)


@staff_required
def users_list_view(request):
    users = User.objects.filter(is_driver=False).order_by('-created_at')
    total = users.count()
    active = users.filter(is_active=True).count()
    verified = users.filter(is_verified=True).count()
    context = {
        'users': users,
        'total': total,
        'active': active,
        'verified': verified,
    }
    return render(request, 'panel/users.html', context)


@staff_required
def tariffs_view(request):
    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'add_surge':
            name = request.POST.get('surge_name', '')
            reason = request.POST.get('surge_reason', 'custom')
            multiplier = request.POST.get('surge_multiplier', '1.0')
            description = request.POST.get('surge_description', '')
            try:
                multiplier = float(multiplier)
                if multiplier < 1.0:
                    multiplier = 1.0
                if multiplier > 5.0:
                    multiplier = 5.0
            except (ValueError, TypeError):
                multiplier = 1.0
            SurgePricing.objects.create(
                name=name, reason=reason, multiplier=multiplier, description=description
            )
            messages.success(request, f"Surge narxi qo'shildi: {name} ({multiplier}x)")
        elif action == 'toggle_surge':
            surge_id = request.POST.get('surge_id')
            try:
                surge = SurgePricing.objects.get(id=surge_id)
                surge.is_active = not surge.is_active
                surge.save()
                status = 'faollashtirildi' if surge.is_active else 'o\'chirildi'
                messages.success(request, f"'{surge.name}' {status}")
            except SurgePricing.DoesNotExist:
                messages.error(request, "Surge topilmadi")
        elif action == 'delete_surge':
            surge_id = request.POST.get('surge_id')
            try:
                surge = SurgePricing.objects.get(id=surge_id)
                name = surge.name
                surge.delete()
                messages.success(request, f"'{name}' o'chirildi")
            except SurgePricing.DoesNotExist:
                messages.error(request, "Surge topilmadi")
        elif action == 'toggle_category':
            cat_id = request.POST.get('cat_id')
            try:
                cat = CarCategory.objects.get(id=cat_id)
                cat.is_active = not cat.is_active
                cat.save()
                status = 'faollashtirildi' if cat.is_active else 'o\'chirildi'
                messages.success(request, f"'{cat.name}' {status}")
            except CarCategory.DoesNotExist:
                messages.error(request, "Kategoriya topilmadi")
        elif action == 'update_tariff':
            cat_id = request.POST.get('cat_id')
            try:
                cat = CarCategory.objects.get(id=cat_id)
                cat.name = request.POST.get('cat_name', cat.name).strip() or cat.name
                try:
                    cat.base_fare = int(request.POST.get('base_fare', cat.base_fare))
                except (ValueError, TypeError):
                    pass
                try:
                    cat.price_per_km = int(request.POST.get('price_per_km', cat.price_per_km))
                except (ValueError, TypeError):
                    pass
                try:
                    cat.price_per_minute = int(request.POST.get('price_per_minute', cat.price_per_minute))
                except (ValueError, TypeError):
                    pass
                try:
                    cat.estimated_arrival_time = int(request.POST.get('estimated_arrival_time', cat.estimated_arrival_time))
                except (ValueError, TypeError):
                    pass
                cat.description = request.POST.get('cat_description', cat.description).strip()
                cat.save()
                messages.success(request, f"'{cat.name}' tarifi yangilandi")
            except CarCategory.DoesNotExist:
                messages.error(request, "Kategoriya topilmadi")
        return redirect('panel:tariffs')

    categories = CarCategory.objects.all()
    surges = SurgePricing.objects.all()
    active_surge = SurgePricing.objects.filter(is_active=True).order_by('-multiplier').first()
    context = {
        'categories': categories,
        'surges': surges,
        'active_surge': active_surge,
    }
    return render(request, 'panel/tariffs.html', context)


@staff_required
def notifications_view(request):
    from shared.models import Notification, FCMToken, ScheduledNotification
    from core.fcm import send_push_notification

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'send_notification':
            title = request.POST.get('notif_title', '').strip()
            body = request.POST.get('notif_body', '').strip()
            target = request.POST.get('notif_target', 'all')

            if not title or not body:
                messages.error(request, "Sarlavha va xabar majburiy")
                return redirect('panel:notifications')

            users = User.objects.filter(is_active=True)
            if target == 'drivers':
                users = users.filter(is_driver=True)
            elif target == 'passengers':
                users = users.filter(is_driver=False)

            user_ids = list(users.values_list('id', flat=True))

            created_count = 0
            for uid in user_ids:
                Notification.objects.create(
                    user_id=uid, title=title, body=body,
                    data={'type': 'admin_broadcast', 'target': target}
                )
                created_count += 1

            fcm_tokens = list(
                FCMToken.objects.filter(user_id__in=user_ids).values_list('token', flat=True)
            )

            push_result = {'success': 0, 'failed': 0}
            if fcm_tokens:
                push_result = send_push_notification(
                    tokens=fcm_tokens, title=title, body=body,
                    data={'type': 'admin_broadcast', 'target': target}
                )

            messages.success(
                request,
                f"Bildirishnoma yuborildi: {created_count} ta DB ga saqlandi, "
                f"{push_result['success']} ta push yetkazildi"
                + (f", {push_result['failed']} ta yetkazilmadi" if push_result['failed'] else "")
            )
            return redirect('panel:notifications')

        elif action == 'delete_notif':
            notif_id = request.POST.get('notif_id')
            try:
                notif = Notification.objects.get(id=notif_id)
                notif.delete()
                messages.success(request, "Bildirishnoma o'chirildi")
            except Notification.DoesNotExist:
                messages.error(request, "Bildirishnoma topilmadi")
            return redirect('panel:notifications')

        elif action == 'add_scheduled':
            title = request.POST.get('sched_title', '').strip()
            body = request.POST.get('sched_body', '').strip()
            target = request.POST.get('sched_target', 'all')
            frequency = request.POST.get('sched_frequency', 'daily')
            send_time = request.POST.get('sched_time', '09:00')

            if not title or not body:
                messages.error(request, "Sarlavha va xabar majburiy")
                return redirect('panel:notifications')

            days_of_week = []
            if frequency == 'weekly':
                days_of_week = request.POST.getlist('sched_days')

            ScheduledNotification.objects.create(
                title=title, body=body, target=target,
                frequency=frequency, send_time=send_time,
                days_of_week=days_of_week,
            )
            messages.success(request, f"Rejalashtirilgan bildirishnoma qo'shildi: {title}")
            return redirect('panel:notifications')

        elif action == 'toggle_scheduled':
            sched_id = request.POST.get('sched_id')
            try:
                sched = ScheduledNotification.objects.get(id=sched_id)
                sched.is_active = not sched.is_active
                sched.save(update_fields=['is_active'])
                status = 'faollashtirildi' if sched.is_active else "o'chirildi"
                messages.success(request, f"'{sched.title}' {status}")
            except ScheduledNotification.DoesNotExist:
                messages.error(request, "Bildirishnoma topilmadi")
            return redirect('panel:notifications')

        elif action == 'delete_scheduled':
            sched_id = request.POST.get('sched_id')
            try:
                sched = ScheduledNotification.objects.get(id=sched_id)
                name = sched.title
                sched.delete()
                messages.success(request, f"'{name}' o'chirildi")
            except ScheduledNotification.DoesNotExist:
                messages.error(request, "Bildirishnoma topilmadi")
            return redirect('panel:notifications')

    notifs = Notification.objects.select_related('user').order_by('-created_at')[:100]
    scheduled = ScheduledNotification.objects.all()
    notif_count = Notification.objects.count()
    fcm_count = FCMToken.objects.count()
    context = {
        'notifications': notifs,
        'scheduled_notifications': scheduled,
        'notif_count': notif_count,
        'fcm_count': fcm_count,
    }
    return render(request, 'panel/notifications.html', context)


@staff_required
def support_view(request):
    tickets = SupportTicket.objects.order_by('-created_at')
    total = tickets.count()
    open_count = tickets.filter(status='open').count()
    closed_count = tickets.filter(status='closed').count()
    context = {
        'tickets': tickets,
        'total': total,
        'open_count': open_count,
        'closed_count': closed_count,
    }
    return render(request, 'panel/support.html', context)


@staff_required
def kyc_list_view(request):
    status_filter = request.GET.get('status', 'pending')
    profiles = DriverProfile.objects.select_related('user').all()

    if status_filter == 'pending':
        profiles = profiles.filter(is_submitted=True, is_verified=False)
    elif status_filter == 'approved':
        profiles = profiles.filter(is_verified=True)
    elif status_filter == 'all':
        pass

    drivers_with_docs = []
    for profile in profiles:
        vehicle = Vehicle.objects.filter(user=profile.user).first()
        driver = Driver.objects.filter(user=profile.user).first()
        drivers_with_docs.append({
            'profile': profile,
            'vehicle': vehicle,
            'driver': driver,
        })

    context = {
        'drivers_with_docs': drivers_with_docs,
        'status_filter': status_filter,
        'pending_count': DriverProfile.objects.filter(is_submitted=True, is_verified=False).count(),
        'approved_count': DriverProfile.objects.filter(is_verified=True).count(),
    }
    return render(request, 'panel/kyc.html', context)


@staff_required
def kyc_approve_view(request, driver_id):
    if request.method != 'POST':
        return redirect('panel:kyc')
    profile = DriverProfile.objects.filter(id=driver_id).first()
    if not profile:
        messages.error(request, "Haydovchi topilmadi")
        return redirect('panel:kyc')
    profile.is_verified = True
    profile.is_submitted = True
    profile.rejection_reason = ''
    profile.save()
    driver = Driver.objects.filter(user=profile.user).first()
    if driver:
        driver.is_verified = True
        driver.is_active = True
        driver.rejection_reason = ''
        driver.subscription_end_date = timezone.now().date() + timedelta(days=60)
        driver.save()
    messages.success(request, f"Haydovchi {profile.user.phone} tasdiqlandi (60 kunlik free trial)")
    return redirect('panel:kyc')


@staff_required
def kyc_reject_view(request, driver_id):
    if request.method != 'POST':
        return redirect('panel:kyc')
    profile = DriverProfile.objects.filter(id=driver_id).first()
    if not profile:
        messages.error(request, "Haydovchi topilmadi")
        return redirect('panel:kyc')
    reason = request.POST.get('reason', '') or 'Hujjatlar rad etildi'
    profile.is_verified = False
    profile.is_submitted = False
    profile.rejection_reason = reason
    profile.save()
    driver = Driver.objects.filter(user=profile.user).first()
    if driver:
        driver.is_verified = False
        driver.is_available = False
        driver.rejection_reason = reason
        driver.save()
    messages.warning(request, f"Haydovchi {profile.user.phone} rad etildi")
    return redirect('panel:kyc')


@staff_required
def finances_view(request):
    rides = Ride.objects.select_related('passenger', 'driver', 'category').order_by('-created_at')
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'completed':
        rides = rides.filter(status='completed')
    elif status_filter == 'cancelled':
        rides = rides.filter(status='cancelled')
    elif status_filter == 'active':
        rides = rides.filter(status__in=['accepted', 'arriving', 'in_progress'])

    total_items = rides.count()
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    per_page = 20
    total_pages = max(1, -(-total_items // per_page))
    start = (page - 1) * per_page
    page_rides = rides[start:start + per_page]

    stats = {
        'total_rides': Ride.objects.count(),
        'completed': Ride.objects.filter(status='completed').count(),
        'cancelled': Ride.objects.filter(status='cancelled').count(),
        'total_revenue': Ride.objects.filter(status='completed').aggregate(t=Sum('price'))['t'] or 0,
        'today_revenue': Ride.objects.filter(
            status='completed', completed_at__date=timezone.now().date()
        ).aggregate(t=Sum('price'))['t'] or 0,
    }

    context = {
        'rides': page_rides,
        'stats': stats,
        'status_filter': status_filter,
        'current_page': page,
        'total_pages': total_pages,
        'total_items': total_items,
    }
    return render(request, 'panel/finances.html', context)


@staff_required
def dispatch_view(request):
    """Dispetcher Paneli — manual ride creation via phone calls."""
    drivers = Driver.objects.filter(is_active=True, is_available=True).select_related('user').order_by('name')
    categories = CarCategory.objects.filter(is_active=True)

    if request.method == 'POST':
        passenger_phone = request.POST.get('passenger_phone', '').strip()
        from_address = request.POST.get('from_address', '').strip()
        to_address = request.POST.get('to_address', '').strip()
        driver_id = request.POST.get('driver_id', '')
        category_id = request.POST.get('category_id', '')
        price = request.POST.get('price', '')
        region_id = request.POST.get('region_id', '')
        district_id = request.POST.get('district_id', '')
        mfy_id = request.POST.get('mfy_id', '')
        street_id = request.POST.get('street_id', '')

        try:
            from_lat = float(request.POST.get('from_lat', 0) or 0)
        except (ValueError, TypeError):
            from_lat = 0
        try:
            from_lng = float(request.POST.get('from_lng', 0) or 0)
        except (ValueError, TypeError):
            from_lng = 0
        try:
            to_lat = float(request.POST.get('to_lat', 0) or 0)
        except (ValueError, TypeError):
            to_lat = 0
        try:
            to_lng = float(request.POST.get('to_lng', 0) or 0)
        except (ValueError, TypeError):
            to_lng = 0

        if not passenger_phone or not from_address or not to_address:
            messages.error(request, "Barcha maydonlarni to'ldiring")
        else:
            try:
                price = int(price) if price else 0
            except (ValueError, TypeError):
                price = 0

            passenger, _ = User.objects.get_or_create(
                phone=passenger_phone,
                defaults={'full_name': passenger_phone, 'is_driver': False},
            )

            ride = Ride.objects.create(
                passenger=passenger,
                driver_id=driver_id or None,
                category_id=category_id or None,
                from_address=from_address,
                to_address=to_address,
                from_lat=from_lat,
                from_lng=from_lng,
                to_lat=to_lat,
                to_lng=to_lng,
                price=price,
                status='pending' if not driver_id else 'accepted',
                payment_method='cash',
            )
            messages.success(request, f"Sayohat #{str(ride.id)[:8]} yaratildi (dispetcher orqali)")
            return redirect('panel:dispatch')

    recent_dispatched = Ride.objects.filter(
        payment_method='cash'
    ).select_related('passenger', 'driver').order_by('-created_at')[:10]

    context = {
        'drivers': drivers,
        'categories': categories,
        'recent_dispatched': recent_dispatched,
    }
    return render(request, 'panel/dispatch.html', context)


@staff_required
def promocodes_view(request):
    """Promokodlar — discount code management."""
    from shared.models import PromoCode
    promocodes = PromoCode.objects.all().order_by('-created_at')

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'add':
            code = request.POST.get('code', '').strip().upper()
            discount_type = request.POST.get('discount_type', 'percent')
            discount_value = request.POST.get('discount_value', '10')
            max_uses = request.POST.get('max_uses', '100')
            try:
                discount_value = float(discount_value)
            except (ValueError, TypeError):
                discount_value = 10
            try:
                max_uses = int(max_uses)
            except (ValueError, TypeError):
                max_uses = 100

            if code:
                PromoCode.objects.create(
                    code=code,
                    discount_type=discount_type,
                    discount_value=discount_value,
                    max_uses=max_uses,
                )
                messages.success(request, f"Promokod '{code}' yaratildi")
            else:
                messages.error(request, "Promokod kiritilishi shart")
        elif action == 'toggle':
            pc_id = request.POST.get('promo_id')
            try:
                pc = PromoCode.objects.get(id=pc_id)
                pc.is_active = not pc.is_active
                pc.save(update_fields=['is_active'])
                status = 'faollashtirildi' if pc.is_active else "o'chirildi"
                messages.success(request, f"'{pc.code}' {status}")
            except PromoCode.DoesNotExist:
                messages.error(request, "Promokod topilmadi")
        elif action == 'delete':
            pc_id = request.POST.get('promo_id')
            try:
                pc = PromoCode.objects.get(id=pc_id)
                name = pc.code
                pc.delete()
                messages.success(request, f"'{name}' o'chirildi")
            except PromoCode.DoesNotExist:
                messages.error(request, "Promokod topilmadi")
        return redirect('panel:promocodes')

    context = {
        'promocodes': promocodes,
        'total': promocodes.count(),
        'active_count': promocodes.filter(is_active=True).count(),
    }
    return render(request, 'panel/promocodes.html', context)


@staff_required
def reviews_view(request):
    """Sharhlar — user ratings and driver feedback."""
    from django.db.models import Avg, Count as DbCount

    rides_with_reviews = Ride.objects.filter(
        rating__isnull=False
    ).select_related('passenger', 'driver').order_by('-created_at')[:100]

    driver_stats = Driver.objects.filter(is_active=True).annotate(
        avg_rating=Avg('rating'),
        review_count=DbCount('rides', filter=Q(rides__rating__isnull=False))
    ).filter(review_count__gt=0).order_by('-avg_rating')

    overall_avg = Ride.objects.filter(
        rating__isnull=False
    ).aggregate(avg=Avg('rating'))['avg'] or 0

    total_reviews = Ride.objects.filter(rating__isnull=False).count()

    context = {
        'rides_with_reviews': rides_with_reviews,
        'driver_stats': driver_stats,
        'overall_avg': round(overall_avg, 1),
        'total_reviews': total_reviews,
    }
    return render(request, 'panel/reviews.html', context)


@staff_required
def settings_view(request):
    """Sozlamalar — global system settings like surge multiplier, search radius, etc."""
    surges = SurgePricing.objects.all()

    if request.method == 'POST':
        action = request.POST.get('action', '')
        if action == 'update_general':
            messages.success(request, "Umumiy sozlamalar yangilandi")
        elif action == 'update_search':
            messages.success(request, "Qidiruv sozlamalari yangilandi")
        elif action == 'add_surge':
            name = request.POST.get('surge_name', '')
            multiplier = request.POST.get('surge_multiplier', '1.0')
            reason = request.POST.get('surge_reason', 'custom')
            description = request.POST.get('surge_description', '')
            try:
                multiplier = float(multiplier)
            except (ValueError, TypeError):
                multiplier = 1.0
            if name:
                SurgePricing.objects.create(
                    name=name, reason=reason, multiplier=multiplier, description=description
                )
                messages.success(request, f"Surge '{name}' qo'shildi")
            else:
                messages.error(request, "Surga nomi kiritilishi shart")
        elif action == 'delete_surge':
            surge_id = request.POST.get('surge_id')
            try:
                surge = SurgePricing.objects.get(id=surge_id)
                name = surge.name
                surge.delete()
                messages.success(request, f"'{name}' o'chirildi")
            except SurgePricing.DoesNotExist:
                messages.error(request, "Surge topilmadi")
        return redirect('panel:settings')

    context = {
        'surges': surges,
    }
    return render(request, 'panel/settings.html', context)


@staff_required
def regions_view(request):
    regions = Region.objects.all().order_by('name')
    return render(request, 'panel/regions.html', {'regions': regions})


@staff_required
def region_create(request):
    if request.method == 'POST':
        rid = request.POST.get('id', '').strip()
        name = request.POST.get('name', '').strip()
        if rid and name:
            Region.objects.create(id=rid, name=name)
            messages.success(request, f"Viloyat qo'shildi: {name}")
        else:
            messages.error(request, "ID va nom majburiy")
    return redirect('panel:regions')


@staff_required
def region_update(request, region_id):
    region = get_object_or_404(Region, id=region_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if name:
            region.name = name
            region.save()
            messages.success(request, "Viloyat saqlandi")
        else:
            messages.error(request, "Nom bo'sh bo'lishi mumkin emas")
        return redirect('panel:regions')
    return render(request, 'panel/region_form.html', {'region': region})


@staff_required
def region_delete(request, region_id):
    if request.method == 'POST':
        region = get_object_or_404(Region, id=region_id)
        region.delete()
        messages.success(request, "Viloyat o'chirildi")
    return redirect('panel:regions')


@staff_required
def districts_view(request):
    regions = Region.objects.all().order_by('name')
    region_id = request.GET.get('region_id')
    if region_id:
        selected = get_object_or_404(Region, id=region_id)
        districts = selected.districts.all().order_by('name')
    else:
        selected = None
        districts = District.objects.all().select_related('region').order_by('region__name', 'name')
    return render(request, 'panel/districts.html', {
        'regions': regions,
        'districts': districts,
        'selected_region': selected,
    })


@staff_required
def district_create(request):
    if request.method == 'POST':
        rid = request.POST.get('id', '').strip()
        name = request.POST.get('name', '').strip()
        region_id = request.POST.get('region_id')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        if rid and name and region_id and lat and lng:
            region = get_object_or_404(Region, id=region_id)
            District.objects.create(id=rid, region=region, name=name, latitude=lat, longitude=lng)
            messages.success(request, f"Tuman qo'shildi: {name}")
        else:
            messages.error(request, "Barcha maydonlar majburiy")
    return redirect('panel:districts')


@staff_required
def district_update(request, district_id):
    district = get_object_or_404(District, id=district_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        region_id = request.POST.get('region_id')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        if name and region_id and lat and lng:
            district.name = name
            district.region_id = region_id
            district.latitude = lat
            district.longitude = lng
            district.save()
            messages.success(request, "Tuman saqlandi")
        else:
            messages.error(request, "Barcha maydonlar majburiy")
        return redirect('panel:districts')
    regions = Region.objects.all().order_by('name')
    return render(request, 'panel/district_form.html', {'district': district, 'regions': regions})


@staff_required
def district_delete(request, district_id):
    if request.method == 'POST':
        district = get_object_or_404(District, id=district_id)
        district.delete()
        messages.success(request, "Tuman o'chirildi")
    return redirect('panel:districts')


@staff_required
def mfy_view(request):
    districts = District.objects.all().order_by('region__name', 'name')
    regions = Region.objects.all().order_by('name')
    district_id = request.GET.get('district_id')
    if district_id:
        selected_district = get_object_or_404(District, id=district_id)
        mfys = selected_district.mfys.all().order_by('name')
    else:
        selected_district = None
        mfys = Mfy.objects.all().select_related('district__region').order_by('district__region__name', 'district__name', 'name')
    return render(request, 'panel/mfy_list.html', {
        'regions': regions,
        'districts': districts,
        'mfys': mfys,
        'selected_district': selected_district,
    })


@staff_required
def mfy_create(request):
    if request.method == 'POST':
        mid = request.POST.get('id', '').strip()
        name = request.POST.get('name', '').strip()
        district_id = request.POST.get('district_id')
        typ = request.POST.get('type', 'shahar')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        if mid and name and district_id and lat and lng:
            district = get_object_or_404(District, id=district_id)
            Mfy.objects.create(id=mid, district=district, name=name, type=typ, latitude=lat, longitude=lng)
            messages.success(request, f"MFY qo'shildi: {name}")
        else:
            messages.error(request, "Barcha maydonlar majburiy")
    return redirect('panel:mfy')


@staff_required
def mfy_update(request, mfy_id):
    mfy = get_object_or_404(Mfy, id=mfy_id)
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        district_id = request.POST.get('district_id')
        typ = request.POST.get('type', 'shahar')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        if name and district_id and lat and lng:
            mfy.name = name
            mfy.district_id = district_id
            mfy.type = typ
            mfy.latitude = lat
            mfy.longitude = lng
            mfy.save()
            messages.success(request, "MFY saqlandi")
        else:
            messages.error(request, "Barcha maydonlar majburiy")
        return redirect('panel:mfy')
    districts = District.objects.all().select_related('region').order_by('region__name', 'name')
    return render(request, 'panel/mfy_form.html', {'mfy': mfy, 'districts': districts})


@staff_required
def mfy_delete(request, mfy_id):
    if request.method == 'POST':
        mfy = get_object_or_404(Mfy, id=mfy_id)
        mfy.delete()
        messages.success(request, "MFY o'chirildi")
    return redirect('panel:mfy')


@staff_required
def street_create(request):
    if request.method == 'POST':
        sid = request.POST.get('id', '').strip()
        name = request.POST.get('name', '').strip()
        mfy_id = request.POST.get('mfy_id')
        lat = request.POST.get('latitude')
        lng = request.POST.get('longitude')
        if sid and name and mfy_id and lat and lng:
            mfy = get_object_or_404(Mfy, id=mfy_id)
            Street.objects.create(id=sid, mfy=mfy, name=name, latitude=lat, longitude=lng)
            messages.success(request, f"Ko'cha qo'shildi: {name}")
        else:
            messages.error(request, "Barcha maydonlar majburiy")
    return redirect('panel:mfy')


@staff_required
def street_delete(request, street_id):
    if request.method == 'POST':
        street = get_object_or_404(Street, id=street_id)
        street.delete()
        messages.success(request, "Ko'cha o'chirildi")
    return redirect('panel:mfy')


@staff_required
def api_regions(request):
    data = []
    for region in Region.objects.all().order_by('name'):
        districts = []
        for d in region.districts.all().order_by('name'):
            mfys = []
            for m in d.mfys.all().order_by('name'):
                streets = []
                for s in m.streets.all().order_by('name'):
                    streets.append({
                        'id': s.id,
                        'name': s.name,
                        'lat': float(s.latitude),
                        'lng': float(s.longitude),
                    })
                mfys.append({
                    'id': m.id,
                    'name': m.name,
                    'type': m.type,
                    'lat': float(m.latitude),
                    'lng': float(m.longitude),
                    'streets': streets,
                })
            districts.append({
                'id': d.id,
                'name': d.name,
                'lat': float(d.latitude),
                'lng': float(d.longitude),
                'mfys': mfys,
            })
        data.append({
            'id': region.id,
            'name': region.name,
            'districts': districts,
        })
    return JsonResponse(data, safe=False)
