import re

with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix discharge_bed
new_discharge = """@app.route("/api/discharge", methods=["POST"])
def discharge_bed():
    data = request.json
    bid = data.get("bed_id")
    bed = Bed.query.get(bid)
    if bed and bed.visit_id:
        v = Visit.query.get(bed.visit_id)
        if v:
            v.status = "Discharged"
            v.score = 0
        bed.visit_id = None
        bed.assigned_staff_ids = '[]'
        db.session.commit()
        socketio.emit('bed_update', {"bed_id": bed.id, "patient_id": None})
        return jsonify({"status": "success"})
    return jsonify({"error": "Bed not found or empty"}), 404"""

content = re.sub(r'@app\.route\("/api/discharge", methods=\\["POST"\\]\).*?return jsonify\(\{"status": "success"\}\)', new_discharge, content, flags=re.DOTALL)

# Fix notes route since replace_file_content failed
new_notes = """@app.route("/api/notes", methods=["POST"])
def add_note():
    data = request.json
    pid = data.get("patient_id")
    note_text = data.get("note")
    if not pid or not note_text:
        return jsonify({"error": "Missing data"}), 400
    visit = Visit.query.filter_by(patient_id=pid).order_by(Visit.id.desc()).first()
    if visit:
        visit.symptoms_text = (visit.symptoms_text or "") + f"\\nNote: {note_text}"
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"error": "Not found"}), 404"""
content = re.sub(r'@app\.route\("/api/notes", methods=\\["POST"\\]\).*?return jsonify\(\{"error": "Patient not found in any bed"\}\), 404', new_notes, content, flags=re.DOTALL)

# Fix IoT Webhook
new_iot = """@app.route("/api/iot/webhook", methods=["POST"])
def iot_webhook():
    data = request.json
    mac = data.get("mac_address")
    device = IoTDevice.query.filter_by(mac_address=mac).first()
    if not device or not device.patient_id:
        return jsonify({"error": "Unknown device"}), 404
    p = Patient.query.get(device.patient_id)
    if not p:
        return jsonify({"error": "Patient not found"}), 404
    # Check thresholds
    if data.get("spo2", 100) < 90 or data.get("fall_detected", False):
        # Dummy SMS/Email Logic
        print(f"[ALERT] SMS sent to {p.emergency_contact_phone}: Critical Alert for {p.name}!")
        socketio.emit('emergency_alert', {"patient_id": p.national_id, "message": "Critical Vitals from Wearable"})
    return jsonify({"status": "logged"})"""

if "@app.route(\"/api/iot/webhook\"" not in content:
    content += "\n\n" + new_iot

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("Refactoring applied.")
