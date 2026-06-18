export function initQtyControls() {
  document.addEventListener('click', (e) => {
    const btn = e.target.closest('[data-qty-action]');
    if (!btn) return;

    const action = btn.dataset.qtyAction;
    const control = btn.closest('.qty-control');
    if (!control) return;

    const valEl = control.querySelector('.qty-val');
    const itemId = control.dataset.itemId;
    let qty = parseInt(valEl?.textContent ?? '1', 10);

    if (action === 'inc') qty += 1;
    else if (action === 'dec') qty = Math.max(0, qty - 1);

    if (valEl) valEl.textContent = qty;

    const form = control.closest('form') ?? document.createElement('form');
    const formEl = control.dataset.updateForm
      ? document.querySelector(`#${control.dataset.updateForm}`)
      : null;

    if (formEl) {
      const input = formEl.querySelector('[name="quantity"]');
      if (input) input.value = qty;
    }
  });
}
