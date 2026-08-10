/**
 * AI Business Twin — Data Validation Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) {
    window.location.href = '/login';
    return;
  }

  const urlParams = new URLSearchParams(window.location.search);
  const jobId = urlParams.get('job_id');
  
  if (!jobId) {
    window.location.href = '/upload';
    return;
  }

  const fileInfo = document.getElementById('file-info');
  const contentDiv = document.getElementById('validation-content');
  const actionMessage = document.getElementById('action-message');
  
  const btnClean = document.getElementById('btn-clean');
  const btnConfirm = document.getElementById('btn-confirm');

  function showMessage(text, type) {
    actionMessage.textContent = text;
    actionMessage.className = 'auth-message ' + type;
  }

  function setButtonState(loading) {
    btnClean.disabled = loading;
    btnConfirm.disabled = loading;
  }

  async function loadValidation() {
    try {
      const resp = await fetch(`/api/data/validate/${jobId}`, {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await resp.json();
      
      if (!resp.ok) {
        fileInfo.textContent = data.detail || 'Error loading validation report.';
        fileInfo.style.color = '#d32f2f';
        return;
      }
      
      renderReport(data);
    } catch (err) {
      fileInfo.textContent = 'Network error fetching report.';
    }
  }

  function renderReport(data) {
    fileInfo.innerHTML = `File: <strong>${data.filename}</strong> &nbsp;|&nbsp; Dataset: <strong>${data.data_type.toUpperCase()}</strong>`;
    
    // Stats
    const errors = data.issues.filter(i => i.type === 'error').length;
    const warnings = data.issues.filter(i => i.type === 'warning').length;
    
    document.getElementById('stat-total').textContent = data.stats.total_rows.toLocaleString();
    document.getElementById('stat-valid').textContent = data.stats.valid_rows.toLocaleString();
    document.getElementById('stat-errors').textContent = errors;
    document.getElementById('stat-warnings').textContent = warnings;
    document.getElementById('stat-duplicates').textContent = data.stats.duplicates;

    // Button states
    if (errors > 0 || data.stats.total_rows === 0) {
      btnConfirm.disabled = true;
      btnConfirm.style.opacity = '0.5';
      btnConfirm.title = "Fix errors or clean data before saving";
    } else {
      btnConfirm.disabled = false;
      btnConfirm.style.opacity = '1';
    }

    if (data.status === 'cleaned') {
      btnClean.style.display = 'none';
    }

    // Mapping
    const tbody = document.getElementById('mapping-tbody');
    tbody.innerHTML = '';
    for (const [orig, canon] of Object.entries(data.mapping)) {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td>${orig}</td><td><strong>${canon}</strong></td>`;
      tbody.appendChild(tr);
    }
    if (Object.keys(data.mapping).length === 0) {
      tbody.innerHTML = `<tr><td colspan="2" style="color:#d32f2f">Could not detect any known columns. Please check your file format.</td></tr>`;
    }

    // Issues
    const list = document.getElementById('issues-list');
    list.innerHTML = '';
    if (data.issues.length === 0 && data.stats.duplicates === 0) {
      list.innerHTML = `<div class="issue-item"><div class="issue-content" style="color:#388e3c">No issues found. Data looks perfect!</div></div>`;
    } else {
      data.issues.forEach(iss => {
        const div = document.createElement('div');
        div.className = `issue-item ${iss.type}`;
        const icon = iss.type === 'error' ? '🔴' : '🟡';
        div.innerHTML = `
          <div class="issue-icon">${icon}</div>
          <div class="issue-content">
            <div class="issue-row">Row ${iss.row}</div>
            <div>${iss.message}</div>
          </div>
        `;
        list.appendChild(tr = div);
      });
    }

    contentDiv.style.display = 'block';
  }

  btnClean.addEventListener('click', async () => {
    setButtonState(true);
    actionMessage.textContent = 'Cleaning data...';
    actionMessage.className = 'auth-message';
    
    try {
      const resp = await fetch(`/api/data/clean/${jobId}`, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await resp.json();
      
      if (!resp.ok) {
        showMessage(data.detail || 'Cleaning failed.', 'error');
        setButtonState(false);
        return;
      }
      
      showMessage('Data cleaned successfully.', 'success');
      // reload validation state
      loadValidation();
    } catch (err) {
      showMessage('Network error during cleaning.', 'error');
      setButtonState(false);
    }
  });

  btnConfirm.addEventListener('click', async () => {
    setButtonState(true);
    actionMessage.textContent = 'Saving data to database...';
    actionMessage.className = 'auth-message';
    
    try {
      const resp = await fetch(`/api/data/confirm/${jobId}`, {
        method: 'POST',
        headers: { 'Authorization': 'Bearer ' + token }
      });
      const data = await resp.json();
      
      if (!resp.ok) {
        showMessage(data.detail || 'Saving failed.', 'error');
        setButtonState(false);
        return;
      }
      
      showMessage('Success! Data saved securely. Redirecting...', 'success');
      setTimeout(() => { window.location.href = '/dashboard'; }, 1500);
    } catch (err) {
      showMessage('Network error during save.', 'error');
      setButtonState(false);
    }
  });

  // Initial load
  loadValidation();
});
