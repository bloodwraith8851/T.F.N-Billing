/* =============================================================
   installer.js  —  T.F.N Billing v2.2.0  Setup Frontend Logic
   ============================================================= */

// ── State ─────────────────────────────────────────────────────
const state = {
    startedAt:    0,          // timestamp when install began
    totalFiles:   0,          // estimated from progress (unused by backend, reserved)
    lastPct:      0,          // last received percent (0–1)
    rafPending:   false,      // rAF throttle flag
    pendingProg:  null,       // { pct, filename } buffer
    done:         false,      // prevents double-complete
};

// ── DOMContentLoaded ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initParticles();
    loadVersionAndPath();
    setupKeyboard();
});

// ── Particles (same config as main dashboard) ────────────────
function initParticles() {
    try {
        if (typeof window.particlesJS !== 'function') return;
        particlesJS('particles-js', {
            particles: {
                number: { value: 120, density: { enable: true, value_area: 900 } },
                color:  { value: ['#ffffff', '#a8d8ff', '#ffd6a5', '#c8b8ff', '#b8f5e0'] },
                shape:  {
                    type: ['circle', 'star'],
                    stroke: { width: 0, color: '#000000' },
                    star:   { nb_sides: 5 }
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
                    onclick: { enable: false },
                    resize:  true
                },
                modes: {
                    bubble: { distance: 120, size: 5, duration: 0.4, opacity: 1, speed: 3 }
                }
            },
            retina_detect: true
        });
    } catch (err) {
        console.warn('Particles.js unavailable (offline?):', err);
    }
}

// ── Version + default path ───────────────────────────────────
function loadVersionAndPath() {
    eel.get_version()(ver => {
        const el = document.getElementById('ver-label');
        if (el) el.textContent = 'v' + ver;
    });

    eel.get_default_path()(path => {
        const el = document.getElementById('path-input');
        if (el && path) el.value = path;
    });
}

// ── Keyboard shortcuts ───────────────────────────────────────
function setupKeyboard() {
    document.addEventListener('keydown', e => {
        const welcome  = document.getElementById('screen-welcome');
        const isActive = welcome && welcome.classList.contains('active-screen');

        if (e.key === 'Enter' && isActive) {
            e.preventDefault();
            startInstall();
        }
        if (e.key === 'Escape') {
            e.preventDefault();
            eel.cancel_install()();
        }
    });
}

// ── Screen switching ─────────────────────────────────────────
function showScreen(name) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active-screen'));
    const target = document.getElementById('screen-' + name);
    if (target) target.classList.add('active-screen');

    // Sidebar step indicators
    const map = { welcome: 1, installing: 2, done: 3, error: 3 };
    const active = map[name] || 1;

    document.querySelectorAll('.step').forEach((el, i) => {
        el.classList.remove('active', 'done', 'error');
        if (i + 1 <  active) el.classList.add('done');
        if (i + 1 === active) el.classList.add(name === 'error' ? 'error' : 'active');
    });
}

// ── Browse folder ────────────────────────────────────────────
let _browsing = false;

async function browsePath() {
    if (_browsing) return;
    _browsing = true;
    const btn = document.querySelector('.btn-browse');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ri-loader-4-line"></i> Opening…'; }

    try {
        const result = await eel.browse_install_dir()();
        if (result) document.getElementById('path-input').value = result;
    } catch (e) {
        console.warn('Browse error:', e);
    } finally {
        _browsing = false;
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="ri-folder-open-line"></i> Browse'; }
    }
}

