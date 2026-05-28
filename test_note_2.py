import sys
sys.path.append('.')
from app import app, db, Patient, Visit, Bed, parse_visit_text
with app.app_context():
    bed = Bed.query.filter(Bed.visit_id.isnot(None)).first()
    if not bed:
        print('No occupied bed')
        sys.exit(0)
    visit = Visit.query.get(bed.visit_id)
    print('BEFORE symptoms:', repr(visit.symptoms_text))
    note_text = 'test note from script'
    author = 'Staff'
    import time
    timestamp = time.strftime('%H:%M')
    visit.symptoms_text = (visit.symptoms_text or '') + f'\nNOTE_START|{author}|{timestamp}|{note_text}|NOTE_END'
    db.session.commit()
    print('AFTER symptoms:', repr(visit.symptoms_text))
    clean, notes = parse_visit_text(visit.symptoms_text)
    print('PARSED NOTES:', notes)
