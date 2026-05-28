from flask import Flask, render_template, request, jsonify, redirect, flash, url_for
import math
from model import predict
from database import db
from db_models import User, Patient, Hospital, Ambulance, RolePolicy, IoTDevice, Visit, Bed, Drone, VolunteerMission
from auth import auth_bp
from ai_copilot import copilot
from location_service import haversine_distance, calculate_eta, MAIN_HOSPITAL_COORDS, get_real_route
from flask_login import LoginManager, current_user, login_required
import time
import random
import os
from datetime import datetime
from flask_socketio import SocketIO, emit

# ── Load .env file automatically (works locally; on cloud use dashboard env vars) ──
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed, rely on system env vars

app = Flask(__name__, static_url_path='/static')
app.config['SECRET_KEY'] = 'resq-regional-submission-secret'
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'patients.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent")
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    # user_id might be integer for User, or string (CPR) for Patient
    if str(user_id).isdigit() and len(str(user_id)) < 9:
        return User.query.get(int(user_id))
    # Check Patient first if it might be CPR
    p = Patient.query.get(str(user_id))
    if p:
        p.role = 'patient'
        return p
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)

incoming_ambulances = []

# Initialize DB with Admin User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@resq.ai').first():
        admin = User(email='admin@resq.ai', name='System Admin', role='superadmin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
    # Initialize Demo Hospitals if none exist
    if Hospital.query.count() == 0:
        h1 = Hospital(name="Salmaniya Medical Complex", lat=26.2137, lng=50.5794, capacity=1200, er_beds_count=10, trauma_beds_count=5, isolation_beds_count=5)
        h2 = Hospital(name="King Hamad University Hospital", lat=26.2690, lng=50.6139, capacity=400, er_beds_count=8, trauma_beds_count=3, isolation_beds_count=3)
        h3 = Hospital(name="BDF Royal Medical Services", lat=26.1107, lng=50.5367, capacity=500, er_beds_count=6, trauma_beds_count=2, isolation_beds_count=2)
        db.session.add_all([h1, h2, h3])
        db.session.commit()
        print("[DB INIT] Added 3 Demo Hospitals to DB.")

    # Initialize Beds based on Hospital config
    from db_models import Bed
    if Bed.query.count() == 0:
        for h in Hospital.query.all():
            beds_to_add = []
            for i in range(h.er_beds_count): beds_to_add.append(Bed(hospital_id=h.id, bed_type="ER", label=f"ER-{i+1}"))
            for i in range(h.trauma_beds_count): beds_to_add.append(Bed(hospital_id=h.id, bed_type="Trauma", label=f"T-{i+1}"))
            for i in range(h.isolation_beds_count): beds_to_add.append(Bed(hospital_id=h.id, bed_type="Isolation", label=f"ISO-{i+1}"))
            db.session.add_all(beds_to_add)
        db.session.commit()
        print("[DB INIT] Generated beds for hospitals.")

    # Initialize Default Roles
    if RolePolicy.query.count() == 0:
        roles = [
            RolePolicy(role_name='superadmin', can_manage_users=True, can_dispatch_fleet=True, can_edit_vitals=True, can_view_analytics=True, can_manage_facilities=True),
            RolePolicy(role_name='hospitaladmin', can_manage_users=True, can_dispatch_fleet=True, can_edit_vitals=True, can_view_analytics=True, can_manage_facilities=False),
            RolePolicy(role_name='doctor', can_manage_users=False, can_dispatch_fleet=False, can_edit_vitals=True, can_view_analytics=True, can_manage_facilities=False),
            RolePolicy(role_name='nurse', can_manage_users=False, can_dispatch_fleet=False, can_edit_vitals=True, can_view_analytics=False, can_manage_facilities=False),
            RolePolicy(role_name='ambulance_crew', can_manage_users=False, can_dispatch_fleet=True, can_edit_vitals=True, can_view_analytics=False, can_manage_facilities=False)
        ]
        db.session.add_all(roles)
        db.session.commit()


# -------------------------
# API Routes
# -------------------------

# Expanded Staff Pool (Arabic/English Mixed)
DOCTORS = ["Dr. Ahmed", "Dr. Sarah", "Dr. Ali", "Dr. Fatima", "Dr. House", "Dr. Kareem", "Dr. Noor", "Dr. Ziad"]
NURSES = ["Nurse Layla", "Nurse Omar", "Nurse Huda", "Nurse Youssef", "Nurse Joy", "Nurse Samia", "Nurse Tarek", "Nurse Mona"]

# Database-backed arrays and logic used below.

@app.route("/ambulance")
@login_required
def ambulance_view():
    return render_template("ambulance.html")

@app.route("/settings")
def settings():
    return redirect(url_for('admin_view'))

@app.route("/drone_tracking")
def drone_tracking():
    drones = Drone.query.all()
    hospitals = Hospital.query.all()
    return render_template("drone_tracking.html", drones=drones, hospitals=hospitals)

@app.route("/patient")
@login_required
def patient_view():
    return render_template("patient.html")

@app.route("/volunteer")
@login_required
def volunteer_view():
    return render_template("volunteer.html")

@app.route("/sign_language")
def sign_language_view():
    return render_template("sign_language.html")

@app.route("/map")
@login_required
def map_view():
    hospitals = [h.to_dict() for h in Hospital.query.all()]
    ambulances = [a.to_dict() for a in Ambulance.query.all()]
    return render_template("map.html", hospitals=hospitals, ambulances=ambulances)

@app.route("/admin")
@login_required
def admin_view():
    if current_user.role not in ['superadmin', 'hospitaladmin']:
        flash("Access Denied: You must be a Super Admin or Hospital Admin to view this page.")
        return redirect("/")
    
    if current_user.role == 'superadmin':
        hospitals = [h.to_dict() for h in Hospital.query.all()]
        users = User.query.all()
        ambulances = Ambulance.query.all()
        drones = Drone.query.all()
    else:
        hospitals = [h.to_dict() for h in Hospital.query.filter_by(id=current_user.hospital_id).all()]
        users = User.query.filter_by(hospital_id=current_user.hospital_id).all()
        ambulances = Ambulance.query.filter_by(hospital_id=current_user.hospital_id).all()
        drones = Drone.query.filter_by(hospital_id=current_user.hospital_id).all()
        
    roles = RolePolicy.query.all()
    iot_devices = IoTDevice.query.all()
    return render_template("admin.html", users=users, ambulances=ambulances, hospitals=hospitals, drones=drones, roles=roles, iot_devices=iot_devices)

@app.route("/api/admin/update_policy", methods=["POST"])
@login_required
def update_policy():
    if current_user.role not in ['superadmin', 'hospitaladmin']:
        return jsonify({"error": "Unauthorized"}), 403
        
    data = request.json
    hospital_id = data.get("hospital_id")
    policy_str = data.get("policy")
    
    if current_user.role == 'hospitaladmin' and current_user.hospital_id != hospital_id:
        return jsonify({"error": "Unauthorized for this hospital"}), 403
        
    hospital = Hospital.query.get(hospital_id)
    if hospital:
        hospital.policies = policy_str
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Hospital not found"}), 404

@app.route("/api/admin/user/create", methods=["POST"])
@login_required
def create_user():
    if current_user.role not in ['superadmin', 'hospitaladmin']:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    if User.query.filter_by(email=data.get('email')).first():
        return jsonify({"error": "Email already exists"}), 400
    
    # Ensure hospital admin can only create users for their hospital
    hosp_id = data.get('hospital_id')
    if current_user.role == 'hospitaladmin':
        hosp_id = current_user.hospital_id
        
    new_user = User(
        name=data.get('name'),
        email=data.get('email'),
        role=data.get('role', 'doctor'),
        hospital_id=hosp_id
    )
    new_user.set_password(data.get('password', 'password123'))
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"status": "success", "user_id": new_user.id})

@app.route("/api/admin/ambulance/create", methods=["POST"])
@login_required
def create_ambulance():
    if current_user.role not in ['superadmin', 'hospitaladmin']:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    if Ambulance.query.filter_by(unit_id=data.get('unit_id')).first():
        return jsonify({"error": "Unit ID already exists"}), 400
        
    hosp_id = data.get('hospital_id')
    if current_user.role == 'hospitaladmin':
        hosp_id = current_user.hospital_id
        
    new_amb = Ambulance(
        unit_id=data.get('unit_id'),
        hospital_id=hosp_id,
        status="Offline",
        lat=data.get('lat', 26.2137),
        lng=data.get('lng', 50.5794)
    )
    db.session.add(new_amb)
    db.session.commit()
    return jsonify({"status": "success", "amb_id": new_amb.id})

@app.route("/api/admin/user/<int:user_id>", methods=["DELETE"])
@login_required
def delete_user(user_id):
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    u = User.query.get(user_id)
    if not u: return jsonify({"error": "Not found"}), 404
    if current_user.role == 'hospitaladmin' and u.hospital_id != current_user.hospital_id:
        return jsonify({"error": "Unauthorized"}), 403
    db.session.delete(u)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/admin/user/<int:user_id>", methods=["PUT"])
@login_required
def edit_user(user_id):
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    u = User.query.get(user_id)
    if not u: return jsonify({"error": "Not found"}), 404
    if current_user.role == 'hospitaladmin' and u.hospital_id != current_user.hospital_id:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    if 'role' in data: u.role = data['role']
    if 'hospital_id' in data and current_user.role == 'superadmin': u.hospital_id = data['hospital_id'] or None
    if 'phone' in data: u.phone = data['phone']
    if 'license_id' in data: u.license_id = data['license_id']
    if 'is_active' in data: u.is_active = data['is_active']
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/admin/ambulance/<int:amb_id>", methods=["DELETE"])
@login_required
def delete_ambulance(amb_id):
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    a = Ambulance.query.get(amb_id)
    if not a: return jsonify({"error": "Not found"}), 404
    if current_user.role == 'hospitaladmin' and a.hospital_id != current_user.hospital_id:
        return jsonify({"error": "Unauthorized"}), 403
    db.session.delete(a)
    db.session.commit()
    return jsonify({"message": "Deleted"})

