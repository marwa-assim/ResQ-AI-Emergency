import sys
sys.path.append('.')
from app import app, db, Patient, Visit, parse_visit_text
with app.app_context():
    for v in Visit.query.all():
        if 'NOTE_START' in (v.symptoms_text or '') or 'Note' in (v.symptoms_text or ''):
            print('Visit ID:', v.id)
            print('Patient ID:', v.patient_id)
            print('Symptoms Text:', repr(v.symptoms_text))
            clean, notes = parse_visit_text(v.symptoms_text)
            print('Parsed Notes:', notes)
            print('-'*40)
