# 🚑 ResQ AI — Emergency Triage & Response System

<div align="center">

![ResQ AI Banner](https://img.shields.io/badge/ResQ-AI%20Emergency-red?style=for-the-badge&logo=heart&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.9-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.1-lightgrey?style=flat-square&logo=flask)
![MindSpore](https://img.shields.io/badge/MindSpore-2.3.0-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

**An AI-powered emergency triage and response platform that bridges the gap between patients and emergency services using real-time AI, sign language recognition, multilingual support, and mesh networking.**

</div>

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Key Features](#-key-features)
3. [System Architecture](#-system-architecture)
4. [Prerequisites](#-prerequisites)
5. [Installation](#-installation)
6. [Configuration](#-configuration)
7. [Running the Application](#-running-the-application)
8. [Feature Walkthrough](#-feature-walkthrough)
9. [AI Model — MindSpore](#-ai-model--mindspore)
10. [Wearable Integration](#-wearable-integration)
11. [Deployment to Cloud](#-deployment-to-cloud)
12. [Technology Stack](#-technology-stack)

---

## 🌟 Overview

ResQ AI is a full-stack emergency response platform designed to reduce emergency response times and improve patient outcomes. It uses Huawei MindSpore to run a neural network trained on **80,000+ real hospital records** from the MIMIC-IV-ED dataset to automatically triage patients by priority level (ESI 1–5).

The platform connects four groups in real time:
- 🧑‍⚕️ **Patients** — report symptoms, receive AI-guided first aid, dispatch ambulances
- 🚑 **Ambulance crews** — receive patient GPS, get turn-by-turn OSRM routing
- 🙋 **Volunteers** — receive nearby emergency alerts, navigate to patient
- 🏥 **Administrators** — monitor all active cases on a live dashboard

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Triage (MindSpore)** | Neural network trained on MIMIC-IV-ED data classifies emergencies Priority 1–5 |
| 💬 **Nurse Sara AI Assistant** | Gemini-powered conversational AI gives real-time first aid guidance |
| ✋ **Sign Language Recognition** | MediaPipe Hands detects ASL gestures for deaf patients |
| 🌍 **15-Language Translation** | Full UI translation via Google Translate widget |
| 🗺️ **Real-Time OSRM Routing** | Turn-by-turn directions for ambulances and volunteers |
| 📡 **WebRTC Mesh Network** | Peer-to-peer communication between responders — works without internet |
| ⌚ **Wearable Integration** | Huawei Health Kit endpoint auto-dispatches on critical vitals |
| 📱 **Mobile Responsive** | Fully accessible on phones over WiFi |
| 🔊 **Multilingual Voice** | Nurse Sara speaks in the user's selected language |

---

## 🏗️ System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌───────────────┐
│   Patient   │────▶│  Flask API  │────▶│  MindSpore    │
│   Portal    │     │  (app.py)   │     │  Triage Model │
└─────────────┘     └──────┬──────┘     └───────────────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
  │  Ambulance   │  │  Volunteer   │  │    Admin     │
  │   Portal     │  │   Portal     │  │  Dashboard   │
  └──────────────┘  └──────────────┘  └──────────────┘
          │                │
          └────────────────┘
               OSRM Routing
```

---

## 📦 Prerequisites

Before installing, ensure you have the following:

| Requirement | Version | Download |
|---|---|---|
| **Python** | 3.9.x | [python.org](https://www.python.org/downloads/release/python-390/) |
| **pip** | Latest | Included with Python |
| **Git** | Any | [git-scm.com](https://git-scm.com) |
| **Google Chrome / Edge** | Latest | For best camera/GPS support |
| **Gemini API Key** | Free | [aistudio.google.com](https://aistudio.google.com/app/apikey) |

> ⚠️ **Python 3.9 is required** — MindSpore 2.3.0 does not support Python 3.10+

---

## 🔧 Installation

### Step 1 — Clone the Repository

```bash
git clone https://github.com/marwa-assim/ResQ-AI-Emergency.git
cd ResQ-AI-Emergency
```

### Step 2 — Create a Virtual Environment (Recommended)

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**Mac / Linux:**
```bash
python3.9 -m venv venv
source venv/bin/activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

> ⏳ MindSpore is a large package. This step may take **3–5 minutes** on first install.

### Step 4 — Verify Installation

```bash
python -c "import flask, mindspore; print('All dependencies installed successfully')"
```

---

## ⚙️ Configuration

### Step 1 — Create the `.env` file

```bash
# Windows
copy .env.example .env

# Mac/Linux
cp .env.example .env
```

### Step 2 — Add your Gemini API Key

Open `.env` in any text editor and set:

```env
GEMINI_API_KEY=your_gemini_api_key_here
SECRET_KEY=any-random-string-here
```

**Getting a Gemini API Key (Free):**
1. Go to [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Sign in with a Google account
3. Click **"Create API Key"**
4. Copy the key and paste it in `.env`

---

## ▶️ Running the Application

```bash
python app.py
```

You should see:
```
[MindSpore] Model loaded: mimic_risk_model.ckpt
 * Running on http://0.0.0.0:5000
 * Running on http://192.168.x.x:5000
```

Open your browser and navigate to:

| Portal | URL | Who uses it |
|---|---|---|
| 🏠 Home | `http://localhost:5000` | Landing page |
| 🧑‍⚕️ Patient | `http://localhost:5000/patient` | Patients in emergency |
| 🚑 Ambulance | `http://localhost:5000/ambulance` | Paramedics / drivers |
| 🙋 Volunteer | `http://localhost:5000/volunteer` | First responders |
| 🏥 Admin | `http://localhost:5000/admin` | Hospital staff |
| ✋ Sign Language | `http://localhost:5000/sign_language` | Deaf users |
| 📡 Mesh Network | `http://localhost:5000/mesh` | Responder comms |

### Access from a Mobile Phone

Make sure your phone is on the **same WiFi network**, then open:
```
http://<your-pc-ip>:5000
```
*(Your PC's IP is shown in the terminal when the server starts)*

---

## 🎯 Feature Walkthrough

### 1. 🏥 Patient Emergency Portal
1. Go to `http://localhost:5000/patient`
2. Enter symptoms, heart rate, oxygen level, and pain score
3. Click **"Assess My Condition"** — the AI triage model scores and prioritizes
4. Nurse Sara (AI Assistant) appears with voice-guided first aid steps
5. Click **"SEND AMBULANCE"** — browser asks for your GPS location
6. Confirm your location on the map → ambulance is dispatched

### 2. 💬 AI Assistant (Nurse Sara)
- Type any medical question in the chat box
- Nurse Sara responds with real AI guidance (powered by Gemini)
- Say "show me CPR steps" or "start burn guide" to activate illustrated protocols
- Click 🤟 icon to switch to **Sign Language mode**

### 3. ✋ Sign Language Mode
1. From the patient page, click the **🤟 icon** (top-right or inside chat box)
2. Review the ASL A–Z reference cards
3. Click **"📷 Start Signing"** — allow camera access
4. Sign letters using ASL hand shapes — hold each ~0.5 seconds
5. Or tap **Quick Phrase buttons** (e.g., "Chest Pain", "Help", "Bleeding")
6. Click **"Review & Send to Triage →"** when done

### 4. 🚑 Ambulance Portal
1. Go to `http://localhost:5000/ambulance` and log in
2. Active cases appear on the map with patient GPS coordinates
3. Click a case → OSRM provides real road distance, ETA, and turn-by-turn directions
4. Navigate to patient → update status → navigate to hospital

### 5. 🙋 Volunteer Portal
1. Go to `http://localhost:5000/volunteer` and register
2. Alert sound plays when a nearby emergency is detected
3. Click **Accept** → map shows patient location with OSRM route
4. Click **"I'm Responding"** or **"Decline"**

### 6. 📡 Mesh Network (Responder Communication)
1. Go to `http://localhost:5000/mesh`
2. Enter your name and role, click **"Connect to Mesh"**
3. All connected responders appear as peers
4. Type messages or use Quick Alerts: 🆘 Emergency / ✅ All Clear / 🚑 En Route / ❤️ CPR Help
5. Works on local WiFi **without internet**

### 7. 🌍 Language Translation
- Click **"اختيار اللغة"** (top-right on any page)
- Select from 15 languages — the entire UI translates instantly
- Nurse Sara's voice also switches to speak in the selected language

### 8. ⌚ Wearable / IoT Integration

Send a POST request to test auto-dispatch from a smartwatch:

```bash
curl -X POST http://localhost:5000/api/wearable/data \
  -H "Content-Type: application/json" \
  -d '{"device_id":"WATCH-001","hr":168,"spo2":91,"lat":24.7136,"lng":46.6753}'
```

**Auto-dispatch triggers when:**
- Heart rate > 160 BPM or < 35 BPM
- SpO2 < 88%
- Alert type: `fall_detected` or `irregular_heartbeat`

---

## 🧠 AI Model — MindSpore

The triage model is a **3-layer neural network** implemented in **Huawei MindSpore**:

```
Input (7 vitals) → Dense(64) → ReLU → Dense(32) → ReLU → Dense(5) → ESI Priority
```

**Training Data:** MIMIC-IV-ED (MIT / Beth Israel Deaconess Medical Center)
- 80,000 real emergency department visits
- Features: Temperature, Heart Rate, Respiratory Rate, SpO2, SBP, DBP, Pain Score
- Labels: Emergency Severity Index (ESI) 1–5

**Model Files:**
| File | Description |
|---|---|
| `mimic_risk_model.ckpt` | Trained MindSpore neural network weights |
| `mindspore_scaling.json` | Feature normalization parameters from MIMIC data |
| `train_risk_model_mindspore.py` | Full training script |

> The model loads automatically on startup. If MindSpore is unavailable, the system falls back to evidence-based clinical triage rules.

---

## ⌚ Wearable Integration

The `/api/wearable/data` endpoint accepts POST requests from Huawei Health Kit companion apps:

```json
{
  "device_id": "HUAWEI-GT4-001",
  "hr": 72,
  "spo2": 98,
  "steps": 3200,
  "lat": 24.7136,
  "lng": 46.6753,
  "alert_type": "fall_detected"
}
```

View latest readings at: `GET /api/wearable/latest`

---

## ☁️ Deployment to Cloud (Render)

1. Fork or push to your GitHub repository
2. Go to [render.com](https://render.com) → Sign up with GitHub
3. Click **New → Web Service** → Select your repository
4. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Add environment variable:
   - `GEMINI_API_KEY` = your key
6. Click **Deploy**

> ✅ `runtime.txt` is already configured to use Python 3.9 so MindSpore installs correctly.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Backend** | Python 3.9, Flask 3.1, SQLAlchemy |
| **AI Triage** | Huawei MindSpore 2.3.0 (Neural Network) |
| **AI Assistant** | Google Gemini API (`gemini-flash-lite-latest`) |
| **Routing** | OSRM (Open Source Routing Machine) |
| **Sign Language** | MediaPipe Hands (ASL recognition) |
| **Mesh Network** | WebRTC + Flask Signaling Server |
| **Translation** | Google Translate Widget |
| **Database** | SQLite (dev) / PostgreSQL (production) |
| **Maps** | Leaflet.js + OpenStreetMap |
| **Frontend** | HTML5, Vanilla CSS, JavaScript |
| **Wearables** | Huawei Health Kit REST API |

---

## 📄 License

This project is submitted for academic and competition purposes.  
Dataset: [MIMIC-IV-ED](https://physionet.org/content/mimic-iv-ed/2.2/) — PhysioNet / MIT License.

---

<div align="center">

**Built with ❤️ for emergency response — saving lives with AI**

</div>
