/**
 * AI Business Twin — Auth Form Handler
 * Handles login and register form submissions via the API.
 */

document.addEventListener('DOMContentLoaded', () => {
  // If user already has a token, redirect to dashboard
  const existingToken = localStorage.getItem('access_token');
  if (existingToken) {
    window.location.href = '/dashboard';
    return;
  }

  const messageEl = document.getElementById('auth-message');
  const submitBtn = document.getElementById('submit-btn');

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
    submitBtn.textContent = loading
      ? (loginForm ? 'Logging in…' : 'Creating account…')
      : (loginForm ? 'Log In' : 'Create Account');
  }

  // --- Login form ---
  const loginForm = document.getElementById('login-form');
  if (loginForm) {
    loginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearMessage();

      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;

      if (!email || !password) {
        showMessage('Please fill in all fields.', 'error');
        return;
      }

      setLoading(true);
      try {
        const resp = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });

        const data = await resp.json();

        if (!resp.ok) {
          showMessage(data.detail || 'Login failed. Please try again.', 'error');
          setLoading(false);
          return;
        }

        // Store token and check business status
        localStorage.setItem('access_token', data.access_token);
        
        // Check if user has a business setup
        const bizResp = await fetch('/api/business', {
          headers: { 'Authorization': 'Bearer ' + data.access_token }
        });
        
        if (bizResp.ok) {
          showMessage('Login successful! Redirecting to dashboard…', 'success');
          setTimeout(() => { window.location.href = '/dashboard'; }, 500);
        } else {
          showMessage('Login successful! Redirecting to setup…', 'success');
          setTimeout(() => { window.location.href = '/setup'; }, 500);
        }
      } catch (err) {
        showMessage('Network error. Please check your connection.', 'error');
        setLoading(false);
      }
    });
  }

  // --- Register form ---
  const registerForm = document.getElementById('register-form');
  if (registerForm) {
    registerForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      clearMessage();

      const name = document.getElementById('name').value.trim();
      const email = document.getElementById('email').value.trim();
      const password = document.getElementById('password').value;

      if (!name || !email || !password) {
        showMessage('Please fill in all fields.', 'error');
        return;
      }

      if (password.length < 8) {
        showMessage('Password must be at least 8 characters.', 'error');
        return;
      }

      setLoading(true);
      try {
        const resp = await fetch('/api/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ name, email, password }),
        });

        const data = await resp.json();

        if (!resp.ok) {
          showMessage(data.detail || 'Registration failed. Please try again.', 'error');
          setLoading(false);
          return;
        }

        // Auto-login after registration
        const loginResp = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        });

        const loginData = await loginResp.json();

        if (loginResp.ok) {
          localStorage.setItem('access_token', loginData.access_token);
          showMessage('Account created! Redirecting to setup…', 'success');
          setTimeout(() => { window.location.href = '/setup'; }, 500);
        } else {
          showMessage('Account created! Please log in.', 'success');
          setTimeout(() => { window.location.href = '/login'; }, 1500);
        }
      } catch (err) {
        showMessage('Network error. Please check your connection.', 'error');
        setLoading(false);
      }
    });
  }
});
