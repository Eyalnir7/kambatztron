// API Configuration
const API_BASE = '/api';

// State
let cadets = [];
let teams = [];
let teamConstraints = [];
let jobs = [];
let shifts = [];

// DOM Elements
const views = document.querySelectorAll('.view-section');
const navLinks = document.querySelectorAll('.nav-links li');

// View Routing
navLinks.forEach(link => {
    link.addEventListener('click', () => {
        const viewId = link.getAttribute('data-view');
        navLinks.forEach(n => n.classList.remove('active'));
        link.classList.add('active');
        views.forEach(v => v.classList.remove('active'));
        document.getElementById(`view-${viewId}`).classList.add('active');
        fetchData();
    });
});

// Fetch Data from Backend
async function fetchData() {
    try {
        const [cadetsRes, teamsRes, constraintsRes, jobsRes, shiftsRes] = await Promise.all([
            fetch(`${API_BASE}/cadets`),
            fetch(`${API_BASE}/teams`),
            fetch(`${API_BASE}/team_constraints`),
            fetch(`${API_BASE}/jobs`),
            fetch(`${API_BASE}/shifts`)
        ]);

        cadets = await cadetsRes.json();
        teams = await teamsRes.json();
        teamConstraints = await constraintsRes.json();
        jobs = await jobsRes.json();
        shifts = await shiftsRes.json();

        renderCadets();
        renderDropdowns();
        renderTeamConstraints();
        renderShifts();
    } catch (e) {
        console.error('Error fetching data:', e);
    }
}

// Renderers
function renderCadets() {
    document.getElementById('cadets-list').innerHTML = cadets.map(c => `
        <tr>
            <td>${c.personal_number || ''}</td>
            <td>${c.name || ''}</td>
            <td><span style="background: rgba(59, 130, 246, 0.2); color: #60a5fa; padding: 4px 8px; border-radius: 4px; font-size: 0.8rem;">${c.team || 'None'}</span></td>
            <td style="font-size: 0.85rem; color: var(--text-muted);">${(c.forbidden_jobs || []).join(', ')}</td>
        </tr>
    `).join('');
}

function renderDropdowns() {
    const teamOptions = '<option value="">Select a Team...</option>' + 
        teams.map(t => `<option value="${t}">${t}</option>`).join('');
    
    document.getElementById('tc-team-select').innerHTML = teamOptions;
    
    const cadetTeamSelect = document.getElementById('cadet-team');
    if (cadetTeamSelect) cadetTeamSelect.innerHTML = teamOptions;

    const jobOptions = jobs.map(j => `<option value="${j.name}">${j.name} (${j.type})</option>`).join('');
    
    const forbiddenJobsSelect = document.getElementById('cadet-forbidden-jobs');
    if (forbiddenJobsSelect) forbiddenJobsSelect.innerHTML = jobOptions;
    
    const shiftJobSelect = document.getElementById('shift-job-select');
    if (shiftJobSelect) shiftJobSelect.innerHTML = '<option value="">Select a Job...</option>' + jobOptions;

    const cadetSelectOptions = '<option value="">Select a Cadet...</option>' + 
        cadets.map(c => `<option value="${c.personal_number}">${c.name} (${c.personal_number})</option>`).join('');
    const ccCadetSelect = document.getElementById('cc-cadet-select');
    if (ccCadetSelect) ccCadetSelect.innerHTML = cadetSelectOptions;
}

function renderTeamConstraints() {
    document.getElementById('team-constraints-list').innerHTML = teamConstraints.map(tc => `
        <li>
            <div><strong>Team: ${tc.team}</strong></div>
            <div style="color: var(--text-muted); font-size: 0.85rem;">Unavailable: ${tc.unavailable_slots.map(s => `${s.start}-${s.end}`).join(', ')}</div>
        </li>
    `).join('');

    const personalConstraints = [];
    cadets.forEach(c => {
        if (c.unavailable_slots && c.unavailable_slots.length > 0) {
            c.unavailable_slots.forEach(s => {
                personalConstraints.push({ name: c.name, pn: c.personal_number, start: s.start, end: s.end });
            });
        }
    });

    document.getElementById('personal-constraints-list').innerHTML = personalConstraints.map(pc => `
        <li>
            <div><strong>Cadet: ${pc.name} (${pc.pn})</strong></div>
            <div style="color: var(--text-muted); font-size: 0.85rem;">Unavailable: ${pc.start}-${pc.end}</div>
        </li>
    `).join('');
}

