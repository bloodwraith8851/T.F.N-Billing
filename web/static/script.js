// App State
let revenueChart = null;
let statusChart = null;

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTheme();

    // Initialize Particles.js Background — Glowing 3D Stars
    if (window.particlesJS) {
        particlesJS('particles-js', {
            "particles": {
                "number": { "value": 120, "density": { "enable": true, "value_area": 900 } },
                "color": { "value": ["#ffffff", "#a8d8ff", "#ffd6a5", "#c8b8ff", "#b8f5e0"] },
                "shape": {
                    "type": ["circle", "star"],
                    "stroke": { "width": 0, "color": "#000000" },
                    "star": { "nb_sides": 5 }
                },
                "opacity": {
                    "value": 0.75,
                    "random": true,
                    "anim": { "enable": true, "speed": 0.6, "opacity_min": 0.05, "sync": false }
                },
                "size": {
                    "value": 2.5,
                    "random": true,
                    "anim": { "enable": true, "speed": 1.5, "size_min": 0.3, "sync": false }
                },
                "line_linked": { "enable": false },
                "move": {
                    "enable": true,
                    "speed": 0.4,
                    "direction": "none",
                    "random": true,
                    "straight": false,
                    "out_mode": "out",
                    "bounce": false,
                    "attract": { "enable": true, "rotateX": 1200, "rotateY": 1600 }
                }
            },
            "interactivity": {
                "detect_on": "window",
                "events": {
                    "onhover": { "enable": true, "mode": "bubble" },
                    "onclick": { "enable": true, "mode": "repulse" },
                    "resize": true
                },
                "modes": {
                    "bubble": { "distance": 120, "size": 5, "duration": 0.4, "opacity": 1, "speed": 3 },
                    "repulse": { "distance": 140, "duration": 0.4 }
                }
            },
            "retina_detect": true
        });
    }

    // Initialize Flatpickr Native Datepickers
    if (window.flatpickr) {
        flatpickr("#inv-billing_from", { dateFormat: "d-M-Y", defaultDate: new Date() });
        let nextMonth = new Date();
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        flatpickr("#inv-billing_to", { dateFormat: "d-M-Y", defaultDate: nextMonth });
    }

    // Load initial data via Python Eel
    loadDashboard();

    // Setup form listener
    document.getElementById('invoiceForm').addEventListener('submit', handleInvoiceSubmit);
    document.getElementById('inv-months').addEventListener('input', calculateTotal);
    document.getElementById('inv-plan').addEventListener('change', calculateTotal);

    // Setup views
    document.querySelectorAll('[data-view]').forEach(item => {
        item.addEventListener('click', (e) => {
            const viewId = e.currentTarget.getAttribute('data-view');
            switchView(viewId);
        });
    });

    // One-time setup: autofill customer select
    const customerSelectEl = document.getElementById('customerSelect');
    if (customerSelectEl) {
        customerSelectEl.addEventListener('change', function () {
            if (!this.value) {
                document.getElementById('invoiceForm').reset();
                return;
            }
            try {
                const data = JSON.parse(this.value);
                document.getElementById('inv-name').value = data.name || '';
                document.getElementById('inv-customer_id').value = data.customer_id || '';
                document.getElementById('inv-tenant_name').value = data.tenant_name || '';
                document.getElementById('inv-phone').value = data.phone || '';
                document.getElementById('inv-customer_address').value = data.customer_address || '';
                document.getElementById('inv-customer_gstin').value = data.customer_gstin || '';
            } catch (err) { console.error('Could not parse customer data:', err); }
        });
    }
});

// Calculate total natively based on dropdown
function calculateTotal() {
    const planMap = {
        '100 MBPS UNL': 400,
        '200 MBPS UNL': 500,
        '300 MBPS UNL': 600,
        '400 MBPS UNL': 700,
        '500 MBPS UNL': 800
    };
    const plan = document.getElementById('inv-plan').value;
    const months = parseInt(document.getElementById('inv-months').value) || 1;
    let base = planMap[plan] || 0;

    // Apply dummy GST logic
    let total = base * months;
    document.getElementById('inv-total_amount').value = total.toFixed(2);
}

