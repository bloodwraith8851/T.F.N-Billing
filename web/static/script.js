// ============================================================
// APP STATE
// ============================================================
let revenueChart       = null;
let statusChart        = null;
let monthlyChart       = null;   // analytics monthly
let planChart          = null;   // analytics plan
let dashMonthlyChart   = null;   // dashboard monthly bar
let dashPlanChart      = null;   // dashboard plan donut
let _currentCustomerId = null;

let activeFilter = { from: null, to: null, label: 'month' };

// Calendar state
let calMonth = new Date().getMonth();
let calYear  = new Date().getFullYear();

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTheme();
    initStarField();
    initParallax();
    initShootingStars();
    initCalendar();

    // Flatpickr Datepickers
    if (window.flatpickr) {
        flatpickr('#inv-billing_from', { dateFormat: 'd-M-Y', defaultDate: new Date() });
        const nextMonth = new Date();
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        flatpickr('#inv-billing_to', { dateFormat: 'd-M-Y', defaultDate: nextMonth });
        
        flatpickr('#dp-from', { dateFormat: 'd-M-Y' });
        flatpickr('#dp-to', { dateFormat: 'd-M-Y' });
    }

    // Load initial data
    const d = new Date();
    const m = d.getMonth() + 1;
    const y = d.getFullYear();
    const lastDay = new Date(y, m, 0).getDate();
    activeFilter.from = `${y}-${m.toString().padStart(2,'0')}-01`;
    activeFilter.to   = `${y}-${m.toString().padStart(2,'0')}-${lastDay.toString().padStart(2,'0')}`;
    loadDashboard();

    // Auto-update check
    setTimeout(checkForUpdates, 3000);

    // Invoice form submit
    document.getElementById('invoiceForm')?.addEventListener('submit', handleInvoiceSubmit);
    document.getElementById('inv-months')?.addEventListener('input', calculateTotal);
    document.getElementById('inv-plan')?.addEventListener('change', calculateTotal);

    // Customer select autofill
    const customerSelectEl = document.getElementById('customerSelect');
    if (customerSelectEl) {
        customerSelectEl.addEventListener('change', function () {
            if (!this.value) { document.getElementById('invoiceForm')?.reset(); return; }
            try {
                const data = JSON.parse(this.value);
                document.getElementById('inv-name').value             = data.name             || '';
                document.getElementById('inv-customer_id').value      = data.customer_id      || '';
                document.getElementById('inv-tenant_name').value      = data.tenant_name      || '';
                document.getElementById('inv-phone').value            = data.phone            || '';
                document.getElementById('inv-customer_address').value = data.customer_address || '';
                document.getElementById('inv-customer_gstin').value   = data.customer_gstin   || '';
            } catch (err) { console.error('Could not parse customer data:', err); }
        });
    }

    // Duplicate check on billing date / customer ID change
    ['inv-customer_id', 'inv-billing_from', 'inv-billing_to'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', checkDuplicateInvoice);
    });

    // Log search / filter / date
    const logSearch   = document.getElementById('log-search');
    const logFilter   = document.getElementById('log-status-filter');
    const logDateFrom = document.getElementById('log-date-from');
    const logDateTo   = document.getElementById('log-date-to');
    if (logSearch)   logSearch.addEventListener('input', filterLogs);
    if (logFilter)   logFilter.addEventListener('change', filterLogs);
    if (logDateFrom) logDateFrom.addEventListener('change', filterLogs);
    if (logDateTo)   logDateTo.addEventListener('change', filterLogs);

    // Customer search / filter
    const custSearch = document.getElementById('customer-search');
    const custStatus = document.getElementById('customer-status-filter');
    if (custSearch) custSearch.addEventListener('input', filterCustomers);
    if (custStatus) custStatus.addEventListener('change', filterCustomers);


    // Period tabs — update active + date range pill
    updateDateRangePill('month'); // initial
    document.querySelectorAll('.period-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            // clear calendar selection
            document.querySelectorAll('.cal-cell.selected').forEach(c => c.classList.remove('selected'));
            
            const period = tab.dataset.period;
            updateDateRangePill(period);
            
            // compute dates using local timezone, NOT toISOString() which shifts to UTC
            const now = new Date();
            const formatLocal = (d) => `${d.getFullYear()}-${(d.getMonth()+1).toString().padStart(2,'0')}-${d.getDate().toString().padStart(2,'0')}`;
            
            let from, to;
            
            if (period === 'day') {
                from = to = formatLocal(now);
            } else if (period === 'week') {
                const day = now.getDay();
                const diff = day === 0 ? -6 : 1 - day;
                const start = new Date(now); start.setDate(now.getDate() + diff);
                const end = new Date(start); end.setDate(start.getDate() + 6);
                from = formatLocal(start);
                to = formatLocal(end);
            } else if (period === 'month') {
                const start = new Date(now.getFullYear(), now.getMonth(), 1);
                const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
                from = `${now.getFullYear()}-${(now.getMonth()+1).toString().padStart(2,'0')}-01`;
                to = `${now.getFullYear()}-${(now.getMonth()+1).toString().padStart(2,'0')}-${end.getDate().toString().padStart(2,'0')}`;
            } else if (period === 'year') {
                from = `${now.getFullYear()}-01-01`;
                to = `${now.getFullYear()}-12-31`;
            }
            activeFilter.from = from;
            activeFilter.to = to;
            activeFilter.label = period;
            applyDateFilter(from, to);
        });
    });


    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Close notification panel on outside click
    document.addEventListener('click', e => {
        const panel = document.getElementById('notification-panel');
        const btn   = document.getElementById('notif-btn');
        if (panel && !panel.contains(e.target) && btn && !btn.contains(e.target)) {
            panel.classList.add('hidden');
        }
    });

    loadNotifications();
    startClock();
});

