export function initBrandFilterMore() {
  const list = document.querySelector('[data-brand-filter-list]');
  if (!list) return;

  const toggle = list.querySelector('[data-brand-filter-toggle]');
  const extras = list.querySelectorAll('.is-brand-extra');

  if (extras.length === 0) {
    toggle?.remove();
    return;
  }

  const hasCheckedExtra = [...extras].some((el) => el.querySelector('input:checked'));
  if (hasCheckedExtra) {
    list.classList.add('is-expanded');
    toggle?.setAttribute('aria-expanded', 'true');
  }

  toggle?.addEventListener('click', () => {
    const expanded = list.classList.toggle('is-expanded');
    toggle.setAttribute('aria-expanded', String(expanded));
  });
}
