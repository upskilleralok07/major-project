/* MediVault – dashboard charts (Chart.js from CDN, with a friendly fallback) */
(function () {
  'use strict';
  const dataEl = document.getElementById('chartData'); if (!dataEl) return;
  const data = JSON.parse(dataEl.textContent);
  const boxes = [document.getElementById('catChartBox'), document.getElementById('timeChartBox')];
  boxes.forEach((b) => b && b.classList.add('loading'));
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const palette = ['#0d9488', '#2563eb', '#f59e0b', '#8b5cf6', '#ef4444', '#10b981', '#64748b'];

  function fallback(box, text) {
    box.classList.remove('loading'); box.innerHTML = '<div class="chart-fallback"><p>' + text + '</p></div>';
  }
  window.addEventListener('load', function () {
    if (typeof Chart === 'undefined') { boxes.forEach((b) => b && fallback(b, 'Charts need an internet connection (Chart.js CDN).')); return; }
    const anim = reduce ? false : { duration: 1000, easing: 'easeOutQuart' };
    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';

    if (!data.categories.length) fallback(boxes[0], 'Upload reports to see category statistics.');
    else {
      boxes[0].classList.remove('loading');
      new Chart(document.getElementById('categoryChart'), {
        type: 'doughnut',
        data: { labels: data.categories.map((c) => c.name), datasets: [{ data: data.categories.map((c) => c.count), backgroundColor: palette, borderWidth: 3, borderColor: '#fff' }] },
        options: { maintainAspectRatio: false, cutout: '62%', animation: anim, plugins: { legend: { position: 'bottom', labels: { usePointStyle: true, boxWidth: 8 } } } }
      });
    }
    if (!data.months.length) fallback(boxes[1], 'Upload reports to see your activity over time.');
    else {
      boxes[1].classList.remove('loading');
      const ctx = document.getElementById('timeChart').getContext('2d');
      const g = ctx.createLinearGradient(0, 0, 0, 260); g.addColorStop(0, 'rgba(13,148,136,.35)'); g.addColorStop(1, 'rgba(13,148,136,0)');
      new Chart(ctx, {
        type: 'line',
        data: { labels: data.months.map((m) => m.label), datasets: [{ label: 'Reports', data: data.months.map((m) => m.count), borderColor: '#0d9488', backgroundColor: g, fill: true, tension: .4, pointRadius: 4, pointBackgroundColor: '#fff', pointBorderWidth: 2 }] },
        options: { maintainAspectRatio: false, animation: anim, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: '#eef2f7' } }, x: { grid: { display: false } } } }
      });
    }
  });
})();
