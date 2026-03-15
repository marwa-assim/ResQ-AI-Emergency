import math
import requests

# ── OSRM Public Routing API (free, no key, real road network) ──────────────────
OSRM_BASE = "http://router.project-osrm.org/route/v1/driving"

MAIN_HOSPITAL_COORDS = {
    "lat": 26.2137,
    "lng": 50.5794  # Salmaniya Medical Complex, Bahrain
}

def haversine_distance(lat1, lon1, lat2, lon2):
    """Straight-line distance in km between two GPS points."""
    lon1, lat1, lon2, lat2 = map(math.radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * math.asin(math.sqrt(a)) * 6371

def calculate_eta(distance_km, speed_kmh=50):
    """Fallback ETA estimate from straight-line distance."""
    if distance_km <= 0.1:
        return 1
    return int((distance_km / speed_kmh) * 60 + 2)

def get_real_route(start_lat, start_lng, end_lat, end_lng):
    """
    Real road routing via OSRM open-source engine.
    Returns: { duration_minutes, distance_km, polyline (encoded), steps[] }
    Falls back to haversine estimate on error.
    """
    try:
        url = f"{OSRM_BASE}/{start_lng},{start_lat};{end_lng},{end_lat}"
        params = {
            "overview": "full",
            "geometries": "polyline",
            "steps": "true",
            "annotations": "false"
        }
        resp = requests.get(url, params=params, timeout=5)
        data = resp.json()

        if data.get("code") != "Ok" or not data.get("routes"):
            raise ValueError("OSRM returned no route")

        route = data["routes"][0]
        leg   = route["legs"][0]

        duration_sec  = route.get("duration", 0)
        distance_m    = route.get("distance", 0)
        duration_mins = max(1, round(duration_sec / 60))
        distance_km   = round(distance_m / 1000, 2)

        # Extract human-readable turn-by-turn steps
        steps = []
        for step in leg.get("steps", [])[:8]:
            maneuver = step.get("maneuver", {})
            mtype = maneuver.get("type", "")
            mod   = maneuver.get("modifier", "")
            road  = step.get("name") or "road"
            dist  = round(step.get("distance", 0))
            txt   = f"{mtype.capitalize()} {mod} onto {road} ({dist}m)" if road else mtype
            steps.append(txt.strip())

        return {
            "duration_minutes": duration_mins,
            "distance_km": distance_km,
            "polyline": route.get("geometry", ""),
            "steps": steps,
            "source": "osrm"
        }
    except Exception as e:
        dist = haversine_distance(start_lat, start_lng, end_lat, end_lng)
        eta  = calculate_eta(dist)
        return {
            "duration_minutes": eta,
            "distance_km": round(dist, 2),
            "polyline": "",
            "steps": [f"Head toward destination ({round(dist,1)} km)"],
            "source": "fallback",
            "error": str(e)
        }

def find_nearest_ambulance(patient_lat, patient_lng, ambulance_fleet):
    """Finds the closest available ambulance using haversine."""
    nearest_amb = None
    min_dist = float('inf')
    for amb in ambulance_fleet:
        if amb.get('status') != 'Available':
            continue
        dist = haversine_distance(patient_lat, patient_lng, amb['lat'], amb['lng'])
        if dist < min_dist:
            min_dist = dist
            nearest_amb = amb
    return nearest_amb, min_dist