// Navigation
function initNavigation() {
    window.switchView = (viewId) => {
        // Update Nav Active State
        document.querySelectorAll('.nav-links li').forEach(li => {
            li.classList.remove('active');
            if (li.getAttribute('data-view') === viewId) li.classList.add('active');
        });

        // Hide all views, show selected with animation
        document.querySelectorAll('.view').forEach(view => {
            view.classList.remove('active-view');
            view.classList.add('hidden-view');
        });

        const activeView = document.getElementById(viewId);
        activeView.classList.remove('hidden-view');
        activeView.classList.add('active-view');

        // Refresh specific view data using local Eel functions
        if (viewId === 'dashboard') loadDashboard();
        if (viewId === 'customers') loadCustomers();
        if (viewId === 'logs') loadHistory();

        // Animate the sidebar indicator pill
        updateSidebarIndicator(viewId);
    };
}

/* --- New Export & WhatsApp Functions --- */
async function exportCustomers() {
    try {
        const response = await eel.export_customers_csv()();
        if (response.status === 'success') {
            showToast('success', 'ri-check-circle-line', response.message);
        } else {
            showToast('error', 'ri-error-warning-line', response.message);
        }
    } catch (e) {
        console.error(e);
        showToast('error', 'ri-error-warning-line', 'Failed to export customers.');
    }
}

async function exportLogs() {
    try {
        const response = await eel.export_logs_csv()();
        if (response.status === 'success') {
            showToast('success', 'ri-check-circle-line', response.message);
        } else {
            showToast('error', 'ri-error-warning-line', response.message);
        }
    } catch (e) {
        console.error(e);
        showToast('error', 'ri-error-warning-line', 'Failed to export invoice history.');
    }
}

// Open PDF in default viewer
function openPdf(filename) {
    if (!filename || filename.trim() === '') {
        showToast('error', 'ri-error-warning-line', 'No PDF file found for this invoice.');
        return;
    }
    eel.open_pdf(filename)();
    showToast('info', 'ri-file-pdf-line', 'Opening PDF...');
}

async function sendWhatsApp(phoneNum, customerName, amount, invoiceNum, filename) {
    if (!phoneNum || phoneNum.trim() === '') {
        showToast('error', 'ri-phone-off-line', 'No phone number found. Please update the customer record.');
        return;
    }

    // Clean up spaces, dashes, etc
    let cleanPhone = phoneNum.replace(/[^\d+]/g, '');

    // Default to +91 if no country code provided
    if (cleanPhone.length === 10) {
        cleanPhone = "91" + cleanPhone;
    }

    const message = `Hello ${customerName}, your bill of ₹${amount} is ready. Invoice: ${invoiceNum}`;

    if (filename) {
        eel.automate_whatsapp_attachment(cleanPhone, message, filename)();
    } else {
        const waLink = `whatsapp://send?phone=${cleanPhone}&text=${encodeURIComponent(message)}`;
        window.open(waLink, '_blank');
    }
}

// Initial loads
loadCustomers();
loadHistory();

// Data Loading via EEL (Python Bridge)
async function loadDashboard() {
    const stats = await eel.get_dashboard_stats()();

    animateCounter(document.getElementById('stat-paid'), stats.paid, '₹', 1000);
    animateCounter(document.getElementById('stat-pending'), stats.pending, '₹', 1000);
    animateCounter(document.getElementById('stat-total'), stats.revenue, '₹', 1000);

    updateCharts(stats);
}

