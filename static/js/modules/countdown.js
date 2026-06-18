export function initCountdown() {
  const el = document.querySelector('[data-countdown]');
  if (!el) return;

  const target = new Date(el.dataset.countdown);
  if (isNaN(target)) return;

  const dEl = el.querySelector('[data-cd-days]');
  const hEl = el.querySelector('[data-cd-hours]');
  const mEl = el.querySelector('[data-cd-mins]');
  const sEl = el.querySelector('[data-cd-secs]');

  const pad = (n) => String(n).padStart(2, '0');

  const tick = () => {
    const diff = Math.max(0, target - Date.now());
    const d = Math.floor(diff / 86400000);
    const h = Math.floor((diff % 86400000) / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    const s = Math.floor((diff % 60000) / 1000);

    if (dEl) dEl.textContent = pad(d);
    if (hEl) hEl.textContent = pad(h);
    if (mEl) mEl.textContent = pad(m);
    if (sEl) sEl.textContent = pad(s);
  };

  tick();
  setInterval(tick, 1000);
}
