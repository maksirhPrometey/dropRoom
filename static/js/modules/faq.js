export function initFAQ() {
  document.addEventListener('click', (e) => {
    const q = e.target.closest('.q');
    if (!q) return;
    const isOpen = q.classList.contains('open');
    document.querySelectorAll('.q.open').forEach((el) => el.classList.remove('open'));
    if (!isOpen) q.classList.add('open');
  });
}
