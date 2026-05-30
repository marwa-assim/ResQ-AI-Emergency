ResQ AI: Emergency Triage and Response System

ResQ AI is an emergency response platform designed to optimize emergency dispatch and triage. The system uses a machine learning model implemented in MindSpore to classify emergency severity and prioritize care. It bridges communication between patients, ambulance crews, volunteers, and hospital administrators in real-time.

Key Features

1. AI Triage: A neural network trained on over 100,000 emergency room records from the MIMIC-IV-ED dataset. It automatically triages patients into priority levels (1 to 5) based on vital signs and symptoms.
2. AI First Aid Assistant: A conversational AI assistant that provides step-by-step, voice-guided first aid instructions based on the patient's condition.
3. Sign Language Recognition: A camera-based input system using MediaPipe to recognize ASL hand shapes, allowing deaf or mute patients to trigger emergency alerts.
4. Multilingual Translation: Instant UI translation into 15 languages, with matching voice-guided first aid instructions in the selected language.
5. Real-Time Routing: Direct road routing and turn-by-turn navigation for ambulance drivers and volunteers, powered by the Open Source Routing Machine (OSRM).
6. Local Mesh Networking: A peer-to-peer WebRTC communication network that allows emergency responders to coordinate local operations even if internet access is down.
7. Wearable Integration: An API that registers data from health sensors and smartwatches to automatically trigger dispatches when critical vitals or falls are detected.
8. Visually impaired people can enable the Voice Command mode where it will read all the text in the screen to guide them using voice.
9. Volunteer Networks system: Where AED trained and certified people will be registered to the system to help as first responders the people in need using the nearwst location using the GPS where they can accept the request and respond before the ambulance arrive.
System Architecture

The platform is built as a modular application:
- Patient Portal: For symptom reporting, tracking dispatch, and viewing first aid instructions.
- Ambulance Portal: For crews to accept tasks and navigate to the patient and hospital.
- Volunteer Portal: For local registered first responders to receive nearby alerts.
- Admin Dashboard: For hospital staff to monitor queue states, assign beds, and coordinate responses.
- Sign Language Interface: For deaf users to communicate emergency needs.
- Mesh Network: For off-grid peer-to-peer text and command communication.

 Installation and Redeployment Steps

Follow these steps to run the system locally for evaluation and testing.

 Prerequisites

- Python 3.9 (Required: MindSpore is only compatible with Python 3.9 on Windows/Linux).
- Git.
- A Gemini API Key (Required for the conversational AI assistant. You can get one for free at aistudio.google.com).

The system is already hoswted on cloud and you can use it and test it as the API key is available and ready to use from the link: 
https://resq-ai-ogb8.onrender.com/


Step 1: Clone or Unzip the Code

Clone the repository from GitHub:
bash
git clone https://github.com/marwa-assim/ResQ-AI-Emergency.git
cd ResQ-AI-Emergency

Or extract the provided ZIP file and open a terminal in the root directory.

Step 2: Create a Virtual Environment

It is highly recommended to run the app inside a virtual environment to avoid version conflicts.

For Windows:
cmd
python -m venv .venv
.venv\Scripts\activate


For Mac or Linux:
bash
python3.9 -m venv .venv
source .venv/bin/activate
```

Step 3: Install Dependencies

Install the required packages:
bash
pip install -r requirements.txt

Note: MindSpore is a large library. The installation process may take 3 to 5 minutes depending on your internet connection.

Step 4: Configure Environment Variables

1. Copy the template configuration file:
   - On Windows: `copy .env.example .env`
   - On Mac/Linux: `cp .env.example .env`
2. Open the `.env` file in a text editor.
3. Set your `GEMINI_API_KEY` to your API key.
4. Set `SECRET_KEY` to any random string of characters.

Step 5: Start the Server

Run the Flask application:
bash
python app.py

Upon a successful start, you should see output indicating that the database is initialized, the MindSpore model has loaded, and the server is running at:
`http://localhost:5000`

How to Test the Portals

Open separate browser tabs to view the different roles:

1. Landing Page: `http://localhost:5000`
2. Patient Portal: `http://localhost:5000/patient`
3. Ambulance Crew: `http://localhost:5000/ambulance` (Auto-logs in as Unit 42)
4. Volunteer Portal: `http://localhost:5000/volunteer`
5. Command Center Dashboard: `http://localhost:5000/admin` or `http://localhost:5000/dashboard`
6. Sign Language Interface: `http://localhost:5000/sign_language`
7. Mesh Network Interface: `http://localhost:5000/mesh`

Testing the Simulation Flow

1. Open the Admin Dashboard (`http://localhost:5000/dashboard`) in one window.
2. Open the Patient Portal (`http://localhost:5000/patient`) in a second window.
3. Scroll to the "Linked Devices" section on the Patient Portal.
4. Click one of the simulation triggers, such as "Trigger 5.2g Impact Alert from Samsung Watch".
5. Observe that the Patient Portal transitions to the tracking map view.
6. The Admin Dashboard will instantly play an alarm sound and show a new incoming case card in the "Incoming Emergency Alerts" section below the traffic map.
7. Open the Ambulance Portal (`http://localhost:5000/ambulance`) in a third window. It will sound an alarm and prompt the driver to "Accept".
8. Click "Accept", then select a hospital, and click "Transmit Data" to send a handoff report.
9. Click "Arrived at ER". You will see the patient automatically disappear from the dashboard's incoming alerts section and move into the Waiting Queue.

Technology Stack

- Backend: Python 3.9, Flask 3.1, SQLAlchemy, Flask-SocketIO.
- AI Triage Engine: Huawei MindSpore 2.3.0 (Neural Network).
- AI Assistant: Google Gemini API.
- Mapping and Navigation: Leaflet.js, OpenStreetMap, OSRM.
- Sign Language Processing: MediaPipe Hands.
- Mesh Signaling: WebRTC Peer-to-Peer LORA Network.