// ── Start install ────────────────────────────────────────────
function startInstall() {
    const inp  = document.getElementById('path-input');
    const path = inp ? inp.value.trim() : '';

    if (!path) {
        // Shake input to signal validation error
        inp.style.borderColor = '#ef4444';
        inp.style.animation   = 'shake 0.4s ease';
        setTimeout(() => {
            inp.style.borderColor = '';
            inp.style.animation   = '';
        }, 900);
        return;
    }

    // Disable install button immediately to prevent double-click
    const btn = document.getElementById('btn-install-now');
    if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ri-loader-4-line"></i> Starting…'; }

    // Reset progress state
    state.startedAt  = Date.now();
    state.lastPct    = 0;
    state.done       = false;

    _setProgress(0, '');
    document.getElementById('install-heading').textContent = 'Installing…';
    document.getElementById('install-sub').textContent     = 'Preparing files, please wait.';
    document.getElementById('progress-file').textContent   = '';

    showScreen('installing');
    eel.start_install(path)();
}

// ── Progress helper ──────────────────────────────────────────
function _setProgress(pct, filename) {
    const fill = document.getElementById('progress-fill');
    const pctL = document.getElementById('progress-pct');
    const file = document.getElementById('progress-file');

    if (fill) fill.style.width   = (pct * 100).toFixed(1) + '%';
    if (pctL) pctL.textContent   = Math.round(pct * 100) + '%';
    if (file) file.textContent   = filename ? _truncatePath(filename, 60) : '';
}

function _truncatePath(p, max) {
    if (p.length <= max) return p;
    return '…' + p.slice(-(max - 1));
}

function _eta(pct) {
    if (pct <= 0 || pct >= 1) return '';
    const elapsed = (Date.now() - state.startedAt) / 1000;
    const total   = elapsed / pct;
    const left    = Math.max(0, Math.round(total - elapsed));
    if (left < 5)  return 'Almost done…';
    if (left < 60) return `About ${left}s remaining`;
    return `About ${Math.ceil(left / 60)}m remaining`;
}

// ── Eel callbacks ────────────────────────────────────────────

// rAF-batched progress  — prevents layout thrashing on rapid calls
eel.expose(update_progress);
function update_progress(pct, filename) {
    state.pendingProg = { pct, filename };
    if (state.rafPending) return;
    state.rafPending = true;

    requestAnimationFrame(() => {
        state.rafPending = false;
        if (!state.pendingProg) return;

        const { pct: p, filename: f } = state.pendingProg;
        state.pendingProg = null;
        state.lastPct     = p;

        _setProgress(p, f);

        // Dynamic sub-label with ETA
        const sub = document.getElementById('install-sub');
        if (sub) {
            if (p < 0.05) {
                sub.textContent = 'Preparing installation…';
            } else if (p < 0.95) {
                sub.textContent = _eta(p) || 'Copying application files…';
            } else {
                sub.textContent = 'Finalizing installation…';
            }
        }
    });
}

eel.expose(install_complete);
function install_complete(target_path) {
    if (state.done) return;
    state.done = true;

    // Snap progress bar to 100 %
    _setProgress(1, '');

    // Short delay for the bar to visually snap to 100 % before switching
    setTimeout(() => {
        const pathEl = document.getElementById('done-path');
        if (pathEl) pathEl.textContent = 'Installed to: ' + target_path;
        showScreen('done');
    }, 400);
}

eel.expose(install_error);
function install_error(msg) {
    const errEl = document.getElementById('error-msg');
    if (errEl) errEl.textContent = msg || 'An unknown error occurred.';

    // Re-enable the Install button so the user can retry
    const btn = document.getElementById('btn-install-now');
    if (btn) {
        btn.disabled   = false;
        btn.innerHTML  = 'Install Now &nbsp;<i class="ri-arrow-right-line"></i>';
    }

    showScreen('error');
}

// ── Inject shake keyframe (avoids editing CSS at runtime) ────
(function injectShakeKeyframe() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes shake {
            0%,100%{transform:translateX(0)}
            20%    {transform:translateX(-6px)}
            40%    {transform:translateX(6px)}
            60%    {transform:translateX(-4px)}
            80%    {transform:translateX(4px)}
        }`;
    document.head.appendChild(style);
})();
