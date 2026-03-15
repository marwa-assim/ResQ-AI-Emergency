from flask import Flask, render_template, request, jsonify, redirect
import math
from model import predict
from database import db
from db_models import User, Patient, Hospital
from auth import auth_bp
from ai_copilot import copilot
from location_service import haversine_distance, calculate_eta, MAIN_HOSPITAL_COORDS, get_real_route
from flask_login import LoginManager, current_user, login_required
import time
import random
import os

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

db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

app.register_blueprint(auth_bp)

# Initialize DB with Admin User
with app.app_context():
    db.create_all()
    if not User.query.filter_by(email='admin@resq.ai').first():
        admin = User(email='admin@resq.ai', name='System Admin', role='admin')
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        
    # Initialize Demo Hospitals if none exist
    if Hospital.query.count() == 0:
        h1 = Hospital(name="Salmaniya Medical Complex", lat=26.2137, lng=50.5794, capacity=1200, available_beds=145)
        h2 = Hospital(name="King Hamad University Hospital", lat=26.2690, lng=50.6139, capacity=400, available_beds=85)
        h3 = Hospital(name="BDF Royal Medical Services", lat=26.1107, lng=50.5367, capacity=500, available_beds=50)
        db.session.add_all([h1, h2, h3])
        db.session.commit()
        print("[DB INIT] Added 3 Demo Hospitals to DB.")


# -------------------------
# API Routes
# -------------------------

# Expanded Staff Pool (Arabic/English Mixed)
DOCTORS = ["Dr. Ahmed", "Dr. Sarah", "Dr. Ali", "Dr. Fatima", "Dr. House", "Dr. Kareem", "Dr. Noor", "Dr. Ziad"]
NURSES = ["Nurse Layla", "Nurse Omar", "Nurse Huda", "Nurse Youssef", "Nurse Joy", "Nurse Samia", "Nurse Tarek", "Nurse Mona"]

# Beds - Localized Naming
beds = [
    {"id": 1, "label": "ER Room 1", "patient": None, "staff": []},
    {"id": 2, "label": "ER Room 2", "patient": None, "staff": []},
    {"id": 3, "label": "ER Room 3", "patient": None, "staff": []},
    {"id": 4, "label": "Trauma A",   "patient": None, "staff": []},
    {"id": 5, "label": "Trauma B",   "patient": None, "staff": []},
    {"id": 6, "label": "Isolation",  "patient": None, "staff": []}
]

incoming_ambulances = [] # List of ambulance objects
incoming_self = [] # List of self-transport objects
volunteers = [] # List of active volunteers
# Structure: {id: "vol-1", status: "offline", lat: 0, lng: 0, alert: None}

def generate_arabic_name():
    first_names = ["Mohammed", "Ahmed", "Ali", "Omar", "Youssef", "Ibrahim", "Hassan", "Fatima", "Maryam", "Aya", "Sarah", "Huda", "Noor", "Layla"]
    last_names = ["Al-Sayed", "Al-Masri", "Hassan", "Ali", "Ibrahim", "Mahmoud", "Youssef", "Abdallah", "Saleh"]
    return f"{random.choice(first_names)} {random.choice(last_names)}"

@app.route("/ambulance")
@login_required
def ambulance_view():
    return render_template("ambulance.html")

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

@app.route("/admin")
@login_required
def admin_view():
    if current_user.role != 'admin':
        return redirect("/")
    hospitals = [h.to_dict() for h in Hospital.query.all()]
    return render_template("admin.html", hospitals=hospitals)

@app.route("/api/hospitals", methods=["GET"])
def get_hospitals():
    hospitals = [h.to_dict() for h in Hospital.query.all()]
    return jsonify(hospitals)

# -------------------------
# Helper Functions
# -------------------------
def assign_random_staff(bed):
    dr = random.choice(DOCTORS)
    rn = random.choice(NURSES)
    dr2 = random.choice(DOCTORS)
    if random.random() > 0.7: bed["staff"] = [dr, rn, dr2]
    else: bed["staff"] = [dr, rn]

# Helper for Names
def generate_arabic_name():
    f = ["Ahmed", "Mohamed", "Ali", "Fatima", "Noor", "Sara", "Khalid", "Omar", "Layla"]
    l = ["Al-Saud", "Al-Harbi", "Al-Otaibi", "Khan", "Malik", "Salem"]
    return f"{random.choice(f)} {random.choice(l)}"



