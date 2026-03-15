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
// 2. Vitals Simulation
// -------------------------
function simulateVital(type) {
    const btn = document.getElementById(`btn-${type}`);
    const display = document.getElementById(`val-${type}`);

    if (!btn || btn.disabled) return;

    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Measuring...';

    // Simulated Delay
    setTimeout(() => {
        let val = 0;
        // Random "Normal-ish" values by default
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
        btn.disabled = false;
    }, 2000);
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
        // Show Success
        document.getElementById('step-3').innerHTML = `
            <div style="text-align: center; margin-top: 5rem;">
                <i class="fa-solid fa-circle-check" style="font-size: 5rem; color: var(--risk-low);"></i>
                <h1>Checking In...</h1>
                <p>Please take a seat. Your queue number is being generated.</p>
            </div>
        `;
        // Redirect after 3s
        setTimeout(() => window.location.href = '/', 4000);
    } catch (e) {
        alert("Submission Failed");
    }
}
