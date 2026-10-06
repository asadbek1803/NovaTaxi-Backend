import json
import subprocess
import sys

from django.core.management.base import BaseCommand

from shared.models import Region, District


class Command(BaseCommand):
    help = 'Seed regions and districts from static/js/uzb_locations.js'

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
        function strip(obj) {{
            if (Array.isArray(obj)) return obj.map(strip);
            if (obj && typeof obj === 'object') {{
                const clean = {{}};
                for (const k of Object.keys(obj)) {{
                    if (k === 'mfy') continue;
                    if (Array.isArray(obj[k])) {{
                        clean[k] = obj[k].map(item => {{
                            if (typeof item === 'object' && item !== null) {{
                                const c = {{}};
                                for (const k2 of Object.keys(item)) {{
                                    if (k2 !== 'streets' && k2 !== 'mfy') c[k2] = item[k2];
                                }}
                                return c;
                            }}
                            return item;
                        }});
                    }} else {{
                        clean[k] = obj[k];
                    }}
                }}
                return clean;
            }}
            return obj;
        }}
        const result = strip(UZB_REGIONS.map(r => ({{
            id: r.id,
            name: r.name,
            districts: r.districts.map(d => ({{
                id: d.id,
                name: d.name,
                lat: d.lat,
                lng: d.lng
            }}))
        }})));
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

        region_count = 0
        district_count = 0

        for r in data:
            region, created = Region.objects.update_or_create(
                id=r['id'],
                defaults={'name': r['name']}
            )
            if created:
                region_count += 1

            for d in r.get('districts', []):
                District.objects.update_or_create(
                    id=d['id'],
                    defaults={
                        'region': region,
                        'name': d['name'],
                        'latitude': d['lat'],
                        'longitude': d['lng'],
                    }
                )
                district_count += 1

        self.stdout.write(self.style.SUCCESS(
            f'Seeded {region_count} regions, {district_count} districts'
        ))
