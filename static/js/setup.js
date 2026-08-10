/**
 * AI Business Twin — Business Setup Form Handler
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');

  // If no token, redirect to login
  if (!token) {
    window.location.href = '/login';
    return;
  }

  // Check if business already exists
  fetch('/api/business', {
    headers: { 'Authorization': 'Bearer ' + token }
  })
  .then(resp => {
    if (resp.ok) {
      // Business exists, redirect to dashboard
      window.location.href = '/dashboard';
    }
  })
  .catch(err => console.error("Error checking business:", err));

  const messageEl = document.getElementById('setup-message');
  const submitBtn = document.getElementById('setup-btn');
  const setupForm = document.getElementById('setup-form');

  function showMessage(text, type) {
    messageEl.textContent = text;
    messageEl.className = 'auth-message ' + type;
  }

  function clearMessage() {
    messageEl.textContent = '';
    messageEl.className = 'auth-message';
  }

  function setLoading(loading) {
    submitBtn.disabled = loading;
    submitBtn.textContent = loading ? 'Saving...' : 'Complete Setup';
  }

  if (setupForm) {
    setupForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearMessage();

      const business_name = document.getElementById('business_name').value.trim();
      const business_type = document.getElementById('business_type').value.trim();
      const location = document.getElementById('location').value.trim();
      const currency = document.getElementById('currency').value.trim();

      if (!business_name || !business_type || !location || !currency) {
        showMessage('Please fill in all fields.', 'error');
        return;
      }

      setLoading(true);
      try {
        const resp = await fetch('/api/business', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
          },
          body: JSON.stringify({ business_name, business_type, location, currency }),
        });

        const data = await resp.json();

        if (!resp.ok) {
          showMessage(data.detail || 'Setup failed. Please try again.', 'error');
          setLoading(false);
          return;
        }

        showMessage('Setup complete! Redirecting...', 'success');
        setTimeout(() => { window.location.href = '/dashboard'; }, 500);
      } catch (err) {
        showMessage('Network error. Please check your connection.', 'error');
        setLoading(false);
      }
    });
  }
});
