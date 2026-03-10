// ── Particles.js (exact copy from dashboard) ───────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    // Graceful offline fallback: particles.js may fail to load from CDN
    try {
        if (typeof window.particlesJS === 'function') {
            particlesJS('particles-js', {
                particles: {
                    number: { value: 120, density: { enable: true, value_area: 900 } },
                    color: { value: ['#ffffff', '#a8d8ff', '#ffd6a5', '#c8b8ff', '#b8f5e0'] },
                    shape: {
                        type: ['circle', 'star'],
                        stroke: { width: 0, color: '#000000' },
                        star: { nb_sides: 5 }
                    },
                    opacity: {
                        value: 0.75, random: true,
                        anim: { enable: true, speed: 0.6, opacity_min: 0.05, sync: false }
                    },
                    size: {
                        value: 2.5, random: true,
                        anim: { enable: true, speed: 1.5, size_min: 0.3, sync: false }
                    },
                    line_linked: { enable: false },
                    move: {
                        enable: true, speed: 0.4, direction: 'none',
                        random: true, straight: false, out_mode: 'out', bounce: false,
                        attract: { enable: true, rotateX: 1200, rotateY: 1600 }
                    }
                },
                interactivity: {
                    detect_on: 'window',
                    events: {
                        onhover: { enable: true, mode: 'bubble' },
                        onclick: { enable: false },   // disabled: pointer-events:none on canvas
                        resize: true
                    },
                    modes: {
                        bubble: { distance: 120, size: 5, duration: 0.4, opacity: 1, speed: 3 }
                    }
                },
                retina_detect: true
            });
        }
    } catch (err) {
        console.warn('Particles.js unavailable (offline?):', err);
    }

    // Load version from Python
    eel.get_version()(ver => {
        document.getElementById('ver-label').textContent = 'v' + ver;
    });

    // Load default install path
    eel.get_default_path()(path => {
        document.getElementById('path-input').value = path;
    });
});

// ── Screen switching ──────────────────────────────────────────────────────────
function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active-screen'));
    document.getElementById('screen-' + name).classList.add('active-screen');

    // Update sidebar step indicators
    const map = { welcome: 1, installing: 2, done: 3, error: 3 };
    const active = map[name] || 1;

    document.querySelectorAll('.step').forEach((el, i) => {
        el.classList.remove('active', 'done', 'error');
        if (i + 1 < active) el.classList.add('done');
        if (i + 1 === active) {
            // error screen: mark step 3 with 'error' class instead of 'active'
            el.classList.add(name === 'error' ? 'error' : 'active');
        }
    });
}

// ── Browse folder ─────────────────────────────────────────────────────────────
let _browsing = false;
async function browsePath() {
    if (_browsing) return;
    _browsing = true;
    const btn = document.querySelector('.btn-browse');
    if (btn) btn.disabled = true;

    try {
        const result = await eel.browse_install_dir()();
        if (result) document.getElementById('path-input').value = result;
    } catch (e) {
        console.warn('Browse error:', e);
    } finally {
        _browsing = false;
        if (btn) btn.disabled = false;
    }
}

// ── Start install ─────────────────────────────────────────────────────────────
function startInstall() {
    const path = document.getElementById('path-input').value.trim();
    if (!path) {
        const inp = document.getElementById('path-input');
        inp.style.borderColor = '#ef4444';
        setTimeout(() => (inp.style.borderColor = ''), 800);
        return;
    }

    // Prevent double-install: disable button immediately
    const btn = document.getElementById('btn-install-now');
    if (btn) btn.disabled = true;

    showScreen('installing');
    eel.start_install(path)();
}

// ── Eel callbacks from Python ──────────────────────────────────────────────────

// rAF-batched progress updates to prevent layout thrashing
let _pendingProgress = null;
let _rafPending = false;

eel.expose(update_progress);
function update_progress(pct, filename) {
    // Store latest values; flush once per animation frame
    _pendingProgress = { pct, filename };
    if (!_rafPending) {
        _rafPending = true;
        requestAnimationFrame(() => {
            if (_pendingProgress === null) { _rafPending = false; return; }
            const { pct: p, filename: f } = _pendingProgress;
            _pendingProgress = null;
            _rafPending = false;

            document.getElementById('progress-fill').style.width = (p * 100) + '%';
            document.getElementById('progress-pct').textContent = Math.round(p * 100) + '%';
            document.getElementById('progress-file').textContent = f || '';

            if (p > 0.1) {
                document.getElementById('install-sub').textContent = 'Copying application files…';
            }
        });
    }
}

eel.expose(install_complete);
function install_complete(target_path) {
    document.getElementById('done-path').textContent = 'Installed to: ' + target_path;
    showScreen('done');
}

eel.expose(install_error);
function install_error(msg) {
    document.getElementById('error-msg').textContent = msg;
    // Re-enable Install button so user can retry
    const btn = document.getElementById('btn-install-now');
    if (btn) btn.disabled = false;
    showScreen('error');
}