function renderShifts() {
    const list = document.getElementById('shifts-list');
    if (list) {
        list.innerHTML = shifts.map(s => `
            <li>
                <div><strong>Job: ${s.job_name}</strong> <span style="font-size:0.8rem; color:var(--text-muted)">Difficulty: ${s.difficulty}</span></div>
                <div style="color: var(--text-muted); font-size: 0.85rem;">Slot: ${s.time_slot}</div>
            </li>
        `).join('');
    }
}

// Form Submissions
document.getElementById('add-cadet-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const forbiddenSelect = document.getElementById('cadet-forbidden-jobs');
    const selectedJobs = Array.from(forbiddenSelect.selectedOptions).map(opt => opt.value);

    const payload = {
        personal_number: document.getElementById('cadet-pn').value,
        name: document.getElementById('cadet-name').value,
        team: document.getElementById('cadet-team').value,
        forbidden_jobs: selectedJobs,
        unavailable_slots: []
    };

    await fetch(`${API_BASE}/cadets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    e.target.reset();
    fetchData();
});

document.getElementById('add-job-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const payload = {
        name: document.getElementById('new-job-name').value,
        type: document.getElementById('new-job-type').value
    };

    await fetch(`${API_BASE}/jobs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    e.target.reset();
    fetchData();
});

// Helper to format slider value (0-96) to HH:MM
const formatTime = (val) => {
    let hours = Math.floor(val / 4);
    const mins = (val % 4) * 15;
    if (hours === 24) hours = 23; // max bound display
    return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}`;
};

// Slider display logic
const setupSlider = (sliderId, displayId) => {
    const slider = document.getElementById(sliderId);
    const display = document.getElementById(displayId);
    if (!slider || !display) return;
    slider.addEventListener('input', (e) => {
        const val = parseInt(e.target.value, 10);
        let timeStr = formatTime(val);
        if (val === 96) timeStr = "24:00"; // display only
        display.textContent = timeStr;
    });
};

setupSlider('shift-start-time', 'shift-start-time-display');
setupSlider('shift-end-time', 'shift-end-time-display');
setupSlider('tc-start-time', 'tc-start-time-display');
setupSlider('tc-end-time', 'tc-end-time-display');
setupSlider('cc-start-time', 'cc-start-time-display');
setupSlider('cc-end-time', 'cc-end-time-display');

document.getElementById('add-shift-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const date = document.getElementById('shift-date').value;
    const startVal = parseInt(document.getElementById('shift-start-time').value, 10);
    const endVal = parseInt(document.getElementById('shift-end-time').value, 10);
    
    let startStr = formatTime(startVal);
    let endStr = formatTime(endVal);
    
    if (endVal === 96) {
        endStr = "23:59";
    }
    
    const timeSlotStr = `${date} ${startStr}-${date} ${endStr}`;

    const payload = {
        job_name: document.getElementById('shift-job-select').value,
        time_slot: timeSlotStr,
        difficulty: parseFloat(document.getElementById('shift-difficulty').value)
    };

    await fetch(`${API_BASE}/shifts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    e.target.reset();
    fetchData();
});

document.getElementById('team-constraint-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const date = document.getElementById('tc-date').value;
    const startVal = parseInt(document.getElementById('tc-start-time').value, 10);
    const endVal = parseInt(document.getElementById('tc-end-time').value, 10);
    
    let startStr = formatTime(startVal);
    let endStr = formatTime(endVal);
    
    if (endVal === 96) {
        endStr = "23:59";
    }
    
    const payload = {
        team: document.getElementById('tc-team-select').value,
        unavailable_slots: [{ start: `${date} ${startStr}`, end: `${date} ${endStr}` }]
    };

    await fetch(`${API_BASE}/team_constraints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    e.target.reset();
    fetchData();
});

document.getElementById('cadet-constraint-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const date = document.getElementById('cc-date').value;
    const startVal = parseInt(document.getElementById('cc-start-time').value, 10);
    const endVal = parseInt(document.getElementById('cc-end-time').value, 10);
    
    let startStr = formatTime(startVal);
    let endStr = formatTime(endVal);
    
    if (endVal === 96) {
        endStr = "23:59";
    }
    
    const payload = {
        personal_number: document.getElementById('cc-cadet-select').value,
        unavailable_slots: [{ start: `${date} ${startStr}`, end: `${date} ${endStr}` }]
    };

    await fetch(`${API_BASE}/cadet_constraints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    e.target.reset();
    fetchData();
});

