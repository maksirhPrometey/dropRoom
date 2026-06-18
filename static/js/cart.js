import { initQtyControls } from './modules/qty-controls.js';

document.addEventListener('DOMContentLoaded', () => {
  initQtyControls();
});

document.addEventListener('htmx:afterSwap', (e) => {
  if (e.detail?.target?.id === 'cart-count') {
    const countEl = document.querySelector('#cart-count .n');
    if (countEl) {
      countEl.classList.add('is-updated');
      setTimeout(() => countEl.classList.remove('is-updated'), 600);
    }
  }
});