@app.route("/api/admin/drone/create", methods=["POST"])
@login_required
def create_drone():
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    call_sign = data.get('call_sign')
    hospital_id = data.get('hospital_id')
    payload = data.get('payload', 'AED Defibrillator')
    if not call_sign:
        return jsonify({"error": "Missing call_sign"}), 400
    d = Drone(call_sign=call_sign, hospital_id=hospital_id, payload=payload, status="Docked", battery=100, lat=26.2235, lng=50.5876)
    db.session.add(d)
    db.session.commit()
    return jsonify({"message": "Created"})

@app.route("/api/admin/drone/<int:drone_id>", methods=["DELETE"])
@login_required
def delete_drone(drone_id):
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    d = Drone.query.get(drone_id)
    if not d: return jsonify({"error": "Not found"}), 404
    db.session.delete(d)
    db.session.commit()
    return jsonify({"message": "Deleted"})

@app.route("/api/admin/iot/create", methods=["POST"])
@login_required
def create_iot():
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    mac_address = data.get('mac_address')
    device_type = data.get('device_type', 'ResQ Band')
    patient_id = data.get('patient_id') or None
    if not mac_address:
        return jsonify({"error": "Missing MAC Address"}), 400
    d = IoTDevice(mac_address=mac_address, device_type=device_type, patient_id=patient_id, battery_level=100)
    db.session.add(d)
    db.session.commit()
    return jsonify({"message": "Created"})

@app.route("/api/admin/iot/<int:iot_id>", methods=["DELETE"])
@login_required
def delete_iot(iot_id):
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    i = IoTDevice.query.get(iot_id)
    if not i: return jsonify({"error": "Not found"}), 404
    db.session.delete(i)
    db.session.commit()
    return jsonify({"message": "Deleted"})

@app.route("/api/admin/hospital/create", methods=["POST"])
@login_required
def create_hospital():
    if current_user.role != 'superadmin': return jsonify({"error": "Unauthorized"}), 403
    data = request.json
    er = int(data.get('er_beds', 10))
    trauma = int(data.get('trauma_beds', 5))
    iso = int(data.get('isolation_beds', 5))
    h = Hospital(name=data['name'], lat=float(data.get('lat', 0.0)), lng=float(data.get('lng', 0.0)), capacity=er+trauma+iso, er_beds_count=er, trauma_beds_count=trauma, isolation_beds_count=iso)
    db.session.add(h)
    db.session.commit()
    # Create Beds in DB
    for i in range(er):
        db.session.add(Bed(hospital_id=h.id, bed_number=f"ER-{i+1}", bed_type="Regular"))
    for i in range(trauma):
        db.session.add(Bed(hospital_id=h.id, bed_number=f"TR-{i+1}", bed_type="Trauma"))
    for i in range(iso):
        db.session.add(Bed(hospital_id=h.id, bed_number=f"ISO-{i+1}", bed_type="Isolation"))
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/admin/hospital/<int:hosp_id>", methods=["DELETE"])
@login_required
def delete_hospital(hosp_id):
    if current_user.role != 'superadmin': return jsonify({"error": "Unauthorized"}), 403
    h = Hospital.query.get(hosp_id)
    if not h: return jsonify({"error": "Not found"}), 404
    db.session.delete(h)
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/hospitals", methods=["GET"])
@app.route("/api/admin/ambulance/<int:amb_id>", methods=["PUT"])
@login_required
def admin_update_ambulance(amb_id):
    if current_user.role not in ['superadmin', 'hospitaladmin']: return jsonify({"error": "Unauthorized"}), 403
    a = Ambulance.query.get(amb_id)
    if not a: return jsonify({"error": "Not found"}), 404
    data = request.json
    if 'unit_id' in data: a.unit_id = data['unit_id']
    if 'hospital_id' in data: a.hospital_id = data['hospital_id'] or None
    if 'equipment_status' in data: a.equipment_status = data['equipment_status']
    db.session.commit()
    return jsonify({"status": "success"})

@app.route("/api/admin/roles", methods=["GET"])
@login_required
def get_roles():
    if current_user.role != 'superadmin': return jsonify({"error": "Unauthorized"}), 403
    roles = RolePolicy.query.all()
    return jsonify([
        {
            "id": r.id, "role_name": r.role_name, 
            "can_manage_users": r.can_manage_users,
            "can_dispatch_fleet": r.can_dispatch_fleet,
            "can_edit_vitals": r.can_edit_vitals,
            "can_view_analytics": r.can_view_analytics,
            "can_manage_facilities": r.can_manage_facilities
        } for r in roles
    ])

@app.route("/api/admin/role/<int:role_id>", methods=["PUT"])
@login_required
def update_role(role_id):
    if current_user.role != 'superadmin': return jsonify({"error": "Unauthorized"}), 403
    role = RolePolicy.query.get(role_id)
    if not role: return jsonify({"error": "Not found"}), 404
    data = request.json
    if 'can_manage_users' in data: role.can_manage_users = data['can_manage_users']
    if 'can_dispatch_fleet' in data: role.can_dispatch_fleet = data['can_dispatch_fleet']
    if 'can_edit_vitals' in data: role.can_edit_vitals = data['can_edit_vitals']
    if 'can_view_analytics' in data: role.can_view_analytics = data['can_view_analytics']
    if 'can_manage_facilities' in data: role.can_manage_facilities = data['can_manage_facilities']
    db.session.commit()
    return jsonify({"status": "success"})

def get_hospitals():
    hospitals = [h.to_dict() for h in Hospital.query.all()]
    return jsonify(hospitals)

# -------------------------
# Helper Functions
# -------------------------
def assign_random_staff(bed):
    pass

def generate_arabic_name():
    pass

@app.route("/api/incoming_self", methods=["POST"])
def add_self_patient():
    data = request.json
    national_id = data.get("national_id") or f"TEMP-{random.randint(1000,9999)}"
    p = Patient.query.get(national_id)
    if not p:
        p = Patient(national_id=national_id, name=data.get("name", "Unknown Patient"), status="En Route to Hospital")
        db.session.add(p)
    else:
        p.status = "En Route to Hospital"
        
    visit = Visit(patient_id=p.national_id, status="En Route", symptoms_text=data.get("symptoms", "CHECK-IN"))
    db.session.add(visit)
    db.session.commit()
    socketio.emit("new_incoming_self", visit.to_dict())
    return jsonify({"status": "notified", "visit_id": visit.id, "patient_id": p.national_id})

@app.route("/api/ai_consult", methods=["POST"])
def ai_consult():
    data = request.json
    text = data.get("text", "") or data.get("symptoms", "")
    patient_id = data.get("patient_id")
    priority = 1
    if patient_id:
        p = Patient.query.get(patient_id)
        if p:
            priority = p.priority
    plan = copilot.generate_plan(text, priority, language=data.get("language", "en"))
    return jsonify(plan)

