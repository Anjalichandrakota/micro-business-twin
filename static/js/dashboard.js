/**
 * AI Business Twin — Dashboard Logic
 * Fetches analytics data and renders KPIs, charts, tables.
 */

document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('access_token');
  if (!token) { window.location.href = '/login'; return; }

  const loadingEl = document.getElementById('loading-state');
  const emptyEl = document.getElementById('empty-state');
  const contentEl = document.getElementById('dashboard-content');

  // Logout
  document.getElementById('logout-btn').addEventListener('click', () => {
    localStorage.removeItem('access_token');
    window.location.href = '/';
  });

  // Check business exists
  fetch('/api/business', { headers: { 'Authorization': 'Bearer ' + token } })
    .then(r => {
      if (r.status === 404) { window.location.href = '/setup'; return null; }
      if (!r.ok) { localStorage.removeItem('access_token'); window.location.href = '/login'; return null; }
      return r.json();
    })
    .then(biz => {
      if (!biz) return;
      document.getElementById('user-name').textContent = biz.business_name;
      loadAnalytics();
    })
    .catch(() => { localStorage.removeItem('access_token'); window.location.href = '/login'; });

  let currentView = 'monthly';
  let analyticsData = null;

  async function loadAnalytics(dateFrom, dateTo) {
    loadingEl.style.display = 'flex';
    emptyEl.style.display = 'none';
    contentEl.style.display = 'none';

    let url = '/api/analytics';
    const params = [];
    if (dateFrom) params.push(`date_from=${dateFrom}`);
    if (dateTo) params.push(`date_to=${dateTo}`);
    if (params.length) url += '?' + params.join('&');

    try {
      const resp = await fetch(url, { headers: { 'Authorization': 'Bearer ' + token } });
      if (!resp.ok) { loadingEl.style.display = 'none'; emptyEl.style.display = 'flex'; return; }
      analyticsData = await resp.json();

      if (!analyticsData.has_sales && !analyticsData.has_inventory && !analyticsData.has_expenses) {
        loadingEl.style.display = 'none';
        emptyEl.style.display = 'flex';
        return;
      }

      renderDashboard(analyticsData);
      loadingEl.style.display = 'none';
      contentEl.style.display = 'block';
    } catch (e) {
      loadingEl.style.display = 'none';
      emptyEl.style.display = 'flex';
    }
  }

  function fmt(n, currency) {
    if (n === undefined || n === null) return '—';
    const c = currency || '₹';
    if (Math.abs(n) >= 1e6) return c + (n / 1e6).toFixed(1) + 'M';
    if (Math.abs(n) >= 1e3) return c + (n / 1e3).toFixed(1) + 'K';
    return c + n.toLocaleString('en-IN', { maximumFractionDigits: 2 });
  }

  function num(n) {
    if (n === undefined || n === null) return '—';
    return n.toLocaleString('en-IN', { maximumFractionDigits: 0 });
  }

  function renderDashboard(data) {
    const biz = data.business || {};
    const k = data.kpis || {};
    const cur = biz.currency === 'INR' ? '₹' : (biz.currency === 'USD' ? '$' : biz.currency + ' ');

    document.getElementById('biz-name').textContent = biz.business_name || 'Dashboard';
    document.getElementById('biz-info').textContent = `${biz.business_type || ''} · ${biz.location || ''}`;

    // KPIs
    document.getElementById('kpi-revenue').textContent = fmt(k.total_revenue, cur);
    const rt = document.getElementById('kpi-revenue-trend');
    rt.textContent = k.revenue_trend !== 0 ? `${k.revenue_trend > 0 ? '↑' : '↓'} ${Math.abs(k.revenue_trend)}% trend` : '';
    rt.className = 'kpi-trend ' + (k.revenue_trend > 0 ? 'up' : k.revenue_trend < 0 ? 'down' : 'neutral');

    document.getElementById('kpi-profit').textContent = fmt(k.gross_profit, cur);
    document.getElementById('kpi-margin').textContent = `${k.profit_margin}% margin`;
    document.getElementById('kpi-margin').className = 'kpi-trend ' + (k.profit_margin >= 20 ? 'up' : k.profit_margin > 0 ? 'neutral' : 'down');

    document.getElementById('kpi-orders').textContent = num(k.total_orders);
    document.getElementById('kpi-aov').textContent = `Avg ${fmt(k.avg_order_value, cur)}`;
    document.getElementById('kpi-aov').className = 'kpi-trend neutral';

    document.getElementById('kpi-expenses').textContent = fmt(k.total_expenses, cur);
    const expPct = k.total_revenue > 0 ? Math.round(k.total_expenses / k.total_revenue * 100) : 0;
    document.getElementById('kpi-expense-pct').textContent = `${expPct}% of revenue`;
    document.getElementById('kpi-expense-pct').className = 'kpi-trend ' + (expPct > 80 ? 'down' : 'neutral');

    document.getElementById('kpi-stock').textContent = num(k.total_stock);
    document.getElementById('kpi-products').textContent = `${k.unique_products} products`;
    document.getElementById('kpi-products').className = 'kpi-trend neutral';

    // Revenue chart
    renderRevenueChart(data, currentView, cur);

    // Top products
    renderTopProducts(data.top_products || [], cur);

    // Expense breakdown
    renderExpenses(data.category_breakdown || [], cur);

    // Inventory
    renderInventory(data.inventory_summary || []);

    // Alerts
    renderAlerts(data.alerts || []);
  }

  function renderRevenueChart(data, view, cur) {
    const container = document.getElementById('revenue-bars');
    container.innerHTML = '';
    const items = view === 'monthly' ? (data.monthly_revenue || []) : (data.daily_revenue || []);
    if (!items.length) { container.innerHTML = '<p class="empty-text">No revenue data</p>'; return; }

    const maxRev = Math.max(...items.map(i => i.revenue), 1);
    items.forEach(item => {
      const wrapper = document.createElement('div');
      wrapper.className = 'chart-bar-wrapper';
      const pct = Math.max((item.revenue / maxRev) * 100, 2);
      const label = view === 'monthly' ? item.month : item.date.slice(5);
      wrapper.innerHTML = `
        <div class="chart-bar" style="height:${pct}%">
          <div class="chart-bar-tooltip">${fmt(item.revenue, cur)} · ${item.orders} orders</div>
        </div>
        <span class="chart-bar-label">${label}</span>`;
      container.appendChild(wrapper);
    });
  }

  function renderTopProducts(products, cur) {
    const list = document.getElementById('top-products-list');
    if (!products.length) { list.innerHTML = '<p class="empty-text">No product data available</p>'; return; }
    list.innerHTML = '';
    products.slice(0, 8).forEach((p, i) => {
      const row = document.createElement('div');
      row.className = 'product-row';
      row.innerHTML = `
        <span class="product-rank">${i + 1}</span>
        <span class="product-name">${p.product}</span>
        <span class="product-qty">${num(p.quantity)} units</span>
        <span class="product-value">${fmt(p.revenue, cur)}</span>`;
      list.appendChild(row);
    });
  }

  function renderExpenses(categories, cur) {
    const container = document.getElementById('expense-chart');
    if (!categories.length) { container.innerHTML = '<p class="empty-text">No expense data available</p>'; return; }
    const maxAmt = Math.max(...categories.map(c => c.total), 1);
    container.innerHTML = '';
    categories.slice(0, 8).forEach(cat => {
      const pct = (cat.total / maxAmt) * 100;
      const row = document.createElement('div');
      row.className = 'expense-bar-row';
      row.innerHTML = `
        <span class="expense-bar-label">${cat.category}</span>
        <div class="expense-bar-track"><div class="expense-bar-fill" style="width:${pct}%"></div></div>
        <span class="expense-bar-value">${fmt(cat.total, cur)}</span>`;
      container.appendChild(row);
    });
  }

  function renderInventory(items) {
    const list = document.getElementById('inventory-list');
    if (!items.length) { list.innerHTML = '<p class="empty-text">No inventory data available</p>'; return; }
    list.innerHTML = '';
    items.slice(0, 10).forEach(item => {
      const cls = item.total_quantity <= 10 ? 'low' : 'ok';
      const row = document.createElement('div');
      row.className = 'inventory-row';
      row.innerHTML = `
        <span class="inventory-name">${item.product}</span>
        <span class="inventory-qty ${cls}">${num(item.total_quantity)} units</span>`;
      list.appendChild(row);
    });
  }

  function renderAlerts(alerts) {
    const section = document.getElementById('alerts-section');
    const list = document.getElementById('alerts-list');
    if (!alerts.length) { section.style.display = 'none'; return; }
    section.style.display = 'block';
    list.innerHTML = '';
    alerts.forEach(a => {
      const item = document.createElement('div');
      item.className = `alert-item ${a.type}`;
      item.innerHTML = `
        <span class="alert-icon">${a.type === 'error' ? '🔴' : '🟡'}</span>
        <div class="alert-content">
          <div class="alert-title">${a.title}</div>
          <div class="alert-message">${a.message}</div>
        </div>`;
      list.appendChild(item);
    });
  }

  // Chart tabs
  document.getElementById('tab-monthly')?.addEventListener('click', () => {
    currentView = 'monthly';
    document.getElementById('tab-monthly').classList.add('active');
    document.getElementById('tab-daily').classList.remove('active');
    if (analyticsData) renderRevenueChart(analyticsData, 'monthly', getCur());
  });
  document.getElementById('tab-daily')?.addEventListener('click', () => {
    currentView = 'daily';
    document.getElementById('tab-daily').classList.add('active');
    document.getElementById('tab-monthly').classList.remove('active');
    if (analyticsData) renderRevenueChart(analyticsData, 'daily', getCur());
  });

  function getCur() {
    if (!analyticsData || !analyticsData.business) return '₹';
    const c = analyticsData.business.currency;
    return c === 'INR' ? '₹' : c === 'USD' ? '$' : c + ' ';
  }

  // Date filter
  document.getElementById('apply-filter')?.addEventListener('click', () => {
    const from = document.getElementById('date-from').value;
    const to = document.getElementById('date-to').value;
    loadAnalytics(from || null, to || null);
  });
});
