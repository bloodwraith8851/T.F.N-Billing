// ============================================================
// APP STATE
// ============================================================
let revenueChart       = null;
let statusChart        = null;
let monthlyChart       = null;
let planChart          = null;
let _currentCustomerId = null;  // for customer profile save

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();
    initTheme();

    // Particles.js Background
    if (window.particlesJS) {
        particlesJS('particles-js', {
            particles: {
                number: { value: 120, density: { enable: true, value_area: 900 } },
                color:  { value: ["#ffffff","#a8d8ff","#ffd6a5","#c8b8ff","#b8f5e0"] },
                shape:  { type: ["circle","star"], stroke: { width: 0, color: "#000" }, star: { nb_sides: 5 } },
                opacity: { value: 0.75, random: true, anim: { enable: true, speed: 0.6, opacity_min: 0.05, sync: false } },
                size:    { value: 2.5,  random: true, anim: { enable: true, speed: 1.5, size_min: 0.3, sync: false } },
                line_linked: { enable: false },
                move: { enable: true, speed: 0.4, direction: "none", random: true, straight: false,
                        out_mode: "out", bounce: false, attract: { enable: true, rotateX: 1200, rotateY: 1600 } }
            },
            interactivity: {
                detect_on: "window",
                events: { onhover: { enable: true, mode: "bubble" }, onclick: { enable: true, mode: "repulse" }, resize: true },
                modes:  { bubble: { distance: 120, size: 5, duration: 0.4, opacity: 1, speed: 3 }, repulse: { distance: 140, duration: 0.4 } }
            },
            retina_detect: true
        });
    }

    // Flatpickr Datepickers
    if (window.flatpickr) {
        flatpickr("#inv-billing_from", { dateFormat: "d-M-Y", defaultDate: new Date() });
        let nextMonth = new Date();
        nextMonth.setMonth(nextMonth.getMonth() + 1);
        flatpickr("#inv-billing_to", { dateFormat: "d-M-Y", defaultDate: nextMonth });
    }

    // Load initial data
    loadDashboard();

    // Check for updates on startup
    setTimeout(checkForUpdates, 3000);

    // Form listeners
    document.getElementById('invoiceForm').addEventListener('submit', handleInvoiceSubmit);
    document.getElementById('inv-months').addEventListener('input', calculateTotal);
    document.getElementById('inv-plan').addEventListener('change', calculateTotal);

    // Customer select autofill
    const customerSelectEl = document.getElementById('customerSelect');
    if (customerSelectEl) {
        customerSelectEl.addEventListener('change', function () {
            if (!this.value) { document.getElementById('invoiceForm').reset(); return; }
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

    // Billing date duplicate check on change
    ['inv-customer_id','inv-billing_from','inv-billing_to'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', checkDuplicateInvoice);
    });

    // Log search / filter
    const logSearch  = document.getElementById('log-search');
    const logFilter  = document.getElementById('log-status-filter');
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

    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);

    // Close notification panel on outside click
    document.addEventListener('click', (e) => {
        const panel = document.getElementById('notification-panel');
        const btn   = document.getElementById('notif-btn');
        if (panel && !panel.contains(e.target) && btn && !btn.contains(e.target)) {
            panel.classList.add('hidden');
        }
    });

    loadNotifications();
});

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
        if (viewId === 'dashboard')  loadDashboard();
        if (viewId === 'customers')  loadCustomers();
        if (viewId === 'logs')       loadHistory();
        if (viewId === 'settings')   loadSettings();
        if (viewId === 'analytics')  loadAnalytics();
        updateSidebarIndicator(viewId);
    };

    document.querySelectorAll('[data-view]').forEach(item => {
        item.addEventListener('click', (e) => {
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
// DASHBOARD
// ============================================================
async function loadDashboard() {
    const stats = await eel.get_dashboard_stats()();
    animateCounter(document.getElementById('stat-paid'),    stats.paid,    '₹', 1000);
    animateCounter(document.getElementById('stat-pending'), stats.pending, '₹', 1000);
    animateCounter(document.getElementById('stat-total'),   stats.revenue, '₹', 1000);

    // Collection rate ring
    const rate   = stats.collection_rate || 0;
    const rateEl = document.getElementById('stat-rate');
    if (rateEl) rateEl.textContent = rate + '%';
    const circle = document.getElementById('rate-ring-fill');
    if (circle) {
        const circumference = 2 * Math.PI * 34;
        const offset = circumference - (rate / 100) * circumference;
        circle.style.strokeDashoffset = offset;
    }

    updateCharts(stats);
    loadHistory();
    loadOutstandingDues();
}

async function loadOutstandingDues() {
    try {
        const dues = await eel.get_outstanding_dues()();
        const list  = document.getElementById('outstanding-list');
        const badge = document.getElementById('outstanding-count');
        if (!list) return;
        if (badge) badge.textContent = dues.length;
        if (dues.length === 0) {
            list.innerHTML = `<p style="color:var(--text-muted);text-align:center;padding:20px 0;font-size:0.9rem;">All invoices are paid ✓</p>`;
            return;
        }
        list.innerHTML = dues.map(d => `
            <div class="outstanding-item">
                <div class="outstanding-info">
                    <span class="outstanding-name">${d.customer_name}</span>
                    <span class="outstanding-inv">${d.invoice_num}</span>
                </div>
                <div class="outstanding-right">
                    <span class="outstanding-amount">₹${Number(d.amount).toLocaleString('en-IN')}</span>
                    <span class="outstanding-days ${d.days_overdue > 30 ? 'overdue-critical' : 'overdue-warn'}">${d.days_overdue}d</span>
                </div>
            </div>
        `).join('');
    } catch (e) { console.error('Outstanding dues error:', e); }
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

        Chart.defaults.color      = '#8b8f98';
        Chart.defaults.font.family = "'Poppins', sans-serif";

        // Monthly Revenue Bar Chart
        const ctxM = document.getElementById('monthlyRevenueChart');
        if (monthlyChart) monthlyChart.destroy();
        monthlyChart = new Chart(ctxM, {
            type: 'bar',
            data: {
                labels: monthly.months || [],
                datasets: [{
                    label: 'Revenue (₹)',
                    data:  monthly.revenues || [],
                    backgroundColor: monthly.revenues.map((_, i) =>
                        `hsla(${240 + i * 20}, 70%, 65%, 0.75)`),
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(255,255,255,0.05)' },
                         ticks: { callback: v => '₹' + v.toLocaleString('en-IN') } },
                    x: { grid: { display: false } }
                }
            }
        });

        // Plan Breakdown Donut
        const ctxP = document.getElementById('planBreakdownChart');
        if (planChart) planChart.destroy();
        const planColors = ['#6366f1','#34d399','#f59e0b','#ef4444','#3b82f6'];
        planChart = new Chart(ctxP, {
            type: 'doughnut',
            data: {
                labels: plans.plans && plans.plans.length ? plans.plans : ['No Data'],
                datasets: [{
                    data:            plans.counts && plans.counts.length ? plans.counts : [1],
                    backgroundColor: plans.plans && plans.plans.length ? planColors : ['#333'],
                    borderWidth: 0, hoverOffset: 6
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                cutout: '70%',
                plugins: { legend: { position: 'bottom', labels: { padding: 15, usePointStyle: true } } }
            }
        });
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
    select.innerHTML = '<option value="">-- New Customer --</option>';

    if (customers.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);font-weight:500;">No customers found.</td></tr>`;
    } else {
        customers.forEach(c => {
            const initials = c.name ? c.name.substring(0,2).toUpperCase() : 'CU';
            const statusHtml = statusBadge(c.connection_status || 'Active');
            const tagsHtml   = (c.tags || '').split(',').filter(t=>t.trim()).map(t =>
                `<span class="tag-pill">${t.trim()}</span>`).join('');
            tbody.innerHTML += `
                <tr onclick="viewCustomerProfile('${c.customer_id}')" style="cursor:pointer;">
                    <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;">${c.name}</span></div></td>
                    <td><span style="color:#6b7280;font-size:0.85em;">${c.customer_id}</span></td>
                    <td><span style="color:#6b7280;">${c.phone || '-'}</span></td>
                    <td><span style="color:#6b7280;">${c.tenant_name || '-'}</span></td>
                    <td><span style="font-size:0.85em;color:var(--text-muted);">${c.customer_address}</span></td>
                    <td>${statusHtml}</td>
                    <td>${tagsHtml}</td>
                </tr>`;
            select.innerHTML += `<option value='${JSON.stringify(c).replace(/'/g,"&#39;")}'>${c.name} (${c.customer_id})</option>`;
        });
    }

    // Re-apply active filter after reload
    filterCustomers();
}

function filterCustomers() {
    const query  = (document.getElementById('customer-search')?.value  || '').toLowerCase();
    const status = (document.getElementById('customer-status-filter')?.value || 'All');
    document.querySelectorAll('#customers-tbody tr').forEach(tr => {
        const text        = tr.innerText.toLowerCase();
        const matchSearch = !query || text.includes(query);
        const matchStatus = status === 'All' || text.includes(status.toLowerCase());
        tr.style.display = (matchSearch && matchStatus) ? '' : 'none';
    });
}

function statusBadge(status) {
    const map = {
        'Active':     'status-active',
        'Suspended':  'status-suspended',
        'Terminated': 'status-terminated'
    };
    return `<span class="conn-badge ${map[status] || 'status-active'}">${status || 'Active'}</span>`;
}

// CSV Import
async function handleCSVImport(input) {
    if (!input.files || !input.files[0]) return;
    const file   = input.files[0];
    const reader = new FileReader();
    reader.onload = async (e) => {
        try {
            const csvText = e.target.result;
            const result  = await eel.import_customers_csv_data(csvText)();
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
    reader.readAsText(file);
    input.value = ''; // reset so same file can be re-selected
}

// ============================================================
// INVOICE HISTORY
// ============================================================
async function loadHistory() {
    const logs  = await eel.get_history()();
    const tbody = document.getElementById('logs-tbody');
    tbody.innerHTML = '';

    document.getElementById('stat-count').textContent = `${logs.length} Invoices Generated`;

    if (logs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;padding:40px;color:var(--text-muted);font-weight:500;">No invoices generated yet.</td></tr>`;
    } else {
        logs.forEach(log => {
            let sc = log.status === 'Paid' ? 'status-paid' : log.status === 'Partial' ? 'status-partial' : 'status-unpaid';
            const initials = log.customer_name ? log.customer_name.substring(0,2).toUpperCase() : 'CU';
            tbody.innerHTML += `
                <tr class="row-${log.status.toLowerCase()}">
                    <td style="color:var(--text-muted)">${log.datetime}</td>
                    <td><span style="color:#6b7280;font-size:0.85em;">${log.invoice_num}</span></td>
                    <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;">${log.customer_name}</span></div></td>
                    <td style="font-weight:500">₹${Number(log.amount).toLocaleString('en-IN')}</td>
                    <td><span class="status-badge ${sc}">${log.status}</span></td>
                    <td><span style="color:var(--text-muted);font-size:0.85em">${log.payment_method || 'None'}</span></td>
                    <td>
                        <button class="icon-btn" style="width:30px;height:30px;background:transparent;border:1px solid rgba(0,0,0,0.1);color:#4A6CFA;" onclick="openPdf('${log.filename}')" title="View PDF"><i class="ri-file-pdf-line"></i></button>
                        <button class="icon-btn" style="width:30px;height:30px;background:transparent;border:1px solid rgba(0,0,0,0.1);color:#25D366;" onclick="sendWhatsApp('${log.phone||''}','${log.customer_name}','${log.amount}','${log.invoice_num}','${log.filename}')" title="WhatsApp"><i class="ri-whatsapp-line"></i></button>
                        ${log.status !== 'Paid' ? `<button class="icon-btn" style="width:30px;height:30px;background:transparent;border:1px solid rgba(0,0,0,0.1);color:#30d158;" onclick="markPaid('${log.invoice_num}')" title="Mark Paid"><i class="ri-check-line"></i></button>` : ''}
                    </td>
                </tr>`;
        });
    }

    // Populate dashboard recent-tbody
    const recentTbody = document.getElementById('recent-tbody');
    if (recentTbody) {
        recentTbody.innerHTML = '';
        if (logs.length === 0) {
            recentTbody.innerHTML = `<tr><td colspan="4" style="text-align:center;padding:30px;color:var(--text-muted);">No recent transactions</td></tr>`;
        } else {
            logs.slice(0,5).forEach(log => {
                let sc = log.status === 'Paid' ? 'status-paid' : log.status === 'Partial' ? 'status-partial' : 'status-unpaid';
                const initials = log.customer_name ? log.customer_name.substring(0,2).toUpperCase() : 'CU';
                recentTbody.innerHTML += `
                    <tr>
                        <td><span style="color:#6b7280;font-size:0.85em;">${log.invoice_num}</span></td>
                        <td><div class="customer-cell"><div class="customer-avatar">${initials}</div><span style="font-weight:500;">${log.customer_name}</span></div></td>
                        <td style="font-weight:500;">₹${Number(log.amount).toLocaleString('en-IN')}</td>
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
            // Extract date from first cell (format dd-mm-yyyy hh:mm)
            const dateCell = tr.cells[0]?.textContent?.trim() || '';
            const parts    = dateCell.split(' ')[0]?.split('-') || [];
            if (parts.length === 3) {
                const rowDate = `${parts[2]}-${parts[1]}-${parts[0]}`; // yyyy-mm-dd
                if (fromVal && rowDate < fromVal) matchDate = false;
                if (toVal   && rowDate > toVal)   matchDate = false;
            }
        }
        tr.style.display = (matchSearch && matchStatus && matchDate) ? '' : 'none';
    });
}

// ============================================================
// INVOICE — FORM SUBMIT & DUPLICATE CHECK
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
    const btn = document.getElementById('generateBtn');
    const orig = btn.innerHTML;
    btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i> Generating...';
    btn.disabled = true;

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
                if (fpTo)   { const nm = new Date(); nm.setMonth(nm.getMonth()+1); fpTo.setDate(nm, true); }
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
        showToast(r.status, r.status==='success'?'ri-check-circle-line':'ri-error-warning-line', r.message);
    } catch (e) { showToast('error', 'ri-error-warning-line', 'Export failed.'); }
}

async function exportLogs() {
    try {
        const r = await eel.export_logs_csv()();
        showToast(r.status, r.status==='success'?'ri-check-circle-line':'ri-error-warning-line', r.message);
    } catch (e) { showToast('error', 'ri-error-warning-line', 'Export failed.'); }
}

function openPdf(filename) {
    if (!filename?.trim()) { showToast('error','ri-error-warning-line','No PDF file found.'); return; }
    eel.open_pdf(filename)();
    showToast('info','ri-file-pdf-line','Opening PDF...');
}

async function sendWhatsApp(phoneNum, customerName, amount, invoiceNum, filename) {
    if (!phoneNum?.trim()) { showToast('error','ri-phone-off-line','No phone number found.'); return; }
    let clean = phoneNum.replace(/[^\d+]/g,'');
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
    if (r.status === 'success') { showToast('success','ri-check-circle-line', r.message); loadHistory(); loadDashboard(); }
    else showToast('error','ri-error-warning-line','Error: ' + r.message);
}

// ============================================================
// CUSTOMER PROFILE
// ============================================================
async function viewCustomerProfile(customerId) {
    try {
        const response = await eel.get_customer_profile(customerId)();
        if (response.status !== 'success') { showToast('error','ri-error-warning-line','Error: '+response.message); return; }

        const { customer, logs, stats } = response;
        _currentCustomerId = customerId;

        document.getElementById('cp-name').textContent    = customer.name;
        document.getElementById('cp-avatar').textContent  = customer.name ? customer.name.substring(0,2).toUpperCase() : 'CU';
        document.getElementById('cp-id').textContent      = customer.customer_id;
        document.getElementById('cp-phone').textContent   = customer.phone || 'Not Provided';
        document.getElementById('cp-address').textContent = customer.customer_address || 'Not Provided';
        document.getElementById('cp-gstin').textContent   = customer.customer_gstin || 'Not Provided';

        // Tags
        const tagsHtml = (customer.tags || '').split(',').filter(t=>t.trim()).map(t=>`<span class="tag-pill">${t.trim()}</span>`).join('') || '--';
        document.getElementById('cp-tags-display').innerHTML = tagsHtml;
        document.getElementById('cp-notes-display').textContent = customer.notes || '--';
        document.getElementById('cp-status-badge').innerHTML = statusBadge(customer.connection_status || 'Active');

        // Pre-fill edit form
        document.getElementById('cp-edit-status').value = customer.connection_status || 'Active';
        document.getElementById('cp-edit-tags').value   = customer.tags || '';
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
                const sc = log.status==='Paid'?'status-paid':log.status==='Partial'?'status-partial':'status-unpaid';
                tbody.innerHTML += `
                    <tr>
                        <td style="color:var(--text-muted)">${log.datetime}</td>
                        <td><span style="color:#6b7280;font-size:0.85em;">${log.invoice_num}</span></td>
                        <td style="font-weight:500">₹${Number(log.amount).toLocaleString('en-IN')}</td>
                        <td><span class="status-badge ${sc}">${log.status}</span></td>
                        <td>
                            <button class="icon-btn" style="width:30px;height:30px;background:transparent;border:1px solid rgba(0,0,0,0.1);color:#4A6CFA;" onclick="openPdf('${log.filename}')"><i class="ri-file-pdf-line"></i></button>
                            ${log.status !== 'Paid' ? `<button class="icon-btn" style="width:30px;height:30px;background:transparent;border:1px solid rgba(0,0,0,0.1);color:#30d158;" onclick="markPaid('${log.invoice_num}');setTimeout(()=>viewCustomerProfile('${customerId}'),500)"><i class="ri-check-line"></i></button>` : ''}
                        </td>
                    </tr>`;
            });
        }

        window.switchView('customer-profile');
    } catch (e) { console.error(e); showToast('error','ri-error-warning-line','Exception loading profile.'); }
}

async function saveCustomerNotes() {
    if (!_currentCustomerId) return;
    const status = document.getElementById('cp-edit-status').value;
    const tags   = document.getElementById('cp-edit-tags').value;
    const notes  = document.getElementById('cp-edit-notes').value;
    const r = await eel.update_customer_notes(_currentCustomerId, notes, tags, status)();
    if (r.status === 'success') {
        showToast('success','ri-check-circle-line','Customer updated.');
        viewCustomerProfile(_currentCustomerId);
    } else {
        showToast('error','ri-error-warning-line',r.message);
    }
}

// ============================================================
// CHARTS (DASHBOARD)
// ============================================================
function updateCharts(stats) {
    Chart.defaults.color      = '#8b8f98';
    Chart.defaults.font.family = "'Poppins', sans-serif";

    // Revenue line (hidden canvas – kept for compat)
    const ctxRev = document.getElementById('revenueChart');
    if (revenueChart) revenueChart.destroy();
    revenueChart = new Chart(ctxRev, {
        type: 'line',
        data: { labels: ['','','','','Now'], datasets: [{ data: [0,0,0,0,stats.revenue], borderColor:'#ff3b30', backgroundColor:'rgba(255,59,48,0.1)', borderWidth:3, tension:0.4, fill:true }] },
        options: { responsive:true, maintainAspectRatio:false, plugins:{legend:{display:false}}, scales:{y:{beginAtZero:true,grid:{color:'rgba(255,255,255,0.05)'}},x:{grid:{display:false}}} }
    });

    // Status Doughnut
    const ctxStat = document.getElementById('statusChart');
    if (statusChart) statusChart.destroy();
    let chartData   = stats.revenue === 0 ? [1] : [stats.paid, stats.pending];
    let chartColors = stats.revenue === 0 ? ['#333'] : ['#30d158', '#ff3b30'];

    statusChart = new Chart(ctxStat, {
        type: 'doughnut',
        data: {
            labels: stats.revenue === 0 ? ['No Data'] : ['Paid','Pending'],
            datasets: [{ data: chartData, backgroundColor: chartColors, borderWidth: 0, hoverOffset: 4 }]
        },
        options: { responsive:true, maintainAspectRatio:false, cutout:'75%', plugins:{legend:{position:'bottom',labels:{padding:20,usePointStyle:true}}} }
    });
}

// ============================================================
// NOTIFICATIONS
// ============================================================
async function loadNotifications() {
    try {
        const logs = await eel.get_history()();
        const list = document.getElementById('notif-list');
        const badge = document.getElementById('notif-badge');
        if (!list) return;
        const recent = logs.slice(0,5);
        if (recent.length === 0) {
            list.innerHTML = '<div class="notif-empty">No recent activity</div>';
            if (badge) badge.style.display = 'none';
            return;
        }
        if (badge) { badge.textContent = recent.length; badge.style.display = ''; }
        list.innerHTML = recent.map(l => {
            const icon  = l.status==='Paid' ? '✓' : l.status==='Partial' ? '⋯' : '!';
            const color = l.status==='Paid' ? '#30d158' : l.status==='Partial' ? '#ffc107' : '#ff3b30';
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
// APP LOGS VIEWER
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
        showToast(res.status, res.status==='success'?'ri-check-circle-line':'ri-error-warning-line',
            res.status==='success' ? 'Settings saved!' : 'Error: '+res.message);
    } catch (e) { showToast('error','ri-error-warning-line','Failed to save settings.'); }
}

async function doResetCounter() {
    if (!confirm('Reset invoice counter to #2059?')) return;
    const res = await eel.reset_invoice_counter()();
    showToast(res.status, res.status==='success'?'ri-refresh-line':'ri-error-warning-line', res.message);
}

// ============================================================
// THEME
// ============================================================
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function updateThemeIcon(theme) {
    const icon = document.querySelector('.theme-toggle i');
    if (icon) icon.className = theme === 'dark' ? 'ri-sun-line' : 'ri-moon-line';
}

function toggleTheme() {
    const current  = document.documentElement.getAttribute('data-theme');
    const newTheme = current === 'light' ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

// ============================================================
// UNIVERSAL SEARCH
// ============================================================
function filterTables(query) {
    const q = query.toLowerCase();
    ['#customers-tbody tr','#logs-tbody tr'].forEach(sel => {
        document.querySelectorAll(sel).forEach(tr => {
            tr.style.display = tr.innerText.toLowerCase().includes(q) ? '' : 'none';
        });
    });
}

// ============================================================
// PLAN TOTAL CALCULATOR
// ============================================================
function calculateTotal() {
    const planMap = { '100 MBPS UNL':400, '200 MBPS UNL':500, '300 MBPS UNL':600, '400 MBPS UNL':700, '500 MBPS UNL':800 };
    const plan   = document.getElementById('inv-plan').value;
    const months = parseInt(document.getElementById('inv-months').value) || 1;
    document.getElementById('inv-total_amount').value = ((planMap[plan] || 0) * months).toFixed(2);
}

// ============================================================
// SIDEBAR INDICATOR
// ============================================================
function updateSidebarIndicator(viewId) {
    const indicator = document.getElementById('nav-indicator');
    const li = document.querySelector(`.nav-links li[data-view="${viewId}"]`);
    if (!indicator || !li) return;
    indicator.style.top = (li.closest('ul').offsetTop + li.offsetTop) + 'px';
}

// ============================================================
// ANIMATED COUNTER
// ============================================================
function animateCounter(el, targetValue, prefix='₹', duration=900) {
    if (!el) return;
    const start = performance.now();
    function step(now) {
        const p = Math.min((now - start) / duration, 1);
        const e = 1 - Math.pow(1-p, 3);
        el.textContent = prefix + Math.round(targetValue * e).toLocaleString('en-IN');
        if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
}

// ============================================================
// LIVE CLOCK
// ============================================================
function startClock() {
    const clockEl = document.getElementById('sidebar-clock');
    const dateEl  = document.getElementById('sidebar-date');
    const greetEl = document.getElementById('dashboard-greeting');
    const days    = ['Sunday','Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'];
    const months  = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

    function tick() {
        const now  = new Date();
        const rawH = now.getHours();
        const ampm = rawH >= 12 ? 'PM' : 'AM';
        const h12  = rawH % 12 || 12;
        const h = String(h12).padStart(2,'0');
        const m = String(now.getMinutes()).padStart(2,'0');
        const s = String(now.getSeconds()).padStart(2,'0');
        if (clockEl) clockEl.textContent = `${h}:${m}:${s} ${ampm}`;
        if (dateEl)  dateEl.textContent  = `${days[now.getDay()]}, ${now.getDate()} ${months[now.getMonth()]} ${now.getFullYear()}`;
        if (greetEl) {
            const hr = now.getHours();
            greetEl.textContent = hr<5?'Good Night 🌌':hr<12?'Good Morning ☀️':hr<17?'Good Afternoon 🌤️':hr<21?'Good Evening 🌇':'Good Night 🌌';
        }
    }
    tick();
    setInterval(tick, 1000);
}
startClock();

// ============================================================
// TOAST SYSTEM
// ============================================================
function showToast(type, icon, message, duration=3500) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className  = `toast ${type}`;
    toast.innerHTML  = `<i class="${icon}"></i><span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
        toast.classList.add('fade-out');
        toast.addEventListener('animationend', () => toast.remove());
    }, duration);
}

// ============================================================
// BUTTON RIPPLE
// ============================================================
document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn,.primary-btn,.btn-primary,.btn-secondary,.icon-btn');
    if (!btn) return;
    const ripple = document.createElement('span');
    ripple.classList.add('ripple');
    const size = Math.max(btn.offsetWidth, btn.offsetHeight);
    const rect = btn.getBoundingClientRect();
    ripple.style.width  = ripple.style.height = size + 'px';
    ripple.style.left   = (e.clientX - rect.left - size/2) + 'px';
    ripple.style.top    = (e.clientY - rect.top  - size/2) + 'px';
    btn.appendChild(ripple);
    ripple.addEventListener('animationend', () => ripple.remove());
});

// ============================================================
// AUTO-UPDATE SYSTEM
// ============================================================
async function checkForUpdates(manual=false) {
    if (manual) showToast('info','ri-refresh-line','Checking for updates...');
    try {
        const result = await eel.check_for_updates()();
        if (result.status === 'update_available') showUpdateBanner(result.latest, result.url);
        else if (manual) showToast('success','ri-checkbox-circle-line','You are on the latest version ✓');
    } catch (e) {
        if (manual) showToast('error','ri-error-warning-line','Update check failed.');
    }
}

function showUpdateBanner(version, downloadUrl) {
    const old = document.getElementById('update-banner');
    if (old) old.remove();
    const banner = document.createElement('div');
    banner.id        = 'update-banner';
    banner.className = 'update-banner animated-entry';
    banner.innerHTML = `
        <div class="update-content"><i class="ri-rocket-2-line"></i><span>Update Available! <strong>v${version}</strong> is ready.</span></div>
        <div class="update-actions">
            <button class="btn-update-now" onclick="runUpdate('${downloadUrl}')">Download &amp; Install</button>
            <button class="btn-update-close" onclick="this.parentElement.parentElement.remove()"><i class="ri-close-line"></i></button>
        </div>`;
    document.body.appendChild(banner);
}

window.runUpdate = async (url) => {
    const btn = document.querySelector('.btn-update-now');
    if (btn) { btn.innerHTML = '<i class="ri-loader-4-line ri-spin"></i> Downloading...'; btn.disabled = true; }
    showToast('info','ri-download-line','Starting update download...', 3000);
    try { await eel.download_and_install_update(url)(); }
    catch (e) { showToast('error','ri-error-warning-line','Failed to initiate download.'); }
};

eel.expose(update_download_status);
function update_download_status(msg) {
    const btn = document.querySelector('.btn-update-now');
    if (btn) btn.innerHTML = msg;
}

eel.expose(handle_update_error);
function handle_update_error(msg) {
    showToast('error','ri-error-warning-line','Update Error: ' + msg, 6000);
    const btn = document.querySelector('.btn-update-now');
    if (btn) { btn.innerHTML = 'Download &amp; Install'; btn.disabled = false; }
}

// Helper: "New Customer" button in customers view
function showNewInvoice() { window.switchView('new-invoice'); }