@app.route("/api/chat", methods=["POST"])
def ai_chat():
    """
    Real LLM medical chat via Google Gemini.
    Body: { "message": "...", "history": [...] }
    Returns: { "reply": "..." }
    """
    import json as _json
    data = request.json or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])   # [{role, content}, ...]
    ui_lang = data.get("language", "en")

    if not message:
        return jsonify({"reply": "Please describe your medical question or emergency."}), 400

    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

    # ── Try real Gemini LLM ──
    if GEMINI_KEY:
        import urllib.request, urllib.error
        SYSTEM = (
            "You are Nurse Sara, a highly experienced emergency medical nurse at ResQ AI Emergency System. "
            "You provide clear, accurate, and calm medical first-aid guidance for emergencies and general health questions. "
            "Always remind the user to call emergency services (911) for life-threatening situations. "
            "Keep responses concise and empathetic. "
            "CRITICAL: When providing step-by-step instructions, YOU MUST separate each distinct step using the delimiter '|||'. "
            "For example: 'First, call 911.|||Next, apply pressure.|||Finally, wait for help.' "
            "Do not diagnose, but DO provide clear first-aid and triage guidance. "
            f"IMPORTANT: The user has selected language code '{ui_lang}' in their UI. YOU MUST ALWAYS respond in the language corresponding to '{ui_lang}', REGARDLESS of the language the user types in."
        )
        contents = []
        for h in history[-8:]:
            role = "user" if h.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        payload = _json.dumps({
            "system_instruction": {"parts": [{"text": SYSTEM}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
        }).encode()

        # Try models in order of quota generosity
        models_to_try = [
            "gemini-flash-lite-latest",
            "gemini-2.0-flash-lite-001",
            "gemini-2.0-flash"
        ]
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    result = _json.loads(resp.read())
                reply = result["candidates"][0]["content"]["parts"][0]["text"]
                return jsonify({"reply": reply})
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print(f"[Gemini] 429 rate limit on {model_name}, trying next model...")
                    import time as _time; _time.sleep(1)
                    continue
                print(f"[Gemini] HTTP {e.code} on {model_name}: {e}")
                break
            except Exception as e:
                print(f"[Gemini] Error on {model_name}: {e}")
                break

    # ── Fallback: rule-based medical responses ──
    msg = message.lower()
    if any(w in msg for w in ["bleed", "blood", "wound", "cut"]):
        reply = ("**Bleeding Control - First Aid:**\n"
                 "1. Apply direct, firm pressure with a clean cloth.\n"
                 "2. Do NOT remove the cloth if soaked - add more layers.\n"
                 "3. Raise the injured limb above heart level.\n"
                 "4. Call 911 immediately for severe bleeding.\n"
                 "_Stay with the patient and keep them calm._")
    elif any(w in msg for w in ["cpr", "cardiac", "heart", "chest", "no pulse", "unconscious"]):
        reply = ("**CPR - Act Now:**\n"
                 "1. Call 911 immediately.\n"
                 "2. Tilt head back, lift chin. Check breathing 10 sec.\n"
                 "3. Give 2 rescue breaths.\n"
                 "4. Push 30 times on center of chest at 110 BPM - hard & fast.\n"
                 "5. Repeat until EMS arrives.\n"
                 "_Don't stop. You are their heartbeat._")
    elif any(w in msg for w in ["chok", "airway", "heimlich"]):
        reply = ("**Choking - Heimlich:**\n"
                 "1. Ask 'Can you speak?' - if NO, act immediately.\n"
                 "2. Give 5 firm back blows between shoulder blades.\n"
                 "3. Give 5 abdominal thrusts inward and upward.\n"
                 "4. Repeat until object is expelled.\n"
                 "_If patient becomes unconscious, start CPR._")
    elif any(w in msg for w in ["burn", "fire", "scald", "hot"]):
        reply = ("**Burn Treatment:**\n"
                 "1. Run COOL (not cold) water over the burn for 10–20 min.\n"
                 "2. Remove jewelry near the burn before swelling.\n"
                 "3. Cover loosely with cling film or clean cloth.\n"
                 "4. Do NOT use ice, butter, or toothpaste.\n"
                 "_Seek medical attention for burns larger than 3cm._")
    elif any(w in msg for w in ["stroke", "face droop", "arm weak", "speech", "slur", "fast"]):
        reply = ("**FAST Stroke Check:**\n"
                 "• **F**ACE - Ask them to smile. Is one side drooping?\n"
                 "• **A**RMS - Raise both arms. Does one drift down?\n"
                 "• **S**PEECH - Can they repeat a sentence clearly?\n"
                 "• **T**IME - If ANY sign, call 911 RIGHT NOW.\n"
                 "_Note the exact time symptoms started - tell EMS._")
    elif any(w in msg for w in ["seiz", "convuls", "epilep"]):
        reply = ("**Seizure Response:**\n"
                 "1. Clear hard/sharp objects from around them.\n"
                 "2. Do NOT restrain or put anything in their mouth.\n"
                 "3. Time the seizure - call 911 if >5 min.\n"
                 "4. After convulsions, roll them on their side.\n"
                 "_Stay with them and speak gently._")
    elif any(w in msg for w in ["allerg", "anaphyl", "epipen", "hive", "sting", "swell"]):
        reply = ("**Allergic Reaction:**\n"
                 "1. Remove/distance them from the allergen.\n"
                 "2. Use EpiPen if available (outer thigh, 10 sec hold).\n"
                 "3. Call 911 for any breathing difficulty or swelling.\n"
                 "4. If conscious & not breathing difficulty: antihistamine.\n"
                 "_EpiPen is NOT a substitute for 911._")
    else:
        reply = ("I'm Nurse Sara, your medical AI assistant. I can help with:\n\n"
                 "🩸 **Bleeding** · 🫀 **CPR** · 😮 **Choking**\n"
                 "🔥 **Burns** · 🧠 **Stroke** · ⚡ **Seizure** · ⚠️ **Allergic reaction**\n\n"
                 "Describe your emergency or medical question and I'll guide you step by step. "
                 "For life-threatening emergencies, always call **911** immediately.")

    if ui_lang and ui_lang != 'en':
        try:
            import urllib.request, urllib.parse, json
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={ui_lang}&dt=t&q={urllib.parse.quote(reply)}"
            with urllib.request.urlopen(url, timeout=3) as res:
                trans_data = json.loads(res.read())
                reply = "".join([t[0] for t in trans_data[0] if t[0]])
        except Exception as e:
            print("[Translate] Error translating fallback:", e)

    return jsonify({"reply": reply})


@app.route("/api/translate", methods=["POST"])
def translate_text():
    """
    Translate text to the target language code.
    Body: { "text": "...", "to": "..." }
    """
    data = request.json or {}
    text = data.get("text", "").strip()
    target_lang = data.get("to", "en").strip()
    if not text or target_lang == "en":
        return jsonify({"translatedText": text})

    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
    if GEMINI_KEY:
        import urllib.request, urllib.error
        import json as _json

        payload = _json.dumps({
            "contents": [{
                "parts": [{"text": f"Translate the following first-aid assistance text into the language corresponding to language code '{target_lang}'. Do not add any explanation or preamble, respond only with the translation: {text}"}]
            }],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 200}
        }).encode()

        models_to_try = [
            "gemini-flash-lite-latest",
            "gemini-2.0-flash-lite-001",
            "gemini-2.0-flash"
        ]
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    result = _json.loads(resp.read())
                    translated = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return jsonify({"translatedText": translated})
            except Exception as e:
                print(f"Translation model {model_name} failed: {e}")

    # Fallback to translate.googleapis.com if Gemini fails/no key
    try:
        import urllib.request, urllib.parse, json as _json
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={target_lang}&dt=t&q={urllib.parse.quote(text)}"
        with urllib.request.urlopen(url, timeout=3) as res:
            trans_data = _json.loads(res.read())
            translated = "".join([t[0] for t in trans_data[0] if t[0]])
            return jsonify({"translatedText": translated})
    except Exception as e:
        print("[Translate API] Fallback translate error:", e)

    return jsonify({"translatedText": text})


@app.route("/api/sign_triage", methods=["POST"])
def sign_triage():
    """
    Accepts signed text from the sign language page.
    Creates/updates a patient record and returns an AI care plan.
    Body: { "text": "CHEST PAIN", "patient_id": null }
    """
    data = request.json
    text = data.get("text", "").strip()
    patient_id = data.get("patient_id") or f"SL-{int(time.time())}"

    if not text:
        return jsonify({"error": "No signed text provided"}), 400

    # Create a placeholder patient if none exists
    p = Patient.query.get(patient_id)
    if not p:
        p = Patient(
            id=patient_id,
            name="Sign Language Patient",
            age=30, gender="U",
            status="Waiting",
            priority=2,  # Urgent default until vitals confirm
            score=60,
            symptoms_text=text,
            arrival_time=time.time()
        )
        db.session.add(p)
    else:
        p.symptoms_text = text
    db.session.commit()

    # Generate AI care plan
    lang = data.get("language", "en")
    plan = copilot.generate_plan(text, 2, language=lang)
    plan["patient_id"] = patient_id
    return jsonify(plan)

# Dispatch Queue for Ambulance Polling
pending_dispatches = []

# --- PHASE 1: SMART CITY APIs ---

@app.route("/api/auth/login", methods=["POST"])
def mobile_login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        # For a production app we'd return a JWT.
        # For this prototype we'll return user data to store locally.
        return jsonify({
            "success": True,
            "user_id": user.id,
            "username": user.username,
            "role": user.role,
            "name": user.name
        })
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route("/api/city/green-wave", methods=["POST"])
def green_wave():
    """
    Mock API to interface with Smart City Traffic Lights
    """
    data = request.json
    ambulance_id = data.get("ambulance_id")
    dest_lat = data.get("lat")
    dest_lng = data.get("lng")
    
    # Simulate pushing a request to the city traffic grid
    print(f"[SMART CITY] Green Wave activated for Ambulance {ambulance_id} to {dest_lat},{dest_lng}")
    
    return jsonify({"status": "Green Wave Active", "message": "Traffic lights overriden on route"})

@app.route("/api/drone/dispatch", methods=["POST"])
def dispatch_drone():
    data = request.json
    lat = data.get("lat")
    lng = data.get("lng")
    drone_id = data.get("drone_id")
    
    if not drone_id:
        drone = Drone.query.filter_by(status="Docked").first()
    else:
        drone = Drone.query.get(drone_id)
        
    if drone:
        drone.status = "In Flight"
        drone.lat = lat
        drone.lng = lng
        db.session.commit()
        return jsonify({"message": "Drone dispatched!", "drone_id": drone.call_sign, "start_lat": drone.lat, "start_lng": drone.lng})
    return jsonify({"error": "No available drones."}), 400


@app.route("/api/emergency/dispatch", methods=["POST"])
def dispatch_emergency():
    # SOS Signal
    data = request.json
    lat = data.get("lat") or data.get("latitude", 26.2235)
    lng = data.get("lng") or data.get("longitude", 50.5876)
    source = data.get("source", "ambulance")
    vitals = data.get("vital_data", {})
    
    # Default Values
    symptoms = "SOS PRESSED - GPS: " + str(lat) + "," + str(lng)
    condition = "CRITICAL DISPATCH"
    hr = 140
    
    # ADVANCED TELEMETRY LOGIC
    if source == "smart_watch":
        symptoms = "❤️ CARDIAC ARREST DETECTED (Watch)"
        condition = "CODE BLUE"
        hr = 0
    elif source == "crash_sensor":
        symptoms = "💥 HIGH IMPACT CRASH (5.2g)"
        condition = "TRAUMA ALERT"
        hr = 110

    # Get real route ETA from hospital
    route = get_real_route(MAIN_HOSPITAL_COORDS["lat"], MAIN_HOSPITAL_COORDS["lng"], float(lat), float(lng))
    eta_mins = route.get("duration_minutes", 10)

    pid = f"SOS-{random.randint(1000, 9999)}"
    p = Patient(
        national_id=pid,
        name="EMERGENCY CALLER",
        age=30, # Default or Unknown
        gender="U" # Unknown
    )
    db.session.add(p)
    db.session.commit()

    v = Visit(
        hospital_id=1,
        patient_id=pid,
        status="Dispatched",
        priority=3,
        score=100,
        hr=hr,
        symptoms_text=f"{condition} - {symptoms}",
        patient_lat=float(lat),
        patient_lng=float(lng),
        arrival_time=time.time()
    )
    db.session.add(v)
    db.session.commit()
    
    entry = {
        "id": str(v.id),
        "name": p.name,
        "age": "UNK",
        "hr": hr, 
        "condition": condition, 
        "symptoms": symptoms,
        "arrival_time": f"ETA {eta_mins}m",
        "full_data": { 
             "name": "Unknown (SOS)", "hr": hr, "spo2": 90, 
             "source": source, "chest_pain": 1, "breathing": 1 
        } 
    }
    
    incoming_ambulances.append(entry)
    
    for vol in active_volunteers.values():
        if vol.get("status") == "active":
            vol["alert"] = {
                "id": entry["id"],
                "lat": lat,
                "lng": lng,
                "symptoms": symptoms,
                "distance": "0.4 km"
            }
            print(f"Volunteer Alert Sent to {vol['id']}")

    socketio.emit('new_emergency', entry)
    return jsonify({
        "status": "success",
        "id": str(v.id),
        "eta": eta_mins,
        "route_polyline": route.get("polyline")
    })



@app.route("/api/ambulance/check_dispatch", methods=["GET"])
def check_dispatch():
    # Find oldest Dispatched visit
    mission = Visit.query.filter_by(status="Dispatched").order_by(Visit.arrival_time.asc()).first()
    
    if mission:
        p = Patient.query.get(mission.patient_id)
        return jsonify({
            "dispatch": True, 
            "mission": {
                "id": p.national_id if p else mission.patient_id,
                "name": p.name if p else "Unknown Patient",
                "lat": mission.patient_lat or 26.2235, 
                "lng": mission.patient_lng or 50.5876,
                "symptoms": mission.symptoms_text or "Emergency Dispatch",
                "condition": "Critical" if mission.priority == 3 else "High Priority"
            }
        })
    return jsonify({"dispatch": False})

@app.route("/api/ambulance/status/<amb_id>", methods=["GET"])
def get_ambulance_status(amb_id):
    v = Visit.query.filter_by(patient_id=str(amb_id)).order_by(Visit.id.desc()).first()
    if not v and str(amb_id).isdigit():
        v = Visit.query.get(int(amb_id))
        
    if v:
        p = Patient.query.get(v.patient_id)
        hosp_lat = None
        hosp_lng = None
        dest_name = "Hospital"
        
        if v.hospital_id:
            h = Hospital.query.get(v.hospital_id)
            if h:
                hosp_lat = h.lat
                hosp_lng = h.lng
                dest_name = h.name
                
        # Simulate ambulance movement
        amb_lat = v.patient_lat
        amb_lng = v.patient_lng
        
        if v.status == "Dispatched" and hosp_lat and hosp_lng:
            elapsed = time.time() - v.arrival_time
            total_time = 120.0 # 2 minutes simulated trip time
            progress = min(1.0, elapsed / total_time)
            
            amb_lat = hosp_lat + (v.patient_lat - hosp_lat) * progress
            amb_lng = hosp_lng + (v.patient_lng - hosp_lng) * progress
            
        return jsonify({
            "id": v.id,
            "name": p.name if p else "Unknown",
            "status": "ARRIVED" if v.status == "Waiting" else v.status,
            "condition": "Critical" if v.priority == 3 else "Stable",
            "symptoms": v.symptoms_text,
            "ambulance_lat": amb_lat,
            "ambulance_lng": amb_lng,
            "patient_lat": v.patient_lat,
            "patient_lng": v.patient_lng,
            "hosp_lat": hosp_lat,
            "hosp_lng": hosp_lng,
            "destination": dest_name,
            "vitals": {
                "hr": v.hr if v.hr is not None else "--",
                "spo2": v.spo2 if v.spo2 is not None else "--",
                "sys_bp": v.sys_bp if v.sys_bp is not None else "--",
                "dia_bp": v.dia_bp if v.dia_bp is not None else "--"
            },
            "full_data": {}
        })
        
    # Fallback to memory
    amb = next((x for x in incoming_ambulances if str(x["id"]) == str(amb_id)), None)
    if amb:
         return jsonify({
            "id": amb["id"],
            "name": amb.get("name"),
            "status": amb.get("status"),
            "condition": amb.get("condition", "Unknown"),
            "ambulance_lat": amb.get("full_data", {}).get("lat"),
            "ambulance_lng": amb.get("full_data", {}).get("lng"),
            "hosp_lat": None,
            "hosp_lng": None,
            "destination": amb.get("destination", "Hospital"),
            "full_data": amb.get("full_data", {})
         })
         
    return jsonify({"error": "Not Found", "status": "UNKNOWN"}), 404

@app.route("/api/patient/tracking/<patient_id>", methods=["GET"])
def get_patient_tracking(patient_id):
    v = None
    if str(patient_id).isdigit():
        v = Visit.query.get(int(patient_id))
    
    if v:
        hosp_lat = None
        hosp_lng = None
        dest_name = "Hospital"
        
        if v.hospital_id:
            h = Hospital.query.get(v.hospital_id)
            if h:
                hosp_lat = h.lat
                hosp_lng = h.lng
                dest_name = h.name
                
        return jsonify({
            "id": v.id,
            "status": v.status,
            "ambulance_lat": v.patient_lat,
            "ambulance_lng": v.patient_lng,
            "patient_lat": v.patient_lat,
            "patient_lng": v.patient_lng,
            "hospital_id": v.hospital_id,
            "hosp_lat": hosp_lat,
            "hosp_lng": hosp_lng,
            "destination": dest_name,
            "symptoms": v.symptoms_text,
            "vitals": {
                "hr": v.hr,
                "spo2": v.spo2,
                "sys_bp": v.sys_bp,
                "dia_bp": v.dia_bp,
                "temp": v.temp
            }
        })
    return jsonify({"error": "Not Found"}), 404

@app.route("/api/ambulance/update", methods=["POST"])
def update_ambulance():
    data = request.json
    amb_id = str(data.get("id", "")) # Patient ID or Visit ID
    status = data.get("status")
    
    mission = None
    if amb_id.isdigit():
        mission = Visit.query.get(int(amb_id))
    if not mission:
        mission = Visit.query.filter_by(patient_id=amb_id).order_by(Visit.id.desc()).first()
    if mission:
        if status:
            mission.status = status
            
        if "hospital_id" in data:
            mission.hospital_id = data["hospital_id"]
            
        db.session.commit()
        
        # Notify Dashboard through socket so it updates the queue globally
        socketio.emit('queue_update', {'patient_id': amb_id, 'status': status})
        
        return jsonify({"status": "updated", "mission": {"id": mission.id, "status": mission.status}})
    return jsonify({"error": "Mission not found"}), 404


@app.route("/api/ambulance/new", methods=["POST"])
def new_ambulance_vitals():
    data = request.json
    amb_id = str(data.get("id", ""))
    
    mission = None
    if amb_id.isdigit():
        mission = Visit.query.get(int(amb_id))
    if not mission:
        mission = Visit.query.filter_by(patient_id=amb_id).order_by(Visit.id.desc()).first()
        
    p = Patient.query.get(mission.patient_id) if mission else Patient.query.get(amb_id)
    
    if p:
        p.name = data.get("name", p.name)
        vitals = data.get("vitals", {})
        
        if mission:
            raw_hr = vitals.get("hr")
            raw_spo2 = vitals.get("spo2")
            mission.hr = int(raw_hr) if (raw_hr and str(raw_hr).strip() != '') else (mission.hr or 80)
            mission.spo2 = int(raw_spo2) if (raw_spo2 and str(raw_spo2).strip() != '') else (mission.spo2 or 98)
            mission.symptoms_text = data.get("symptoms", mission.symptoms_text)
            mission.status = data.get("status", "HEADS UP")
            
        db.session.commit()
        return jsonify({"status": "received"})
    return jsonify({"error": "Patient not found"}), 404

@app.route("/api/ambulance/cancel", methods=["POST"])
def cancel_ambulance():
    amb_id = str(request.json.get("id", ""))
    mission = None
    if amb_id.isdigit():
        mission = Visit.query.get(int(amb_id))
    if not mission:
        mission = Visit.query.filter_by(patient_id=amb_id).order_by(Visit.id.desc()).first()
        
    if mission and mission.status in ["Waiting", "En Route", "Dispatched", "ON_SCENE", "ON SCENE", "TRANSPORTING", "HEADS UP"]:
        mission.status = "Cancelled"
        db.session.commit()
    return jsonify({"status": "cancelled"})

@app.route("/api/ambulance/arrive", methods=["POST"])
def arrive_ambulance():
    amb_id = str(request.json.get("id", ""))
    
    mission = None
    if amb_id.isdigit():
        mission = Visit.query.get(int(amb_id))
    if not mission:
        mission = Visit.query.filter_by(patient_id=amb_id).order_by(Visit.id.desc()).first()
        
    if not mission:
        return jsonify({"error": "Entry not found"}), 404
        
    p = Patient.query.filter_by(national_id=str(mission.patient_id)).first()
    if not p:
        # Fallback if no patient record exists
        p = Patient(national_id=mission.patient_id, name="Unknown SOS")
        db.session.add(p)
        db.session.commit()
    
    # We use their existing vitals, or defaults if they didn't send them
    hr_val = mission.hr if (mission and mission.hr) else None
    spo2_val = mission.spo2 if (mission and mission.spo2) else None
    sys_bp_val = mission.sys_bp if (mission and mission.sys_bp) else None
    dia_bp_val = mission.dia_bp if (mission and mission.dia_bp) else None
    
    hr = float(hr_val) if (hr_val and str(hr_val).strip() != '') else 80.0
    spo2 = float(spo2_val) if (spo2_val and str(spo2_val).strip() != '') else 98.0
    sys_bp = float(sys_bp_val) if (sys_bp_val and str(sys_bp_val).strip() != '') else 120.0
    dia_bp = float(dia_bp_val) if (dia_bp_val and str(dia_bp_val).strip() != '') else 80.0
    temp = 37.0
    
    # 2. Run MindSpore AI Prediction
    features = {
        "heartrate": float(hr),
        "o2sat": float(spo2),
        "temperature": float(temp),
        "sbp": float(sys_bp),
        "dbp": float(dia_bp),
        "resprate": 18, 
        "pain": 5 if (mission and mission.symptoms_text) else 0 
    }
    
    final_priority, ai_risk = predict(features)
    
    # Force Critical if SOS Dispatch
    if "SOS" in str(p.national_id) or ai_risk > 0.8:
        final_priority = 3
        ai_risk = max(ai_risk, 0.9)
    
    p.priority = final_priority
    p.score = int(ai_risk * 100)
        
    # Ensure status is Waiting so they show up in ER Queue!
    p.status = "Waiting"
    
    # Update mission status to Waiting so they appear on dashboard ER Queue
    mission = Visit.query.filter_by(patient_id=amb_id).order_by(Visit.id.desc()).first()
    if mission:
        mission.status = "Waiting"
        mission.priority = final_priority
        mission.score = int(ai_risk * 100)
        
    db.session.commit()
        
    return jsonify({"status": "arrived"})

# Override get_ambulances to use real list (MERGED)
@app.route("/api/ambulances_real")
def get_ambulances_real():
    display_list = []
    
    # Get all actual ambulances
    ambs = Ambulance.query.all()
    for a in ambs:
        a_dict = {"id": a.id, "status": a.status, "lat": a.current_lat, "lng": a.current_lng, "unit": a.unit_id, "ETA": f"{random.randint(2, 8)} mins"}
        a_dict["display_type"] = "AMB"
        display_list.append(a_dict)
        
    # Get all active incoming/dispatched visits (Only show on ticker after Handoff)
    active_statuses = ["HEADS UP"]
    slfs = Visit.query.filter(Visit.status.in_(active_statuses)).all()
    for s in slfs:
        s_display = s.to_dict()
        p_obj = Patient.query.filter_by(national_id=str(s.patient_id)).first()
        s_display["name"] = p_obj.name if p_obj else "Emergency Patient"
        s_display["display_type"] = "AMB" if s.status != "En Route" else "CAR"
        s_display["condition"] = s.status
        s_display["hr"] = s.hr if s.hr else "--"
        s_display["spo2"] = s.spo2 if s.spo2 else "--"
        s_display["sys_bp"] = s.sys_bp if s.sys_bp else "--"
        s_display["dia_bp"] = s.dia_bp if s.dia_bp else "--"
        s_display["symptoms"] = s.symptoms_text or s_display.get("symptoms") or "Emergency"
        display_list.append(s_display)
        
    return jsonify(display_list)

@app.route("/api/patient/<patient_id>")
def get_patient_api(patient_id):
    # ORM lookup
    p = Patient.query.get(patient_id)
    if p:
        return jsonify({
            "found": True,
            "name": p.name,
            "age": p.age,
            "chronic": p.chronic,
            "allergy": p.allergy
        })
    return jsonify({"found": False})

@app.route("/api/patient/me/history")
@login_required
def get_patient_me_history():
    if getattr(current_user, 'role', '') != 'patient':
        return jsonify([])
    # current_user is a Patient
    hist = getattr(current_user, 'medical_history', '')
    if not hist:
        return jsonify([])
    
    out = []
    for h in hist.split('|'):
        h = h.strip()
        if h:
            out.append({"date": "Prior Record", "symptoms": h, "hospital": "ResQ Hospital", "status": "Archived"})
    # Sort latest first (reverse order since history is appended)
    return jsonify(out[::-1])

@app.route("/api/iot/webhook", methods=["POST"])
def iot_webhook():
    data = request.json
    # In a real scenario we map mac_address to a patient/bed.
    # For the Kiosk, we broadcast the raw sensor readings to the frontend.
    socketio.emit('hardware_vitals_scanned', data)
    return jsonify({"status": "success", "message": "Telemetry received and broadcasted"})

@app.route("/api/triage", methods=["POST"])
def triage_patient():
    lang = request.json.get("language", "en")
    data = request.json
    
    # 1. Parse Data
    patient_id = data.get("patient_id", f"UNK-{int(time.time())}")
    name = data.get("name", "Unknown")
    # Graceful handling if age is empty string
    try:
        age_raw = data.get("age", 30)
        age = int(age_raw) if age_raw else 30
    except:
        age = 30
        
    gender = data.get("gender", "M")
    
    # Clinical Data
    hr = float(data.get("hr", 80))
    spo2 = float(data.get("spo2", 98))
    temp = float(data.get("temp", 37.0))
    sys_bp = float(data.get("sys_bp", 120))
    dia_bp = float(data.get("dia_bp", 80))
    
    # Symptoms (Booleans)
    chest_pain = int(data.get("chest_pain", False))
    breathing = int(data.get("breathing", False))
    bleeding = int(data.get("bleeding", False))
    fainting = int(data.get("fainting", False))
    
    # History
    chronic = int(data.get("chronic", False))
    allergy = int(data.get("allergy", False))
    
    # Save/Update Patient History (ORM)
    p = Patient.query.get(patient_id)
    if not p:
        p = Patient(national_id=patient_id, name=name, age=age, gender=gender)
    else:
        p.age = age # Update age
    
    p.chronic = bool(chronic)
    p.allergy = bool(allergy)
    
    db.session.add(p)
    db.session.commit()

    # Store text symptoms if provided by user
    symptoms_text_str = data.get("symptoms", "")
    if chest_pain: symptoms_text_str += " chest pain"
    if breathing: symptoms_text_str += " short of breath"
    if bleeding: symptoms_text_str += " bleeding"
    if fainting: symptoms_text_str += " fainting"
    symptoms_text_str = symptoms_text_str.strip()

    # 2. AI Model Prediction
    # Map app variables to MIMIC model feature names
    features = {
        "heartrate": hr,
        "o2sat": spo2,
        "temperature": temp,
        "sbp": sys_bp,
        "dbp": dia_bp,
        "resprate": 18, # Default if not collected in Kiosk
        "pain": 5 if chest_pain else 0, # Simple heuristic mapping
        "symptoms": symptoms_text_str
    }
    
    ai_priority, ai_risk = predict(features)
    
    # 3. Heuristic Adjustments (Hybrid Intelligence)
    bp_risk_adder = 0.0
    symptom_risk_adder = 0.0
    
    # Hypertensive Crisis / Shock
    if sys_bp > 180 or dia_bp > 120: bp_risk_adder += 0.4
    if sys_bp < 90: bp_risk_adder += 0.35
    
    # Critical Symptoms Overrides
    if chest_pain or breathing:
        symptom_risk_adder += 0.5 # Immediate High Risk base
        
    final_risk = min(ai_risk + bp_risk_adder + symptom_risk_adder, 1.0)
    
    # Silent Hypoxia Detection
    # Standard Def: Low SpO2 but Heart Rate isn't compensating enough (or just general dangerous mismatch)
    # Simple rule for app: SpO2 < 94 WITHOUT severe distress complaints (optional) OR just general hidden danger
    silent_risk = False
    if spo2 < 94 and hr > 100:
        silent_risk = True
        final_risk = max(final_risk, 0.85) # Force Critical
        
    # ---------------------------
    # SANITY CHECK (Sanitization)
    # ---------------------------
    # If Vitals are normal and No Symptoms, FORCE Low Risk
    # This overrides over-sensitive AI or history weights as a safety fail-safe.
    is_vitals_normal = (
        60 <= hr <= 100 and
        95 <= spo2 <= 100 and
        36.0 <= temp <= 37.5 and
        90 <= sys_bp <= 140
    )
    has_no_symptoms = not (chest_pain or breathing or bleeding or fainting)
    
    if is_vitals_normal and has_no_symptoms:
        final_risk = min(final_risk, 0.15) # Force Green (Low Risk)
        ai_priority = 0 # Override AI model opinion
    
    # Priority Calculation (Strict Buckets)
    # 3 = Critical (Red): 80-100%
    # 2 = Urgent (Orange): 50-79%
    # 1 = Normal (Yellow): 30-49%
    # 0 = Low (Green): 0-29%
    
    # Force Critical for Chest Pain/Breathing (Overrides Score to 90+)
    if chest_pain or breathing:
        final_risk = max(final_risk, 0.9)

    # STRICT MAPPING based on User's requested buckets
    # Ignore 'ai_priority' for final bucket assignment to ensure strict color match
    if math.isnan(final_risk):
        final_risk = 0.0
        
    if final_risk >= 0.8: 
        final_priority = 3
    elif final_risk >= 0.5: 
        final_priority = 2
    elif final_risk >= 0.3: 
        final_priority = 1
    else: 
        final_priority = 0
        
    # User Request: If 100%, MUST be top priority
    if final_risk >= 0.99: final_priority = 3

    # 4. Create Visit with Final Risk/Priority
    visit = Visit(patient_id=patient_id)
    visit.hospital_id = data.get("hospital_id", 1)
    visit.priority = final_priority
    visit.score = int(final_risk * 100)
    visit.status = "Waiting"
    
    # SAVE VITALS
    visit.hr = int(hr)
    visit.spo2 = int(spo2)
    visit.temp = float(temp)
    visit.sys_bp = int(sys_bp)
    visit.dia_bp = int(dia_bp)
    
    # SAVE TEXT
    parts = []
    if chest_pain: parts.append("Chest Pain")
    if breathing: parts.append("Breathing Issues")
    if bleeding: parts.append("Bleeding")
    if fainting: parts.append("Unconscious")
    if not parts: parts.append("General Checklist")
    visit.symptoms_text = ", ".join(parts)
    
    db.session.add(visit)
    db.session.commit()

    # Create response entry (from DB obj to ensure consistency)
    patient_entry = {
         "id": patient_id,
         "name": name,
         "priority": visit.priority,
         "score": visit.score,
    }
    
    # queue.append(...) # REMOVED
    # queue.sort(...)   # REMOVED
    
    hospital_stats["total_entered"] += 1
    
    return jsonify({
        "status": "triaged", 
        "patient": patient_entry,
        "risk_level": "Critical" if final_risk > 0.8 else "Normal",
        "position": Visit.query.filter_by(status='Waiting').count(), # Real Count
        "queue_length": Visit.query.filter_by(status='Waiting').count()
    })

def parse_visit_text(text):
    notes = []
    clean = []
    for line in (text or "").split('\n'):
        if line.startswith("NOTE_START|"):
            parts = line.split("|")
            if len(parts) >= 4:
                notes.append({"author": parts[1], "time": parts[2], "text": parts[3]})
        else:
            clean.append(line)
    return "\n".join(clean), notes

@app.route("/api/queue")
def get_queue():
    # Fetch from Real DB
    visits = Visit.query.filter_by(status="Waiting").order_by(Visit.priority.desc(), Visit.score.desc()).all()
    output = []
    for v in visits:
        pat = Patient.query.get(v.patient_id)
        clean_symp, notes = parse_visit_text(v.symptoms_text)
        # Reconstruct dict for frontend
        output.append({
            "id": v.id,
            "name": pat.name if pat else "Unknown",
            "age": pat.age if pat else 30,
            "gender": pat.gender if pat else "M", 
            "priority": v.priority,
            "score": v.score,
            "arrival_time": v.arrival_time,
            "symptoms": { "Chronic": pat.chronic if pat else False, "Allergy": pat.allergy if pat else False },
            "symptoms_text": clean_symp,
            "notes": notes,
            "medical_history": pat.medical_history if pat else "",
            "vitals": {
                "hr": v.hr,
                "spo2": v.spo2,
                "bp": f"{v.sys_bp}/{v.dia_bp}"
            }
        })
    return jsonify(output)

@app.route("/api/beds")
def get_beds():
    beds = Bed.query.all()
    out = []
    for b in beds:
        d = { "id": b.id, "label": b.label, "type": b.bed_type, "staff": b.get_staff(), "patient": None }
        if b.visit_id:
            v = Visit.query.get(b.visit_id)
            if v:
                p = Patient.query.get(v.patient_id)
                if p:
                    clean_symp, notes = parse_visit_text(v.symptoms_text)
                    d["patient"] = {
                        "id": p.national_id, "name": p.name, "priority": v.priority, "arrival_time": v.arrival_time,
                        "age": p.age, "gender": p.gender, "symptoms_text": clean_symp, "symptoms": clean_symp,
                        "score": v.score, "notes": notes, "medical_history": p.medical_history,
                        "vitals": {"hr": v.hr, "spo2": v.spo2, "bp": f"{v.sys_bp}/{v.dia_bp}"}
                    }
        out.append(d)
    return jsonify(out)

@app.route("/api/assign", methods=["POST"])
def assign_bed():
    data = request.json
    pid = data.get("patient_id")
    bid = data.get("bed_id")
    staff_ids = data.get("staff_ids", [])
    
    visit = Visit.query.get(pid)
    if not visit or visit.status != "Waiting":
         return jsonify({"error": "Patient not in waiting queue"}), 400
         
    patient = Patient.query.get(visit.patient_id)
    if not patient:
         return jsonify({"error": "Patient not found"}), 404
        
    bed = Bed.query.get(bid)
    if not bed:
        return jsonify({"error": "Bed not found"}), 404
        
    if bed.visit_id:
        return jsonify({"error": "Bed occupied"}), 400
        
    import time
    visit.status = "Admitted"
    bed.visit_id = visit.id
    bed.set_staff(staff_ids)
    patient.medical_history = (patient.medical_history or "") + f" | Visit on {time.strftime('%Y-%m-%d')}: Assigned to Bed {bed.label}"
    db.session.commit()
    socketio.emit('bed_update', {"bed_id": bed.id, "patient_id": patient.national_id})
    return jsonify({"status": "success"})

@app.route("/api/notes", methods=["POST"])
def add_note():
    data = request.json
    pid = data.get("patient_id")
    bed_id = data.get("bed_id")
    note_text = data.get("note")
    
    if not pid or not note_text:
        return jsonify({"error": "Missing data"}), 400
        
    patient = Patient.query.filter_by(national_id=pid).first()
    if not patient:
        return jsonify({"error": "Patient not found"}), 404
        
    visit = None
    if bed_id:
        bed = Bed.query.get(bed_id)
        if bed and bed.visit_id:
            visit = Visit.query.get(bed.visit_id)
            
    if not visit:
        visit = Visit.query.filter_by(patient_id=patient.national_id).order_by(Visit.id.desc()).first()
        
    author = getattr(current_user, 'name', 'Staff')
    import time
    timestamp = time.strftime("%H:%M")
    
    if patient:
        patient.medical_history = (patient.medical_history or "") + f" | [{timestamp}] Note: {note_text}"
        
    if visit:
        visit.symptoms_text = (visit.symptoms_text or "") + f"\nNOTE_START|{author}|{timestamp}|{note_text}|NOTE_END"
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Visit not found"}), 404

# -------------------------
# Analytics & Chaos (Phase 4)
# -------------------------
hospital_stats = {
    "total_discharged": 0,
    "total_entered": 0,
    "start_time": time.time()
}

@app.route("/api/stats")
def get_stats():
    # Calculate Live Stats from DB
    triage_counts = {0:0, 1:0, 2:0, 3:0}
    wait_times = []
    now = time.time()
    
    # Active Patients (Waiting)
    # Note: status is on the Visit model, not Patient.
    waiting_visits = Visit.query.filter_by(status='Waiting').all()
    for v in waiting_visits:
        if v.priority in triage_counts: triage_counts[v.priority] += 1
        if v.arrival_time:
            wait_times.append(now - v.arrival_time)
        
    # Active Beds (Treated) using the Bed model
    db_beds = Bed.query.all()
    beds_occupied = 0
    for b in db_beds:
        if b.visit_id is not None:
            beds_occupied += 1
            v = Visit.query.get(b.visit_id)
            if v and v.priority in triage_counts:
                triage_counts[v.priority] += 1

    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
    
    # Saturation Calculation (User Request: Waiting + Beds / Total Beds)
    # Total Beds = 6
    TOTAL_BEDS = 6
    waiting_count = Visit.query.filter_by(status='Waiting').count()
    current_load = waiting_count + beds_occupied
    
    # Saturation % = (Current Load / Capacity) * 100
    saturation_risk = int((current_load / TOTAL_BEDS) * 100)
    
    # Capacity Forecast (1 Hour)
    # How many *more* can we take?
    # Logic: (Avg Discharges/Hr * 1hr) - (Current Deficit)
    # Discharge Rate (per min)
    uptime_mins = max(1, (now - hospital_stats["start_time"])/60)
    
    # Use DB for persistent counts instead of in-memory stats
    total_entered_db = Visit.query.count()
    discharged_db = Visit.query.filter_by(status="Discharged").count()
    
    discharge_rate_hr = (discharged_db / uptime_mins) * 60
    
    # Current available now = 6 - Beds Occupied (ignore queue for "Physical Capacity")
    physical_free = TOTAL_BEDS - beds_occupied
    
    # Forecasted Capacity = Physical Free + Expected Discharges
    # But if Queue > 0, they eat that capacity first.
    expected_capacity = (physical_free + discharge_rate_hr) - waiting_count
    
    return jsonify({
        "total_entered": total_entered_db,
        "discharged": discharged_db,
        "remaining": current_load,
        "active_patients": current_load,
        "avg_wait_seconds": int(avg_wait),
        "triage_distribution": triage_counts,
        "uptime_minutes": int(uptime_mins),
        "saturation_prediction": saturation_risk,
        "capacity_prediction": int(expected_capacity)
    })

@app.route("/api/ambulances")
def get_ambulances():
    # Return REAL stateful ambulances (Patients with status != Waiting/Treated)
    # Actually, we treat 'Dispatched' or 'En Route' as active ambulances
    active = Patient.query.filter(Patient.status.in_(['Dispatched', 'En Route', 'Transporting'])).all()
    
    output = []
    for p in active:
        output.append({
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "arrival_time": "ETA 8m",
            "display_type": "AMB",
            "condition": "Critical" if p.priority == 3 else "Stable",
             # Keeping static parameters for UI visual compatibility if keys are missing.
            "symptoms": "Emergency Response",
            "destination": "Trauma Center"
        })
    return jsonify(output)

@app.route("/api/chaos", methods=["POST"])
def trigger_chaos():
    # Mass Casualty Simulation
    # Generate 15-20 patients instantly
    count = random.randint(15, 20)
    
    first_names = ["John", "Jane", "Mike", "Sarah", "Chris", "Alex", "Taylor", "Jordan", "Casey", "Morgan"]
    last_names = ["Smith", "Doe", "Johnson", "Brown", "Williams", "Jones", "Miller", "Davis", "Garcia", "Rodriguez"]
    
    for _ in range(count):
        # 30% Critical, 40% Major, 30% Minor
        r = random.random()
        severity_profile = "minor"
        if r < 0.3: severity_profile = "critical"
        elif r < 0.7: severity_profile = "major"
        
        # Build Patient Data (Mixed Names)
        if random.random() > 0.3: 
             name = generate_arabic_name()
        else:
             name = f"{random.choice(first_names)} {random.choice(last_names)}"
             
        age = random.randint(18, 90)
        
        # Vitals Generator
        hr = random.randint(60, 100)
        spo2 = random.randint(95, 100)
        sbp = random.randint(110, 130)
        dbp = random.randint(70, 85)
        
        cp = 0
        br = 0
        bl = 0
        fa = 0
        
        if severity_profile == "critical":
            hr = random.randint(120, 160)
            sbp = random.randint(80, 100) # Shock
            spo2 = random.randint(80, 92)
            bl = 1 # Bleeding
            if random.random() > 0.5: br = 1 # Breathing
            
        elif severity_profile == "major":
            hr = random.randint(100, 120)
            sbp = random.randint(140, 160) # Pain/Stress
            cp = 1 if random.random() > 0.7 else 0
            
        # Simulate POST payload
        data = {
            "patient_id": f"MCI-{random.randint(1000,9999)}",
            "name": name,
            "age": age,
            "hr": hr, "spo2": spo2, "sys_bp": sbp, "dia_bp": dbp,
            "chest_pain": cp, "breathing": br, "bleeding": bl, "fainting": fa
        }
        
        # Reuse existing logic via internal call (or refactor, but here we just replicate for speed/simplicity)
        # Actually better to just call the function logic or hit the endpoint internally
        # Quick state update bypass to avoid context recursion issues in Flask
        # Duplicating logic is safer for this hackathon-style script to avoid request context errors
        
        # ... logic replication ...
        # Actually, let's just create a helper function
        process_triage(data)
        
    return jsonify({"status": "chaos_triggered", "count": count})

def process_triage(data):
    # Unified Logic: Uses the exact same criteria as Kiosk (triage_patient)
    # 1. Parse Data
    patient_id = data.get("patient_id", f"AMB-{random.randint(1000,9999)}")
    name = data.get("name", "Unknown")
    
    try:
        age = int(data.get("age", 30))
    except:
        age = 30
        
    gender = data.get("gender", "M")
    
    # Clinical Data
    hr = float(data.get("hr", 80))
    spo2 = float(data.get("spo2", 98))
    temp = float(data.get("temp", 37.0))
    sys_bp = float(data.get("sys_bp", 120))
    dia_bp = float(data.get("dia_bp", 80))
    
    # History (Defaults if missing)
    chronic = int(data.get("chronic", 0))
    allergy = int(data.get("allergy", 0))

    # ---------------------------------------------------------
    # PARSE SYMPTOMS (String/List Support for Ambulance App)
    # ---------------------------------------------------------
    chest_pain = int(data.get("chest_pain", 0))
    breathing = int(data.get("breathing", 0))
    bleeding = int(data.get("bleeding", 0))
    fainting = int(data.get("fainting", 0))

    # If flags are not set, try to parse from text (Ambulance Workflow)
    raw_symptoms = str(data.get("symptoms", "")).lower()
    
    if not (chest_pain or breathing or bleeding or fainting):
        checklist = data.get("checklist", [])
        if checklist: raw_symptoms += " " + " ".join(checklist).lower() # Merge list
        
        if "chest pain" in raw_symptoms or "heart" in raw_symptoms: chest_pain = 1
        if "breath" in raw_symptoms or "sob" in raw_symptoms: breathing = 1
        if "bleed" in raw_symptoms or "hemorrhage" in raw_symptoms: bleeding = 1
        if "faint" in raw_symptoms or "unconscious" in raw_symptoms: fainting = 1

    # Reconstruct text for display if empty but flags are set (Kiosk Fallback)
    if not raw_symptoms:
        parts = []
        if chest_pain: parts.append("Chest Pain")
        if breathing: parts.append("Breathing Issues")
        if bleeding: parts.append("Bleeding")
        if fainting: parts.append("Unconscious")
        raw_symptoms = ", ".join(parts)

    # 2. AI Model Prediction (Robust)
    # Map app variables to MIMIC model feature names
    features = {
        "heartrate": hr,
        "o2sat": spo2,
        "temperature": temp,
        "sbp": sys_bp,
        "dbp": dia_bp,
        "resprate": 18, # Default if not collected
        "pain": 5 if chest_pain else 0 # Simple heuristic mapping
    }
    
    ai_priority, ai_risk = predict(features)
    
    # 3. Heuristic Adjustments (Hybrid Intelligence - SAME AS KIOSK)
    bp_risk_adder = 0.0
    symptom_risk_adder = 0.0
    
    # Hypertensive Crisis / Shock
    if sys_bp > 180 or dia_bp > 120: bp_risk_adder += 0.4
    if sys_bp < 90: bp_risk_adder += 0.35
    
    # Critical Symptoms Overrides
    if chest_pain or breathing or fainting:
        symptom_risk_adder += 0.5 # Immediate High Risk base
        
    final_risk = min(ai_risk + bp_risk_adder + symptom_risk_adder, 1.0)
    
    # Silent Hypoxia Detection
    silent_risk = False
    if spo2 < 94 and hr > 100:
        silent_risk = True
        final_risk = max(final_risk, 0.85) # Force Critical
        
    # Priority Calculation (Strict Buckets)
    # 3 = Critical (Red): >= 80%
    # 2 = Urgent (Orange): >= 50%
    # 1 = Normal (Yellow): >= 30%
    # 0 = Low (Green): < 30%
    
    # Force Critical for Chest Pain/Breathing (Overrides Score to 90+)
    if chest_pain or breathing or "unconscious" in str(data.get("symptoms","")).lower():
        final_risk = max(final_risk, 0.95)

    if final_risk >= 0.8: 
        final_priority = 3
    elif final_risk >= 0.5: 
        final_priority = 2
    elif final_risk >= 0.3: 
        final_priority = 1
    else: 
        final_priority = 0
        
    # User Request: If 99%, MUST be top priority
    if final_risk >= 0.99: final_priority = 3

    # 4. Add to Database
    p = Patient.query.get(patient_id)
    if not p:
        p = Patient(national_id=patient_id)
        
    p.name = name
    p.age = age
    p.gender = gender
    p.chronic = bool(choice == 1 for choice in [chronic]) # simplified
    p.allergy = bool(choice == 1 for choice in [allergy])
    db.session.add(p)
    
    # Create Visit record
    visit = Visit(patient_id=patient_id)
    visit.hospital_id = data.get("hospital_id", 1)
    visit.priority = final_priority
    visit.score = int(final_risk * 100)
    visit.status = "Waiting"
    
    visit.hr = int(hr)
    visit.spo2 = int(spo2)
    visit.temp = float(temp)
    visit.sys_bp = int(sys_bp)
    visit.dia_bp = int(dia_bp)
    visit.symptoms_text = raw_symptoms.title() if raw_symptoms else "Triage Assessment"
    
    db.session.add(visit)
    db.session.commit()
    
    hospital_stats["total_entered"] += 1
    
    socketio.emit('new_emergency', {"id": visit.id, "patient": name, "priority": final_priority})

# ...



@app.route("/api/discharge", methods=["POST"])
def discharge_bed():
    data = request.json
    bid = data.get("bed_id")
    
    bed = Bed.query.get(bid)
    if bed:
        if bed.visit_id:
            visit = Visit.query.get(bed.visit_id)
            if visit:
                visit.status = "Discharged"
                p = Patient.query.get(visit.patient_id)
                if p:
                    import time
                    p.medical_history = (p.medical_history or "") + f" | Visit on {time.strftime('%Y-%m-%d')}: Discharged."
            hospital_stats["total_discharged"] += 1
        bed.visit_id = None
        bed.set_staff([])
        db.session.commit()
        return jsonify({"status": "discharged"})
    return jsonify({"error": "Bed not found"}), 404

@app.route("/api/staff/assign", methods=["POST"])
def assign_staff_to_bed():
    data = request.json
    bid = data.get("bed_id")
    staff_name = data.get("staff")
    bed = Bed.query.get(bid)
    if bed:
        staff_list = bed.get_staff()
        if staff_name not in staff_list:
            staff_list.append(staff_name)
        bed.set_staff(staff_list)
        if bed.visit_id:
            v = Visit.query.get(bed.visit_id)
            if v:
                pat = Patient.query.get(v.patient_id)
                if pat:
                    import time
                    pat.medical_history = (pat.medical_history or "") + f" | [{time.strftime('%H:%M')}] Assigned Staff: {staff_name}"
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Bed not found"}), 404

# -------------------------
# View Routes
# -------------------------



@app.route("/")
def index():
    return render_template("landing.html")

@app.route("/kiosk")
def kiosk():
    return render_template("kiosk.html")

# --- Volunteer Endpoints ---
active_volunteers = {}

@app.route("/api/volunteer/status", methods=["POST"])
def update_volunteer_status():
    data = request.json
    # Basic tracking in memory
    if current_user.is_authenticated:
        vid = current_user.id
    else:
        vid = "vol_demo"
        
    if data.get("status") == "offline":
        if vid in active_volunteers:
            del active_volunteers[vid]
    else:
        active_volunteers[vid] = {
            "lat": data.get("lat"),
            "lng": data.get("lng"),
            "last_seen": time.time()
        }
    return jsonify({"status": "ok"})

@app.route("/api/volunteer/check_alerts", methods=["GET"])
def check_volunteer_alerts():
    # Find any critical patient waiting for ambulance
    mission = Visit.query.filter(Visit.status.in_(["Waiting", "Dispatched"]), Visit.patient_lat != None).first()
    
    if mission:
        p = Patient.query.filter_by(national_id=mission.patient_id).first()
        return jsonify({
            "alert": {
                "id": mission.patient_id,
                "type": "CARDIAC ARREST" if mission.priority == 3 else "MEDICAL EMERGENCY",
                "lat": mission.patient_lat,
                "lng": mission.patient_lng,
                "distance": "0.4 km", 
                "details": f"{mission.symptoms_text} ({p.age}y {p.gender})" if p else mission.symptoms_text
            }
        })
    return jsonify({"alert": None})

@app.route("/api/volunteer/respond", methods=["POST"])
def volunteer_respond():
    # Acknowledge volunteer acceptance 
    return jsonify({"status": "accepted"})

@app.route("/api/volunteer/complete", methods=["POST"])
@login_required
def volunteer_complete():
    data = request.json
    patient_id = data.get("patient_id")
    details = data.get("details", "")
    vm = VolunteerMission(volunteer_id=current_user.id, patient_id=patient_id, status="Completed", details=details)
    db.session.add(vm)
    
    # Update the Visit status so patient portal knows it's finished
    v = Visit.query.filter_by(patient_id=str(patient_id)).order_by(Visit.id.desc()).first()
    if v:
        v.status = "Completed"
        
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/api/volunteer/reject", methods=["POST"])
@login_required
def volunteer_reject():
    data = request.json
    patient_id = data.get("patient_id")
    details = data.get("details", "")
    vm = VolunteerMission(volunteer_id=current_user.id, patient_id=patient_id, status="Rejected", details=details)
    db.session.add(vm)
    db.session.commit()
    return jsonify({"status": "ok"})

@app.route("/api/volunteer/history", methods=["GET"])
@login_required
def volunteer_history():
    missions = VolunteerMission.query.filter_by(volunteer_id=current_user.id).order_by(VolunteerMission.timestamp.desc()).all()
    history = []
    for m in missions:
        history.append({
            "id": m.id,
            "patient_id": m.patient_id,
            "status": m.status,
            "timestamp": m.timestamp,
            "details": m.details
        })
    return jsonify({"history": history})


@app.route("/api/ambulance/new", methods=["POST"])
def new_ambulance_update():
    # Handles BOTH new missions and status updates (Upsert)
    data = request.json
    amb_id = data.get("id", f"AMB-{random.randint(1000,9999)}")
    
    # 1. Check if exists
    amb = next((x for x in incoming_ambulances if x["id"] == amb_id), None)
    
    if amb:
        # UPDATE Existing
        if data.get("status"): amb["status"] = data.get("status")
        if data.get("symptoms"): amb["symptoms"] = data.get("symptoms")
        if data.get("destination"): amb["destination"] = data.get("destination")
        # Merge full data if provided (e.g. from Transmit)
        if "vitals" in data:
            amb["full_data"] = data
            # Recalculate risk if vitals provided
            triage_payload = {
                "patient_id": amb_id,
                "name": data.get("name"),
                "hr": data["vitals"].get("hr"),
                "spo2": data["vitals"].get("spo2"),
                "symptoms": data.get("symptoms"),
                "checklist": data.get("checklist", [])
            }
            process_triage_lite(amb, triage_payload)
            
        return jsonify({"status": "updated", "id": amb_id})
    else:
        # CREATE New
        new_entry = {
            "id": amb_id,
            "name": data.get("name", "Unknown"),
            "display_type": "AMB",
            "status": data.get("status", "En Route"),
            "arrival_time": "ETA 10m",
            "condition": "Stable", # Default
            "symptoms": data.get("symptoms", "Dispatch"),
            "destination": data.get("destination", ""),
            "full_data": data
        }
        incoming_ambulances.append(new_entry)
        return jsonify({"status": "created", "id": amb_id})

def process_triage_lite(amb, data):
    hr = float(data.get("hr", 80))
    spo2 = float(data.get("spo2", 98))
    raw = str(data.get("symptoms", "")).lower()
    checklist = data.get("checklist", [])
    if checklist: raw += " " + " ".join(checklist).lower()
    
    is_crit = False
    if "pain" in raw or "chest" in raw: is_crit = True
    if "breath" in raw or "sob" in raw: is_crit = True
    if "bleed" in raw or "trauma" in raw: is_crit = True
    if spo2 < 90 or hr > 130: is_crit = True
    
    amb["condition"] = "CRITICAL" if is_crit else "Stable"
    amb["symptoms"] = str(data.get("symptoms", "Assessment")).title()

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


# ═══════════════════════════════════════════════════════════
# OSRM REAL ROAD ROUTE API
# ═══════════════════════════════════════════════════════════
@app.route("/api/route", methods=["POST"])
def get_route():
    """Real road routing via OSRM. POST {start_lat, start_lng, end_lat, end_lng}"""
    data = request.json
    result = get_real_route(
        float(data.get("start_lat", MAIN_HOSPITAL_COORDS["lat"])),
        float(data.get("start_lng", MAIN_HOSPITAL_COORDS["lng"])),
        float(data.get("end_lat",   MAIN_HOSPITAL_COORDS["lat"])),
        float(data.get("end_lng",   MAIN_HOSPITAL_COORDS["lng"]))
    )
    return jsonify(result)


# ═══════════════════════════════════════════════════════════
# HUAWEI HEALTH / SMART WATCH INTEGRATION
# ═══════════════════════════════════════════════════════════
_wearable_data = {}   # patient_id -> latest vitals from watch

@app.route("/api/wearable/data", methods=["POST"])
def receive_wearable_data():
    """
    Receives real-time health data from Huawei Health Kit.
    The Huawei Health Android app sends POST requests to this endpoint.
    Required JSON: { device_id, hr, spo2, steps, lat?, lng?, alert_type? }
    alert_type options: 'fall_detected', 'irregular_heartbeat', 'low_spo2'
    """
    data = request.json or {}
    device_id = data.get("device_id", "unknown")
    hr  = data.get("hr",   0)
    spo2 = data.get("spo2", 100)
    lat  = data.get("lat")
    lng  = data.get("lng")
    alert_type = data.get("alert_type")

    # Store latest reading
    _wearable_data[device_id] = {
        "hr": hr, "spo2": spo2, "lat": lat, "lng": lng,
        "alert_type": alert_type, "timestamp": time.time()
    }

    # Auto-dispatch if critical health event detected
    if alert_type in ("fall_detected", "irregular_heartbeat") or hr > 160 or hr < 35 or spo2 < 88:
        if lat and lng:
            pid = f"WATCH-{random.randint(1000,9999)}"
            p = Patient(
                id=pid, name=f"Huawei Watch ({device_id})",
                status="Dispatched", priority=3, score=99,
                hr=hr, spo2=spo2,
                patient_lat=float(lat), patient_lng=float(lng),
                symptoms_text=f"Watch alert: {alert_type or 'Critical vitals'} | HR:{hr} SpO2:{spo2}%",
                arrival_time=time.time()
            )
            db.session.add(p)
            db.session.commit()
            return jsonify({"status": "dispatched", "patient_id": pid, "action": "auto_dispatch"})

    return jsonify({"status": "received", "device_id": device_id})

@app.route("/api/wearable/latest", methods=["GET"])
def get_wearable_latest():
    """Returns most recent wearable reading for display on dashboard."""
    return jsonify(_wearable_data)

@socketio.on('wearable_telemetry')
def handle_wearable_telemetry(data):
    # { mac_address: "XX:XX", hr: 80, spo2: 98, ecg: [...] }
    device = IoTDevice.query.filter_by(mac_address=data.get('mac_address')).first()
    if device and device.patient_id:
        p = Patient.query.get(device.patient_id)
        if p:
            if 'hr' in data: p.hr = data['hr']
            if 'spo2' in data: p.spo2 = data['spo2']
            db.session.commit()
            emit('vital_update', {'patient_id': p.id, 'hr': p.hr, 'spo2': p.spo2}, broadcast=True)

@socketio.on('cv_frame')
def handle_cv_frame(data):
    # data contains { image: 'base64...' }
    # Here we would run actual CV inference (like MediaPipe/YOLO)
    # For demo, we just echo a generic detection back.
    # In a real setup, we process data['image']
    import random
    mock_detections = ['CHEST PAIN', 'HEART ATTACK', 'BLEEDING', 'NORMAL']
    result = random.choice(mock_detections)
    emit('cv_result', {'prediction': result, 'confidence': 0.89 + (random.random() * 0.1)})


# ═══════════════════════════════════════════════════════════
# WEBRTC MESH NETWORK – SIGNALING SERVER
# ═══════════════════════════════════════════════════════════
import uuid as _uuid
_webrtc_peers   = {}   # peer_id -> {offer, answer, candidates, role}
_webrtc_messages = []  # shared broadcast messages

@app.route("/api/webrtc/register", methods=["POST"])
def webrtc_register():
    """Register as a peer and get a unique peer ID."""
    peer_id = str(_uuid.uuid4())[:8]
    role    = request.json.get("role", "peer")   # 'ambulance', 'nurse', 'volunteer'
    name    = request.json.get("name", "Unknown")
    _webrtc_peers[peer_id] = {
        "id": peer_id, "role": role, "name": name,
        "offer": None, "answer": None, "candidates": [],
        "joined": time.time()
    }
    return jsonify({"peer_id": peer_id, "total_peers": len(_webrtc_peers)})

@app.route("/api/webrtc/peers", methods=["GET"])
def webrtc_list_peers():
    """Returns list of active peers for discovery."""
    active = {k: {"id": v["id"], "role": v["role"], "name": v["name"]}
              for k, v in _webrtc_peers.items()}
    return jsonify({"peers": list(active.values()), "count": len(active)})

@app.route("/api/webrtc/signal", methods=["POST"])
def webrtc_signal():
    """
    SDP offer/answer exchange for WebRTC peer connection.
    POST { from_peer, to_peer, type: 'offer'|'answer'|'candidate', payload }
    """
    data      = request.json or {}
    from_peer = data.get("from_peer")
    to_peer   = data.get("to_peer")
    sig_type  = data.get("type")
    payload   = data.get("payload")

    if to_peer not in _webrtc_peers:
        return jsonify({"error": "target peer not found"}), 404

    target = _webrtc_peers[to_peer]
    if sig_type == "offer":
        target["offer"] = {"from": from_peer, "sdp": payload}
    elif sig_type == "answer":
        target["answer"] = {"from": from_peer, "sdp": payload}
    elif sig_type == "candidate":
        target["candidates"].append({"from": from_peer, "candidate": payload})

    return jsonify({"status": "delivered", "type": sig_type})

@app.route("/api/webrtc/poll", methods=["GET"])
def webrtc_poll():
    """Peer polls for pending signals (offer/answer/candidates)."""
    peer_id = request.args.get("peer_id")
    if peer_id not in _webrtc_peers:
        return jsonify({"error": "unknown peer"}), 404
    peer = _webrtc_peers[peer_id]
    result = {
        "offer":      peer.pop("offer",      None),
        "answer":     peer.pop("answer",     None),
        "candidates": peer.pop("candidates", [])
    }
    peer["offer"] = None
    peer["answer"] = None
    peer["candidates"] = []
    return jsonify(result)

@app.route("/api/webrtc/broadcast", methods=["POST"])
def webrtc_broadcast():
    """Send a text message to all mesh peers (fallback data channel)."""
    data = request.json or {}
    msg = {
        "from":    data.get("from_peer", "unknown"),
        "role":    data.get("role", "peer"),
        "text":    data.get("text", ""),
        "time":    time.time()
    }
    _webrtc_messages.append(msg)
    if len(_webrtc_messages) > 100:  # cap history
        _webrtc_messages.pop(0)
    return jsonify({"status": "broadcast", "recipients": len(_webrtc_peers)})

@app.route("/api/webrtc/messages", methods=["GET"])
def webrtc_messages():
    """Fetch all broadcast messages since a given timestamp."""
    since = float(request.args.get("since", 0))
    msgs  = [m for m in _webrtc_messages if m["time"] > since]
    return jsonify({"messages": msgs})

@app.route("/mesh")
def mesh_page():
    return render_template("mesh.html")


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    print(f"[SocketIO] Starting real-time server on port {port}...")
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