// ============================================================
// ★ STAR FIELD — Canvas-based twinkling stars
// ============================================================
function initStarField() {
    const canvas = document.getElementById('stars-canvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let stars   = [];
    let animId  = null;

    function resize() {
        canvas.width  = window.innerWidth;
        canvas.height = window.innerHeight;
        generateStars();
    }

    function generateStars() {
        const density = Math.floor((canvas.width * canvas.height) / 7000);
        stars = Array.from({ length: Math.min(density, 280) }, () => ({
            x:      Math.random() * canvas.width,
            y:      Math.random() * canvas.height,
            r:      Math.random() * 1.6 + 0.2,
            alpha:  Math.random(),
            phase:  Math.random() * Math.PI * 2,
            speed:  Math.random() * 0.008 + 0.002,
            color:  ['255,255,255', '180,200,255', '255,240,180', '200,180,255'][Math.floor(Math.random() * 4)],
        }));
    }

    function drawStars(ts) {
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        const t = ts * 0.001;
        for (const s of stars) {
            const a = (Math.sin(t * s.speed * 60 + s.phase) * 0.5 + 0.5) * 0.85 + 0.1;
            ctx.beginPath();
            ctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(${s.color},${a.toFixed(2)})`;
            ctx.fill();
        }
        animId = requestAnimationFrame(drawStars);
    }

    window.addEventListener('resize', resize);
    resize();
    animId = requestAnimationFrame(drawStars);
}

// ============================================================
// ★ PARALLAX — Mouse-driven cloud layer movement
// ============================================================
function initParallax() {
    const layers = document.querySelectorAll('.cloud-row[data-parallax]');
    if (!layers.length) return;
    let cx = window.innerWidth  / 2;
    let cy = window.innerHeight / 2;

    window.addEventListener('resize', () => {
        cx = window.innerWidth  / 2;
        cy = window.innerHeight / 2;
    });

    document.addEventListener('mousemove', e => {
        const dx = (e.clientX - cx) / cx;
        const dy = (e.clientY - cy) / cy;
        layers.forEach(layer => {
            const speed = parseFloat(layer.dataset.parallax) || 0.03;
            const tx = dx * speed * 70;
            const ty = dy * speed * 35;
            layer.style.transform = `translate(${tx}px, ${ty}px)`;
        });
    });
}

// ============================================================
// ★ SHOOTING STARS — Random spawning
// ============================================================
function initShootingStars() {
    const wrap = document.getElementById('shooting-stars-wrap');
    if (!wrap) return;

    function spawnStar() {
        const star = document.createElement('div');
        star.className = 'shooting-star';
        // Random position in upper 70% of screen
        star.style.top   = (Math.random() * 55 + 5)  + '%';
        star.style.left  = (Math.random() * 55 + 5)  + '%';
        const dur = (Math.random() * 0.8 + 0.5).toFixed(2);
        star.style.animationDuration = dur + 's';
        wrap.appendChild(star);
        star.addEventListener('animationend', () => star.remove());

        // Schedule next star
        const next = 2500 + Math.random() * 5000;
        setTimeout(spawnStar, next);
    }

    // First star after a short delay
    setTimeout(spawnStar, 1500 + Math.random() * 3000);
}

// ============================================================
// ★ MINI CALENDAR
// ============================================================
function initCalendar() {
    renderCalendar();
    document.getElementById('cal-prev')?.addEventListener('click', () => {
        calMonth--;
        if (calMonth < 0) { calMonth = 11; calYear--; }
        renderCalendar();
    });
    document.getElementById('cal-next')?.addEventListener('click', () => {
        calMonth++;
        if (calMonth > 11) { calMonth = 0; calYear++; }
        renderCalendar();
    });
}

function renderCalendar() {
    const titleEl = document.getElementById('cal-month-title');
    const gridEl  = document.getElementById('cal-grid');
    if (!titleEl || !gridEl) return;

    const MONTHS = ['January','February','March','April','May','June',
                    'July','August','September','October','November','December'];
    titleEl.textContent = `${MONTHS[calMonth]} ${calYear}`;

    const firstDay    = new Date(calYear, calMonth, 1).getDay();
    const daysInMonth = new Date(calYear, calMonth + 1, 0).getDate();
    const today       = new Date();

    gridEl.innerHTML = '';

    // Empty prefix cells
    for (let i = 0; i < firstDay; i++) {
        const cell = document.createElement('div');
        cell.className = 'cal-cell cal-empty';
        gridEl.appendChild(cell);
    }

    for (let d = 1; d <= daysInMonth; d++) {
        const cell = document.createElement('div');
        cell.className = 'cal-cell';
        cell.textContent = d;
        if (d === today.getDate() &&
            calMonth === today.getMonth() &&
            calYear  === today.getFullYear()) {
            cell.classList.add('cal-today');
        }
        
        // Add click listener for filtering
        cell.addEventListener('click', () => {
            document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.cal-cell.selected').forEach(c => c.classList.remove('selected'));
            cell.classList.add('selected');
            
            const selectedDate = `${calYear}-${(calMonth+1).toString().padStart(2,'0')}-${d.toString().padStart(2,'0')}`;
            updateDateRangePill('custom', selectedDate, selectedDate);
            
            activeFilter.from = selectedDate;
            activeFilter.to = selectedDate;
            activeFilter.label = 'custom';
            applyDateFilter(selectedDate, selectedDate);
        });
        
        gridEl.appendChild(cell);
    }
}

// ============================================================
// NAVIGATION
// ============================================================
function initNavigation() {
    window.switchView = (viewId) => {
        document.querySelectorAll('.nav-links li').forEach(li => {
            li.classList.remove('active');
            if (li.getAttribute('data-view') === viewId) li.classList.add('active');
        });
        document.querySelectorAll('.view').forEach(v => {
            v.classList.remove('active-view');
            v.classList.add('hidden-view');
        });
        const activeView = document.getElementById(viewId);
        if (activeView) {
            activeView.classList.remove('hidden-view');
            activeView.classList.add('active-view');
        }

        // Update page title in header
        const titles = {
            dashboard:         'Billing Dashboard',
            'new-invoice':     'Create Invoice',
            customers:         'Customer Directory',
            analytics:         'Analytics',
            logs:              'Invoice History',
            settings:          'Settings',
            'customer-profile':'Customer Profile',
        };
        const titleEl = document.getElementById('page-title');
        if (titleEl) titleEl.textContent = titles[viewId] || viewId;

        if (viewId === 'dashboard')  loadDashboard();
        if (viewId === 'customers')  loadCustomers();
        if (viewId === 'logs')       loadHistory();
        if (viewId === 'settings')   loadSettings();
        if (viewId === 'analytics')  loadAnalytics();
        updateSidebarIndicator(viewId);
    };

    document.querySelectorAll('[data-view]').forEach(item => {
        item.addEventListener('click', e => {
            window.switchView(e.currentTarget.getAttribute('data-view'));
        });
    });
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
function handleKeyboardShortcuts(e) {
    if (e.ctrlKey) {
        if (e.key === 'n' || e.key === 'N') { e.preventDefault(); window.switchView('new-invoice'); }
        if (e.key === 'h' || e.key === 'H') { e.preventDefault(); window.switchView('logs'); }
        if (e.key === 's' || e.key === 'S') {
            e.preventDefault();
            const settings = document.getElementById('settings');
            if (settings && settings.classList.contains('active-view')) saveSettings();
            else window.switchView('settings');
        }
    }
}

// ============================================================
// DASHBOARD & DATE FILTERING
// ============================================================

function toggleDatePicker() {
    const panel = document.getElementById('date-picker-panel');
    if (panel) panel.classList.toggle('hidden');
}

function applyCustomDateRange() {
    let fromInput = document.getElementById('dp-from').value;
    let toInput   = document.getElementById('dp-to').value;
    
    // Convert DD-MMM-YYYY to YYYY-MM-DD
    const parseFlatpickrDate = (val) => {
        if (!val) return null;
        const d = new Date(val);
        return `${d.getFullYear()}-${(d.getMonth()+1).toString().padStart(2,'0')}-${d.getDate().toString().padStart(2,'0')}`;
    };
    
    const from = parseFlatpickrDate(fromInput);
    const to = parseFlatpickrDate(toInput);
    
    if (from && to) {
        document.querySelectorAll('.period-tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.cal-cell.selected').forEach(c => c.classList.remove('selected'));
        
        activeFilter.from = from;
        activeFilter.to = to;
        activeFilter.label = 'custom';
        
        updateDateRangePill('custom', from, to);
        applyDateFilter(from, to);
        toggleDatePicker();
    }
}

async function applyDateFilter(from, to) {
    if (!from || !to) return;
    try {
        const data = await eel.get_filtered_dashboard(from, to)();
        
        // 1. Stats
        const stats = data.stats;
        animateCounter(document.getElementById('stat-paid'),    stats.paid,    '₹', 1000);
        animateCounter(document.getElementById('stat-pending'), stats.pending, '₹', 1000);
        animateCounter(document.getElementById('stat-total'),   stats.revenue, '₹', 1000);

        const countSubEl = document.getElementById('stat-count-sub');
        if (countSubEl) countSubEl.textContent = (stats.invoice_count ?? 0) + ' Invoices Generated';

        const countEl = document.getElementById('stat-count');
        if (countEl) countEl.textContent = stats.invoice_count ?? 0;

        // 2. Collection Rate
        const rate = data.collection_rate || 0;
        const rateText = rate + '%';
        const statRate = document.getElementById('stat-rate');
        if (statRate) statRate.textContent = rateText;
        const cgwLabel = document.getElementById('cgw-rate-label');
        if (cgwLabel) cgwLabel.textContent = rateText;

        const circle = document.getElementById('rate-ring-fill');
        if (circle) {
            const circumference = 2 * Math.PI * 34;
            const offset = circumference - (rate / 100) * circumference;
            circle.style.strokeDashoffset = offset;
            injectRateGradient();
        }
        
        // 3. Charts
        updateCharts(stats);
        
        // 4. Monthly Chart
        setChartDefaults();
        const ctxDM = document.getElementById('dashMonthlyChart');
        if (ctxDM) {
            if (dashMonthlyChart) dashMonthlyChart.destroy();
            const revenues = data.monthly.revenues || [];
            const labels = data.monthly.months || [];
            
            // If Day view and 0/1 elements, gracefully display
            dashMonthlyChart = new Chart(ctxDM, {
                type: 'bar',
                data: {
                    labels: labels.length ? labels : ['No Data'],
                    datasets: [{
                        label: 'Revenue (₹)',
                        data:  revenues.length ? revenues : [0],
                        backgroundColor: (revenues.length ? revenues : [0]).map((_, i) =>
                            `hsla(${240 + i * 22}, 75%, 65%, 0.75)`),
                        borderRadius: 9,
                        borderSkipped: false,
                        maxBarThickness: 50,
                        hoverBackgroundColor: (revenues.length ? revenues : [0]).map((_, i) =>
                            `hsla(${240 + i * 22}, 75%, 65%, 1)`),
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => ' ₹' + Number(ctx.raw).toLocaleString('en-IN')
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { callback: v => '₹' + v.toLocaleString('en-IN'), font: { size: 10 } },
                            border: { display: false }
                        },
                        x: {
                            grid: { display: false },
                            ticks: { font: { size: 10 } },
                            border: { display: false }
                        }
                    },
                    animation: { duration: 900, easing: 'easeOutCubic' }
                }
            });
        }
        
        // 5. Logs Table
        renderLogsTable(data.logs);
        
    } catch (e) {
        console.error('Date filter error:', e);
        if (typeof showToast === 'function') {
            showToast('error', 'ri-error-warning-line', 'Date Filter Error: ' + e.message);
        }
    }
}

async function loadDashboard() {
    if (activeFilter.from && activeFilter.to) {
        applyDateFilter(activeFilter.from, activeFilter.to);
    }
}

function injectRateGradient() {
    if (document.getElementById('rateGradDef')) return;
    const svg = document.querySelector('.rate-ring');
    if (!svg) return;
    const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
    defs.id = 'rateGradDef';
    defs.innerHTML = `
        <linearGradient id="rateGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%"   stop-color="#6366f1"/>
            <stop offset="100%" stop-color="#10b981"/>
        </linearGradient>`;
    svg.prepend(defs);
}

async function loadOutstandingDues() {
    // Compat shim — outstanding dues display removed from dashboard
    try {
        const dues  = await eel.get_outstanding_dues()();
        const badge = document.getElementById('outstanding-count');
        if (badge) badge.textContent = dues.length;
    } catch (e) { /* silent */ }
}

// ============================================================
// ANALYTICS
// ============================================================
async function loadAnalytics() {
    try {
        const [monthly, plans] = await Promise.all([
            eel.get_monthly_revenue()(),
            eel.get_plan_breakdown()()
        ]);

        setChartDefaults();

        // Monthly Revenue Bar Chart (Analytics page)
        const ctxM = document.getElementById('monthlyRevenueChart');
        if (monthlyChart) monthlyChart.destroy();
        if (ctxM) {
            monthlyChart = new Chart(ctxM, {
                type: 'bar',
                data: {
                    labels: monthly.months || [],
                    datasets: [{
                        label: 'Revenue (₹)',
                        data:  monthly.revenues || [],
                        backgroundColor: (monthly.revenues || []).map((_, i) =>
                            `hsla(${240 + i * 20}, 70%, 65%, 0.75)`),
                        borderRadius: 8,
                        borderSkipped: false,
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false,
                    plugins: { legend: { display: false } },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: { color: 'rgba(255,255,255,0.04)' },
                            ticks: { callback: v => '₹' + v.toLocaleString('en-IN') },
                            border: { display: false }
                        },
                        x: { grid: { display: false }, border: { display: false } }
                    }
                }
            });
        }

        // Plan Breakdown Donut (Analytics page)
        const ctxP = document.getElementById('planBreakdownChart');
        if (planChart) planChart.destroy();
        if (ctxP) {
            const planColors = ['#6366f1','#34d399','#f59e0b','#ef4444','#3b82f6'];
            planChart = new Chart(ctxP, {
                type: 'doughnut',
                data: {
                    labels: plans.plans?.length ? plans.plans : ['No Data'],
                    datasets: [{
                        data:            plans.counts?.length ? plans.counts : [1],
                        backgroundColor: plans.plans?.length ? planColors : ['#334155'],
                        borderWidth: 0, hoverOffset: 6
                    }]
                },
                options: {
                    responsive: true, maintainAspectRatio: false, cutout: '70%',
                    plugins: { legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true } } }
                }
            });
        }
    } catch (e) { console.error('Analytics load error:', e); }
}

// ============================================================
// CUSTOMERS
// ============================================================
async function loadCustomers() {
    const customers = await eel.get_customers()();
    const tbody  = document.getElementById('customers-tbody');
    const select = document.getElementById('customerSelect');

    tbody.innerHTML  = '';
    select.innerHTML = '<option value="">— New Customer —</option>';

    if (customers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);font-weight:500;">No customers found.</td></tr>`;
    } else {
        customers.forEach(c => {
            const initials   = c.name ? c.name.substring(0, 2).toUpperCase() : 'CU';
            const statusHtml = statusBadge(c.connection_status || 'Active');
            const tagsHtml   = (c.tags || '').split(',').filter(t => t.trim()).map(t =>
                `<span class="tag-pill">${t.trim()}</span>`).join('');
            tbody.innerHTML += `
                <tr onclick="viewCustomerProfile('${c.customer_id}')" style="cursor:pointer;">
                    <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;">${c.name}</span></div></td>
                    <td><span style="color:var(--text-muted);font-size:0.82em;">${c.customer_id}</span></td>
                    <td><span style="color:var(--text-muted);">${c.phone || '-'}</span></td>
                    <td><span style="color:var(--text-muted);">${c.tenant_name || '-'}</span></td>
                    <td><span style="font-size:0.82em;color:var(--text-muted);max-width:160px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.customer_address}</span></td>
                    <td>${statusHtml}</td>
                    <td>${tagsHtml}</td>
                </tr>`;
            select.innerHTML += `<option value='${JSON.stringify(c).replace(/'/g, "&#39;")}'>${c.name} (${c.customer_id})</option>`;
        });
    }
    filterCustomers();
}

function filterCustomers() {
    const query  = (document.getElementById('customer-search')?.value  || '').toLowerCase();
    const status = (document.getElementById('customer-status-filter')?.value || 'All');
    document.querySelectorAll('#customers-tbody tr').forEach(tr => {
        const text        = tr.innerText.toLowerCase();
        const matchSearch = !query || text.includes(query);
        const matchStatus = status === 'All' || text.includes(status.toLowerCase());
        tr.style.display  = (matchSearch && matchStatus) ? '' : 'none';
    });
}

function statusBadge(status) {
    const map = { Active: 'status-active', Suspended: 'status-suspended', Terminated: 'status-terminated' };
    return `<span class="conn-badge ${map[status] || 'status-active'}">${status || 'Active'}</span>`;
}

// CSV Import
async function handleCSVImport(input) {
    if (!input.files || !input.files[0]) return;
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const result = await eel.import_customers_csv_data(e.target.result)();
            if (result.status === 'success') {
                showToast('success', 'ri-upload-2-line', result.message);
                loadCustomers();
            } else {
                showToast('error', 'ri-error-warning-line', result.message);
            }
        } catch (err) {
            showToast('error', 'ri-error-warning-line', 'CSV import failed: ' + err);
        }
    };
    reader.readAsText(input.files[0]);
    input.value = '';
}

