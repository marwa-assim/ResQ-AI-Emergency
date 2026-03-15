@app.route("/api/ambulance/new", methods=["POST"])
def new_ambulance_update():
    # Handles BOTH new missions and status updates (Upsert)
    data = request.json
    amb_id = data.get("id", f"AMB-{random.randint(1000,9999)}")
    
    # 1. Check if exists
    amb = next((x for x in incoming_ambulances if x["id"] == amb_id), None)
    
    if amb:
        # UPDATE Existing
        if data.get("status"): amb["status"] = data.get("status")
        if data.get("symptoms"): amb["symptoms"] = data.get("symptoms")
        if data.get("destination"): amb["destination"] = data.get("destination")
        # Merge full data if provided (e.g. from Transmit)
        if "vitals" in data:
            amb["full_data"] = data
            # Recalculate risk if vitals provided
            # We map the fields to what process_triage expects
            triage_payload = {
                "patient_id": amb_id,
                "name": data.get("name"),
                "hr": data["vitals"].get("hr"),
                "spo2": data["vitals"].get("spo2"),
                "symptoms": data.get("symptoms"),
                "checklist": data.get("checklist", [])
            }
            # Run "Lite" Triage for the dashboard display (Full Triage happens on Arrival)
            # We don't have full history yet, but we can do a rough score
            process_triage_lite(amb, triage_payload)
            
        return jsonify({"status": "updated", "id": amb_id})
    else:
        # CREATE New
        new_entry = {
            "id": amb_id,
            "name": data.get("name", "Unknown"),
            "display_type": "AMB",
            "status": data.get("status", "En Route"),
            "arrival_time": "ETA 10m",
            "condition": "Stable", # Default
            "symptoms": data.get("symptoms", "Dispatch"),
            "destination": data.get("destination", ""),
            "full_data": data
        }
        incoming_ambulances.append(new_entry)
        return jsonify({"status": "created", "id": amb_id})

def process_triage_lite(amb, data):
    # Quick risk calc for the dashboard ticker before full arrival
    # Parses symptoms and vitals to update 'condition' and 'symptoms' text
    hr = float(data.get("hr", 80))
    spo2 = float(data.get("spo2", 98))
    
    # Parse text symptoms
    raw = str(data.get("symptoms", "")).lower()
    checklist = data.get("checklist", [])
    if checklist: raw += " " + " ".join(checklist).lower()
    
    is_crit = False
    if "pain" in raw or "chest" in raw: is_crit = True
    if "breath" in raw or "sob" in raw: is_crit = True
    if "bleed" in raw or "trauma" in raw: is_crit = True
    if spo2 < 90 or hr > 130: is_crit = True
    
    amb["condition"] = "CRITICAL" if is_crit else "Stable"
    amb["symptoms"] = str(data.get("symptoms", "Assessment")).title()
