/* MediVault – shared behaviour: sidebar, dropdowns, toasts, modals, preview, print, star, forms */
(function () {
  'use strict';
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const isMobile = () => window.matchMedia('(max-width: 900px)').matches;
  const csrf = () => (document.querySelector('meta[name="csrf-token"]') || {}).content || '';
  const icon = (n) => '<svg class="icon" aria-hidden="true"><use href="#i-' + n + '"/></svg>';
  window.MV = { $, $$, csrf, icon, reduceMotion };

  /* ---------- toasts ---------- */
  window.toast = function (message, type) {
    type = type || 'info';
    const box = $('#toasts');
    if (!box) return;
    const el = document.createElement('div');
    el.className = 'toast ' + type;
    el.setAttribute('role', 'status');
    const ic = type === 'success' ? 'check' : type === 'error' ? 'alert' : 'bell';
    el.innerHTML = icon(ic) + '<span></span><button class="toast-close" aria-label="Dismiss">' + icon('x') + '</button>';
    el.querySelector('span').textContent = message;
    box.appendChild(el);
    const remove = () => { el.classList.add('leaving'); setTimeout(() => el.remove(), 300); };
    el.querySelector('.toast-close').addEventListener('click', remove);
    setTimeout(remove, 4500);
  };
  $$('.flash-data').forEach((f) => window.toast(f.dataset.message, f.dataset.category === 'error' ? 'error' : f.dataset.category));

  /* ---------- modal helpers ---------- */
  window.openModal = function (el) { el.classList.add('open'); el.setAttribute('aria-hidden', 'false'); document.body.style.overflow = 'hidden'; };
  window.closeModal = function (el) {
    el.classList.remove('open'); el.setAttribute('aria-hidden', 'true');
    if (!$('.modal-backdrop.open')) document.body.style.overflow = '';
  };
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') { $$('.modal-backdrop.open').forEach((m) => m.dispatchEvent(new Event('mv:close'))); $$('.dropdown.open').forEach((d) => d.classList.remove('open')); }
  });

  /* ---------- sidebar ---------- */
  const body = document.body;
  const toggle = $('#sidebarToggle');
  if (toggle) {
    try { if (!isMobile() && localStorage.getItem('mv-collapsed') === '1') body.classList.add('sidebar-collapsed'); } catch (e) {}
    toggle.addEventListener('click', () => {
      if (isMobile()) { body.classList.toggle('sidebar-open'); }
      else {
        body.classList.toggle('sidebar-collapsed');
        try { localStorage.setItem('mv-collapsed', body.classList.contains('sidebar-collapsed') ? '1' : '0'); } catch (e) {}
        setTimeout(moveIndicator, 320);
      }
    });
    const ov = $('#sidebarOverlay');
    if (ov) ov.addEventListener('click', () => body.classList.remove('sidebar-open'));
  }
  function moveIndicator() {
    const ind = $('#navIndicator'); const active = $('.nav-link.active');
    if (!ind || !active) { if (ind) ind.style.opacity = 0; return; }
    ind.style.opacity = 1; ind.style.height = active.offsetHeight + 'px';
    ind.style.transform = 'translateY(' + active.offsetTop + 'px)';
  }
  moveIndicator(); window.addEventListener('resize', moveIndicator); window.addEventListener('load', moveIndicator);

  /* ---------- dropdowns ---------- */
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-dropdown]');
    $$('.dropdown.open').forEach((d) => { if (!btn || d !== btn.closest('.dropdown')) d.classList.remove('open'); });
    if (btn) btn.closest('.dropdown').classList.toggle('open');
  });

  /* ---------- password show/hide, demo login, register helpers ---------- */
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-toggle-password]');
    if (t) {
      const input = document.getElementById(t.dataset.togglePassword); const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      t.innerHTML = icon(show ? 'eye-off' : 'eye'); t.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    }
    const d = e.target.closest('.demo-fill');
    if (d) { $('#email').value = d.dataset.email; $('#password').value = d.dataset.pass; $('#email').dispatchEvent(new Event('input')); $('#password').focus(); }
  });
  const regForm = $('#registerForm');
  if (regForm) {
    const spec = $('#specWrap');
    const syncRole = () => { spec.hidden = regForm.role.value !== 'doctor'; };
    $$('input[name=role]', regForm).forEach((r) => r.addEventListener('change', syncRole)); syncRole();
    const pw = $('#password'), meter = $('#pwMeter span');
    pw.addEventListener('input', () => {
      const v = pw.value; let s = 0;
      if (v.length >= 8) s++; if (/[A-Z]/.test(v) && /[a-z]/.test(v)) s++; if (/\d/.test(v)) s++; if (/[^A-Za-z0-9]/.test(v)) s++;
      meter.style.width = (s * 25) + '%'; meter.style.background = ['#ef4444', '#ef4444', '#f59e0b', '#10b981', '#059669'][s];
    });
    regForm.addEventListener('submit', (e) => {
      const msgs = [];
      if (pw.value !== $('#confirm_password').value) msgs.push('Passwords do not match.');
      if (pw.value.length < 8) msgs.push('Password must be at least 8 characters.');
      if (!$('#name').value.trim() || !$('#email').value.trim()) msgs.push('Please fill in all required fields.');
      if (msgs.length) { e.preventDefault(); window.toast(msgs[0], 'error'); regForm.closest('.auth-card').classList.remove('shake'); void regForm.offsetWidth; regForm.classList.add('shake'); }
    });
  }
  const loginForm = $('#loginForm');
  if (loginForm) loginForm.addEventListener('submit', (e) => {
    if (!$('#email').value.trim() || !$('#password').value) { e.preventDefault(); window.toast('Please enter your email and password.', 'error'); loginForm.classList.remove('shake'); void loginForm.offsetWidth; loginForm.classList.add('shake'); }
  });

  /* ---------- landing nav ---------- */
  const ln = $('#landNav');
  if (ln) {
    window.addEventListener('scroll', () => ln.classList.toggle('scrolled', window.scrollY > 10), { passive: true });
    const b = $('#landBurger'); if (b) b.addEventListener('click', () => ln.classList.toggle('open'));
    $$('#landLinks a').forEach((a) => a.addEventListener('click', () => ln.classList.remove('open')));
  }

  /* ---------- confirm dialogs (<form data-confirm="...">) ---------- */
  const cm = $('#confirmModal'); let pendingForm = null;
  if (cm) {
    document.addEventListener('submit', (e) => {
      const f = e.target; if (!f.dataset || !f.dataset.confirm || f.dataset.confirmed) return;
      e.preventDefault(); pendingForm = f; $('#confirmText').textContent = f.dataset.confirm; openModal(cm);
    });
    $('[data-confirm-ok]', cm).addEventListener('click', () => { if (pendingForm) { pendingForm.dataset.confirmed = '1'; closeModal(cm); pendingForm.submit(); } });
    const cancel = () => { closeModal(cm); pendingForm = null; };
    $('[data-confirm-cancel]', cm).addEventListener('click', cancel); cm.addEventListener('mv:close', cancel);
    cm.addEventListener('click', (e) => { if (e.target === cm) cancel(); });
  }

  /* ---------- print helper ---------- */
  window.printUrl = function (url) {
    const f = document.createElement('iframe');
    f.style.cssText = 'position:fixed;right:0;bottom:0;width:0;height:0;border:0;';
    f.src = url;
    f.onload = () => { try { f.contentWindow.focus(); f.contentWindow.print(); } catch (e) { window.open(url, '_blank'); } setTimeout(() => f.remove(), 60000); };
    document.body.appendChild(f);
  };
  document.addEventListener('click', (e) => { const p = e.target.closest('.js-print'); if (p) window.printUrl(p.dataset.printUrl); });

  /* ---------- preview modal (zoom, fullscreen, download, print) ---------- */
  const pm = $('#previewModal');
  if (pm) {
    const pbody = $('#previewBody'), zl = $('#zoomLabel'), dlink = $('#pvDownload'), dialog = $('.preview-modal', pm);
    const st = { url: '', type: '', zoom: 100 };
    function render(first) {
      pbody.innerHTML = ''; zl.textContent = st.zoom + '%'; pbody.classList.toggle('zoomed', st.zoom > 100);
      if (st.type === 'pdf') {
        const fr = document.createElement('iframe'); fr.title = 'Report preview';
        fr.src = st.url + (first ? '?log=1' : '') + '#zoom=' + st.zoom; pbody.appendChild(fr);
      } else {
        const img = document.createElement('img'); img.alt = 'Report preview';
        img.src = st.url + (first ? '?log=1' : '');
        if (st.zoom !== 100) { img.classList.add('zoomable'); img.style.width = st.zoom + '%'; }
        pbody.appendChild(img);
      }
    }
    function open(btn) {
      st.url = btn.dataset.previewUrl; st.type = btn.dataset.type; st.zoom = 100;
      $('#previewTitle').textContent = btn.dataset.title || 'Preview'; dlink.href = btn.dataset.downloadUrl;
      render(true); openModal(pm);
    }
    function close() { if (document.fullscreenElement) document.exitFullscreen(); pbody.innerHTML = ''; closeModal(pm); }
    document.addEventListener('click', (e) => { const b = e.target.closest('.js-preview'); if (b) { e.preventDefault(); open(b); } });
    pm.addEventListener('click', (e) => {
      if (e.target === pm) return close();
      const a = e.target.closest('[data-pv]'); if (!a) return;
      const act = a.dataset.pv;
      if (act === 'close') close();
      else if (act === 'zoom-in') { st.zoom = Math.min(300, st.zoom + 25); render(false); }
      else if (act === 'zoom-out') { st.zoom = Math.max(50, st.zoom - 25); render(false); }
      else if (act === 'print') window.printUrl(st.url);
      else if (act === 'fullscreen') { if (document.fullscreenElement) document.exitFullscreen(); else if (dialog.requestFullscreen) dialog.requestFullscreen(); }
    });
    pm.addEventListener('mv:close', close);
  }

  /* ---------- animated star (important) ---------- */
  document.addEventListener('click', async (e) => {
    const b = e.target.closest('.star-btn'); if (!b || !b.dataset.url) return;
    e.preventDefault(); if (b.dataset.busy) return; b.dataset.busy = '1';
    try {
      const r = await fetch(b.dataset.url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest', 'X-CSRF-Token': csrf() } });
      const data = await r.json();
      if (!r.ok || !data.ok) throw new Error(data.message || 'Unable to update report.');
      b.classList.toggle('on', data.important); b.setAttribute('aria-pressed', data.important);
      b.classList.remove('pop'); void b.offsetWidth; b.classList.add('pop');
      window.toast(data.message, 'success');
      b.dispatchEvent(new CustomEvent('star:toggled', { bubbles: true, detail: { important: data.important } }));
    } catch (err) { window.toast(err.message, 'error'); }
    finally { delete b.dataset.busy; }
  });

  /* ---------- soft page transition ---------- */
  document.addEventListener('click', (e) => {
    const a = e.target.closest('a[href]');
    if (reduceMotion || !a || e.defaultPrevented || e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank' || a.hasAttribute('download')) return;
    const u = new URL(a.href, location.href);
    if (u.origin !== location.origin || u.pathname === location.pathname && u.hash || /\/(download|preview)/.test(u.pathname) || a.getAttribute('href').startsWith('javascript')) return;
    body.classList.add('leaving');
  });
  window.addEventListener('pageshow', () => body.classList.remove('leaving'));
})();
