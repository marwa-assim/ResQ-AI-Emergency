const state = {
    patient_id: '',
    name: '',
    age: '',
    vitals: { hr: 0, spo2: 0, temp: 0, sys_bp: 0, dia_bp: 0 },
    symptoms: {},
    history: {}
};

// Wizard Navigation
let currentStep = 1;
function showStep(step) {
    document.querySelectorAll('.wizard-step').forEach(el => el.style.display = 'none');
    document.getElementById(`step-${step}`).style.display = 'block';
    currentStep = step;
}

// -------------------------
// 1. ID Scanning
// -------------------------
async function scanID() {
    const btn = document.getElementById('scan-btn');
    const visual = document.getElementById('id-visual');
    const input = document.getElementById('patient-id-input');
    const manualDiv = document.getElementById('manual-entry');

    // Animation
    visual.classList.add('scan-active');
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Scanning...';

    // Simulate delay
    await new Promise(r => setTimeout(r, 1500));

    // Fetch from API
    const pid = input.value || "1001";
    state.patient_id = pid;

    try {
        const res = await axios.get(`/api/patient/${pid}`);
        if (res.data.found) {
            state.name = res.data.name;
            state.age = res.data.age;
            state.history = { chronic: res.data.chronic, allergy: res.data.allergy };

            // UI Feedback
            document.getElementById('patient-name-display').innerHTML = `
                <div style="color: var(--risk-low); margin-top: 1rem;">
                    <i class="fa-solid fa-check-circle"></i> Identity Verified
                </div>
                <h3>${state.name}</h3>
                <p>History Loaded • Age: ${state.age}</p>
            `;
            // Auto Advance
            setTimeout(() => showStep(2), 1000);

        } else {
            // Not Found -> Show Manual Entry
            manualDiv.style.display = 'block';
            manualDiv.style.animation = 'pulse-glow 0.5s';

            btn.innerHTML = 'ID Not Found';
            btn.style.background = 'var(--risk-high)';

            document.getElementById('patient-name-display').innerHTML = `
                 <div style="color: var(--risk-high); margin-top: 1rem;">
                    <i class="fa-solid fa-circle-exclamation"></i> New Patient
                </div>
            `;
        }
    } catch (e) {
        console.error(e);
        alert("System Error");
    } finally {
        visual.classList.remove('scan-active');
        if (document.getElementById('manual-entry').style.display !== 'block') {
            btn.innerHTML = 'Scan ID Card';
        }
    }
}

// Function called when user manually submits name/age
function submitManualEntry() {
    const nameIn = document.getElementById('manual-name').value;
    const ageIn = document.getElementById('manual-age').value;

    if (!nameIn || !ageIn) {
        alert("Please enter Name and Age.");
        return;
    }

    state.name = nameIn;
    state.age = parseInt(ageIn);
    state.history = { chronic: false, allergy: false }; // New patient default

    showStep(2);
}

// -------------------------
// 2. Hardware Socket Integration
// -------------------------
// Initialize Socket.io
const socket = io();

socket.on('hardware_vitals_scanned', function(data) {
    if (currentStep !== 2) return; // Only process if on vitals step

    // Real hardware usually sends hr and spo2, but let's map whatever it sends
    if (data.hr) {
        state.vitals.hr = data.hr;
        document.getElementById('val-hr').innerText = data.hr;
        document.getElementById('val-hr').style.color = 'var(--accent-cyan)';
        document.getElementById('btn-hr').innerText = 'Synced';
    }
    if (data.spo2) {
        state.vitals.spo2 = data.spo2;
        document.getElementById('val-spo2').innerText = data.spo2;
        document.getElementById('val-spo2').style.color = 'var(--accent-cyan)';
        document.getElementById('btn-spo2').innerText = 'Synced';
    }
    if (data.temp) {
        state.vitals.temp = data.temp;
        document.getElementById('val-temp').innerText = data.temp;
        document.getElementById('val-temp').style.color = 'var(--accent-cyan)';
        document.getElementById('btn-temp').innerText = 'Synced';
    }
    if (data.sys_bp && data.dia_bp) {
        state.vitals.sys_bp = data.sys_bp;
        state.vitals.dia_bp = data.dia_bp;
        document.getElementById('val-bp').innerText = `${data.sys_bp}/${data.dia_bp}`;
        document.getElementById('val-bp').style.color = 'var(--accent-cyan)';
        document.getElementById('btn-bp').innerText = 'Synced';
    }
});

