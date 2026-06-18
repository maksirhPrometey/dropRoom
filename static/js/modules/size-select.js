export function initSizeSelect() {
  const select = document.querySelector('[data-size-select]');
  if (!select) return;

  select.addEventListener('change', () => {
    const chosen = select.options[select.selectedIndex];
    const variantId = chosen.dataset.variantId ?? '';
    const price = chosen.dataset.price ?? '';
    const inStock = chosen.dataset.inStock === 'true';

    const priceEl = document.querySelector('[data-product-price]');
    if (priceEl && price) priceEl.textContent = price;

    const addBtn = document.querySelector('[data-add-btn]');
    if (addBtn) {
      const hiddenInput = document.querySelector('[data-variant-input]');
      if (hiddenInput) hiddenInput.value = variantId;

      if (inStock) {
        addBtn.removeAttribute('disabled');
        addBtn.textContent = addBtn.dataset.labelStock ?? 'Додати до кошика';
      } else {
        addBtn.setAttribute('disabled', '');
        addBtn.textContent = addBtn.dataset.labelOrder ?? 'Під замовлення';
      }
    }

    const stockStatus = document.querySelector('[data-stock-status]');
    if (stockStatus) {
      const dot = stockStatus.querySelector('.stock-dot');
      const label = stockStatus.querySelector('[data-stock-label]');
      if (dot) {
        dot.classList.toggle('in-stock', inStock);
        dot.classList.toggle('out-of-stock', !inStock);
      }
      if (label) {
        label.textContent = inStock ? 'В наявності' : 'Під замовлення';
      }
    }
  });
}