async function loadCustomers() {
    const customers = await eel.get_customers()();
    const tbody = document.getElementById('customers-tbody');
    const select = document.getElementById('customerSelect');

    tbody.innerHTML = '';
    select.innerHTML = '<option value="">-- New Customer --</option>';

    if (customers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 40px; color: var(--text-muted); font-weight: 500;">No customers found. Generate an invoice to save one.</td></tr>`;
    } else {
        customers.forEach(c => {
            let initials = c.name ? c.name.substring(0, 2).toUpperCase() : 'CU';
            tbody.innerHTML += `
                <tr onclick="viewCustomerProfile('${c.customer_id}')" style="cursor: pointer;">
                    <td>
                        <div class="customer-cell">
                            <div class="customer-avatar">${initials}</div>
                            <span style="font-weight: 500;">${c.name}</span>
                        </div>
                    </td>
                    <td><span style="color: #6b7280; font-size: 0.85em;">${c.customer_id}</span></td>
                    <td><span style="color: #6b7280;">${c.phone || '-'}</span></td>
                    <td><span style="color: #6b7280;">${c.tenant_name || '-'}</span></td>
                    <td><span style="font-size: 0.85em; color: var(--text-muted)">${c.customer_address}</span></td>
                    <td><span style="color: #6b7280;">${c.customer_gstin || '-'}</span></td>
                </tr>
            `;
            select.innerHTML += `<option value='${JSON.stringify(c).replace(/'/g, "&#39;")}'>${c.name} (${c.customer_id})</option>`;
        });
    }
}

async function loadHistory() {
    const logs = await eel.get_history()();
    const tbody = document.getElementById('logs-tbody');
    tbody.innerHTML = '';

    document.getElementById('stat-count').textContent = `${logs.length} Invoices Generated`;

    if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 40px; color: var(--text-muted); font-weight: 500;">No invoices generated yet.</td></tr>`;
    } else {
        logs.forEach(log => {
            let statusClass = 'status-unpaid';
            if (log.status === 'Paid') statusClass = 'status-paid';
            if (log.status === 'Partial') statusClass = 'status-partial';

            // Generate Avatar Initials
            let initials = log.customer_name ? log.customer_name.substring(0, 2).toUpperCase() : 'CU';

            tbody.innerHTML += `
                <tr class="row-${log.status.toLowerCase()}">
                    <td style="color: var(--text-muted)">${log.datetime}</td>
                    <td><span style="color: #6b7280; font-size: 0.85em;">${log.invoice_num}</span></td>
                    <td>
                        <div class="customer-cell">
                            <div class="customer-avatar">${initials}</div>
                            <span style="font-weight: 500;">${log.customer_name}</span>
                        </div>
                    </td>
                    <td style="font-weight: 500">₹${log.amount.toLocaleString('en-IN')}</td>
                    <td><span class="status-badge ${statusClass}">${log.status}</span></td>
                    <td><span style="color: var(--text-muted); font-size: 0.85em">${log.payment_method || 'None'}</span></td>
                    <td>
                        <button class="icon-btn" style="width: 30px; height: 30px; background: transparent; border: 1px solid rgba(0,0,0,0.1); color: #4A6CFA;" onclick="openPdf('${log.filename}')" title="View PDF"><i class="ri-file-pdf-line"></i></button>
                        <button class="icon-btn" style="width: 30px; height: 30px; background: transparent; border: 1px solid rgba(0,0,0,0.1); color: #25D366;" onclick="sendWhatsApp('${log.phone || ''}', '${log.customer_name}', '${log.amount}', '${log.invoice_num}', '${log.filename}')" title="Send via WhatsApp with Attachment"><i class="ri-whatsapp-line"></i></button>
                        ${log.status !== 'Paid' ? `<button class="icon-btn" style="width: 30px; height: 30px; background: transparent; border: 1px solid rgba(0,0,0,0.1); color: #30d158;" onclick="markPaid('${log.invoice_num}')" title="Mark as Paid"><i class="ri-check-line"></i></button>` : ''}
                    </td>
                </tr>
            `;
        });
    }

    // Also populate recent in dashboard
    const recentTbody = document.getElementById('recent-tbody');
    if (recentTbody) {
        recentTbody.innerHTML = '';
        if (logs.length === 0) {
            recentTbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 30px; color: var(--text-muted); font-weight: 500;">No recent transactions</td></tr>`;
        } else {
            logs.slice(0, 2).forEach(log => {
                let statusClass = 'status-unpaid';
                if (log.status === 'Paid') statusClass = 'status-paid';
                if (log.status === 'Partial') statusClass = 'status-partial';

                // Generate Avatar Initials
                let initials = log.customer_name ? log.customer_name.substring(0, 2).toUpperCase() : 'CU';

                recentTbody.innerHTML += `
                    <tr>
                        <td><span style="color: #6b7280; font-size: 0.85em;">${log.invoice_num}</span></td>
                        <td>
                            <div class="customer-cell">
                                <div class="customer-avatar">${initials}</div>
                                <span style="font-weight: 500;">${log.customer_name}</span>
                            </div>
                        </td>
                        <td style="font-weight: 500;">₹${log.amount.toLocaleString('en-IN')}</td>
                        <td><span class="status-badge ${statusClass}">${log.status}</span></td>
                    </tr>
                `;
            });
        }
    }
}

