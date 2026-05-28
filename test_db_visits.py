import sys
sys.path.append('.')
from app import app, db, Patient, Visit
with app.app_context():
    for v in Visit.query.all():
        print(f'Visit ID: {v.id}, Patient ID: {v.patient_id}, Status: {v.status}, Priority: {v.priority}, Score: {v.score}')
