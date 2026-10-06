import json
import subprocess

from django.core.management.base import BaseCommand

from shared.models import Region, District, Mfy, Street


class Command(BaseCommand):
    help = 'Seed MFY and Street data from static/js/uzb_locations.js'

    def handle(self, *args, **options):
        import os
        from django.conf import settings
        js_path = settings.BASE_DIR / 'static' / 'js' / 'uzb_locations.js'
        if not os.path.exists(js_path):
            self.stdout.write(self.style.WARNING(f'{js_path} not found, skipping'))
            return

        js_path_str = str(js_path).replace('\\', '/')
        node_code = f'''
        const fs = require('fs');
        const code = fs.readFileSync('{js_path_str}', 'utf8');
        eval(code);
        const result = UZB_REGIONS.map(r => ({{
            id: r.id,
            districts: (r.districts || []).map(d => ({{
                id: d.id,
                mfy: (d.mfy || []).map(m => ({{
                    id: m.id,
                    name: m.name,
                    type: m.type || 'shahar',
                    lat: m.lat,
                    lng: m.lng,
                    streets: (m.streets || []).map(s => ({{
                        id: s.id,
                        name: s.name,
                        lat: s.lat,
                        lng: s.lng
                    }}))
                }}))
            }}))
        }}));
        process.stdout.write(JSON.stringify(result));
        '''

        try:
            result = subprocess.run(
                ['node', '-e', node_code],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                self.stderr.write(self.style.ERROR(f'Node error: {result.stderr}'))
                return
            data = json.loads(result.stdout)
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'Failed: {e}'))
            return

        mfy_count = 0
        street_count = 0

        for r in data:
            region = Region.objects.filter(id=r['id']).first()
            if not region:
                continue
            for d in r.get('districts', []):
                district = District.objects.filter(id=d['id']).first()
                if not district:
                    continue
                for m in d.get('mfy', []):
                    mfy, created = Mfy.objects.update_or_create(
                        id=m['id'],
                        defaults={
                            'district': district,
                            'name': m['name'],
                            'type': m['type'],
                            'latitude': m['lat'],
                            'longitude': m['lng'],
                        }
                    )
                    mfy_count += 1
                    for s in m.get('streets', []):
                        Street.objects.update_or_create(
                            id=s['id'],
                            defaults={
                                'mfy': mfy,
                                'name': s['name'],
                                'latitude': s['lat'],
                                'longitude': s['lng'],
                            }
                        )
                        street_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {mfy_count} MFY, {street_count} streets'
        ))