// ============================================================
// INVOICE HISTORY
// ============================================================
async function loadHistory() {
    const logs  = await eel.get_history()();
    renderLogsTable(logs);
}

function renderLogsTable(logs) {
    const tbody = document.getElementById('logs-tbody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const countEl = document.getElementById('stat-count');
    if (countEl) countEl.textContent = logs.length;

    if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);font-weight:500;">No invoices found.</td></tr>`;
    } else {
        logs.forEach(log => {
            const sc       = log.status === 'Paid' ? 'status-paid' : log.status === 'Partial' ? 'status-partial' : 'status-unpaid';
            const initials = log.customer_name ? log.customer_name.substring(0, 2).toUpperCase() : 'CU';
            tbody.innerHTML += `
                <tr>
                    <td style="color:var(--text-muted);font-size:0.8em;">${log.datetime}</td>
                    <td><span style="color:var(--text-muted);font-size:0.82em;">${log.invoice_num}</span></td>
                    <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;">${log.customer_name}</span></div></td>
                    <td style="font-weight:600;">₹${Number(log.amount).toLocaleString('en-IN')}</td>
                    <td><span class="status-badge ${sc}">${log.status}</span></td>
                    <td><span style="color:var(--text-muted);font-size:0.82em;">${log.payment_method || 'None'}</span></td>
                    <td style="display:flex;gap:5px;align-items:center;flex-wrap:wrap;">
                        <button class="icon-btn" style="width:30px;height:30px;color:#818cf8;" onclick="openPdf('${log.filename}')" title="View PDF"><i class="ri-file-pdf-line"></i></button>
                        <button class="icon-btn" style="width:30px;height:30px;color:#25D366;" onclick="sendWhatsApp('${log.phone || ''}','${log.customer_name}','${log.amount}','${log.invoice_num}','${log.filename}')" title="WhatsApp"><i class="ri-whatsapp-line"></i></button>
                        ${log.status !== 'Paid' ? `<button class="icon-btn" style="width:30px;height:30px;color:var(--success);" onclick="markPaid('${log.invoice_num}')" title="Mark Paid"><i class="ri-check-line"></i></button>` : ''}
                    </td>
                </tr>`;
        });
    }

    // Dashboard recent-tbody (top 5)
    const recentTbody = document.getElementById('recent-tbody');
    if (recentTbody) {
        recentTbody.innerHTML = '';
        if (logs.length === 0) {
            recentTbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:30px;color:var(--text-muted);">No recent transactions</td></tr>`;
        } else {
            logs.slice(0, 6).forEach(log => {
                const sc       = log.status === 'Paid' ? 'status-paid' : log.status === 'Partial' ? 'status-partial' : 'status-unpaid';
                const initials = log.customer_name ? log.customer_name.substring(0, 2).toUpperCase() : 'CU';
                recentTbody.innerHTML += `
                    <tr>
                        <td><span style="color:var(--text-muted);font-size:0.8em;">${log.invoice_num}</span></td>
                        <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;font-size:0.83rem;">${log.customer_name}</span></div></td>
                        <td style="font-weight:600;">₹${Number(log.amount).toLocaleString('en-IN')}</td>
                        <td><span class="status-badge ${sc}">${log.status}</span></td>
                    </tr>`;
            });
        }
    }

    filterLogs();
}