@app.route("/api/incoming_self", methods=["POST"])
def add_self_patient():
    data = request.json
    entry = {
        "id": f"SLF-{random.randint(100,999)}",
        "name": data.get("name") or generate_arabic_name(),
        "symptoms": data.get("symptoms", "CHECK-IN"),
        "arrival_time": f"ETA {data.get('eta', '15')}m",
        "full_data": data,
        "type": "self"
    }
    incoming_self.append(entry)
    return jsonify({"status": "notified", "id": entry["id"]})

    incoming_self.append(entry)
    return jsonify({"status": "notified", "id": entry["id"]})

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
    plan = copilot.generate_plan(text, priority)
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
            "Keep responses concise, empathetic, and structured (numbered steps when giving instructions). "
            "Do not diagnose, but DO provide clear first-aid and triage guidance. "
            "IMPORTANT: Automatically detect the language of the user's message and ALWAYS respond in that SAME language. "
            "If the user writes in Arabic, respond in Arabic. If in French, respond in French. Match their language exactly."
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
            "gemini-flash-lite-latest",   # highest free quota, confirmed working
            "gemini-2.0-flash-lite-001",  # flash-lite stable release
            "gemini-2.0-flash",           # fallback
        ]
        for model_name in models_to_try:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={GEMINI_KEY}"
                req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(req, timeout=15) as resp:
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

    return jsonify({"reply": reply})


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
    plan = copilot.generate_plan(text, 2)
    plan["patient_id"] = patient_id
    return jsonify(plan)

# Dispatch Queue for Ambulance Polling
pending_dispatches = []

@app.route("/api/emergency/dispatch", methods=["POST"])
def dispatch_emergency():
    # SOS Signal
    data = request.json
    lat = data.get("lat", 26.2235)
    lng = data.get("lng", 50.5876)
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

    p = Patient(
        id=f"SOS-{random.randint(100,999)}",
        name="EMERGENCY CALLER",
        age=30, # Default or Unknown
        gender="U", # Unknown
        status="Dispatched",
        priority=3, # Assumed Critical
        score=100,
        patient_lat=float(lat),
        patient_lng=float(lng),
        arrival_time=time.time()
    )
    
    # Store full telemetry in a note or dedicated field? 
    # For now, we reuse the Patient Model but we might lose 'full_data' flexible dict if not careful.
    # In a real app we'd have a Telemetry table.
    # Let's map key fields to the Patient model.
    # We will repurpose 'chronic'/'allergy' for now or just trust the ID.
    
    db.session.add(p)
    db.session.commit()
    
    entry = {
        "id": p.id,
        "name": p.name,
        "age": "UNK",
        "hr": hr, 
        "condition": condition, 
        "symptoms": symptoms,
        "arrival_time": "DISPATCHED",
        "full_data": { 
             "name": "Unknown (SOS)", "hr": hr, "spo2": 90, 
             "source": source, "chest_pain": 1, "breathing": 1 
        } 
    }
    
    # 1. Add to Dashboard Queue (Legacy - REMOVED, now query DB)
    # incoming_ambulances.insert(0, entry) # REMOVED
    
    # 2. Add to Pending Dispatch Queue (For Driver App - REMOVED, query DB)
    # pending_dispatches.append(entry) # REMOVED
    
    # ---------------------------
    # VOLUNTEER ALERT LOGIC
    # ---------------------------
    # Simple Geofence Sim: If volunteer is Active, send alert
    for vol in volunteers:
        if vol.get("status") == "active":
            # In a real app, calculate Haversine distance.
            # Here, we assume "Nearby" assignment logic based on geography.
            vol["alert"] = {
                "id": entry["id"],
                "lat": lat,
                "lng": lng,
                "symptoms": symptoms,
                "distance": "0.4 km"
            }
            print(f"Volunteer Alert Sent to {vol['id']}")

    return jsonify({"status": "dispatched", "id": entry["id"]})



@app.route("/api/ambulance/check_dispatch", methods=["GET"])
def check_dispatch():
    # Find oldest Dispatched patient
    mission = Patient.query.filter_by(status="Dispatched").order_by(Patient.arrival_time.asc()).first()
    
    if mission:
        return jsonify({
            "dispatch": True, 
            "mission": {
                "id": mission.id,
                "name": mission.name,
                "lat": mission.patient_lat or 26.2235, 
                "lng": mission.patient_lng or 50.5876,
                "symptoms": "Emergency Dispatch",
                "condition": "Critical"
            }
        })
    return jsonify({"dispatch": False})

