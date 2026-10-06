import random

from django.core.management.base import BaseCommand

from shared.models import CarCategory, Driver, Location


class Command(BaseCommand):
    help = 'Seed database with initial data'

    def handle(self, *args, **options):
        categories = [
            {'id': 'economy', 'name': 'Ekonom', 'description': 'Budjetga mos transport',
             'base_fare': 7000, 'price_per_km': 1500, 'price_per_minute': 200,
             'estimated_arrival_time': 5,
             'icon_url': 'https://cdn.novataxi.uz/icons/economy.png'},
            {'id': 'comfort', 'name': 'Komfort', 'description': 'Qulay va tez xizmat',
             'base_fare': 12000, 'price_per_km': 2200, 'price_per_minute': 300,
             'estimated_arrival_time': 4,
             'icon_url': 'https://cdn.novataxi.uz/icons/comfort.png'},
            {'id': 'business', 'name': 'Biznes', 'description': 'Premium xizmat',
             'base_fare': 20000, 'price_per_km': 3500, 'price_per_minute': 500,
             'estimated_arrival_time': 3,
             'icon_url': 'https://cdn.novataxi.uz/icons/business.png'},
            {'id': 'cargo', 'name': 'Yuk mashinasi', 'description': 'Katta yuk mashinalari va yetkazib berish',
             'base_fare': 35000, 'price_per_km': 5000, 'price_per_minute': 800,
             'estimated_arrival_time': 10, 'is_cargo': True,
             'icon_url': 'https://cdn.novataxi.uz/icons/cargo.png'},
        ]
        for c in categories:
            CarCategory.objects.update_or_create(id=c['id'], defaults=c)
        self.stdout.write(self.style.SUCCESS(f'{len(categories)} categories created'))

        locations = [
            {'name': 'Chorsu bozori', 'address': "Toshkent shahri, Beruniy ko'chasi",
             'subtitle': 'Toshkent markazi', 'lat': 41.3076, 'lng': 69.2480,
             'type': 'market', 'icon': 'store'},
            {'name': 'Tashkent City', 'address': "Toshkent shahri, Navoiy ko'chasi",
             'subtitle': 'Toshkent shahri', 'lat': 41.3111, 'lng': 69.2797,
             'type': 'mall', 'icon': 'apartment'},
            {'name': 'Aeroport', 'address': 'Toshkent Xalqaro Aeroporti, Terminallar',
             'subtitle': 'Tashkent Xalqaro Aeroporti', 'lat': 41.2579, 'lng': 69.2812,
             'type': 'transport', 'icon': 'flight'},
            {'name': "Temir yo'l vokzali", 'address': "Toshkent shahri, Vokzal ko'chasi",
             'subtitle': 'Toshkent vokzali', 'lat': 41.2977, 'lng': 69.2932,
             'type': 'transport', 'icon': 'train'},
            {'name': 'Samarqand Darvoza', 'address': "Toshkent shahri, Muqimiy ko'chasi",
             'subtitle': 'Savdo markazi', 'lat': 41.3001, 'lng': 69.2604,
             'type': 'mall', 'icon': 'shopping_bag'},
            {'name': "Bog'i Eram", 'address': "Toshkent shahri, Bog'i Eram ko'chasi",
             'subtitle': "Dam olish bog'i", 'lat': 41.3134, 'lng': 69.2765,
             'type': 'park', 'icon': 'park'},
            {'name': 'Milliy stadion', 'address': "Toshkent shahri, Bunyodkor ko'chasi",
             'subtitle': 'Respublika stadioni', 'lat': 41.2839, 'lng': 69.2540,
             'type': 'sports', 'icon': 'sports_soccer'},
            {'name': 'INOUE Campus', 'address': "Toshkent shahri, Olmazor ko'chasi",
             'subtitle': "O'quv markazi", 'lat': 41.3278, 'lng': 69.2856,
             'type': 'education', 'icon': 'school'},
        ]
        for loc in locations:
            Location.objects.update_or_create(name=loc['name'], defaults=loc)
        self.stdout.write(self.style.SUCCESS(f'{len(locations)} locations created'))

        drivers_data = [
            {'name': 'Sardor Raximov', 'phone': '+998901111111', 'car_model': 'Cobalt', 'license_plate': '70 A 123 BB',
             'category_id': 'economy'},
            {'name': 'Jasur Karimov', 'phone': '+998902222222', 'car_model': 'Malibu 2', 'license_plate': '70 B 456 CC',
             'category_id': 'comfort'},
            {'name': 'Bobur Mirzoev', 'phone': '+998903333333', 'car_model': 'Sonata', 'license_plate': '70 C 789 DD',
             'category_id': 'business'},
            {'name': 'Dilshod Toshmatov', 'phone': '+998904444444', 'car_model': 'Cobalt', 'license_plate': '70 A 234 EE',
             'category_id': 'economy'},
            {'name': 'Otabek Sherqulov', 'phone': '+998905555555', 'car_model': 'Camry', 'license_plate': '70 B 567 FF',
             'category_id': 'comfort'},
            {'name': 'Kamoliddin Nazarov', 'phone': '+998906666666', 'car_model': 'Isuzu NQR', 'license_plate': '70 D 111 CC',
             'category_id': 'cargo'},
        ]
        for d in drivers_data:
            cat_id = d.pop('category_id')
            is_cargo = cat_id == 'cargo'
            lat = 41.2995 + random.uniform(-0.05, 0.05)
            lng = 69.2401 + random.uniform(-0.05, 0.05)
            Driver.objects.update_or_create(
                phone=d['phone'],
                defaults={**d, 'category_id': cat_id, 'current_lat': lat, 'current_lng': lng,
                          'rating': round(random.uniform(4.5, 5.0), 1), 'is_available': True,
                          'is_cargo': is_cargo}
            )
        self.stdout.write(self.style.SUCCESS(f'{len(drivers_data)} drivers created'))

        self.stdout.write(self.style.SUCCESS('Seed data complete!'))
