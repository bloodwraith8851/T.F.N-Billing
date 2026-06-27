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
let _currentCustomerData = null;  // full customer object for "New Invoice from Profile"
let _currentProfileLogs  = [];    // cached invoice logs for profile timeline filter
let _markPaidInvoiceNum  = null;  // current mark-paid invoice number
let _confirmCallback     = null;  // current confirm modal callback
let _allCustomers        = [];    // cached for autocomplete + bulk select
let _plansData           = [];    // cached plans list
let gaugeChart           = null;  // collection rate solid gauge
let activeFilter = { from: null, to: null, label: 'month' };

// Highcharts Network State
let isOnline = navigator.onLine;
let highchartsLoaded = false;
let highchartsLoading = false;


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
    initNetworkSystem();

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

    // Customer autocomplete (replaces old select autofill)
    initCustomerAutocomplete();

    // Live GST breakdown preview
    document.getElementById('inv-total_amount')?.addEventListener('input', calculateGSTBreakdown);
    document.getElementById('inv-plan')?.addEventListener('change', () => { calculateTotal(); calculateGSTBreakdown(); });
    document.getElementById('inv-months')?.addEventListener('input', () => { calculateTotal(); calculateGSTBreakdown(); });

    // Star field pause on tab hidden
    document.addEventListener('visibilitychange', () => {
        if (window._starAnimId) {
            if (document.hidden) { cancelAnimationFrame(window._starAnimId); window._starAnimId = null; }
            else { window._starAnimId = requestAnimationFrame(window._drawStarsFn); }
        }
    });


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
        window._starAnimId = requestAnimationFrame(drawStars);
    }

    window._drawStarsFn = drawStars;  // exposed for visibility-change pause
    window.addEventListener('resize', resize);
    resize();
    window._starAnimId = requestAnimationFrame(drawStars);
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
        
        // If we are on Analytics view, update Analytics charts specifically
        const analyticsSection = document.getElementById('analytics');
        if (analyticsSection && !analyticsSection.classList.contains('hidden-view')) {
            loadAnalytics(from, to);
        }
        
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
        const rate = Math.round((data.monthly.collected / (data.monthly.total || 1)) * 100) || 0;
        document.getElementById('stat-rate').textContent = rate + '%';
        document.getElementById('cgw-rate-label').textContent = rate + '%';
        
        // Render Solid Gauge or fallback to SVG Ring
        if (isOnline && window.Highcharts && highchartsLoaded && Highcharts.seriesTypes.solidgauge) {
            document.querySelector('.rate-ring').style.display = 'none'; // hide SVG
            document.getElementById('stat-rate').style.display = 'none'; // hide text
            if (gaugeChart) gaugeChart.destroy();
            gaugeChart = Highcharts.chart('collectionRateGauge', {
                chart: { type: 'solidgauge', backgroundColor: 'transparent' },
                title: null,
                tooltip: { enabled: false },
                pane: { center: ['50%', '50%'], size: '100%', startAngle: 0, endAngle: 360, background: { backgroundColor: 'rgba(255,255,255,0.05)', innerRadius: '75%', outerRadius: '100%', shape: 'arc', borderWidth: 0 } },
                yAxis: { min: 0, max: 100, stops: [ [0.3, '#ef4444'], [0.7, '#f59e0b'], [1, '#10b981'] ], lineWidth: 0, tickWidth: 0, minorTickInterval: null, tickAmount: 2, labels: { enabled: false } },
                plotOptions: { solidgauge: { dataLabels: { y: -15, borderWidth: 0, useHTML: true }, innerRadius: '75%' } },
                series: [{ name: 'Collection Rate', data: [rate], dataLabels: { format: '<div style="text-align:center"><span style="font-size:16px;color:#f8fafc;font-weight:600">{y}%</span></div>' } }],
                credits: { enabled: false }
            });
        } else {
            // Fallback SVG behavior
            document.querySelector('.rate-ring').style.display = 'block';
            document.getElementById('stat-rate').style.display = 'block';
            const circle = document.getElementById('rate-ring-fill');
            if (circle) {
                const circumference = 2 * Math.PI * 34;
                const offset = circumference - (rate / 100) * circumference;
                circle.style.strokeDashoffset = offset;
                injectRateGradient();
            }
        }
        
        // 3. Charts
        updateCharts(stats);
        
        // 4. Monthly Chart
        setChartDefaults();
        const ctxDM = document.getElementById('dashMonthlyChart');
        if (ctxDM) {
            const revenues = data.monthly.revenues || [];
            const labels = data.monthly.months || [];
            dashMonthlyChart = renderBarChart('dashMonthlyChart', dashMonthlyChart, labels, revenues);
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
async function loadAnalytics(from = null, to = null) {
    try {
        // Use global filter if none provided
        if (!from || !to) {
            from = activeFilter.from;
            to = activeFilter.to;
        }
        
        let monthly, plans;
        if (from && to) {
            [monthly, plans] = await Promise.all([
                eel.get_monthly_revenue_filtered(from, to)(),
                eel.get_plan_breakdown_filtered(from, to)()
            ]);
        } else {
            [monthly, plans] = await Promise.all([
                eel.get_monthly_revenue()(),
                eel.get_plan_breakdown()()
            ]);
        }

        setChartDefaults();

        // Monthly Revenue Bar Chart (Analytics page)
        const ctxM = document.getElementById('monthlyRevenueChart');
        if (ctxM) {
            monthlyChart = renderBarChart('monthlyRevenueChart', monthlyChart, monthly.months || [], monthly.revenues || []);
        }

        // Plan Breakdown Donut (Analytics page)
        const ctxP = document.getElementById('planBreakdownChart');
        if (ctxP) {
            const planColors = ['#6366f1','#34d399','#f59e0b','#ef4444','#3b82f6'];
            const pLabels = plans.plans?.length ? plans.plans : ['No Data'];
            const pData = plans.counts?.length ? plans.counts : [1];
            const pCols = plans.plans?.length ? planColors : ['#334155'];
            planChart = renderDonutChart('planBreakdownChart', planChart, pLabels, pData, pCols);
        }
    } catch (e) {
        console.error('Analytics load error:', e);
        if (typeof showToast === 'function') {
            showToast('error', 'ri-error-warning-line', 'Analytics Error: ' + e.message);
        }
    }
}

// ============================================================
// CUSTOMERS
// ============================================================
async function loadCustomers() {
    const customers = await eel.get_customers()();
    const tbody  = document.getElementById('customers-tbody');

    // Cache for autocomplete and bulk invoice
    _allCustomers = customers;
    initCustomerAutocomplete();   // refresh autocomplete with fresh data
    refreshBulkPlanDropdown();    // populate bulk invoice plan selector

    tbody.innerHTML = '';

    if (customers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" style="text-align:center;padding:40px;color:var(--text-muted);font-weight:500;">No customers found.</td></tr>`;
    } else {
        customers.forEach(c => {
            const initials   = c.name ? c.name.substring(0, 2).toUpperCase() : 'CU';
            const statusHtml = statusBadge(c.connection_status || 'Active');
            const tagsHtml   = (c.tags || '').split(',').filter(t => t.trim()).map(t =>
                `<span class="tag-pill">${t.trim()}</span>`).join('');
            tbody.innerHTML += `
                <tr onclick="viewCustomerProfile('${c.customer_id}')" style="cursor:pointer;">
                    <td onclick="event.stopPropagation()"><input type="checkbox" class="bulk-chk" data-id="${c.customer_id}" onchange="updateBulkCount()"></td>
                    <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;">${c.name}</span></div></td>
                    <td><span style="color:var(--text-muted);font-size:0.82em;">${c.customer_id}</span></td>
                    <td><span style="color:var(--text-muted);">${c.phone || '-'}</span></td>
                    <td><span style="color:var(--text-muted);">${c.tenant_name || '-'}</span></td>
                    <td><span style="font-size:0.82em;color:var(--text-muted);max-width:160px;display:inline-block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${c.customer_address}</span></td>
                    <td>${statusHtml}</td>
                    <td>${tagsHtml}</td>
                </tr>`;
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
    showMarkPaidModal(invoiceNum);
}

// ============================================================
// CUSTOMER PROFILE  —  Hero + Designer Timeline
// ============================================================
async function viewCustomerProfile(customerId) {
    try {
        const response = await eel.get_customer_profile(customerId)();
        if (response.status !== 'success') {
            showToast('error', 'ri-error-warning-line', 'Error: ' + response.message);
            return;
        }

        const { customer, logs, stats } = response;
        _currentCustomerId   = customerId;
        _currentCustomerData = customer;
        _currentProfileLogs  = logs;

        // ── Hero strip ──
        document.getElementById('cp-name').textContent    = customer.name;
        document.getElementById('cp-avatar').textContent  = customer.name ? customer.name.substring(0, 2).toUpperCase() : 'CU';
        document.getElementById('cp-id').textContent      = customer.customer_id;
        document.getElementById('cp-phone').textContent   = customer.phone || 'Not Provided';
        document.getElementById('cp-address').textContent = customer.customer_address || 'Not Provided';
        document.getElementById('cp-gstin').textContent   = customer.customer_gstin || '--';
        document.getElementById('cp-status-badge').innerHTML = statusBadge(customer.connection_status || 'Active');

        // ── Edit panel info ──
        const tagsHtml = (customer.tags || '').split(',').filter(t => t.trim()).map(t =>
            `<span class="tag-pill">${t.trim()}</span>`).join('') || '--';
        document.getElementById('cp-tags-display').innerHTML    = tagsHtml;
        document.getElementById('cp-notes-display').textContent = customer.notes || '--';

        // ── Stat pills ──
        document.getElementById('cp-ltv').textContent     = `₹${stats.total_paid.toLocaleString('en-IN')}`;
        document.getElementById('cp-pending').textContent = `₹${stats.pending_dues.toLocaleString('en-IN')}`;
        document.getElementById('cp-count').textContent   = stats.total_invoices;

        // ── Edit fields ──
        document.getElementById('cp-edit-status').value = customer.connection_status || 'Active';
        document.getElementById('cp-edit-tags').value   = customer.tags  || '';
        document.getElementById('cp-edit-notes').value  = customer.notes || '';
        const emailEl = document.getElementById('cp-edit-email');
        if (emailEl) emailEl.value = customer.customer_email || '';

        // ── Reset tabs & render timeline ──
        document.querySelectorAll('.cp-tab').forEach(t => t.classList.remove('active'));
        const firstTab = document.querySelector('.cp-tab');
        if (firstTab) firstTab.classList.add('active');
        renderProfileTimeline(logs, 'all');

        window.switchView('customer-profile');
    } catch (e) {
        console.error(e);
        showToast('error', 'ri-error-warning-line', 'Exception loading profile.');
    }
}

function filterProfileInvoices(filter, btn) {
    document.querySelectorAll('.cp-tab').forEach(t => t.classList.remove('active'));
    if (btn) btn.classList.add('active');
    renderProfileTimeline(_currentProfileLogs, filter);
}

function renderProfileTimeline(logs, filter) {
    const timeline = document.getElementById('cp-timeline');
    const hint     = document.getElementById('tl-scroll-hint');

    const filtered = (filter === 'all')
        ? logs
        : logs.filter(l => l.status.toLowerCase() === filter.toLowerCase());

    if (!filtered || filtered.length === 0) {
        timeline.innerHTML = `<div class="tl-empty"><i class="ri-history-line"></i> No ${filter === 'all' ? '' : filter + ' '}invoices found.</div>`;
        if (hint) hint.style.display = 'none';
        return;
    }

    const dotClass = { Paid: 'tl-dot-paid', Unpaid: 'tl-dot-unpaid', Partial: 'tl-dot-partial' };
    const sc       = { Paid: 'status-paid',  Unpaid: 'status-unpaid',  Partial: 'status-partial' };

    let html = '<div class="tl-track"><div class="tl-line"></div>';

    filtered.forEach((log, i) => {
        const above = (i % 2 === 0);
        const dot   = dotClass[log.status] || 'tl-dot-unpaid';
        const badge = sc[log.status]       || 'status-unpaid';

        // Parse date
        const d   = new Date(log.datetime);
        const mon = isNaN(d.getTime())
            ? log.datetime
            : d.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

        const safeFile   = (log.filename    || '').replace(/'/g, "\\'");
        const safeInv    = (log.invoice_num || '').replace(/'/g, "\\'");
        const safeCid    = (_currentCustomerId || '').replace(/'/g, "\\'");
        const planLabel  = (log.plan_name || log.plan) ? `<div class="tl-card-plan">${log.plan_name || log.plan}</div>` : '';
        const payBtn     = log.status !== 'Paid'
            ? `<button class="tl-btn tl-pay-btn" onclick="markPaid('${safeInv}');setTimeout(()=>viewCustomerProfile('${safeCid}'),700)" title="Mark Paid"><i class="ri-check-line"></i></button>`
            : '';

        const card = `
        <div class="tl-card ${above ? 'tl-card-above' : 'tl-card-below'}">
            <div class="tl-connector ${above ? 'tl-connector-above' : 'tl-connector-below'}"></div>
            <div class="tl-card-month">${mon}</div>
            <div class="tl-card-inv">${log.invoice_num}</div>
            <div class="tl-card-amount">₹${Number(log.amount).toLocaleString('en-IN')}</div>
            ${planLabel}
            <div class="tl-card-footer">
                <span class="status-badge ${badge}">${log.status}</span>
                <button class="tl-btn tl-pdf-btn" onclick="openPdf('${safeFile}')" title="View PDF"><i class="ri-file-pdf-line"></i></button>
                ${payBtn}
            </div>
        </div>`;

        html += `<div class="tl-node">${above ? card : ''}<div class="tl-dot ${dot}"></div>${!above ? card : ''}</div>`;
    });

    html += '</div>';
    timeline.innerHTML = html;
    if (hint) hint.style.display = filtered.length > 4 ? 'flex' : 'none';
}

async function saveCustomerFull() {
    if (!_currentCustomerId || !_currentCustomerData) return;
    const status = document.getElementById('cp-edit-status').value;
    const tags   = document.getElementById('cp-edit-tags').value;
    const notes  = document.getElementById('cp-edit-notes').value;
    const email  = document.getElementById('cp-edit-email')?.value || '';
    const r = await eel.save_customer_full({
        ..._currentCustomerData,
        connection_status: status,
        tags, notes,
        customer_email: email
    })();
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
    if (ctxRev) {
        revenueChart = renderLineChart('revenueChart', revenueChart, ['', '', '', '', 'Now'], [0, 0, 0, 0, stats.revenue], '#6366f1');
    }

    const ctxStat = document.getElementById('statusChart');
    if (ctxStat) {
        const chartData   = stats.revenue === 0 ? [1] : [stats.paid, stats.pending];
        const chartColors = stats.revenue === 0 ? ['#334155'] : ['#10b981', '#ef4444'];
        const chartLabels = stats.revenue === 0 ? ['No Data'] : ['Paid', 'Pending'];
        statusChart = renderDonutChart('statusChart', statusChart, chartLabels, chartData, chartColors);
    }
}

// ============================================================
// NOTIFICATIONS
// ============================================================
async function loadNotifications() {
    try {
        // Use efficient get_recent_logs_eel instead of loading all history
        const logs  = await eel.get_recent_logs_eel(5)();
        const unpaid = await eel.get_unpaid_count_this_month()();
        const list  = document.getElementById('notif-list');
        const badge = document.getElementById('notif-badge');
        if (!list) return;
        if (logs.length === 0) {
            list.innerHTML = '<div class="notif-empty">No recent activity</div>';
            if (badge) badge.style.display = 'none';
            return;
        }
        // Badge shows UNPAID count, not total recent
        if (badge) {
            if (unpaid > 0) {
                badge.textContent = unpaid;
                badge.style.display = '';
            } else {
                badge.style.display = 'none';
            }
        }
        list.innerHTML = logs.map(l => {
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
// NETWORK & HIGHCHARTS DYNAMIC LOADING
// ============================================================
function initNetworkSystem() {
    window.addEventListener('online', handleNetworkChange);
    window.addEventListener('offline', handleNetworkChange);
    
    // Initial check
    if (isOnline) {
        loadHighcharts();
    }
}

function handleNetworkChange() {
    isOnline = navigator.onLine;
    console.log(`Network status changed: ${isOnline ? 'Online' : 'Offline'}`);
    
    if (typeof showToast === 'function') {
        if (isOnline) {
            showToast('success', 'ri-wifi-line', 'Back online. Upgrading charts to Highcharts.');
            loadHighcharts().then(() => refreshAllCharts());
        } else {
            showToast('warning', 'ri-wifi-off-line', 'You are offline. Falling back to local Chart.js.');
            refreshAllCharts();
        }
    } else {
        if (isOnline) {
            loadHighcharts().then(() => refreshAllCharts());
        } else {
            refreshAllCharts();
        }
    }
}

function loadHighcharts() {
    return new Promise((resolve, reject) => {
        if (highchartsLoaded) return resolve();
        if (highchartsLoading) {
            // Wait for it to finish loading
            const checkInterval = setInterval(() => {
                if (highchartsLoaded) {
                    clearInterval(checkInterval);
                    resolve();
                }
            }, 100);
            return;
        }
        
        highchartsLoading = true;
        
        // Load Highcharts Base
        const scriptBase = document.createElement('script');
        scriptBase.src = 'https://code.highcharts.com/highcharts.js';
        
        scriptBase.onload = () => {
            // Load required modules
            const modules = [
                'https://code.highcharts.com/highcharts-3d.js',
                'https://code.highcharts.com/modules/cylinder.js',
                'https://code.highcharts.com/highcharts-more.js',
                'https://code.highcharts.com/modules/solid-gauge.js',
                'https://code.highcharts.com/modules/drilldown.js',
                'https://code.highcharts.com/modules/exporting.js',
                'https://code.highcharts.com/modules/export-data.js',
                'https://code.highcharts.com/modules/accessibility.js'
            ];
            
            function loadNextModule(index) {
                if (index >= modules.length) {
                    // Apply Dark Theme by default for Highcharts
                    if (window.Highcharts) {
                        Highcharts.setOptions({
                            chart: { backgroundColor: 'transparent', style: { fontFamily: "'Poppins', sans-serif" } },
                            title: { style: { color: '#f8fafc' } },
                            legend: { itemStyle: { color: '#94a3b8' } },
                            tooltip: { backgroundColor: 'rgba(15, 23, 42, 0.9)', style: { color: '#f8fafc' }, borderWidth: 0, borderRadius: 8 }
                        });
                    }
                    highchartsLoaded = true;
                    highchartsLoading = false;
                    resolve();
                    return;
                }
                
                const modScript = document.createElement('script');
                modScript.src = modules[index];
                modScript.onload = () => loadNextModule(index + 1);
                modScript.onerror = () => {
                    console.warn(`Failed to load Highcharts module: ${modules[index]}`);
                    loadNextModule(index + 1);
                };
                document.head.appendChild(modScript);
            }
            
            loadNextModule(0);
        };
        
        scriptBase.onerror = (e) => {
            highchartsLoading = false;
            console.error('Failed to load Highcharts', e);
            reject(e);
        };
        
        document.head.appendChild(scriptBase);
    });
}

function refreshAllCharts() {
    // If we are on dashboard, reload dashboard charts
    const dashSection = document.getElementById('dashboard');
    if (dashSection && !dashSection.classList.contains('hidden-view')) {
        loadDashboard();
    }
    
    // If we are on Analytics, reload analytics charts
    const analyticsSection = document.getElementById('analytics');
    if (analyticsSection && !analyticsSection.classList.contains('hidden-view')) {
        loadAnalytics();
    }
}


// ============================================================
// DYNAMIC CHART RENDERING (Highcharts / Chart.js Fallback)
// ============================================================
function getChartContainer(ctxId, useHighcharts) {
    const container = document.getElementById(ctxId);
    if (!container) return null;
    const parent = container.parentElement;
    
    if (useHighcharts) {
        if (container.tagName.toLowerCase() === 'canvas') {
            const div = document.createElement('div');
            div.id = ctxId;
            div.className = container.className;
            div.style.width = '100%';
            div.style.height = '100%';
            parent.replaceChild(div, container);
            return div;
        }
        return container;
    } else {
        if (container.tagName.toLowerCase() === 'div') {
            const canvas = document.createElement('canvas');
            canvas.id = ctxId;
            canvas.className = container.className;
            parent.replaceChild(canvas, container);
            return canvas;
        }
        return container;
    }
}

function renderBarChart(ctxId, existingChart, labels, data, colors) {
    if (existingChart) existingChart.destroy();
    const l = labels.length ? labels : ['No Data'];
    const d = data.length ? data : [0];
    const useHighcharts = isOnline && window.Highcharts && highchartsLoaded;
    const container = getChartContainer(ctxId, useHighcharts);
    if (!container) return null;
    
    if (useHighcharts) {
        return Highcharts.chart(container, {
            chart: { 
                type: 'cylinder', 
                backgroundColor: 'transparent', 
                style: { fontFamily: "'Poppins', sans-serif" },
                options3d: { enabled: true, alpha: 10, beta: 15, depth: 40, viewDistance: 25 }
            },
            title: { text: null },
            xAxis: { categories: l, labels: { style: { color: '#94a3b8' } }, gridLineWidth: 0, lineWidth: 0, tickWidth: 0 },
            yAxis: { title: { text: null }, labels: { style: { color: '#94a3b8' }, formatter: function() { return '₹' + this.value.toLocaleString('en-IN'); } }, gridLineColor: 'rgba(255,255,255,0.04)' },
            legend: { enabled: false },
            plotOptions: {
                cylinder: {
                    depth: 25, colorByPoint: true,
                    colors: colors || l.map((_, i) => ({
                        linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
                        stops: [
                            [0, `hsla(${240 + i * 22}, 85%, 70%, 1)`],
                            [1, `hsla(${240 + i * 22}, 85%, 50%, 1)`]
                        ]
                    }))
                }
            },
            tooltip: { valuePrefix: '₹', backgroundColor: 'rgba(15, 23, 42, 0.95)', borderColor: '#334155', style: { color: '#f8fafc' } },
            series: [{ name: 'Revenue', data: l.map((label, idx) => ({ name: label, y: d[idx], drilldown: label + '-drill' })), showInLegend: false }],
            drilldown: {
                activeDataLabelStyle: { color: '#f8fafc', textDecoration: 'none' },
                series: l.map((label, idx) => ({
                    name: label,
                    id: label + '-drill',
                    data: [
                        ['Week 1', d[idx] * 0.25],
                        ['Week 2', d[idx] * 0.35],
                        ['Week 3', d[idx] * 0.15],
                        ['Week 4', d[idx] * 0.25]
                    ]
                }))
            },
            credits: { enabled: false }
        });
    } else {
        return new Chart(container, {
            type: 'bar',
            data: {
                labels: l,
                datasets: [{
                    label: 'Revenue (₹)',
                    data: d,
                    backgroundColor: colors || l.map((_, i) => `hsla(${240 + i * 22}, 75%, 65%, 0.75)`),
                    borderRadius: 9,
                    maxBarThickness: 50,
                    hoverBackgroundColor: colors ? null : l.map((_, i) => `hsla(${240 + i * 22}, 75%, 65%, 1)`)
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                layout: { padding: { top: 20 } },
                plugins: { legend: { display: false }, tooltip: { callbacks: { label: c => ' ₹' + Number(c.raw).toLocaleString('en-IN') } } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { callback: v => '₹' + v.toLocaleString('en-IN') }, border: { display: false } },
                    x: { grid: { display: false }, border: { display: false } }
                }
            }
        });
    }
}

function renderDonutChart(ctxId, existingChart, labels, data, colors) {
    if (existingChart) existingChart.destroy();
    const useHighcharts = isOnline && window.Highcharts && highchartsLoaded;
    const container = getChartContainer(ctxId, useHighcharts);
    if (!container) return null;
    
    if (useHighcharts) {
        const seriesData = labels.map((lbl, i) => ({ name: lbl, y: data[i] || 0, color: colors[i % colors.length] }));
        return Highcharts.chart(container, {
            chart: { 
                type: 'pie', 
                backgroundColor: 'transparent', 
                style: { fontFamily: "'Poppins', sans-serif" },
                options3d: { enabled: true, alpha: 45 }
            },
            title: { text: null },
            plotOptions: {
                pie: { 
                    innerSize: '65%', depth: 35, borderWidth: 0, 
                    dataLabels: { enabled: true, color: '#f8fafc', format: '<b>{point.name}</b>: {point.y}', style: { textOutline: 'none', fontWeight: '500', fontSize: '11px' } }, 
                    showInLegend: true 
                }
            },
            legend: { itemStyle: { color: '#94a3b8', fontWeight: 'normal' }, symbolRadius: 6 },
            tooltip: { pointFormat: '<b>{point.y}</b>', backgroundColor: 'rgba(15, 23, 42, 0.95)', borderColor: '#334155', style: { color: '#f8fafc' } },
            series: [{ name: 'Count', data: seriesData }],
            credits: { enabled: false }
        });
    } else {
        return new Chart(container, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{ data: data, backgroundColor: colors, borderWidth: 0, hoverOffset: 6 }]
            },
            options: {
                responsive: true, maintainAspectRatio: false, cutout: '75%',
                plugins: { legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true } } }
            }
        });
    }
}

function renderLineChart(ctxId, existingChart, labels, data, color) {
    if (existingChart) existingChart.destroy();
    const useHighcharts = isOnline && window.Highcharts && highchartsLoaded;
    const container = getChartContainer(ctxId, useHighcharts);
    if (!container) return null;
    
    if (useHighcharts) {
        return Highcharts.chart(container, {
            chart: { type: 'areaspline', backgroundColor: 'transparent', style: { fontFamily: "'Poppins', sans-serif" } },
            title: { text: null },
            xAxis: { categories: labels, visible: false },
            yAxis: { visible: false, min: 0 },
            legend: { enabled: false },
            plotOptions: {
                areaspline: {
                    fillColor: {
                        linearGradient: { x1: 0, y1: 0, x2: 0, y2: 1 },
                        stops: [ [0, Highcharts.color(color).setOpacity(0.5).get('rgba')], [1, Highcharts.color(color).setOpacity(0).get('rgba')] ]
                    },
                    marker: { radius: 3, fillColor: color, lineWidth: 2, lineColor: '#fff' },
                    lineWidth: 3,
                    states: { hover: { lineWidth: 3 } },
                    threshold: null
                }
            },
            tooltip: { valuePrefix: '₹', backgroundColor: 'rgba(15, 23, 42, 0.95)', borderColor: '#334155', style: { color: '#f8fafc' } },
            series: [{ name: 'Revenue', data: data, color: color }],
            credits: { enabled: false }
        });
    } else {
        return new Chart(container, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    data: data, borderColor: color, backgroundColor: 'rgba(99,102,241,0.1)',
                    borderWidth: 2, tension: 0.4, fill: true
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, display: false },
                    x: { display: false }
                }
            }
        });
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

        // WhatsApp template
        const waEl = document.getElementById('s-wa-template');
        if (waEl) {
            const tmpl = await eel.get_whatsapp_template()();
            waEl.value = tmpl;
        }

        // Monthly target
        const targetEl = document.getElementById('s-monthly-target');
        if (targetEl) {
            const target = await eel.get_monthly_target()();
            targetEl.value = target || 0;
        }

        // Plans list
        const plans = await eel.get_plans()();
        _plansData = [...plans];
        renderPlansSettings();
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
    showConfirmModal('Reset invoice counter to #2059?', async () => {
        const res = await eel.reset_invoice_counter()();
        showToast(res.status,
            res.status === 'success' ? 'ri-refresh-line' : 'ri-error-warning-line',
            res.message);
    });
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

// ============================================================
// CONFIRM MODAL (replaces window.confirm)
// ============================================================
function showConfirmModal(message, callback, title = 'Confirm Action') {
    _confirmCallback = callback;
    document.getElementById('confirm-modal-title').textContent = title;
    document.getElementById('confirm-modal-msg').textContent   = message;
    document.getElementById('confirm-modal-ok').onclick        = () => {
        closeConfirmModal();
        if (_confirmCallback) _confirmCallback();
    };
    document.getElementById('confirm-modal').classList.remove('hidden');
}

function closeConfirmModal() {
    document.getElementById('confirm-modal').classList.add('hidden');
    _confirmCallback = null;
}

// ============================================================
// MARK PAID MODAL (replaces native confirm + hardcoded method)
// ============================================================
function showMarkPaidModal(invoiceNum) {
    _markPaidInvoiceNum = invoiceNum;
    document.getElementById('mark-paid-invoice-label').textContent = `Invoice: ${invoiceNum}`;
    document.getElementById('mark-paid-modal').classList.remove('hidden');
}

function closeMarkPaidModal() {
    document.getElementById('mark-paid-modal').classList.add('hidden');
    _markPaidInvoiceNum = null;
}

async function confirmMarkPaid() {
    if (!_markPaidInvoiceNum) return;
    try {
        const method = document.getElementById('mark-paid-method').value;
        const r = await eel.mark_invoice_paid_with_method(_markPaidInvoiceNum, method)();
        if (r.status !== 'success') {
            showToast('error', 'ri-error-warning-line', r.message);
        } else {
            showToast('success', 'ri-check-line', `Invoice ${_markPaidInvoiceNum} marked Paid!`);
            
            // FIREWORKS CONFETTI CELEBRATION!
            if (typeof confetti === 'function') {
                const duration = 3 * 1000;
                const end = Date.now() + duration;
                (function frame() {
                    confetti({ particleCount: 5, angle: 60, spread: 55, origin: { x: 0 }, colors: ['#6366f1', '#10b981', '#f59e0b'] });
                    confetti({ particleCount: 5, angle: 120, spread: 55, origin: { x: 1 }, colors: ['#6366f1', '#10b981', '#f59e0b'] });
                    if (Date.now() < end) requestAnimationFrame(frame);
                }());
            }
            
            closeMarkPaidModal();
            loadHistory();
            loadDashboard();
            if (typeof loadOverdueDues === 'function') loadOverdueDues();
            if (_confirmCallback) _confirmCallback();
        }
    } catch (e) {
        showToast('error', 'ri-error-warning-line', 'Error marking paid: ' + e);
    }
}

// ============================================================
// CUSTOMER AUTOCOMPLETE
// ============================================================
function initCustomerAutocomplete() {
    const input    = document.getElementById('customerSearch');
    const dropdown = document.getElementById('customerDropdown');
    if (!input || !dropdown) return;

    // Remove old listener by cloning
    const newInput = input.cloneNode(true);
    input.parentNode.replaceChild(newInput, input);

    newInput.addEventListener('input', () => {
        const q = newInput.value.toLowerCase().trim();
        if (!q) { dropdown.classList.add('hidden'); return; }

        const matches = _allCustomers.filter(c =>
            (c.name || '').toLowerCase().includes(q) ||
            (c.customer_id || '').toLowerCase().includes(q) ||
            (c.phone || '').toLowerCase().includes(q)
        ).slice(0, 8);

        if (!matches.length) { dropdown.classList.add('hidden'); return; }

        dropdown.innerHTML = matches.map(c => `
            <div class="autocomplete-item" data-cid="${c.customer_id}">
                <strong>${c.name}</strong>
                <span>${c.customer_id}</span>
                <small>${c.phone || ''}</small>
            </div>
        `).join('');
        dropdown.classList.remove('hidden');

        dropdown.querySelectorAll('.autocomplete-item').forEach(item => {
            item.addEventListener('click', () => {
                const cid  = item.dataset.cid;
                const data = _allCustomers.find(c => c.customer_id === cid);
                if (data) selectAutocompleteCustomer(data, newInput, dropdown);
            });
        });
    });

    newInput.addEventListener('keydown', e => {
        if (e.key === 'Escape') dropdown.classList.add('hidden');
    });

    document.addEventListener('click', e => {
        if (!e.target.closest('.autocomplete-wrap')) dropdown.classList.add('hidden');
    }, { passive: true });
}

function selectAutocompleteCustomer(data, input, dropdown) {
    input.value = `${data.name} (${data.customer_id})`;
    dropdown.classList.add('hidden');
    document.getElementById('inv-name').value             = data.name             || '';
    document.getElementById('inv-customer_id').value      = data.customer_id      || '';
    document.getElementById('inv-tenant_name').value      = data.tenant_name      || '';
    document.getElementById('inv-phone').value            = data.phone            || '';
    document.getElementById('inv-customer_address').value = data.customer_address || '';
    document.getElementById('inv-customer_gstin').value   = data.customer_gstin   || '';
    calculateGSTBreakdown();
    checkDuplicateInvoice();
}

// ============================================================
// LIVE GST BREAKDOWN PREVIEW
// ============================================================
async function calculateGSTBreakdown() {
    const amountEl  = document.getElementById('inv-total_amount');
    const previewEl = document.getElementById('gst-preview');
    if (!amountEl || !previewEl) return;

    const total = parseFloat(amountEl.value) || 0;
    if (total <= 0) { previewEl.style.display = 'none'; return; }

    // Fetch live GST rate from settings
    let gstRate = 9;
    try {
        const s = await eel.get_settings()();
        gstRate = parseFloat(s.gst_rate) || 9;
    } catch (e) { /* use default */ }

    const gstTotal  = gstRate * 2;          // CGST + SGST
    const base      = total / (1 + gstTotal / 100);
    const cgst      = base * (gstRate / 100);
    const sgst      = cgst;

    const fmt = v => '\u20b9' + v.toFixed(2);
    document.getElementById('gst-base').textContent      = fmt(base);
    document.getElementById('gst-cgst').textContent      = fmt(cgst);
    document.getElementById('gst-sgst').textContent      = fmt(sgst);
    document.getElementById('gst-net').textContent       = fmt(total);
    document.getElementById('gst-cgst-label').textContent = `CGST (${gstRate}%)`;
    document.getElementById('gst-sgst-label').textContent = `SGST (${gstRate}%)`;
    previewEl.style.display = 'block';
}

// ============================================================
// OVERDUE INVOICES PANEL
// ============================================================
async function loadOverdueDues() {
    try {
        const items = await eel.get_overdue_invoices()();
        const list  = document.getElementById('overdue-list');
        const badge = document.getElementById('overdue-count-badge');
        if (!list) return;

        if (badge) badge.textContent = items.length;

        if (items.length === 0) {
            list.innerHTML = `<div class="overdue-empty"><i class="ri-checkbox-circle-line"></i> All invoices are up to date!</div>`;
            return;
        }

        list.innerHTML = items.slice(0, 20).map(item => {
            const sev   = item.severity || 'normal';
            const days  = item.days_overdue || 0;
            const label = days === 0 ? 'Today' : `${days}d overdue`;
            return `
                <div class="overdue-item">
                    <div>
                        <div class="overdue-customer">${item.customer_name}</div>
                        <div class="overdue-meta">${item.invoice_num} &middot; \u20b9${Number(item.amount).toLocaleString('en-IN')}</div>
                    </div>
                    <div style="display:flex;align-items:center;gap:10px;">
                        <span class="severity-${sev}">${label}</span>
                        <span class="status-badge ${item.status === 'Partial' ? 'status-partial' : 'status-unpaid'}">${item.status}</span>
                        <button class="icon-btn" style="width:26px;height:26px;color:var(--success);" onclick="markPaid('${item.invoice_num}')" title="Mark Paid">
                            <i class="ri-check-line"></i>
                        </button>
                    </div>
                </div>`;
        }).join('');
    } catch (e) { console.error('loadOverdueDues:', e); }
}

// ============================================================
// MONTHLY TARGET TRACKER
// ============================================================
async function loadMonthlyTarget() {
    try {
        const target = await eel.get_monthly_target()();
        const wrap   = document.getElementById('target-progress-wrap');
        const fill   = document.getElementById('target-bar-fill');
        const label  = document.getElementById('target-bar-label');
        if (!wrap || !fill || !label) return;

        if (!target || target <= 0) { wrap.style.display = 'none'; return; }

        // Get current month revenue from active filter stats
        const stats = await eel.get_filtered_dashboard(
            new Date().getFullYear() + '-' + String(new Date().getMonth()+1).padStart(2,'0') + '-01',
            new Date().getFullYear() + '-' + String(new Date().getMonth()+1).padStart(2,'0') + '-' + new Date(new Date().getFullYear(), new Date().getMonth()+1, 0).getDate()
        )();
        const actual = stats?.stats?.revenue || 0;
        const pct    = Math.min(Math.round((actual / target) * 100), 100);

        wrap.style.display = 'block';
        setTimeout(() => { fill.style.width = pct + '%'; }, 100);
        label.textContent  = `${pct}% of \u20b9${Number(target).toLocaleString('en-IN')} target`;
    } catch (e) { console.error('loadMonthlyTarget:', e); }
}

async function saveMonthlyTarget() {
    const val = parseFloat(document.getElementById('s-monthly-target')?.value) || 0;
    const r   = await eel.save_monthly_target(val)();
    showToast(r.status, r.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line',
        r.status === 'success' ? 'Monthly target saved!' : 'Error: ' + r.message);
    loadMonthlyTarget();
}

// ============================================================
// WHATSAPP TEMPLATE
// ============================================================
async function saveWATemplate() {
    const tmpl = document.getElementById('s-wa-template')?.value || '';
    const r    = await eel.save_whatsapp_template(tmpl)();
    showToast(r.status, r.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line',
        r.status === 'success' ? 'Template saved!' : 'Error: ' + r.message);
}

// Update sendWhatsApp to use the saved template
async function sendWhatsApp(phoneNum, customerName, amount, invoiceNum, filename) {
    if (!phoneNum?.trim()) { showToast('error', 'ri-phone-off-line', 'No phone number found.'); return; }
    let clean = phoneNum.replace(/[^\d+]/g, '');
    if (clean.length === 10) clean = '91' + clean;

    let tmpl = 'Hello {name}, your internet bill of \u20b9{amount} is due. Invoice: {invoice_num}.';
    try { tmpl = await eel.get_whatsapp_template()(); } catch (e) { /* use default */ }

    const msg = tmpl
        .replace('{name}', customerName)
        .replace('{amount}', amount)
        .replace('{invoice_num}', invoiceNum)
        .replace('{plan}', '');

    if (filename) {
        eel.automate_whatsapp_attachment(clean, msg, filename)();
    } else {
        window.open(`whatsapp://send?phone=${clean}&text=${encodeURIComponent(msg)}`, '_blank');
    }
}

// ============================================================
// PLANS MANAGEMENT (Settings)
// ============================================================
function renderPlansSettings() {
    const container = document.getElementById('plans-list');
    if (!container) return;
    if (_plansData.length === 0) {
        container.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;padding:8px;">No plans configured.</p>';
        return;
    }
    container.innerHTML = _plansData.map((plan, idx) => `
        <div class="plan-item">
            <span>${plan}</span>
            <button onclick="removePlan(${idx})" title="Remove"><i class="ri-delete-bin-line"></i></button>
        </div>
    `).join('');

    // Also update invoice form Plan dropdown
    const invPlan = document.getElementById('inv-plan');
    if (invPlan) {
        invPlan.innerHTML = _plansData.map(p => `<option value="${p}">${p}</option>`).join('');
    }
}

function addPlan() {
    const input = document.getElementById('new-plan-input');
    const val   = input?.value?.trim();
    if (!val) return;
    if (!_plansData.includes(val)) { _plansData.push(val); renderPlansSettings(); }
    if (input) input.value = '';
}

function removePlan(idx) {
    _plansData.splice(idx, 1);
    renderPlansSettings();
}

async function savePlans() {
    const r = await eel.save_plans(_plansData)();
    showToast(r.status, r.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line',
        r.status === 'success' ? 'Plans saved! Invoice form updated.' : 'Error: ' + r.message);
}

function refreshBulkPlanDropdown() {
    const sel = document.getElementById('bulk-plan');
    if (!sel) return;
    const plans = _plansData.length ? _plansData : ['100 MBPS UNL', '200 MBPS UNL', '300 MBPS UNL'];
    sel.innerHTML = plans.map(p => `<option value="${p}">${p}</option>`).join('');
}

// ============================================================
// BULK INVOICE GENERATION
// ============================================================
function updateBulkCount() {
    const checked = document.querySelectorAll('.bulk-chk:checked').length;
    const label   = document.getElementById('bulk-selected-count');
    if (label) label.textContent = `${checked} customer${checked !== 1 ? 's' : ''} selected`;
}

function toggleBulkSelectAll(chk) {
    document.querySelectorAll('.bulk-chk').forEach(c => { c.checked = chk.checked; });
    updateBulkCount();
}

async function runBulkInvoice() {
    const checkedBoxes = document.querySelectorAll('.bulk-chk:checked');
    if (checkedBoxes.length === 0) {
        showToast('error', 'ri-error-warning-line', 'Select at least one customer first!');
        return;
    }

    const plan    = document.getElementById('bulk-plan')?.value;
    const from    = document.getElementById('bulk-from')?.value;
    const to      = document.getElementById('bulk-to')?.value;
    const amount  = document.getElementById('bulk-amount')?.value;
    const months  = document.getElementById('bulk-months')?.value || 1;
    const status  = document.getElementById('bulk-status')?.value || 'Unpaid';
    const method  = document.getElementById('bulk-method')?.value || 'Cash';

    if (!from || !to || !amount) {
        showToast('error', 'ri-error-warning-line', 'Please fill in Billing From, To and Amount.');
        return;
    }

    const customer_ids = Array.from(checkedBoxes).map(c => c.dataset.id);
    const fromFmt = from.split('-').reverse().join('-');  // YYYY-MM-DD → DD-MM-YYYY
    const toFmt   = to.split('-').reverse().join('-');

    showConfirmModal(
        `Generate invoices for ${customer_ids.length} customer(s) — ${plan} @ \u20b9${amount}?`,
        async () => {
            const btn = document.getElementById('bulk-generate-btn');
            if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ri-loader-4-line" style="animation:spin 0.8s linear infinite;display:inline-block;"></i> Generating...'; }
            const r = await eel.generate_bulk_invoices(customer_ids, plan, fromFmt, toFmt, months, amount, status, method)();
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="ri-thunder-line"></i> Generate All'; }

            if (r.status === 'success') {
                showToast('success', 'ri-check-circle-line', `Generated ${r.generated}/${r.total} invoices!`);
                if (r.errors?.length) showToast('error', 'ri-error-warning-line', `Errors: ${r.errors.join(', ')}`);
                loadDashboard();
            } else {
                showToast('error', 'ri-error-warning-line', r.message);
            }
        },
        'Bulk Invoice Generation'
    );
}

// ============================================================
// CSV TEMPLATE DOWNLOAD
// ============================================================
function downloadCSVTemplate() {
    const headers = ['customer_id', 'name', 'tenant_name', 'phone', 'customer_address', 'customer_gstin', 'customer_email', 'notes', 'tags', 'connection_status'];
    const sample  = ['CUST-001', 'John Doe', 'Main Tenant', '9876543210', '123 Main St, City - 000000', '', 'john@email.com', '', 'VIP', 'Active'];
    const csv     = [headers.join(','), sample.join(',')].join('\n');
    const blob    = new Blob([csv], { type: 'text/csv' });
    const url     = URL.createObjectURL(blob);
    const a       = document.createElement('a');
    a.href     = url;
    a.download = 'Customer_Import_Template.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', 'ri-file-download-line', 'Template downloaded!');
}

// ============================================================
// SAMPLE PDF PREVIEW (Settings)
// ============================================================
async function previewSamplePDF() {
    showToast('info', 'ri-file-pdf-line', 'Generating sample invoice...');
    const r = await eel.generate_sample_pdf()();
    showToast(r.status, r.status === 'success' ? 'ri-check-circle-line' : 'ri-error-warning-line', r.message);
}

// ============================================================
// NEW INVOICE FROM CUSTOMER PROFILE
// ============================================================
function newInvoiceFromProfile() {
    if (!_currentCustomerData) { window.switchView('new-invoice'); return; }
    window.switchView('new-invoice');
    setTimeout(() => {
        const d = _currentCustomerData;
        document.getElementById('inv-name').value             = d.name             || '';
        document.getElementById('inv-customer_id').value      = d.customer_id      || '';
        document.getElementById('inv-tenant_name').value      = d.tenant_name      || '';
        document.getElementById('inv-phone').value            = d.phone            || '';
        document.getElementById('inv-customer_address').value = d.customer_address || '';
        document.getElementById('inv-customer_gstin').value   = d.customer_gstin   || '';
        const searchEl = document.getElementById('customerSearch');
        if (searchEl) searchEl.value = `${d.name} (${d.customer_id})`;
        showToast('info', 'ri-user-line', `Customer ${d.name} pre-filled.`);
    }, 100);
}

// ============================================================
// DASHBOARD AUGMENTATION — Load overdue + target on startup
// ============================================================
const _origLoadDashboard = window.loadDashboard || loadDashboard;
window.loadDashboard = async function() {
    await _origLoadDashboard?.();
    loadOverdueDues();
    loadMonthlyTarget();
};