// Hidden simulation for testing (double click Title)
function triggerSimulation() {
    ['hr', 'spo2', 'temp', 'bp'].forEach(type => {
        const btn = document.getElementById(`btn-${type}`);
        const display = document.getElementById(`val-${type}`);

        btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Measuring...';

        setTimeout(() => {
            let val = 0;
            if (type === 'hr') val = Math.floor(Math.random() * (100 - 60) + 60);
            if (type === 'spo2') val = Math.floor(Math.random() * (100 - 95) + 95);
            if (type === 'temp') val = (Math.random() * (37.5 - 36.5) + 36.5).toFixed(1);
            if (type === 'bp') {
                const sys = Math.floor(Math.random() * (130 - 110) + 110);
                const dia = Math.floor(Math.random() * (85 - 70) + 70);
                val = `${sys}/${dia}`;
                state.vitals.sys_bp = sys;
                state.vitals.dia_bp = dia;
            } else {
                state.vitals[type] = parseFloat(val);
            }
            display.innerText = val;
            display.style.color = 'var(--accent-cyan)';
            btn.innerHTML = 'Retake';
        }, Math.random() * 1000 + 500);
    });
}

// -------------------------
// 3. Submission
// -------------------------
async function submitTriage() {
    // Gather Symptoms
    const symptoms = {
        chest_pain: document.getElementById('sym-cp').checked,
        breathing: document.getElementById('sym-br').checked,
        bleeding: document.getElementById('sym-bl').checked,
        fainting: document.getElementById('sym-fa').checked,
    };

    const payload = {
        patient_id: state.patient_id,
        name: state.name,
        age: state.age,
        hr: state.vitals.hr,
        spo2: state.vitals.spo2,
        temp: state.vitals.temp,
        sys_bp: state.vitals.sys_bp,
        dia_bp: state.vitals.dia_bp,
        ...symptoms,
        ...state.history
    };

    try {
        const res = await axios.post('/api/triage', payload);
        const data = res.data;
        const p = data.patient;
        
        let color = "var(--risk-low)";
        let icon = "fa-circle-check";
        let prioLabel = "Normal / Level 0";
        if (p.priority === 1) { color = "var(--risk-high)"; icon = "fa-circle-exclamation"; prioLabel = "Urgent / Level 1"; }
        if (p.priority === 2) { color = "var(--risk-critical)"; icon = "fa-truck-medical"; prioLabel = "Emergency / Level 2"; }
        if (p.priority >= 3) { color = "red"; icon = "fa-skull-crossbones"; prioLabel = "Critical / Resuscitation"; }

        // Show Success
        document.getElementById('step-3').innerHTML = `
            <div style="text-align: center; margin-top: 3rem;">
                <i class="fa-solid ${icon}" style="font-size: 5rem; color: ${color}; margin-bottom: 1rem;"></i>
                <h1 style="color: ${color}">Triage Complete</h1>
                
                <div style="background: rgba(0,0,0,0.3); border: 1px solid ${color}; padding: 2rem; border-radius: 12px; max-width: 400px; margin: 2rem auto; text-align: left;">
                    <div style="font-size: 1.2rem; color: white; margin-bottom: 0.5rem;"><b>Patient:</b> ${p.name}</div>
                    <div style="font-size: 1.2rem; color: white; margin-bottom: 0.5rem;"><b>Priority:</b> <span style="color: ${color}">${prioLabel}</span></div>
                    <div style="font-size: 1.2rem; color: white; margin-bottom: 0.5rem;"><b>AI Risk Score:</b> ${p.score}%</div>
                    <hr style="border-color: #333; margin: 1rem 0;">
                    <div style="font-size: 1.5rem; text-align: center; color: var(--accent-cyan);">
                        <b>Queue Number: #${data.position}</b>
                    </div>
                </div>
                
                <p style="color: #94a3b8; font-size: 1.1rem;">Please proceed to the waiting area. The doctor will see you shortly.</p>
                <button onclick="window.location.reload()" style="margin-top: 1rem; background: white; color: black; padding: 0.8rem 2.5rem; border: none; font-weight: bold; border-radius: 30px; cursor: pointer;">Done</button>
            </div>
        `;
        
        // Remove auto-redirect so the patient has time to read it!
    } catch (e) {
        alert("Submission Failed");
    }
}
