/* MediVault – report search/filter (talks to /reports/search), compare page, share page, share tabs */
(function () {
  'use strict';
  const { $, $$, csrf, icon, reduceMotion } = window.MV;
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const fmtDate = (d) => { const [y, m, dd] = d.split('-').map(Number); return new Date(y, m - 1, dd).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }); };
  const fmtSize = (n) => n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(2) + ' MB';

  /* ================= report list ================= */
  const list = $('#reportList');
  if (list) {
    const grid = $('#reportGrid'), count = $('#resultCount'), url = list.dataset.searchUrl;
    const importantPage = list.dataset.importantOnly === '1';
    const el = { q: $('#q'), category: $('#category'), hospital: $('#hospital'), doctor: $('#doctor'), from: $('#dateFrom'), to: $('#dateTo'), sort: $('#sort'), imp: $('#importantOnly') };
    let timer = null, seq = 0, optionsLoaded = false;
    const qp = new URLSearchParams(location.search); if (qp.get('q')) el.q.value = qp.get('q');

    const filtersActive = () => el.q.value.trim() || el.category.value || el.hospital.value || el.doctor.value || el.from.value || el.to.value || (el.imp && el.imp.checked);

    function fillSelect(select, values) {
      const keep = select.value; const first = select.options[0];
      select.innerHTML = ''; select.appendChild(first);
      values.forEach((v) => { const o = document.createElement('option'); o.value = v; o.textContent = v; select.appendChild(o); });
      select.value = keep;
    }
    function card(r, i) {
      const place = r.hospital || r.laboratory || '—';
      return '<article class="report-card enter" style="animation-delay:' + Math.min(i * 35, 350) + 'ms" data-id="' + r.id + '">' +
        '<div class="rc-top"><span class="cat-icon">' + icon(r.category_icon) + '</span>' +
        '<div class="grow"><a class="rc-title" href="' + esc(r.urls.view) + '">' + esc(r.title) + '</a>' +
        '<div class="rc-badges"><span class="chip">' + esc(r.category) + '</span>' + (r.important ? '<span class="badge badge-star" title="Important">' + icon('star') + ' Important</span>' : '') + '</div></div>' +
        '<button class="star-btn ' + (r.important ? 'on' : '') + '" data-url="' + esc(r.urls.important) + '" aria-pressed="' + r.important + '" aria-label="Toggle important" title="Mark as important">' + icon('star') + '</button></div>' +
        '<div class="rc-meta"><span>' + icon('building') + esc(place) + '</span><span>' + icon('user') + esc(r.doctor || '—') + '</span><span>' + icon('calendar') + fmtDate(r.date) + ' · ' + esc(r.file_type.toUpperCase()) + ' · ' + fmtSize(r.file_size) + '</span></div>' +
        '<div class="rc-actions"><button class="btn btn-outline btn-sm js-preview" data-preview-url="' + esc(r.urls.preview) + '" data-download-url="' + esc(r.urls.download) + '" data-type="' + esc(r.file_type) + '" data-title="' + esc(r.title) + '">' + icon('eye') + ' View</button>' +
        '<a class="btn btn-outline btn-sm" href="' + esc(r.urls.download) + '" title="Download">' + icon('download') + '</a>' +
        '<a class="btn btn-outline btn-sm" href="' + esc(r.urls.share) + '" title="Share">' + icon('share') + '</a></div></article>';
    }
    function emptyState(none) {
      if (none) {
        const t = importantPage ? 'No important reports' : 'No Medical Reports Yet';
        const d = importantPage ? 'Tap the star on any report to keep it here for quick access.' : 'Upload your first report to start building your medical history.';
        return '<div class="empty-state empty-wide"><div class="empty-illustration">' + icon(importantPage ? 'star' : 'file') + '</div><h3>' + t + '</h3><p>' + d + '</p><a class="btn btn-primary" href="' + esc(list.dataset.uploadUrl) + '">Upload report</a></div>';
      }
      return '<div class="empty-state empty-wide"><div class="empty-illustration">' + icon('search-x') + '</div><h3>No reports found</h3><p>No report matches your search or filters. Try something different.</p><button class="btn btn-outline" data-clear>Clear filters</button></div>';
    }
    function params() {
      const p = new URLSearchParams();
      if (el.q.value.trim()) p.set('q', el.q.value.trim());
      if (el.category.value) p.set('category', el.category.value); if (el.hospital.value) p.set('hospital', el.hospital.value); if (el.doctor.value) p.set('doctor', el.doctor.value);
      if (el.from.value) p.set('date_from', el.from.value); if (el.to.value) p.set('date_to', el.to.value);
      if (importantPage || (el.imp && el.imp.checked)) p.set('important', '1');
      p.set('sort', el.sort.value); return p;
    }
    async function load() {
      const my = ++seq;
      try {
        const res = await fetch(url + '?' + params().toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest', 'Accept': 'application/json' } });
        const data = await res.json(); if (my !== seq) return;
        if (!res.ok || !data.ok) throw new Error(data.message || 'Unable to load reports.');
        if (!optionsLoaded || !filtersActive()) { fillSelect(el.hospital, data.hospitals); fillSelect(el.doctor, data.doctors); optionsLoaded = true; }
        grid.innerHTML = data.reports.length ? data.reports.map(card).join('') : emptyState(!filtersActive());
        count.textContent = data.count + (data.count === 1 ? ' report' : ' reports') + (filtersActive() ? ' found' : '');
      } catch (err) {
        grid.innerHTML = '<div class="empty-state empty-wide"><div class="empty-illustration danger">' + icon('alert') + '</div><h3>Unable to load reports</h3><p>' + esc(err.message) + '</p><button class="btn btn-outline" data-clear>Try again</button></div>';
        count.textContent = '';
      }
    }
    const debounced = () => { clearTimeout(timer); timer = setTimeout(load, 250); };
    el.q.addEventListener('input', debounced);
    [el.category, el.hospital, el.doctor, el.from, el.to, el.sort, el.imp].forEach((x) => x && x.addEventListener('change', load));
    function clearAll() { [el.q, el.category, el.hospital, el.doctor, el.from, el.to].forEach((x) => x.value = ''); if (el.imp) el.imp.checked = false; el.sort.value = 'newest'; load(); }
    $('#clearFilters').addEventListener('click', clearAll);
    list.addEventListener('click', (e) => { if (e.target.closest('[data-clear]')) clearAll(); });
    // On the "Important" page an un-starred card leaves the list
    list.addEventListener('star:toggled', (e) => {
      const c = e.target.closest('.report-card'); if (!c) return;
      if (importantPage && !e.detail.important) { c.classList.add('leaving'); setTimeout(() => load(), reduceMotion ? 0 : 250); return; }
      const badges = $('.rc-badges', c), old = $('.badge-star', c);   // keep the badge in sync
      if (e.detail.important && !old) badges.insertAdjacentHTML('beforeend', '<span class="badge badge-star" title="Important">' + icon('star') + ' Important</span>');
      if (!e.detail.important && old) old.remove();
    });
    load();
  }

  /* ================= compare page ================= */
  const cat = $('#cmpCategory'), a = $('#cmpA'), b = $('#cmpB');
  if (cat && a && b) {
    function filterOptions() {
      [a, b].forEach((sel) => {
        Array.from(sel.options).forEach((o) => { if (!o.value) return; const ok = !cat.value || o.dataset.category === cat.value; o.hidden = !ok; o.disabled = !ok; });
        const cur = sel.selectedOptions[0]; if (cur && cur.value && cur.disabled) sel.value = '';
      });
    }
    cat.addEventListener('change', filterOptions);
    a.addEventListener('change', () => { const o = a.selectedOptions[0]; if (o && o.value && !cat.value) { cat.value = o.dataset.category; filterOptions(); } });
    b.addEventListener('change', () => { const o = b.selectedOptions[0]; if (o && o.value && !cat.value) { cat.value = o.dataset.category; filterOptions(); } });
    $('#compareForm').addEventListener('submit', (e) => {
      if (a.value && a.value === b.value) { e.preventDefault(); window.toast('Please choose two different reports.', 'error'); }
    });
    filterOptions();
  }

  /* ================= share page: expiry presets ================= */
  $$('[data-add-hours]').forEach((btn) => btn.addEventListener('click', () => {
    const d = new Date(Date.now() + parseInt(btn.dataset.addHours, 10) * 3600000), p = (n) => String(n).padStart(2, '0');
    $('#expiry_date').value = d.getFullYear() + '-' + p(d.getMonth() + 1) + '-' + p(d.getDate());
    $('#expiry_time').value = p(d.getHours()) + ':' + p(d.getMinutes());
  }));

  /* ================= shared reports: status tabs ================= */
  const tabs = $('#shareTabs');
  if (tabs) tabs.addEventListener('click', (e) => {
    const t = e.target.closest('.tab'); if (!t) return;
    $$('.tab', tabs).forEach((x) => x.classList.toggle('active', x === t));
    $$('tbody tr[data-status]').forEach((r) => { r.style.display = (t.dataset.filter === 'all' || r.dataset.status === t.dataset.filter) ? '' : 'none'; });
  });
})();
