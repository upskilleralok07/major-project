/* MediVault – scroll reveal + count-up numbers */
(function () {
  'use strict';
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const items = Array.from(document.querySelectorAll('.reveal'));
  if (items.length) {
    if (reduce || !('IntersectionObserver' in window)) items.forEach((i) => i.classList.add('visible'));
    else {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('visible'); io.unobserve(en.target); } });
      }, { threshold: 0.12, rootMargin: '0px 0px -40px 0px' });
      items.forEach((el, i) => { el.style.transitionDelay = Math.min((i % 6) * 60, 300) + 'ms'; io.observe(el); });
    }
  }

  document.querySelectorAll('[data-count]').forEach((el) => {
    const target = parseInt(el.dataset.count, 10) || 0;
    if (reduce || target === 0) { el.textContent = target; return; }
    const dur = 900, start = performance.now();
    (function tick(now) {
      const p = Math.min((now - start) / dur, 1), eased = 1 - Math.pow(1 - p, 3);
      el.textContent = Math.round(target * eased);
      if (p < 1) requestAnimationFrame(tick);
    })(start);
  });
})();
