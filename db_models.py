from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
import time
import json

class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False) # e.g., "United States", "UK NHS"
    country_code = db.Column(db.String(10))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default="doctor") # superadmin, hospitaladmin, doctor, nurse, volunteer
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True) # None for superadmin or volunteer
    phone = db.Column(db.String(20), nullable=True)
    license_id = db.Column(db.String(50), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.Float, nullable=True)

    # Volunteer specific fields
    is_volunteer = db.Column(db.Boolean, default=False)
    certificate_url = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    is_on_duty = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class RolePolicy(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), unique=True, nullable=False)
    can_manage_users = db.Column(db.Boolean, default=False)
    can_dispatch_fleet = db.Column(db.Boolean, default=False)
    can_edit_vitals = db.Column(db.Boolean, default=False)
    can_view_analytics = db.Column(db.Boolean, default=False)
    can_manage_facilities = db.Column(db.Boolean, default=False)

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey('tenant.id'), nullable=True)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, default=100)
    
    # Dynamic Beds count
    er_beds_count = db.Column(db.Integer, default=10)
    trauma_beds_count = db.Column(db.Integer, default=5)
    isolation_beds_count = db.Column(db.Integer, default=5)
    
    policies = db.Column(db.Text, default='{}') 
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "tenant_id": self.tenant_id,
            "lat": self.lat,
            "lng": self.lng,
            "er_beds_count": self.er_beds_count,
            "trauma_beds_count": self.trauma_beds_count,
            "isolation_beds_count": self.isolation_beds_count,
            "policies": self.policies
        }

class Patient(UserMixin, db.Model): 
    national_id = db.Column(db.String(50), primary_key=True) # Unique identifier CPR
    name = db.Column(db.String(100))
    password_hash = db.Column(db.String(256), nullable=True) # For portal login
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    country = db.Column(db.String(100), nullable=True)
    
    # Medical History International Standard
    blood_type = db.Column(db.String(10), nullable=True)
    medical_history = db.Column(db.Text, nullable=True)
    chronic = db.Column(db.Boolean, default=False)
    allergy = db.Column(db.Boolean, default=False)
    heart_issues = db.Column(db.Boolean, default=False)
    blood_pressure_issues = db.Column(db.Boolean, default=False)
    
    # Personal Info
    marital_status = db.Column(db.String(50), nullable=True)
    children_count = db.Column(db.Integer, default=0)
    
    # Emergency Contact
    emergency_contact_name = db.Column(db.String(100), nullable=True)
    emergency_contact_phone = db.Column(db.String(20), nullable=True)
    emergency_contact_email = db.Column(db.String(120), nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash: return False
        return check_password_hash(self.password_hash, password)
        
    def get_id(self):
        return self.national_id

class Visit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.String(50), db.ForeignKey('patient.national_id'), nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True)
    
    # Tracking Status
    status = db.Column(db.String(50), default="Waiting") # Waiting, Dispatched, En Route, Treated, Admitted
    priority = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    
    # GPS Live Tracking
    patient_lat = db.Column(db.Float, nullable=True)
    patient_lng = db.Column(db.Float, nullable=True)
    ambulance_id = db.Column(db.Integer, db.ForeignKey('ambulance.id'), nullable=True)
    
    # Vitals at time of visit
    hr = db.Column(db.Integer)
    spo2 = db.Column(db.Integer)
    temp = db.Column(db.Float)
    sys_bp = db.Column(db.Integer)
    dia_bp = db.Column(db.Integer)
    
    symptoms_text = db.Column(db.String(500))
    arrival_time = db.Column(db.Float, default=time.time)

    def to_dict(self):
        return {
            "id": self.id,
            "patient_id": self.patient_id,
            "status": self.status,
            "priority": self.priority,
            "patient_lat": self.patient_lat,
            "patient_lng": self.patient_lng,
            "hr": self.hr, "spo2": self.spo2, "sys_bp": self.sys_bp, "dia_bp": self.dia_bp, "temp": self.temp,
            "symptoms_text": self.symptoms_text,
            "arrival_time": self.arrival_time
        }

class Bed(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=False)
    bed_type = db.Column(db.String(50)) # ER, Trauma, Isolation
    label = db.Column(db.String(50)) # ER-1, T-1
    visit_id = db.Column(db.Integer, db.ForeignKey('visit.id'), nullable=True)
    
    # Store IDs of assigned staff as JSON string
    assigned_staff_ids = db.Column(db.Text, default='[]')
    
    def set_staff(self, staff_list):
        self.assigned_staff_ids = json.dumps(staff_list)
        
    def get_staff(self):
        return json.loads(self.assigned_staff_ids)

class Ambulance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.String(50), unique=True, nullable=False)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True)
    status = db.Column(db.String(50), default="Offline") 
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    crew_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    last_maintenance = db.Column(db.Float, nullable=True)
    equipment_status = db.Column(db.String(100), default="Operational")

class Drone(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    call_sign = db.Column(db.String(50), nullable=False, unique=True)
    status = db.Column(db.String(50), default='Docked')
    battery = db.Column(db.Integer, default=100)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    payload = db.Column(db.String(100), default='AED Defibrillator')
    video_url = db.Column(db.String(255), nullable=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True)

class IoTDevice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    mac_address = db.Column(db.String(50), unique=True, nullable=False)
    device_type = db.Column(db.String(100), default="ResQ Band")
    patient_id = db.Column(db.String(50), db.ForeignKey('patient.national_id'), nullable=True)
    hr = db.Column(db.Integer, nullable=True)
    spo2 = db.Column(db.Integer, nullable=True)
    last_sync = db.Column(db.Float, nullable=True)
    battery_level = db.Column(db.Integer, default=100)

class VolunteerMission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    volunteer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    patient_id = db.Column(db.String(50))
    status = db.Column(db.String(50)) # 'Completed', 'Rejected'
    timestamp = db.Column(db.Float, default=time.time)
    details = db.Column(db.Text)