function filterLogs() {
    const query   = (document.getElementById('log-search')?.value || '').toLowerCase();
    const status  = (document.getElementById('log-status-filter')?.value || 'All');
    const fromVal = document.getElementById('log-date-from')?.value || '';
    const toVal   = document.getElementById('log-date-to')?.value   || '';

    document.querySelectorAll('#logs-tbody tr').forEach(tr => {
        const text        = tr.innerText.toLowerCase();
        const matchSearch = !query  || text.includes(query);
        const matchStatus = status === 'All' || text.includes(status.toLowerCase());

        let matchDate = true;
        if (fromVal || toVal) {
            const dateCell = tr.cells[0]?.textContent?.trim() || '';
            const parts    = dateCell.split(' ')[0]?.split('-') || [];
            if (parts.length === 3) {
                const rowDate = `${parts[2]}-${parts[1]}-${parts[0]}`;
                if (fromVal && rowDate < fromVal) matchDate = false;
                if (toVal   && rowDate > toVal)   matchDate = false;
            }
        }
        tr.style.display = (matchSearch && matchStatus && matchDate) ? '' : 'none';
    });
}

// ============================================================
// INVOICE FORM — DUPLICATE CHECK & SUBMIT
// ============================================================
async function checkDuplicateInvoice() {
    const cid  = document.getElementById('inv-customer_id')?.value?.trim();
    const from = document.getElementById('inv-billing_from')?.value?.trim();
    const to   = document.getElementById('inv-billing_to')?.value?.trim();
    if (!cid || !from || !to) { hideDuplicateWarning(); return; }
    try {
        const isDuplicate = await eel.check_duplicate_invoice(cid, from, to)();
        if (isDuplicate) {
            document.getElementById('duplicate-warning-text').textContent =
                `A duplicate invoice may already exist for customer "${cid}" in this billing period.`;
            document.getElementById('duplicate-warning').style.display = 'flex';
        } else {
            hideDuplicateWarning();
        }
    } catch (e) { hideDuplicateWarning(); }
}

