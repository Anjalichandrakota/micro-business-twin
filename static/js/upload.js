/**
 * AI Business Twin — Data Upload Form Handler
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');

  // If no token, redirect to login
  if (!token) {
    window.location.href = '/login';
    return;
  }

  // Logout handler
  const logoutBtn = document.getElementById('logout-btn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      localStorage.removeItem('access_token');
      window.location.href = '/';
    });
  }

  const uploadForm = document.getElementById('upload-form');
  const uploadArea = document.getElementById('upload-area');
  const fileInput = document.getElementById('file_input');
  const fileSelected = document.getElementById('file-selected');
  const fileNameDisplay = document.getElementById('file-name-display');
  const btnRemoveFile = document.getElementById('btn-remove-file');
  const messageEl = document.getElementById('upload-message');
  const uploadBtn = document.getElementById('upload-btn');

  function showMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = 'auth-message ' + type;
  }

  function clearMessage() {
    messageEl.textContent = '';
    messageEl.className = 'auth-message';
  }

  function setLoading(loading) {
    uploadBtn.disabled = loading;
    uploadBtn.textContent = loading ? 'Uploading...' : 'Upload Data';
  }

  // File selection UI handlers
  function handleFileSelect(file) {
    if (!file) return;
    
    // Check extension
    const ext = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    if (ext !== '.csv' && ext !== '.xlsx' && ext !== '.xls') {
      showMessage('Invalid file type. Only CSV and Excel are supported.', 'error');
      fileInput.value = '';
      return;
    }

    clearMessage();
    fileNameDisplay.textContent = file.name;
    uploadArea.style.display = 'none';
    fileSelected.style.display = 'flex';
  }

  function resetFile() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileSelected.style.display = 'none';
    clearMessage();
  }

  uploadArea.addEventListener('click', () => fileInput.click());
  btnRemoveFile.addEventListener('click', resetFile);

  uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.classList.add('dragover');
  });

  uploadArea.addEventListener('dragleave', () => {
    uploadArea.classList.remove('dragover');
  });

  uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      fileInput.files = e.dataTransfer.files;
      handleFileSelect(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleFileSelect(e.target.files[0]);
    }
  });

  // Form Submission
  if (uploadForm) {
    uploadForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearMessage();

      const dataType = document.getElementById('data_type').value;
      if (!dataType) {
        showMessage('Please select a data type.', 'error');
        return;
      }

      if (!fileInput.files.length) {
        showMessage('Please select a file to upload.', 'error');
        return;
      }

      const file = fileInput.files[0];
      const formData = new FormData();
      formData.append('data_type', dataType);
      formData.append('file', file);

      setLoading(true);
      try {
        const resp = await fetch('/api/data/upload', {
          method: 'POST',
          headers: {
            'Authorization': 'Bearer ' + token
          },
          body: formData
        });

        const data = await resp.json();

        if (!resp.ok) {
          if (resp.status === 400 && data.detail.includes("set up your business")) {
            window.location.href = '/setup';
            return;
          }
          showMessage(data.detail || 'Upload failed. Please try again.', 'error');
          setLoading(false);
          return;
        }

        showMessage(`Successfully uploaded. Redirecting to validation...`, 'success');
        setTimeout(() => {
          window.location.href = `/validate?job_id=${data.job_id}`;
        }, 1000);
      } catch (err) {
        showMessage('Network error. Please check your connection.', 'error');
      } finally {
        setLoading(false);
      }
    });
  }
});
