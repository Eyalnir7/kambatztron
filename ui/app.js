// API Configuration
const API_BASE = '/api';

// State
let cadets = [];
let teams = [];
let teamConstraints = [];
let jobConstraints = [];
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
        const [cadetsRes, teamsRes, teamConstraintsRes, jobConstraintsRes, jobsRes, shiftsRes] = await Promise.all([
            fetch(`${API_BASE}/cadets`),
            fetch(`${API_BASE}/teams`),
            fetch(`${API_BASE}/team_constraints`),
            fetch(`${API_BASE}/job_constraints`),
            fetch(`${API_BASE}/jobs`),
            fetch(`${API_BASE}/shifts`)
        ]);

        cadets = await cadetsRes.json();
        teams = await teamsRes.json();
        teamConstraints = await teamConstraintsRes.json();
        jobConstraints = await jobConstraintsRes.json();
        jobs = await jobsRes.json();
        shifts = await shiftsRes.json();

        renderCadets();
        renderDropdowns();
        renderConstraints();
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
    
    const tcTeamSelect = document.getElementById('tc-team-select');
    if (tcTeamSelect) tcTeamSelect.innerHTML = teamOptions;
    
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

function renderConstraints() {
    // Team Constraints
    const tcList = document.getElementById('team-constraints-list');
    if (tcList) {
        tcList.innerHTML = teamConstraints.map(tc => `
            <li>
                <div><strong>Team: ${tc.team}</strong></div>
                <div style="color: var(--text-muted); font-size: 0.85rem;">Unavailable: ${tc.unavailable_slots.map(s => `${s.start}-${s.end}`).join(', ')}</div>
            </li>
        `).join('');
    }

    // Personal Constraints
    const personalConstraints = [];
    cadets.forEach(c => {
        if (c.unavailable_slots && c.unavailable_slots.length > 0) {
            c.unavailable_slots.forEach(s => {
                personalConstraints.push({ name: c.name, pn: c.personal_number, start: s.start, end: s.end });
            });
        }
    });

    const pcList = document.getElementById('personal-constraints-list');
    if (pcList) {
        pcList.innerHTML = personalConstraints.map(pc => `
            <li>
                <div><strong>Cadet: ${pc.name} (${pc.pn})</strong></div>
                <div style="color: var(--text-muted); font-size: 0.85rem;">Unavailable: ${pc.start}-${pc.end}</div>
            </li>
        `).join('');
    }

    // Job Matrix
    const jmList = document.getElementById('job-matrix-list');
    if (jmList) {
        jmList.innerHTML = jobConstraints.map(jc => `
            <tr>
                <td>${jc.job_type_a}</td>
                <td>${jc.job_type_b}</td>
                <td><span style="color: ${jc.can_overlap ? '#10b981' : '#ef4444'}">${jc.can_overlap ? 'Yes' : 'No'}</span></td>
                <td><span style="color: ${jc.can_be_consecutive ? '#10b981' : '#ef4444'}">${jc.can_be_consecutive ? 'Yes' : 'No'}</span></td>
            </tr>
        `).join('');
    }
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

// Midnight Crossover Logic Helper
const computeTimeSlot = (dateStr, startH, endH) => {
    let startDate = new Date(`${dateStr}T${startH}`);
    let endDate = new Date(`${dateStr}T${endH}`);
    
    // If end time is less than or equal to start time, it crossed midnight to the next day
    if (endDate <= startDate) {
        endDate.setDate(endDate.getDate() + 1);
    }
    
    const endStrDate = endDate.toISOString().split('T')[0];
    return `${dateStr} ${startH}-${endStrDate} ${endH}`;
};

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

document.getElementById('add-shift-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const date = document.getElementById('shift-date').value;
    const startH = document.getElementById('shift-start-time').value; // "HH:MM"
    const endH = document.getElementById('shift-end-time').value; // "HH:MM"
    
    const timeSlotStr = computeTimeSlot(date, startH, endH);

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
    const startH = document.getElementById('tc-start-time').value;
    const endH = document.getElementById('tc-end-time').value;
    
    const timeSlotStr = computeTimeSlot(date, startH, endH);
    const [computedStart, computedEnd] = timeSlotStr.split('-');

    const payload = {
        team: document.getElementById('tc-team-select').value,
        unavailable_slots: [{ start: computedStart, end: computedEnd }]
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
    const startH = document.getElementById('cc-start-time').value;
    const endH = document.getElementById('cc-end-time').value;
    
    const timeSlotStr = computeTimeSlot(date, startH, endH);
    const [computedStart, computedEnd] = timeSlotStr.split('-');
    
    const payload = {
        personal_number: document.getElementById('cc-cadet-select').value,
        unavailable_slots: [{ start: computedStart, end: computedEnd }]
    };

    await fetch(`${API_BASE}/cadet_constraints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    
    e.target.reset();
    fetchData();
});

document.getElementById('job-matrix-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const payload = {
        job_type_a: document.getElementById('jm-type-a').value.toLowerCase(),
        job_type_b: document.getElementById('jm-type-b').value.toLowerCase(),
        can_overlap: document.getElementById('jm-overlap').checked,
        can_be_consecutive: document.getElementById('jm-consecutive').checked
    };

    await fetch(`${API_BASE}/job_constraints`, {
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
                unavailable_slots: []
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
