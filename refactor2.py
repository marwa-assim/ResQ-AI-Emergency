import re
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix get_queue
c = c.replace('Patient.query.filter_by(status="Waiting").order_by(Patient.priority.desc(), Patient.score.desc()).all()', 'Visit.query.filter_by(status="Waiting").order_by(Visit.priority.desc(), Visit.score.desc()).all()')
c = c.replace('patients = [p.to_dict() for p in patients]', 'patients = [v.to_dict() for v in patients]')

# Fix get_ambulances_real
c = re.sub(r'def get_ambulances_real\(\):.*?return jsonify\(\{\"ambulances\": ambs, \"self\": slfs\}\)', 'def get_ambulances_real():\n    ambs = Ambulance.query.all()\n    slfs = Visit.query.filter_by(status="En Route").all()\n    return jsonify({"ambulances": [{"id": a.id, "lat": a.lat, "lng": a.lng, "status": a.status} for a in ambs], "self": [s.to_dict() for s in slfs]})', c, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Done fixing app.py")
