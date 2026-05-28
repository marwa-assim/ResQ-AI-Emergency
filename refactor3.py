import re
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Fix indentation error around old webhook
c = re.sub(r'\s*\}\)\s*return jsonify\(\{"status": "success"\}\)', '', c)

# Fix Visit not defined (make sure it is imported)
if 'from db_models import ' in c and 'Visit' not in c.split('from db_models import ')[1].split('\n')[0]:
    c = c.replace('from db_models import Patient, Bed, Hospital, Ambulance, User, Volunteer, IoTDevice', 'from db_models import Patient, Bed, Hospital, Ambulance, User, Volunteer, IoTDevice, Visit')

# Fix get_queue
c = re.sub(r'def get_queue\(\):.*?return jsonify\(\{"queue": patients\}\)', 'def get_queue():\n    patients = Visit.query.filter_by(status="Waiting").order_by(Visit.priority.desc(), Visit.score.desc()).all()\n    return jsonify({"queue": [v.to_dict() for v in patients]})', c, flags=re.DOTALL)

# Fix get_ambulances_real
c = re.sub(r'def get_ambulances_real\(\):.*?return jsonify\(\{"ambulances\": ambs, \"self\": slfs\}\)', 'def get_ambulances_real():\n    ambs = Ambulance.query.all()\n    slfs = Visit.query.filter_by(status="En Route").all()\n    return jsonify({"ambulances": [a.to_dict() for a in ambs], "self": [s.to_dict() for s in slfs]})', c, flags=re.DOTALL)

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(c)
print("Fixed app.py")