function hideDuplicateWarning() {
    const el = document.getElementById('duplicate-warning');
    if (el) el.style.display = 'none';
}

async function handleInvoiceSubmit(e) {
    e.preventDefault();
    const btn  = document.getElementById('generateBtn');
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line" style="animation:spin 0.8s linear infinite;display:inline-block;"></i> Generating...';
    btn.disabled  = true;

    try {
        const data = {
            name:             document.getElementById('inv-name').value,
            customer_id:      document.getElementById('inv-customer_id').value,
            tenant_name:      document.getElementById('inv-tenant_name').value,
            phone:            document.getElementById('inv-phone').value,
            customer_address: document.getElementById('inv-customer_address').value,
            customer_gstin:   document.getElementById('inv-customer_gstin').value,
            plan:             document.getElementById('inv-plan').value,
            months:           document.getElementById('inv-months').value,
            billing_from:     document.getElementById('inv-billing_from').value,
            billing_to:       document.getElementById('inv-billing_to').value,
            total_amount:     document.getElementById('inv-total_amount').value,
            discount:         document.getElementById('inv-discount').value,
            late_fee:         document.getElementById('inv-late_fee').value,
            payment_status:   document.getElementById('inv-payment_status').value,
            payment_method:   document.getElementById('inv-payment_method').value,
            save_customer:    document.getElementById('inv-save_customer').checked,
            custom_notes:     document.getElementById('inv-notes').value,
        };

        const response = await eel.generate_invoice(data)();
        if (response.status === 'success') {
            showToast('success', 'ri-check-circle-line', response.message);
            document.getElementById('invoiceForm').reset();
            hideDuplicateWarning();
            if (window.flatpickr) {
                const fpFrom = document.querySelector('#inv-billing_from')._flatpickr;
                const fpTo   = document.querySelector('#inv-billing_to')._flatpickr;
                if (fpFrom) fpFrom.setDate(new Date(), true);
                if (fpTo)   { const nm = new Date(); nm.setMonth(nm.getMonth() + 1); fpTo.setDate(nm, true); }
            }
            loadNotifications();
            window.switchView('dashboard');
        } else {
            showToast('error', 'ri-error-warning-line', 'Error: ' + response.message);
        }
    } catch (err) {
        showToast('error', 'ri-error-warning-line', 'Exception: ' + err);
    } finally {
        btn.innerHTML = orig;
        btn.disabled  = false;
    }
}