// Generate Invoice
async function handleInvoiceSubmit(e) {
    e.preventDefault();
    const btn = document.getElementById('generateBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i> Generating...';
    btn.disabled = true;

    try {
        const data = {
            name: document.getElementById('inv-name').value,
            customer_id: document.getElementById('inv-customer_id').value,
            tenant_name: document.getElementById('inv-tenant_name').value,
            phone: document.getElementById('inv-phone').value,
            customer_address: document.getElementById('inv-customer_address').value,
            customer_gstin: document.getElementById('inv-customer_gstin').value,
            plan: document.getElementById('inv-plan').value,
            months: document.getElementById('inv-months').value,
            billing_from: document.getElementById('inv-billing_from').value,
            billing_to: document.getElementById('inv-billing_to').value,
            total_amount: document.getElementById('inv-total_amount').value,
            discount: document.getElementById('inv-discount').value,
            late_fee: document.getElementById('inv-late_fee').value,
            payment_status: document.getElementById('inv-payment_status').value,
            payment_method: document.getElementById('inv-payment_method').value,
            save_customer: document.getElementById('inv-save_customer').checked
        };

        const response = await eel.generate_invoice(data)();

        if (response.status === 'success') {
            showToast('success', 'ri-check-circle-line', response.message);
            document.getElementById('invoiceForm').reset();
            window.switchView('dashboard');
        } else {
            showToast('error', 'ri-error-warning-line', 'Error: ' + response.message);
        }
    } catch (error) {
        showToast('error', 'ri-error-warning-line', "Exception triggering Python backend: " + error);
    } finally {
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// Charting
function updateCharts(stats) {
    Chart.defaults.color = '#8b8f98';
    Chart.defaults.font.family = "'Poppins', sans-serif";

    // Revenue Line
    const ctxRev = document.getElementById('revenueChart');
    if (revenueChart) revenueChart.destroy();

    revenueChart = new Chart(ctxRev, {
        type: 'line',
        data: {
            labels: ['Week 1', 'Week 2', 'Week 3', 'Week 4', 'This Week'],
            datasets: [{
                label: 'Revenue',
                data: [0, 0, 0, 0, stats.revenue],
                borderColor: '#ff3b30',
                backgroundColor: 'rgba(255, 59, 48, 0.1)',
                borderWidth: 3,
                tension: 0.4,
                fill: true,
                pointBackgroundColor: '#1a1c23',
                pointBorderColor: '#ff3b30',
                pointBorderWidth: 2,
                pointRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)', drawBorder: false } },
                x: { grid: { display: false, drawBorder: false } }
            }
        }
    });

    // Status Doughnut
    const ctxStat = document.getElementById('statusChart');
    if (statusChart) statusChart.destroy();

    let chartData = [stats.paid, stats.pending];
    if (stats.revenue === 0) chartData = [1];
    let chartColors = ['#30d158', '#ff3b30'];
    if (stats.revenue === 0) chartColors = ['#333'];

    statusChart = new Chart(ctxStat, {
        type: 'doughnut',
        data: {
            labels: stats.revenue === 0 ? ['No Data'] : ['Paid', 'Pending'],
            datasets: [{
                data: chartData,
                backgroundColor: chartColors,
                borderWidth: 0,
                hoverOffset: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '75%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 20, usePointStyle: true } }
            }
        }
    });
}

// Theme Handling
function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-toggle i');
    if (!icon) return;
    if (theme === 'dark') {
        icon.className = 'ri-sun-line';
    } else {
        icon.className = 'ri-moon-line';
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

// Universal Search Filter
function filterTables(query) {
    const q = query.toLowerCase();

    // Filter Customers
    const customersRows = document.querySelectorAll('#customers-tbody tr');
    if (customersRows.length) {
        customersRows.forEach(tr => {
            if (tr.innerText.toLowerCase().includes(q)) tr.style.display = '';
            else tr.style.display = 'none';
        });
    }

    // Filter History
    const historyRows = document.querySelectorAll('#logs-tbody tr');
    if (historyRows.length) {
        historyRows.forEach(tr => {
            if (tr.innerText.toLowerCase().includes(q)) tr.style.display = '';
            else tr.style.display = 'none';
        });
    }
}

// Mark Invoice as Paid
async function markPaid(invoiceNum) {
    if (!confirm(`Are you sure you want to mark Invoice ${invoiceNum} as Paid?`)) return;
    try {
        const response = await eel.mark_invoice_paid(invoiceNum)();
        if (response.status === 'success') {
            showToast('success', 'ri-check-circle-line', response.message || 'Invoice marked as paid.');
            loadHistory();
            loadDashboard();
        } else {
            showToast('error', 'ri-error-warning-line', 'Error: ' + response.message);
        }
    } catch (e) {
        console.error(e);
        showToast('error', 'ri-error-warning-line', 'Failed to mark as paid.');
    }
}

// Customer Profile
async function viewCustomerProfile(customerId) {
    try {
        const response = await eel.get_customer_profile(customerId)();
        if (response.status === 'success') {
            const { customer, logs, stats } = response;

            // Hydrate Header/Stats
            document.getElementById('cp-name').textContent = customer.name;
            document.getElementById('cp-avatar').textContent = customer.name ? customer.name.substring(0, 2).toUpperCase() : 'CU';
            document.getElementById('cp-id').textContent = customer.customer_id;
            document.getElementById('cp-phone').textContent = customer.phone || 'Not Provided';
            document.getElementById('cp-address').textContent = customer.customer_address || 'Not Provided';
            document.getElementById('cp-gstin').textContent = customer.customer_gstin || 'Not Provided';

            document.getElementById('cp-ltv').textContent = `₹${stats.total_paid.toLocaleString('en-IN')}`;
            document.getElementById('cp-pending').textContent = `₹${stats.pending_dues.toLocaleString('en-IN')}`;
            document.getElementById('cp-count').textContent = stats.total_invoices;

            // Hydrate specific table
            const tbody = document.getElementById('cp-logs-tbody');
            tbody.innerHTML = '';

            if (logs.length === 0) {
                tbody.innerHTML = `<tr><td colspan="5" style="text-align: center; padding: 40px; color: var(--text-muted); font-weight: 500;">No historic invoices for this customer.</td></tr>`;
            } else {
                logs.forEach(log => {
                    let statusClass = 'status-unpaid';
                    if (log.status === 'Paid') statusClass = 'status-paid';
                    if (log.status === 'Partial') statusClass = 'status-partial';

                    tbody.innerHTML += `
                        <tr>
                            <td style="color: var(--text-muted)">${log.datetime}</td>
                            <td><span style="color: #6b7280; font-size: 0.85em;">${log.invoice_num}</span></td>
                            <td style="font-weight: 500">₹${log.amount.toLocaleString('en-IN')}</td>
                            <td><span class="status-badge ${statusClass}">${log.status}</span></td>
                            <td>
                                <button class="icon-btn" style="width: 30px; height: 30px; background: transparent; border: 1px solid rgba(0,0,0,0.1); color: #4A6CFA;" onclick="openPdf('${log.filename}')" title="View PDF"><i class="ri-file-pdf-line"></i></button>
                                <button class="icon-btn" style="width: 30px; height: 30px; background: transparent; border: 1px solid rgba(0,0,0,0.1); color: #25D366;" onclick="sendWhatsApp('${log.phone || ''}', '${log.customer_name}', '${log.amount}', '${log.invoice_num}', '${log.filename}')" title="Send via WhatsApp with Attachment"><i class="ri-whatsapp-line"></i></button>
                                ${log.status !== 'Paid' ? `<button class="icon-btn" style="width: 30px; height: 30px; background: transparent; border: 1px solid rgba(0,0,0,0.1); color: #30d158;" onclick="markPaid('${log.invoice_num}'); setTimeout(() => viewCustomerProfile('${customerId}'), 500);" title="Mark as Paid"><i class="ri-check-line"></i></button>` : ''}
                            </td>
                        </tr>
                    `;
                });
            }

            // Transition View
            window.switchView('customer-profile');

        } else {
            showToast('error', 'ri-error-warning-line', 'Error loading profile: ' + response.message);
        }
    } catch (e) {
        console.error(e);
        showToast('error', 'ri-error-warning-line', 'Exception retrieving profile data.');
    }
}

// ==================== TOAST SYSTEM ====================
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

// ==================== LIVE CLOCK ====================
function startClock() {
    const clockEl = document.getElementById('sidebar-clock');
    const dateEl = document.getElementById('sidebar-date');
    const greetEl = document.getElementById('dashboard-greeting');
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    function tick() {
        const now = new Date();
        const rawH = now.getHours();
        const ampm = rawH >= 12 ? 'PM' : 'AM';
        const h12 = rawH % 12 || 12;
        const h = String(h12).padStart(2, '0');
        const m = String(now.getMinutes()).padStart(2, '0');
        const s = String(now.getSeconds()).padStart(2, '0');
        if (clockEl) clockEl.textContent = `${h}:${m}:${s} ${ampm}`;
        if (dateEl) dateEl.textContent = `${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
        if (greetEl) {
            const hr = now.getHours();
            let greeting;
            if (hr >= 0 && hr < 5) greeting = 'Good Night 🌌';
            else if (hr >= 5 && hr < 12) greeting = 'Good Morning ☀️';
            else if (hr >= 12 && hr < 17) greeting = 'Good Afternoon 🌤️';
            else if (hr >= 17 && hr < 21) greeting = 'Good Evening 🌇';
            else greeting = 'Good Night 🌌';
            greetEl.textContent = greeting;
        }
    }
    tick();
    setInterval(tick, 1000);
}
startClock();

// ==================== SIDEBAR INDICATOR ====================
function updateSidebarIndicator(viewId) {
    const indicator = document.getElementById('nav-indicator');
    const li = document.querySelector(`.nav-links li[data-view="${viewId}"]`);
    if (!indicator || !li) return;
    const navList = li.closest('ul');
    const liTop = li.offsetTop;
    indicator.style.top = (navList.offsetTop + liTop) + 'px';
}

// ==================== ANIMATED COUNTER ====================
function animateCounter(el, targetValue, prefix = '₹', duration = 900) {
    if (!el) return;
    const start = performance.now();
    const startVal = 0;
    function step(now) {
        const progress = Math.min((now - start) / duration, 1);
        const ease = 1 - Math.pow(1 - progress, 3);
        const current = Math.round(startVal + (targetValue - startVal) * ease);
        el.textContent = prefix + current.toLocaleString('en-IN');
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ==================== BUTTON RIPPLE ====================
document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn, .primary-btn, .btn-primary, .btn-secondary, .icon-btn');
    if (!btn) return;
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    const size = Math.max(btn.offsetWidth, btn.offsetHeight);
    const rect = btn.getBoundingClientRect();
    ripple.style.width = ripple.style.height = size + 'px';
    ripple.style.left = (e.clientX - rect.left - size / 2) + 'px';
    ripple.style.top = (e.clientY - rect.top - size / 2) + 'px';
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
});
