with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = lines[:253]

replacement = """@app.route("/api/chat", methods=["POST"])
def ai_chat():
    \"\"\"
    Real LLM medical chat via Google Gemini.
    Body: { "message": "...", "history": [...] }
    Returns: { "reply": "..." }
    \"\"\"
    import json as _json
    data = request.json or {}
    message = data.get("message", "").strip()
    history = data.get("history", [])   # [{role, content}, ...]
    ui_lang = data.get("language", "en")

    if not message:
        return jsonify({"reply": "Please describe your medical question or emergency."}), 400

    GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

    # ── Try real Gemini LLM ──
    if GEMINI_KEY:
        import urllib.request, urllib.error
        SYSTEM = (
            "You are Nurse Sara, a highly experienced emergency medical nurse at ResQ AI Emergency System. "
            "You provide clear, accurate, and calm medical first-aid guidance for emergencies and general health questions. "
            "Always remind the user to call emergency services (911) for life-threatening situations. "
            "Keep responses concise, empathetic, and structured (numbered steps when giving instructions). "
            "Do not diagnose, but DO provide clear first-aid and triage guidance. "
            f"IMPORTANT: The user has selected language code '{ui_lang}' in their UI. YOU MUST ALWAYS respond in the language corresponding to '{ui_lang}', REGARDLESS of the language the user types in."
        )
        contents = []
        for h in history[-8:]:
            role = "user" if h.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h.get("content", "")}]})
        contents.append({"role": "user", "parts": [{"text": message}]})
        payload = _json.dumps({
            "system_instruction": {"parts": [{"text": SYSTEM}]},
            "contents": contents,
            "generationConfig": {"temperature": 0.4, "maxOutputTokens": 600}
        }).encode()

        # Try models in order of quota generosity
        models_to_try = [
            "gemini-flash-lite-latest",   # highest free quota, confirmed working
            "gemini-2.0-flash-lite-001",  # flash-lite stable release
            "gemini-2.0-flash",           # fallback
        ]
"""

new_lines.extend([line + "\n" for line in replacement.split("\n")][:-1])
new_lines.extend(lines[461:])

with open("app.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
