import os

db_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "patients.db")
if os.path.exists(db_path):
    os.remove(db_path)
print("Deleted old database file.")

from app import app
from database import db
from db_models import User, Hospital, Tenant, Patient
import json

def seed_database():
    with app.app_context():
        # Drop and recreate all tables
        db.drop_all()
        db.create_all()

        print("Database tables created.")

        # 1. Create a Global Tenant (e.g., Global Health Org)
        t1 = Tenant(name="Global Health Network", country_code="GLO")
        db.session.add(t1)
        db.session.commit()

        # 2. Create Hospitals under this Tenant with custom policies
        default_policy = json.dumps({"critical_spo2": 92, "auto_dispatch": True})
        strict_policy = json.dumps({"critical_spo2": 94, "auto_dispatch": False})

        h1 = Hospital(name="Central City Hospital", tenant_id=t1.id, lat=34.0522, lng=-118.2437, capacity=200, available_beds=15, policies=default_policy)
        h2 = Hospital(name="Northside General", tenant_id=t1.id, lat=34.0622, lng=-118.2537, capacity=100, available_beds=5, policies=strict_policy)
        
        db.session.add_all([h1, h2])
        db.session.commit()

        # 3. Create Users (SuperAdmin and Hospital Staff)
        super_admin = User(email="super@resq.ai", name="Global Admin", role="superadmin")
        super_admin.set_password("admin123")

        h1_admin = User(email="admin@central.org", name="Central Admin", role="hospitaladmin", hospital_id=h1.id)
        h1_admin.set_password("admin123")

        h1_doc = User(email="doc@central.org", name="Dr. Smith", role="doctor", hospital_id=h1.id)
        h1_doc.set_password("doc123")

        h2_doc = User(email="doc@northside.org", name="Dr. Jones", role="doctor", hospital_id=h2.id)
        h2_doc.set_password("doc123")

        db.session.add_all([super_admin, h1_admin, h1_doc, h2_doc])
        db.session.commit()

        print("Database seeded successfully with Multi-Tenant data!")

if __name__ == "__main__":
    seed_database()
