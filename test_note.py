import sys
sys.path.append('.')
from app import app, db, Patient, Visit, Bed
with app.app_context():
    bed = Bed.query.filter(Bed.visit_id.isnot(None)).first()
    if not bed:
        visit = Visit.query.first()
    else:
        visit = Visit.query.get(bed.visit_id)
    if not visit:
        print('No visits at all')
        sys.exit(0)
    pid = visit.patient_id
    print('Patient ID:', pid)
    patient = Patient.query.filter_by(national_id=pid).first()
    if patient:
        print('Patient found by national_id:', patient.name)
    else:
        print('Patient NOT found by national_id!')