@app.route("/api/ambulance/status/<amb_id>", methods=["GET"])
def get_ambulance_status(amb_id):
    # Search in DB
    p = Patient.query.get(amb_id)
    if p:
        hosp_lat = None
        hosp_lng = None
        dest_name = "Hospital"
        
        if p.assigned_hospital_id:
            h = Hospital.query.get(p.assigned_hospital_id)
            if h:
                hosp_lat = h.lat
                hosp_lng = h.lng
                dest_name = h.name
                
        # Map to legacy format + new tracking fields
        return jsonify({
            "id": p.id,
            "name": p.name,
            "status": p.status,
            "condition": "Critical" if p.priority == 3 else "Stable",
            "ambulance_lat": p.ambulance_lat,
            "ambulance_lng": p.ambulance_lng,
            "hosp_lat": hosp_lat,
            "hosp_lng": hosp_lng,
            "destination": dest_name,
            "full_data": {} # Todo: Telemetry
        })
    return jsonify({"error": "Not Found", "status": "UNKNOWN"}), 404

@app.route("/api/patient/tracking/<patient_id>", methods=["GET"])
def get_patient_tracking(patient_id):
    p = Patient.query.get(patient_id)
    if p:
        hosp_lat = None
        hosp_lng = None
        dest_name = "Hospital"
        
        if p.assigned_hospital_id:
            h = Hospital.query.get(p.assigned_hospital_id)
            if h:
                hosp_lat = h.lat
                hosp_lng = h.lng
                dest_name = h.name
                
        return jsonify({
            "id": p.id,
            "status": p.status,
            "ambulance_lat": p.ambulance_lat,
            "ambulance_lng": p.ambulance_lng,
            "patient_lat": p.patient_lat,
            "patient_lng": p.patient_lng,
            "hospital_id": p.assigned_hospital_id,
            "hosp_lat": hosp_lat,
            "hosp_lng": hosp_lng,
            "destination": dest_name
        })
    return jsonify({"error": "Not Found"}), 404

@app.route("/api/ambulance/update", methods=["POST"])
def update_ambulance():
    data = request.json
    amb_id = data.get("id")
    status = data.get("status")
    
    # The "Ambulance" updates the Patient record's state directly
    p = Patient.query.get(amb_id)
    if p:
        p.status = status
        
        if "lat" in data and "lng" in data:
            p.ambulance_lat = float(data["lat"])
            p.ambulance_lng = float(data["lng"])
            
        if "hospital_id" in data:
            p.assigned_hospital_id = data["hospital_id"]
            
        db.session.commit()
        if status: 
            p.status = status
            db.session.commit()
        return jsonify({"status": "updated", "ambulance": {"id": p.id, "status": p.status}})
    return jsonify({"error": "Ambulance not found"}), 404

@app.route("/api/ambulance/new", methods=["POST"])
def new_ambulance_vitals():
    data = request.json
    amb_id = data.get("id")
    
    p = Patient.query.get(amb_id)
    if p:
        p.name = data.get("name", p.name)
        vitals = data.get("vitals", {})
        p.hr = int(vitals.get("hr", p.hr or 80))
        p.spo2 = int(vitals.get("spo2", p.spo2 or 98))
        p.symptoms_text = data.get("symptoms", "")
        # Update status to Heads Up (en-route with data)
        p.status = data.get("status", "HEADS UP")
        db.session.commit()
        return jsonify({"status": "received"})
    return jsonify({"error": "Patient not found"}), 404

@app.route("/api/ambulance/arrive", methods=["POST"])
def arrive_ambulance():
    amb_id = request.json.get("id")
    
    # 1. Find Patient in DB
    p = Patient.query.get(amb_id)
    if not p:
        return jsonify({"error": "Entry not found"}), 404
        
    # We use their existing vitals, or defaults if they didn't send them
    hr = p.hr or 80
    spo2 = p.spo2 or 98
    sys_bp = p.sys_bp or 120
    dia_bp = p.dia_bp or 80
    temp = p.temp or 37.0
    
    # 2. Run MindSpore AI Prediction
    features = {
        "heartrate": float(hr),
        "o2sat": float(spo2),
        "temperature": float(temp),
        "sbp": float(sys_bp),
        "dbp": float(dia_bp),
        "resprate": 18, 
        "pain": 5 if p.symptoms_text else 0 
    }
    
    final_priority, ai_risk = predict(features)
    
    # Force Critical if SOS Dispatch
    if "SOS" in str(p.id) or ai_risk > 0.8:
        final_priority = 3
        ai_risk = max(ai_risk, 0.9)
    
    p.priority = final_priority
    p.score = int(ai_risk * 100)
        
    # Ensure status is Waiting so they show up in ER Queue!
    p.status = "Waiting"
    db.session.commit()
        
    return jsonify({"status": "arrived"})

