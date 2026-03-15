from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
import time

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(256))
    role = db.Column(db.String(20), default="doctor") # doctor, admin, nurse

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Hospital(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    capacity = db.Column(db.Integer, default=100)
    available_beds = db.Column(db.Integer, default=10)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "available_beds": self.available_beds
        }

class Patient(db.Model):
    id = db.Column(db.String(50), primary_key=True) # Using String ID to match "SOS-123" format
    name = db.Column(db.String(100))
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))
    chronic = db.Column(db.Boolean, default=False)
    allergy = db.Column(db.Boolean, default=False)
    
    # Tracking Status
    status = db.Column(db.String(50), default="Waiting") # Waiting, Dispatched, En Route to Hospital, Treated
    priority = db.Column(db.Integer, default=0)
    score = db.Column(db.Integer, default=0)
    
    # GPS Live Tracking
    patient_lat = db.Column(db.Float, nullable=True)
    patient_lng = db.Column(db.Float, nullable=True)
    ambulance_lat = db.Column(db.Float, nullable=True)
    ambulance_lng = db.Column(db.Float, nullable=True)
    assigned_hospital_id = db.Column(db.Integer, db.ForeignKey('hospital.id'), nullable=True)
    
    # Vitals
    hr = db.Column(db.Integer)
    spo2 = db.Column(db.Integer)
    temp = db.Column(db.Float)
    sys_bp = db.Column(db.Integer)
    dia_bp = db.Column(db.Integer)
    
    # Clinical Text
    symptoms_text = db.Column(db.String(500))

    arrival_time = db.Column(db.Float, default=time.time)
    
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "age": self.age,
            "chronic": self.chronic,
            "allergy": self.allergy,
            "status": self.status,
            "patient_lat": self.patient_lat,
            "patient_lng": self.patient_lng,
            "ambulance_lat": self.ambulance_lat,
            "ambulance_lng": self.ambulance_lng,
            "assigned_hospital_id": self.assigned_hospital_id
        }
