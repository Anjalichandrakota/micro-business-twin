/**
 * AI Business Twin — What-If Scenario Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) { window.location.href = '/login'; return; }

  // Logout
  document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('access_token');
    window.location.href = '/';
  });

  // Load business name + products
  fetch('/api/business', { headers: { 'Authorization': 'Bearer ' + token } })
    .then(r => {
      if (r.status === 404) { window.location.href = '/setup'; return null; }
      if (!r.ok) { localStorage.removeItem('access_token'); window.location.href = '/login'; return null; }
      return r.json();
    })
    .then(biz => {
      if (biz) {
        document.getElementById('user-name').textContent = biz.business_name;
        loadProducts();
      }
    })
    .catch(() => {});

  async function loadProducts() {
    try {
      const resp = await fetch('/api/analytics/products', {
        headers: { 'Authorization': 'Bearer ' + token }
      });
      if (resp.ok) {
        const data = await resp.json();
        const sel = document.getElementById('scenario-product');
        (data.products || []).forEach(p => {
          const opt = document.createElement('option');
          opt.value = p;
          opt.textContent = p;
          sel.appendChild(opt);
        });
      }
    } catch (e) {}
  }

  // Show/hide absolute change field
  document.getElementById('scenario-type').addEventListener('change', (e) => {
    const absGroup = document.getElementById('abs-group');
    absGroup.style.display = e.target.value === 'quantity_change' ? 'flex' : 'none';
  });

  const messageEl = document.getElementById('whatif-message');
  const resultsEl = document.getElementById('whatif-results');

  function showMsg(text, type) {
    messageEl.textContent = text;
    messageEl.className = 'auth-message ' + type;
  }

  function fmt(n) {
    if (n === undefined || n === null) return '—';
    return n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  }

  document.getElementById('run-scenario').addEventListener('click', async () => {
    const scenarioType = document.getElementById('scenario-type').value;
    const product = document.getElementById('scenario-product').value;
    const changePct = parseFloat(document.getElementById('scenario-pct').value) || 0;
    const changeAbs = parseFloat(document.getElementById('scenario-abs').value) || 0;

    if (changePct === 0 && changeAbs === 0) {
      showMsg('Please enter a change percentage or absolute value.', 'error');
      return;
    }

    const scenario = {
      type: scenarioType,
      change_percent: changePct,
    };
    if (product) scenario.product = product;
    if (changeAbs) scenario.change_absolute = changeAbs;

    const btn = document.getElementById('run-scenario');
    btn.disabled = true;
    btn.textContent = 'Running...';
    messageEl.className = 'auth-message';
    messageEl.textContent = '';

    try {
      const resp = await fetch('/api/analytics/whatif', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify(scenario)
      });

      const data = await resp.json();

      if (!resp.ok) {
        showMsg(data.detail || 'Scenario failed.', 'error');
        btn.disabled = false;
        btn.textContent = 'Run Scenario';
        return;
      }

      renderResults(data);
    } catch (e) {
      showMsg('Network error. Please try again.', 'error');
    }

    btn.disabled = false;
    btn.textContent = 'Run Scenario';
  });

  function renderResults(data) {
    const cur = data.current || {};
    const proj = data.projected || {};
    const impact = data.impact || {};

    document.getElementById('cur-revenue').textContent = '₹' + fmt(cur.revenue);
    document.getElementById('cur-expenses').textContent = '₹' + fmt(cur.expenses);
    document.getElementById('cur-profit').textContent = '₹' + fmt(cur.profit);

    document.getElementById('proj-revenue').textContent = '₹' + fmt(proj.revenue);
    document.getElementById('proj-expenses').textContent = '₹' + fmt(proj.expenses);
    document.getElementById('proj-profit').textContent = '₹' + fmt(proj.profit);

    const revEl = document.getElementById('impact-revenue');
    revEl.textContent = `${impact.revenue_change >= 0 ? '+' : ''}₹${fmt(impact.revenue_change)} (${impact.revenue_change_pct >= 0 ? '+' : ''}${impact.revenue_change_pct}%)`;
    revEl.className = 'impact-value ' + (impact.revenue_change >= 0 ? 'positive' : 'negative');

    const profEl = document.getElementById('impact-profit');
    profEl.textContent = `${impact.profit_change >= 0 ? '+' : ''}₹${fmt(impact.profit_change)} (${impact.profit_change_pct >= 0 ? '+' : ''}${impact.profit_change_pct}%)`;
    profEl.className = 'impact-value ' + (impact.profit_change >= 0 ? 'positive' : 'negative');

    document.getElementById('whatif-explanation').textContent = data.explanation || '';
    document.getElementById('whatif-disclaimer').textContent = data.disclaimer || '';

    resultsEl.style.display = 'block';
    resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }
});
