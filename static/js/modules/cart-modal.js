export function initCartModal() {
  const modal = document.getElementById('cart-modal');
  if (!modal) return;

  const productEl = document.getElementById('cart-modal-product');

  function open(productName) {
    if (productEl) {
      productEl.textContent = productName || '';
    }
    modal.hidden = false;
    document.body.classList.add('modal-open');
  }

  function close() {
    modal.hidden = true;
    document.body.classList.remove('modal-open');
  }

  modal.querySelectorAll('[data-modal-close]').forEach((el) => {
    el.addEventListener('click', close);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !modal.hidden) close();
  });

  document.body.addEventListener('cartAdded', (event) => {
    const detail = event.detail || {};
    open(detail.productName);
  });
}