// ============================================================
// EXPORT / PDF / WHATSAPP
// ============================================================
async function exportCustomers() {
    try {
        const r = await eel.export_customers_csv()();
        showToast(r.status, r.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line', r.message);
    } catch (e) { showToast('error', 'ri-error-warning-line', 'Export failed.'); }
}

async function exportLogs() {
    try {
        const r = await eel.export_logs_csv()();
        showToast(r.status, r.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line', r.message);
    } catch (e) { showToast('error', 'ri-error-warning-line', 'Export failed.'); }
}

function openPdf(filename) {
    if (!filename?.trim()) { showToast('error', 'ri-error-warning-line', 'No PDF file found.'); return; }
    eel.open_pdf(filename)();
    showToast('info', 'ri-file-pdf-line', 'Opening PDF...');
}

async function sendWhatsApp(phoneNum, customerName, amount, invoiceNum, filename) {
    if (!phoneNum?.trim()) { showToast('error', 'ri-phone-off-line', 'No phone number found.'); return; }
    let clean = phoneNum.replace(/[^\d+]/g, '');
    if (clean.length === 10) clean = '91' + clean;
    const msg = `Hello ${customerName}, your bill of ₹${amount} is ready. Invoice: ${invoiceNum}`;
    if (filename) {
        eel.automate_whatsapp_attachment(clean, msg, filename)();
    } else {
        window.open(`whatsapp://send?phone=${clean}&text=${encodeURIComponent(msg)}`, '_blank');
    }
}

// ============================================================
// MARK AS PAID
// ============================================================
async function markPaid(invoiceNum) {
    if (!confirm(`Mark Invoice ${invoiceNum} as Paid?`)) return;
    const r = await eel.mark_invoice_paid(invoiceNum)();
    if (r.status === 'success') {
        showToast('success', 'ri-check-circle-line', r.message);
        loadHistory();
        loadDashboard();
    } else {
        showToast('error', 'ri-error-warning-line', 'Error: ' + r.message);
    }
}

// ============================================================
// CUSTOMER PROFILE
// ============================================================
async function viewCustomerProfile(customerId) {
    try {
        const response = await eel.get_customer_profile(customerId)();
        if (response.status !== 'success') {
            showToast('error', 'ri-error-warning-line', 'Error: ' + response.message);
            return;
        }

        const { customer, logs, stats } = response;
        _currentCustomerId = customerId;

        document.getElementById('cp-name').textContent    = customer.name;
        document.getElementById('cp-avatar').textContent  = customer.name ? customer.name.substring(0, 2).toUpperCase() : 'CU';
        document.getElementById('cp-id').textContent      = customer.customer_id;
        document.getElementById('cp-phone').textContent   = customer.phone || 'Not Provided';
        document.getElementById('cp-address').textContent = customer.customer_address || 'Not Provided';
        document.getElementById('cp-gstin').textContent   = customer.customer_gstin || 'Not Provided';

        const tagsHtml = (customer.tags || '').split(',').filter(t => t.trim()).map(t =>
            `<span class="tag-pill">${t.trim()}</span>`).join('') || '--';
        document.getElementById('cp-tags-display').innerHTML    = tagsHtml;
        document.getElementById('cp-notes-display').textContent = customer.notes || '--';
        document.getElementById('cp-status-badge').innerHTML    = statusBadge(customer.connection_status || 'Active');

        document.getElementById('cp-edit-status').value = customer.connection_status || 'Active';
        document.getElementById('cp-edit-tags').value   = customer.tags  || '';
        document.getElementById('cp-edit-notes').value  = customer.notes || '';

        document.getElementById('cp-ltv').textContent     = `₹${stats.total_paid.toLocaleString('en-IN')}`;
        document.getElementById('cp-pending').textContent = `₹${stats.pending_dues.toLocaleString('en-IN')}`;
        document.getElementById('cp-count').textContent   = stats.total_invoices;

        const tbody = document.getElementById('cp-logs-tbody');
        tbody.innerHTML = '';
        if (logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;padding:40px;color:var(--text-muted);">No historic invoices.</td></tr>`;
        } else {
            logs.forEach(log => {
                const sc = log.status === 'Paid' ? 'status-paid' : log.status === 'Partial' ? 'status-partial' : 'status-unpaid';
                tbody.innerHTML += `
                    <tr>
                        <td style="color:var(--text-muted);font-size:0.8em;">${log.datetime}</td>
                        <td><span style="color:var(--text-muted);font-size:0.82em;">${log.invoice_num}</span></td>
                        <td style="font-weight:600;">₹${Number(log.amount).toLocaleString('en-IN')}</td>
                        <td><span class="status-badge ${sc}">${log.status}</span></td>
                        <td style="display:flex;gap:5px;">
                            <button class="icon-btn" style="width:28px;height:28px;color:#818cf8;" onclick="openPdf('${log.filename}')"><i class="ri-file-pdf-line"></i></button>
                            ${log.status !== 'Paid' ? `<button class="icon-btn" style="width:28px;height:28px;color:var(--success);" onclick="markPaid('${log.invoice_num}');setTimeout(()=>viewCustomerProfile('${customerId}'),600)"><i class="ri-check-line"></i></button>` : ''}
                        </td>
                    </tr>`;
            });
        }

        window.switchView('customer-profile');
    } catch (e) {
        console.error(e);
        showToast('error', 'ri-error-warning-line', 'Exception loading profile.');
    }
}

async function saveCustomerNotes() {
    if (!_currentCustomerId) return;
    const status = document.getElementById('cp-edit-status').value;
    const tags   = document.getElementById('cp-edit-tags').value;
    const notes  = document.getElementById('cp-edit-notes').value;
    const r = await eel.update_customer_notes(_currentCustomerId, notes, tags, status)();
    if (r.status === 'success') {
        showToast('success', 'ri-check-circle-line', 'Customer updated.');
        viewCustomerProfile(_currentCustomerId);
    } else {
        showToast('error', 'ri-error-warning-line', r.message);
    }
}

// ============================================================
// DASHBOARD COMPAT CHARTS (hidden canvases)
// ============================================================
function updateCharts(stats) {
    setChartDefaults();

    const ctxRev = document.getElementById('revenueChart');
    if (revenueChart) revenueChart.destroy();
    if (ctxRev) {
        revenueChart = new Chart(ctxRev, {
            type: 'line',
            data: {
                labels: ['', '', '', '', 'Now'],
                datasets: [{
                    data: [0, 0, 0, 0, stats.revenue],
                    borderColor: '#6366f1',
                    backgroundColor: 'rgba(99,102,241,0.1)',
                    borderWidth: 2,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' } },
                    x: { grid: { display: false } }
                }
            }
        });
    }

    const ctxStat = document.getElementById('statusChart');
    if (statusChart) statusChart.destroy();
    if (ctxStat) {
        const chartData   = stats.revenue === 0 ? [1] : [stats.paid, stats.pending];
        const chartColors = stats.revenue === 0 ? ['#334155'] : ['#10b981', '#ef4444'];
        statusChart = new Chart(ctxStat, {
            type: 'doughnut',
            data: {
                labels: stats.revenue === 0 ? ['No Data'] : ['Paid', 'Pending'],
                datasets: [{ data: chartData, backgroundColor: chartColors, borderWidth: 0, hoverOffset: 4 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '75%',
                plugins: { legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } } }
            }
        });
    }
}

// ============================================================
// NOTIFICATIONS
// ============================================================
async function loadNotifications() {
    try {
        const logs  = await eel.get_history()();
        const list  = document.getElementById('notif-list');
        const badge = document.getElementById('notif-badge');
        if (!list) return;
        const recent = logs.slice(0, 5);
        if (recent.length === 0) {
            list.innerHTML = '<div class="notif-empty">No recent activity</div>';
            if (badge) badge.style.display = 'none';
            return;
        }
        if (badge) { badge.textContent = recent.length; badge.style.display = ''; }
        list.innerHTML = recent.map(l => {
            const icon  = l.status === 'Paid' ? '✓' : l.status === 'Partial' ? '⋯' : '!';
            const color = l.status === 'Paid' ? '#10b981' : l.status === 'Partial' ? '#f59e0b' : '#ef4444';
            return `<div class="notif-item">
                <span class="notif-icon" style="background:${color}22;color:${color};">${icon}</span>
                <div class="notif-content">
                    <p class="notif-title">${l.customer_name}</p>
                    <p class="notif-sub">${l.invoice_num} · ₹${Number(l.amount).toLocaleString('en-IN')} · ${l.status}</p>
                    <p class="notif-time">${l.datetime}</p>
                </div>
            </div>`;
        }).join('');
    } catch (e) { console.error('Notifications error:', e); }
}

function toggleNotifications() {
    const panel = document.getElementById('notification-panel');
    if (panel) {
        panel.classList.toggle('hidden');
        if (!panel.classList.contains('hidden')) loadNotifications();
    }
}

function closeNotifications() {
    const panel = document.getElementById('notification-panel');
    if (panel) panel.classList.add('hidden');
}

// ============================================================
// APP LOGS
// ============================================================
async function loadAppLogs() {
    const viewer = document.getElementById('log-viewer');
    if (!viewer) return;
    viewer.textContent = 'Loading...';
    try {
        const lines = await eel.get_app_logs()();
        viewer.textContent = lines.join('\n');
        viewer.scrollTop   = viewer.scrollHeight;
    } catch (e) {
        viewer.textContent = 'Failed to load logs: ' + e;
    }
}

// ============================================================
// SETTINGS
// ============================================================
async function loadSettings() {
    try {
        const s   = await eel.get_settings()();
        const ver = await eel.get_version()();
        document.getElementById('s-company_name').value    = s.company_name    || '';
        document.getElementById('s-company_address').value = s.company_address || '';
        document.getElementById('s-company_gstin').value   = s.company_gstin   || '';
        document.getElementById('s-company_phone').value   = s.company_phone   || '';
        document.getElementById('s-company_email').value   = s.company_email   || '';
        document.getElementById('s-place_of_supply').value = s.place_of_supply || '';
        document.getElementById('s-gst_rate').value        = s.gst_rate ?? 9;
        document.getElementById('s-invoice_prefix').value  = s.invoice_prefix  || '';
        const vEl = document.getElementById('s-version');
        if (vEl) vEl.textContent = ver;
    } catch (e) { console.error('Failed to load settings:', e); }
}

async function saveSettings() {
    const data = {
        company_name:    document.getElementById('s-company_name').value.trim(),
        company_address: document.getElementById('s-company_address').value.trim(),
        company_gstin:   document.getElementById('s-company_gstin').value.trim(),
        company_phone:   document.getElementById('s-company_phone').value.trim(),
        company_email:   document.getElementById('s-company_email').value.trim(),
        place_of_supply: document.getElementById('s-place_of_supply').value.trim(),
        gst_rate:        parseFloat(document.getElementById('s-gst_rate').value) || 9.0,
        invoice_prefix:  document.getElementById('s-invoice_prefix').value.trim(),
    };
    try {
        const res = await eel.save_settings_data(data)();
        showToast(res.status,
            res.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line',
            res.status === 'success' ? 'Settings saved!' : 'Error: ' + res.message);
    } catch (e) { showToast('error', 'ri-error-warning-line', 'Failed to save settings.'); }
}

async function doResetCounter() {
    if (!confirm('Reset invoice counter to #2059?')) return;
    const res = await eel.reset_invoice_counter()();
    showToast(res.status,
        res.status === 'success' ? 'ri-refresh-line' : 'ri-error-warning-line',
        res.message);
}

// ============================================================
// THEME
// ============================================================
function initTheme() {
    const saved = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', saved);
    updateThemeIcon(saved);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-toggle i');
    if (icon) icon.className = theme === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
    const settingsIcon = document.getElementById('settings-theme-icon');
    if (settingsIcon) settingsIcon.className = theme === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
}

function toggleTheme() {
    const current  = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
    // Reload charts so colors adapt
    setTimeout(() => {
        if (dashMonthlyChart) loadDashboardCharts();
        const analytics = document.getElementById('analytics');
        if (analytics?.classList.contains('active-view')) loadAnalytics();
    }, 300);
}

// ============================================================
// UNIVERSAL SEARCH
// ============================================================
function filterTables(query) {
    const q = query.toLowerCase();
    ['#customers-tbody tr', '#logs-tbody tr'].forEach(sel => {
        document.querySelectorAll(sel).forEach(tr => {
            tr.style.display = tr.innerText.toLowerCase().includes(q) ? '' : 'none';
        });
    });
}

// ============================================================
// PLAN TOTAL CALCULATOR
// ============================================================
function calculateTotal() {
    const planMap = {
        '100 MBPS UNL': 400, '200 MBPS UNL': 500,
        '300 MBPS UNL': 600, '400 MBPS UNL': 700, '500 MBPS UNL': 800
    };
    const plan   = document.getElementById('inv-plan')?.value;
    const months = parseInt(document.getElementById('inv-months')?.value) || 1;
    const amtEl  = document.getElementById('inv-total_amount');
    if (amtEl) amtEl.value = ((planMap[plan] || 0) * months).toFixed(2);
}

// ============================================================
// SIDEBAR INDICATOR (compat shim)
// ============================================================
function updateSidebarIndicator(viewId) {
    // Visual indicator not needed in new design; shim kept for compat
}

// ============================================================
// ANIMATED COUNTER
// ============================================================
function animateCounter(el, targetValue, prefix = '₹', duration = 900) {
    if (!el) return;
    const start = performance.now();
    function step(now) {
        const p = Math.min((now - start) / duration, 1);
        const e = 1 - Math.pow(1 - p, 3);
        el.textContent = prefix + Math.round(targetValue * e).toLocaleString('en-IN');
        if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ============================================================
// LIVE CLOCK
// ============================================================
// ============================================================
// DATE RANGE PILL
// ============================================================
function updateDateRangePill(period, customFrom, customTo) {
    const el    = document.getElementById('date-range-text');
    if (!el) return;
    const now   = new Date();
    const MONTHS = ['Jan','Feb','Mar','Apr','May','Jun',
                    'Jul','Aug','Sep','Oct','Nov','Dec'];
    let text = '';
    
    if (period === 'custom') {
        const f = new Date(customFrom);
        const t = new Date(customTo);
        if (customFrom === customTo) {
            text = `${f.getDate()} ${MONTHS[f.getMonth()]} ${f.getFullYear()}`;
        } else {
            text = `${f.getDate()} ${MONTHS[f.getMonth()]} ${f.getFullYear()} – ${t.getDate()} ${MONTHS[t.getMonth()]} ${t.getFullYear()}`;
        }
    } else if (period === 'day') {
        text = `${now.getDate()} ${MONTHS[now.getMonth()]} ${now.getFullYear()}`;

    } else if (period === 'week') {
        // Start of week (Monday)
        const day  = now.getDay();
        const diff = (day === 0 ? -6 : 1 - day);
        const mon  = new Date(now); mon.setDate(now.getDate() + diff);
        const sun  = new Date(mon); sun.setDate(mon.getDate() + 6);
        text = `${mon.getDate()} ${MONTHS[mon.getMonth()]} – ${sun.getDate()} ${MONTHS[sun.getMonth()]} ${sun.getFullYear()}`;

    } else if (period === 'month') {
        const lastDay = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
        text = `1 ${MONTHS[now.getMonth()]} ${now.getFullYear()} – ${lastDay} ${MONTHS[now.getMonth()]} ${now.getFullYear()}`;

    } else if (period === 'year') {
        text = `1 Jan ${now.getFullYear()} – 31 Dec ${now.getFullYear()}`;
    }
    el.textContent = text;
}

// ============================================================
// LIVE CLOCK
// ============================================================
function startClock() {

    const clockEl = document.getElementById('sidebar-clock');
    const dateEl  = document.getElementById('sidebar-date');
    const greetEl = document.getElementById('dashboard-greeting');
    const DAYS    = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    const MONTHS  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    function tick() {
        const now   = new Date();
        const rawH  = now.getHours();
        const ampm  = rawH >= 12 ? 'PM' : 'AM';
        const h12   = rawH % 12 || 12;
        const hStr  = String(h12).padStart(2, '0');
        const mStr  = String(now.getMinutes()).padStart(2, '0');
        const sStr  = String(now.getSeconds()).padStart(2, '0');
        if (clockEl) clockEl.textContent = `${hStr}:${mStr}:${sStr} ${ampm}`;
        if (dateEl)  dateEl.textContent  = `${DAYS[now.getDay()]}, ${now.getDate()} ${MONTHS[now.getMonth()]}`;
        if (greetEl) {
            const hr = now.getHours();
            greetEl.textContent = hr < 5  ? 'Good Night 🌌' :
                                  hr < 12 ? 'Good Morning ☀️' :
                                  hr < 17 ? 'Good Afternoon 🌤️' :
                                  hr < 21 ? 'Good Evening 🌇' : 'Good Night 🌌';
        }
    }
    tick();
    setInterval(tick, 1000);
}

// ============================================================
// TOAST SYSTEM
// ============================================================
function showToast(type, icon, message, duration = 3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `<i class="${icon}"></i><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        toast.addEventListener('animationend', () => toast.remove());
    }, duration);
}

// ============================================================
// BUTTON RIPPLE
// ============================================================
document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn, .btn-primary, .btn-secondary, .icon-btn, .promo-btn');
    if (!btn) return;
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    const size = Math.max(btn.offsetWidth, btn.offsetHeight);
    const rect = btn.getBoundingClientRect();
    ripple.style.cssText = `
        width:${size}px; height:${size}px;
        left:${e.clientX - rect.left - size / 2}px;
        top:${e.clientY - rect.top  - size / 2}px;`;
    btn.style.position = 'relative';
    btn.style.overflow = 'hidden';
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
});

// ============================================================
// CHART DEFAULTS
// ============================================================
function setChartDefaults() {
    const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
    Chart.defaults.color       = isDark ? '#64748b' : '#94a3b8';
    Chart.defaults.font.family = "'Poppins', sans-serif";
    Chart.defaults.font.size   = 11;
}

// ============================================================
// AUTO-UPDATE SYSTEM
// ============================================================
async function checkForUpdates(manual = false) {
    if (manual) showToast('info', 'ri-refresh-line', 'Checking for updates...');
    try {
        const result = await eel.check_for_updates()();
        if (result.status === 'update_available') showUpdateBanner(result.latest, result.url);
        else if (manual) showToast('success', 'ri-checkbox-circle-line', 'You are on the latest version ✓');
    } catch (e) {
        if (manual) showToast('error', 'ri-error-warning-line', 'Update check failed.');
    }
}

function showUpdateBanner(version, downloadUrl) {
    const old = document.getElementById('update-banner');
    if (old) old.remove();
    const banner = document.createElement('div');
    banner.id        = 'update-banner';
    banner.className = 'update-banner';
    banner.innerHTML = `
        <div class="update-content">
            <i class="ri-rocket-2-line" style="color:var(--accent-light);font-size:1.1rem;"></i>
            <span>Update Available! <strong>v${version}</strong> is ready.</span>
        </div>
        <div class="update-actions">
            <button class="btn-update-now" onclick="runUpdate('${downloadUrl}')">
                <i class="ri-download-line"></i> Download &amp; Install
            </button>
            <button class="btn-update-close" onclick="this.parentElement.parentElement.remove()">
                <i class="ri-close-line"></i>
            </button>
        </div>`;
    document.body.appendChild(banner);
}

window.runUpdate = async (url) => {
    const btn = document.querySelector('.btn-update-now');
    if (btn) {
        btn.innerHTML = '<i class="ri-loader-4-line" style="animation:spin 0.8s linear infinite;display:inline-block;"></i> Downloading...';
        btn.disabled = true;
    }
    showToast('info', 'ri-download-line', 'Starting update download...', 3000);
    try { await eel.download_and_install_update(url)(); }
    catch (e) { showToast('error', 'ri-error-warning-line', 'Failed to initiate download.'); }
};

eel.expose(update_download_status);
function update_download_status(msg) {
    const btn = document.querySelector('.btn-update-now');
    if (btn) btn.innerHTML = msg;
}

eel.expose(handle_update_error);
function handle_update_error(msg) {
    showToast('error', 'ri-error-warning-line', 'Update Error: ' + msg, 6000);
    const btn = document.querySelector('.btn-update-now');
    if (btn) { btn.innerHTML = '<i class="ri-download-line"></i> Download &amp; Install'; btn.disabled = false; }
}

// Helper: "New Customer" button
function showNewInvoice() { window.switchView('new-invoice'); }

// CSS for spin animation (injected once)
const spinStyle = document.createElement('style');
spinStyle.textContent = `
    @keyframes spin { to { transform: rotate(360deg); } }
`;
document.head.appendChild(spinStyle);