# Override get_ambulances to use real list (MERGED)
@app.route("/api/ambulances_real")
def get_ambulances_real():
    # Merge lists for the display ticker
    # Add a 'type' flag visually
    display_list = []
    for a in incoming_ambulances:
        a["display_type"] = "AMB"
        display_list.append(a)
    for s in incoming_self:
        # Clone to avoid mutating original
        s_display = s.copy()
        s_display["display_type"] = "CAR"
        s_display["condition"] = "Incoming"
        s_display["hr"] = "--"
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

@app.route("/api/triage", methods=["POST"])
def triage_patient():
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
        p = Patient(id=patient_id, name=name, age=age, gender=gender)
    else:
        p.age = age # Update age
    
    p.chronic = bool(chronic)
    p.allergy = bool(allergy)
    # p.visits += 1 # If we tracked visits
    db.session.add(p)
    db.session.commit()

    # 2. AI Model Prediction
    # Map app variables to MIMIC model feature names
    features = {
        "heartrate": hr,
        "o2sat": spo2,
        "temperature": temp,
        "sbp": sys_bp,
        "dbp": dia_bp,
        "resprate": 18, # Default if not collected in Kiosk
        "pain": 5 if chest_pain else 0 # Simple heuristic mapping
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

    # 4. Update DB with Final Risk/Priority
    p = Patient.query.get(patient_id)
    if not p:
        p = Patient(id=patient_id)
        db.session.add(p)
        
    p.name = name
    p.age = age
    p.gender = "M" # Default or from input if available
    
    p.priority = final_priority
    p.score = int(final_risk * 100)
    p.status = "Waiting" 
    
    # SAVE VITALS
    p.hr = int(hr)
    p.spo2 = int(spo2)
    p.temp = float(temp)
    p.sys_bp = int(sys_bp)
    p.dia_bp = int(dia_bp)
    
    # SAVE TEXT
    parts = []
    if chest_pain: parts.append("Chest Pain")
    if breathing: parts.append("Breathing Issues")
    if bleeding: parts.append("Bleeding")
    if fainting: parts.append("Unconscious")
    if not parts: parts.append("General Checklist")
    p.symptoms_text = ", ".join(parts)
    
    db.session.commit()

    # Create response entry (from DB obj to ensure consistency)
    patient_entry = {
         "id": p.id,
         "name": p.name,
         "priority": p.priority,
         "score": p.score,
         # ... minimal data for response ...
    }
    
    # queue.append(...) # REMOVED
    # queue.sort(...)   # REMOVED
    
    hospital_stats["total_entered"] += 1
    
    return jsonify({
        "status": "triaged", 
        "patient": patient_entry,
        "risk_level": "Critical" if final_risk > 0.8 else "Normal",
        "position": Patient.query.filter_by(status='Waiting').count(), # Real Count
        "queue_length": Patient.query.filter_by(status='Waiting').count()
    })

@app.route("/api/queue")
def get_queue():
    # Fetch from Real DB
    patients = Patient.query.filter_by(status="Waiting").order_by(Patient.priority.desc(), Patient.score.desc()).all()
    output = []
    for p in patients:
        # Reconstruct dict for frontend
        output.append({
            "id": p.id,
            "name": p.name,
            "age": p.age,
            "gender": p.gender, 
            "priority": p.priority,
            "score": p.score,
            "arrival_time": p.arrival_time,
            "symptoms": { "Chronic": p.chronic, "Allergy": p.allergy },
            "symptoms_text": p.symptoms_text,
            "vitals": {
                "hr": p.hr,
                "spo2": p.spo2,
                "bp": f"{p.sys_bp}/{p.dia_bp}"
            }
        })
    return jsonify(output)

@app.route("/api/beds")
def get_beds():
    return jsonify(beds)

@app.route("/api/assign", methods=["POST"])
def assign_bed():
    # Payload: { "patient_id": "...", "bed_id": 1 }
    data = request.json
    pid = data.get("patient_id")
    bid = data.get("bed_id")
    
    # 1. Find Patient in DB
    patient = Patient.query.get(pid)
    if not patient:
         return jsonify({"error": "Patient not found"}), 404
         
    if patient.status != "Waiting":
         return jsonify({"error": "Patient not in waiting queue (Status: " + patient.status + ")"}), 400
        
    # 2. Find Bed
    bed = next((b for b in beds if b["id"] == bid), None)
    if not bed:
        return jsonify({"error": "Bed not found"}), 404
        
    if bed["patient"]:
        return jsonify({"error": "Bed occupied"}), 400
        
    # 3. Move Patient (Update Status)
    # In a full normalized DB, we'd have a 'beds' table. 
    # For hybrids, we update the Patient status and link the in-memory Bed to a simple dict.
    
    patient.status = "Treated"
    db.session.commit()
    
    # Update In-Memory Bed (for Dashboard display)
    # Update In-Memory Bed (for Dashboard display)
    bed["patient"] = {
        "id": patient.id,
        "name": patient.name,
        "priority": patient.priority,
        "arrival_time": patient.arrival_time,
        "age": patient.age,
        "gender": patient.gender,
        "symptoms_text": patient.symptoms_text,
        "vitals": {
            "hr": patient.hr,
            "spo2": patient.spo2,
            "bp": f"{patient.sys_bp}/{patient.dia_bp}"
        }
    }
    
    # queue.remove(patient) # REMOVED
    
    # 4. Auto-Assign 2-3 Staff from Large Pool
    assign_random_staff(bed)
        
    return jsonify({"status": "assigned", "bed": bed})

@app.route("/api/notes", methods=["POST"])
def add_note():
    data = request.json
    pid = data.get("patient_id")
    note_text = data.get("note")
    
    if not pid or not note_text:
        return jsonify({"error": "Missing patient_id or note text"}), 400
        
    # Find the bed holding this patient
    target_bed = next((b for b in beds if b["patient"] and b["patient"]["id"] == pid), None)
    
    if target_bed:
        if "notes" not in target_bed["patient"]:
            target_bed["patient"]["notes"] = []
            
        import datetime
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        
        target_bed["patient"]["notes"].append({
            "text": note_text,
            "author": getattr(current_user, 'name', 'Chief Medical Officer') if current_user.is_authenticated else 'Chief Medical Officer',
            "time": current_time
        })
        
        return jsonify({"status": "success"})
        
    return jsonify({"error": "Patient not found in any bed"}), 404

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
    waiting = Patient.query.filter_by(status='Waiting').all()
    for p in waiting:
        if p.priority in triage_counts: triage_counts[p.priority] += 1
        wait_times.append(now - p.arrival_time)
        
    # Active Beds (Treated) is tricky without a 'Bed' model linked.
    # We will assume 'Treated' status means in bed for now, or check beds list (which is in-memory for beds still)
    # Hybrid Approach: Keep beds in memory for fast assignment, but sync patient data
    
    beds_occupied = 0
    for b in beds:
        if b["patient"]:
            beds_occupied += 1
            # triage_counts[b["patient"]["priority"]] += 1 # Don't double count if we only care about waiting stats?
            # actually dashboard usually shows total active
            pass

    avg_wait = sum(wait_times) / len(wait_times) if wait_times else 0
    
    # Saturation Calculation (User Request: Waiting + Beds / Total Beds)
    # Total Beds = 6
    TOTAL_BEDS = 6
    waiting_count = Patient.query.filter_by(status='Waiting').count()
    current_load = waiting_count + beds_occupied
    
    # Saturation % = (Current Load / Capacity) * 100
    saturation_risk = int((current_load / TOTAL_BEDS) * 100)
    
    # Capacity Forecast (1 Hour)
    # How many *more* can we take?
    # Logic: (Avg Discharges/Hr * 1hr) - (Current Deficit)
    # Discharge Rate (per min)
    uptime_mins = max(1, (now - hospital_stats["start_time"])/60)
    discharge_rate_hr = (hospital_stats["total_discharged"] / uptime_mins) * 60
    
    # Current available now = 6 - Beds Occupied (ignore queue for "Physical Capacity")
    physical_free = TOTAL_BEDS - beds_occupied
    
    # Forecasted Capacity = Physical Free + Expected Discharges
    # But if Queue > 0, they eat that capacity first.
    expected_capacity = (physical_free + discharge_rate_hr) - waiting_count
    
    return jsonify({
        "total_entered": hospital_stats["total_entered"],
        "discharged": hospital_stats["total_discharged"],
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

@app.route("/api/incoming_self", methods=["POST"])
def incoming_self_route():
    data = request.json
    lat = data.get("lat", 26.2235)
    lng = data.get("lng", 50.5876)
    
    # 1. Use Huawei Map Kit to get real route ETA from Hospital
    route = get_real_route(MAIN_HOSPITAL_COORDS["lat"], MAIN_HOSPITAL_COORDS["lng"], lat, lng)
    eta_mins = route.get("duration_minutes", 10)
    
@app.route("/api/emergency/dispatch", methods=["POST"])
def emergency_dispatch():
    """Second dispatch endpoint - saves GPS coordinates like the primary one."""
    data = request.json
    lat = data.get("lat") or data.get("latitude", 26.2235)
    lng = data.get("lng") or data.get("longitude", 50.5876)

    # Get real route ETA from hospital
    route = get_real_route(MAIN_HOSPITAL_COORDS["lat"], MAIN_HOSPITAL_COORDS["lng"], float(lat), float(lng))
    eta_mins = route.get("duration_minutes", 10)

    # Create Emergency Patient Record WITH GPS
    pid = f"SOS-{random.randint(1000, 9999)}"
    p = Patient(
        id=pid,
        name="Emergency Caller",
        status="Dispatched",
        priority=3,
        score=99,
        patient_lat=float(lat),
        patient_lng=float(lng),
        arrival_time=time.time()
    )
    db.session.add(p)
    db.session.commit()

    incoming_ambulances.append({
        "id": pid,
        "name": "Emergency Caller",
        "display_type": "AMB",
        "status": "Dispatched",
        "arrival_time": f"ETA {eta_mins}m",
        "condition": "Critical",
        "symptoms": "SOS Request",
        "destination": "Trauma Center"
    })
    
    return jsonify({
        "status": "success",
        "id": pid,
        "eta": eta_mins,
        "route_polyline": route.get("polyline")
    })

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
        p = Patient(id=patient_id)
        
    p.name = name
    p.age = age
    p.gender = gender
    p.status = "Waiting"
    p.priority = final_priority
    p.score = int(final_risk * 100)
    p.arrival_time = time.time()
    
    # Store Symptoms
    p.symptoms_text = raw_symptoms.title() if raw_symptoms else "Triage Assessment"
    p.chronic = bool(choice == 1 for choice in [chronic]) # simplified
    p.allergy = bool(choice == 1 for choice in [allergy])
    
    p.hr = int(hr)
    p.spo2 = int(spo2)
    p.sys_bp = int(sys_bp)
    p.dia_bp = int(dia_bp)
    
    db.session.add(p)
    db.session.commit()
    
    hospital_stats["total_entered"] += 1

# ...



@app.route("/api/discharge", methods=["POST"])
def discharge_bed():
    # Payload: { "bed_id": 1 }
    data = request.json
    bid = data.get("bed_id")
    
    bed = next((b for b in beds if b["id"] == bid), None)
    if bed:
        if bed["patient"]:
            hospital_stats["total_discharged"] += 1 # Track throughput
            
        bed["patient"] = None
        bed["staff"] = []
        return jsonify({"status": "discharged"})
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
    # For demo purposes, we alert volunteers if there is ANY Dispatched/Waiting patient with GPS
    patient = Patient.query.filter(Patient.status.in_(["Waiting", "Dispatched"]), Patient.patient_lat != None).first()
    
    if patient:
        return jsonify({
            "alert": {
                "id": patient.id,
                "type": "CARDIAC ARREST" if patient.priority == 3 else "MEDICAL EMERGENCY",
                "lat": patient.patient_lat,
                "lng": patient.patient_lng,
                "distance": "0.4 km", # In a real app, calculate true distance from active_volunteers[vid]
                "details": f"{patient.symptoms_text} ({patient.age}y {patient.gender})"
            }
        })
    return jsonify({"alert": None})

@app.route("/api/volunteer/respond", methods=["POST"])
def volunteer_respond():
    # Acknowledge volunteer acceptance 
    return jsonify({"status": "accepted"})


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


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)

