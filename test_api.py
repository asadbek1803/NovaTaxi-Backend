import urllib.request
import json
import sqlite3

BASE = "http://127.0.0.1:8000/api/v1"

def post(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else b"{}"
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="GET")
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code

def put(path, data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode() if data else b"{}"
    req = urllib.request.Request(f"{BASE}{path}", data=body, headers=headers, method="PUT")
    try:
        resp = urllib.request.urlopen(req)
        return json.loads(resp.read().decode()), resp.status
    except urllib.error.HTTPError as e:
        return json.loads(e.read().decode()), e.code

def get_otp(phone):
    conn = sqlite3.connect("db.sqlite3")
    c = conn.cursor()
    c.execute("SELECT code FROM otp_codes WHERE phone=? AND is_used=0 ORDER BY id DESC LIMIT 1", (phone,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

print("=" * 60)
print("NOVA TAXI API - FULL TESTS (User + Driver)")
print("=" * 60)

# ============================================================
# USER API TESTS
# ============================================================
print("\n--- USER API ---")

print("\n[1] POST /user/auth/send-otp")
r, s = post("/user/auth/send-otp", {"phone": "+998901234567"})
print(f"  Status: {s} | {json.dumps(r, ensure_ascii=False)}")

code = get_otp("+998901234567")
print(f"  OTP Code: {code}")

print("\n[2] POST /user/auth/verify-otp")
r, s = post("/user/auth/verify-otp", {"phone": "+998901234567", "code": code})
print(f"  Status: {s}")
user_token = r["data"]["access_token"]
user_refresh = r["data"]["refresh_token"]
print(f"  User ID: {r['data']['user']['id']}")
print(f"  Token: {user_token[:40]}...")

print("\n[3] GET /user/user/profile")
r, s = get("/user/user/profile", user_token)
print(f"  Status: {s} | {json.dumps(r['data'], ensure_ascii=False)}")

print("\n[4] PUT /user/user/profile")
r, s = put("/user/user/profile", {"full_name": "Asadbek Abdubannobov"}, user_token)
print(f"  Status: {s} | {json.dumps(r['data'], ensure_ascii=False)}")

print("\n[5] GET /user/user/settings")
r, s = get("/user/user/settings", user_token)
print(f"  Status: {s} | {json.dumps(r['data'], ensure_ascii=False)}")

print("\n[6] PUT /user/user/settings")
r, s = put("/user/user/settings", {"dark_mode": True, "language": "ru"}, user_token)
print(f"  Status: {s} | {json.dumps(r['data'], ensure_ascii=False)}")

print("\n[7] GET /user/car-categories")
r, s = get("/user/car-categories", user_token)
print(f"  Status: {s} | {len(r['data'])} categories")
for cat in r["data"]:
    print(f"    - {cat['id']}: {cat['name']} ({cat['base_fare']} UZS)")

print("\n[8] GET /user/locations/search?q=chorsu")
r, s = get("/user/locations/search?q=chorsu", user_token)
print(f"  Status: {s} | {len(r['data'])} results")

print("\n[9] GET /user/locations/popular")
r, s = get("/user/locations/popular", user_token)
print(f"  Status: {s} | {len(r['data'])} locations")

print("\n[10] POST /user/saved-locations")
r, s = post("/user/saved-locations", {"type": "home", "name": "Uy", "address": "Chilonzor-3", "lat": 41.2785, "lng": 69.2256}, user_token)
print(f"  Status: {s} | {json.dumps(r.get('data', r), ensure_ascii=False)}")

print("\n[10b] GET /user/saved-locations")
r, s = get("/user/saved-locations", user_token)
print(f"  Status: {s} | {len(r['data'])} saved locations")

print("\n[11] POST /user/rides/estimate")
r, s = post("/user/rides/estimate", {"from_lat": 41.3111, "from_lng": 69.2797, "to_lat": 41.2579, "to_lng": 69.2812, "category_id": "economy"}, user_token)
print(f"  Status: {s} | {json.dumps(r['data'], ensure_ascii=False)}")

print("\n[12] POST /user/rides/request")
r, s = post("/user/rides/request", {"from_address": "Amir Temur", "from_lat": 41.3111, "from_lng": 69.2797, "to_address": "Aeroport", "to_lat": 41.2579, "to_lng": 69.2812, "category_id": "economy", "payment_method": "cash"}, user_token)
print(f"  Status: {s}")
ride_id = r["data"]["id"]
print(f"  Ride ID: {ride_id} | Status: {r['data']['status']} | Price: {r['data']['price']}")

print("\n[13] GET /user/rides/" + ride_id)
r, s = get(f"/user/rides/{ride_id}", user_token)
print(f"  Status: {s} | route_points: {r['data']['route_points']}")

print("\n[14] GET /user/rides/history")
r, s = get("/user/rides/history", user_token)
print(f"  Status: {s} | {len(r['data']['rides'])} rides")

print("\n[15] GET /user/drivers/nearby?lat=41.2995&lng=69.2401")
r, s = get("/user/drivers/nearby?lat=41.2995&lng=69.2401", user_token)
print(f"  Status: {s} | {len(r['data'])} drivers nearby")

print("\n[16] POST /user/payment-methods")
r, s = post("/user/payment-methods", {"type": "uzcard", "card_number": "8600123456784521", "holder_name": "ASADBEK A.", "expiry": "12/27"}, user_token)
print(f"  Status: {s} | {json.dumps(r.get('data', r), ensure_ascii=False)}")

print("\n[16b] GET /user/payment-methods")
r, s = get("/user/payment-methods", user_token)
print(f"  Status: {s} | {len(r['data'])} methods")

print("\n[17] POST /user/notifications/register")
r, s = post("/user/notifications/register", {"token": "test_fcm_token_123"}, user_token)
print(f"  Status: {s} | {json.dumps(r, ensure_ascii=False)}")

print("\n[18] POST /user/support/ticket")
r, s = post("/user/support/ticket", {"subject": "To'lov muammosi", "message": "Kartamdan ikki marta pul yechildi"}, user_token)
print(f"  Status: {s} | {json.dumps(r, ensure_ascii=False)}")

# ============================================================
# DRIVER API TESTS
# ============================================================
print("\n\n--- DRIVER API ---")

print("\n[19] POST /driver/auth/send-otp")
r, s = post("/driver/auth/send-otp", {"phone": "+998907654321"})
print(f"  Status: {s} | {json.dumps(r, ensure_ascii=False)}")

driver_code = get_otp("+998907654321")
print(f"  Driver OTP: {driver_code}")

print("\n[20] POST /driver/auth/verify-otp")
r, s = post("/driver/auth/verify-otp", {"phone": "+998907654321", "code": driver_code})
print(f"  Status: {s}")
driver_token = r["data"]["access_token"]
driver_refresh = r["data"]["refresh_token"]
print(f"  Is new driver: {r['data']['is_new_driver']}")
print(f"  Token: {driver_token[:40]}...")

print("\n[21] GET /driver/profile/status")
r, s = get("/driver/profile/status", driver_token)
print(f"  Status: {s} | {json.dumps(r['data'], ensure_ascii=False)}")

print("\n[22] POST /driver/profile/onboarding")
r, s = post("/driver/profile/onboarding", {
    "license_number": "AA1234567",
    "car_model": "Chevrolet Cobalt",
    "car_number": "77AB123",
    "car_color": "Oq",
}, driver_token)
print(f"  Status: {s}")
print(f"  is_submitted: {r['data']['is_submitted']}")
print(f"  doc: {json.dumps(r['data']['document'], ensure_ascii=False)}")
print(f"  vehicle: {json.dumps(r['data']['vehicle'], ensure_ascii=False)}")

print("\n[23] GET /driver/profile/onboarding (check)")
r, s = get("/driver/profile/onboarding", driver_token)
print(f"  Status: {s} | is_submitted: {r['data']['document']['is_submitted']}")

print("\n[24] GET /driver/profile/status (after onboarding)")
r, s = get("/driver/profile/status", driver_token)
print(f"  Status: {s}")
print(f"  is_verified: {r['data']['is_verified']}")
print(f"  balance: {r['data']['balance']}")

# Simulate admin approval: set driver as verified + 60-day free trial
print("\n  [ADMIN] Approving driver + setting free trial...")
conn = sqlite3.connect("db.sqlite3")
c = conn.cursor()
c.execute("UPDATE drivers SET is_verified=1, subscription_end_date=date('now', '+60 days') WHERE phone='+998907654321'")
conn.commit()
conn.close()
print("  Driver approved with 60-day free trial!")

print("\n[25] POST /driver/location/update")
r, s = post("/driver/location/update", {"lat": 41.3111, "lng": 69.2797, "heading": 180}, driver_token)
print(f"  Status: {s} | {json.dumps(r, ensure_ascii=False)}")

print("\n[26] POST /driver/profile/availability toggle")
r, s = post("/driver/profile/availability", {}, driver_token)
print(f"  Status: {s} | is_available: {r['data']['is_available']}")

# Toggle back to available
r, s = post("/driver/profile/availability", {}, driver_token)

print("\n[27] GET /driver/rides/available (as verified driver)")
r, s = get("/driver/rides/available?lat=41.3111&lng=69.2797", driver_token)
print(f"  Status: {s}")
if s == 200:
    print(f"  Available rides: {r['data']['total']}")
    for ride in r['data']['rides']:
        print(f"    - {ride['ride_id']}: {ride['from_address']} -> {ride['to_address']} ({ride['price']} UZS, {ride['distance_to_pickup_km']}km away)")
else:
    print(f"  Response: {json.dumps(r, ensure_ascii=False)}")

# Create a pending ride from user to test acceptance
print("\n  [SETUP] Creating a pending ride for driver acceptance...")
r, s = post("/user/rides/request", {
    "from_address": "Registon maydoni",
    "from_lat": 41.3111,
    "from_lng": 69.2800,
    "to_address": "Bozor",
    "to_lat": 41.2995,
    "to_lng": 69.2401,
    "category_id": "economy",
    "payment_method": "cash"
}, user_token)
pending_ride_id = r["data"]["id"]
print(f"  Created ride: {pending_ride_id} | Status: {r['data']['status']}")

print("\n[28] GET /driver/rides/available (with pending ride)")
r, s = get("/driver/rides/available?lat=41.3111&lng=69.2800", driver_token)
print(f"  Status: {s} | Available: {r['data']['total']}")

if r['data']['total'] > 0:
    target_ride_id = r['data']['rides'][0]['ride_id']
    print(f"\n[29] POST /driver/rides/{target_ride_id}/accept")
    r, s = post(f"/driver/rides/{target_ride_id}/accept", {}, driver_token)
    print(f"  Status: {s} | Status: {r['data']['status']}")
    print(f"  Passenger: {r['data']['passenger_name']} ({r['data']['passenger_phone']})")

    print(f"\n[30] GET /driver/rides/active")
    r, s = get("/driver/rides/active", driver_token)
    print(f"  Status: {s}")
    if r['data']:
        print(f"  Active ride: {r['data']['id']} | Status: {r['data']['status']}")

    print(f"\n[31] POST /driver/rides/{target_ride_id}/status -> arriving")
    r, s = post(f"/driver/rides/{target_ride_id}/status", {"status": "arriving"}, driver_token)
    print(f"  Status: {s} | Ride status: {r['data']['status']}")

    print(f"\n[32] POST /driver/rides/{target_ride_id}/status -> in_progress")
    r, s = post(f"/driver/rides/{target_ride_id}/status", {"status": "in_progress"}, driver_token)
    print(f"  Status: {s} | Ride status: {r['data']['status']}")

    print(f"\n[33] POST /driver/rides/{target_ride_id}/status -> completed")
    r, s = post(f"/driver/rides/{target_ride_id}/status", {"status": "completed"}, driver_token)
    print(f"  Status: {s} | Ride status: {r['data']['status']}")
    print(f"  Completed at: {r['data']['completed_at']}")

    # Check balance increased
    print(f"\n[34] GET /driver/profile/status (after completing ride)")
    r, s = get("/driver/profile/status", driver_token)
    print(f"  Status: {s}")
    print(f"  balance: {r['data']['balance']}")
    print(f"  subscription_active: {r['data']['subscription_active']}")
    print(f"  days_until_expiry: {r['data']['days_until_expiry']}")

print(f"\n[35] GET /driver/rides/history")
r, s = get("/driver/rides/history", driver_token)
print(f"  Status: {s} | {len(r['data']['rides'])} rides")

print(f"\n[36] POST /driver/auth/logout")
r, s = post("/driver/auth/logout", token=driver_token)
print(f"  Status: {s} | {json.dumps(r, ensure_ascii=False)}")

print(f"\n[37] POST /driver/auth/refresh-token")
r, s = post("/driver/auth/refresh-token", {"refresh_token": driver_refresh})
print(f"  Status: {s}")
if s == 200:
    print(f"  New token: {r['data']['access_token'][:40]}...")
else:
    print(f"  Response: {json.dumps(r, ensure_ascii=False)}")

print("\n" + "=" * 60)
print("ALL TESTS COMPLETED!")
print("=" * 60)