// Run Solver
document.getElementById('run-solver-btn').addEventListener('click', async () => {
    const btn = document.getElementById('run-solver-btn');
    btn.textContent = 'Running...';
    btn.disabled = true;

    try {
        const res = await fetch(`${API_BASE}/solve`, { method: 'POST' });
        const data = await res.json();
        
        if (data.status === 'success') {
            const scheduleHtml = data.schedule.map(s => `
                <div style="margin-bottom: 8px; padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px;">
                    <div style="display: flex; justify-content: space-between;">
                        <strong>${s.job}</strong>
                        <span style="color: var(--primary-color)">${s.cadet}</span>
                    </div>
                    <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">${s.time_slot}</div>
                </div>
            `).join('');

            document.getElementById('schedule-output').innerHTML = `
                <div style="padding: 16px; margin-bottom: 16px; background: rgba(16, 185, 129, 0.1); border-left: 4px solid var(--secondary-color); color: #34d399;">
                    <strong>Success!</strong> ${data.message}
                </div>
                ${scheduleHtml}
            `;
        } else {
            document.getElementById('schedule-output').innerHTML = `
                <div style="padding: 16px; background: rgba(239, 68, 68, 0.1); border-left: 4px solid #ef4444; color: #ef4444;">
                    <strong>Error:</strong> ${data.message}
                </div>
            `;
        }
    } catch (e) {
        alert('Failed to run solver');
    } finally {
        btn.textContent = 'Run Solver';
        btn.disabled = false;
    }
});

// CSV Parsing Logic
function parseCSV(text) {
    const rows = text.split('\\n').filter(row => row.trim() !== '');
    if (rows.length < 2) return [];
    
    const headers = rows[0].split(',').map(h => h.trim());
    const data = [];
    
    for (let i = 1; i < rows.length; i++) {
        const values = rows[i].split(',').map(v => v.trim());
        let obj = {};
        headers.forEach((h, idx) => {
            obj[h] = values[idx] || '';
        });
        data.push(obj);
    }
    return data;
}

document.getElementById('upload-cadets-btn').addEventListener('click', () => {
    const file = document.getElementById('cadets-csv-file').files[0];
    if (!file) return alert("Please select a CSV file first");

    const reader = new FileReader();
    reader.onload = async (e) => {
        const parsed = parseCSV(e.target.result);
        let count = 0;
        for (const row of parsed) {
            if (!row.personal_number) continue;
            const payload = {
                personal_number: row.personal_number,
                name: row.name || '',
                team: row.team || '',
                forbidden_jobs: row.forbidden_jobs ? row.forbidden_jobs.split(';').map(s=>s.trim()).filter(s=>s) : [],
                unavailable_slots: [] // not fully parsed here for simplicity, but could be added
            };
            await fetch(`${API_BASE}/cadets`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            count++;
        }
        alert(`Successfully uploaded ${count} cadets.`);
        fetchData();
    };
    reader.readAsText(file);
});

document.getElementById('upload-jobs-btn').addEventListener('click', () => {
    const file = document.getElementById('jobs-csv-file').files[0];
    if (!file) return alert("Please select a CSV file first");

    const reader = new FileReader();
    reader.onload = async (e) => {
        const parsed = parseCSV(e.target.result);
        let count = 0;
        for (const row of parsed) {
            if (!row.job_name) continue;
            const payload = {
                name: row.job_name,
                type: row.job_type || 'general'
            };
            await fetch(`${API_BASE}/jobs`, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(payload) });
            count++;
        }
        alert(`Successfully uploaded ${count} jobs.`);
        fetchData();
    };
    reader.readAsText(file);
});

// Initial Fetch
fetchData();
