import { applyVariantState, destroySizePicker, refreshSizePicker } from './size-select.js';

function cloneOptions(select) {
  return [...select.options].map((option) => option.cloneNode(true));
}

export function initColorSelect() {
  const block = document.querySelector('[data-variant-block][data-has-colors="true"]');
  if (!block) return false;

  const colorRoot = block.querySelector('[data-color-select]');
  const sizeSelect = block.querySelector('[data-size-select]');
  const colorLabel = block.querySelector('[data-color-label]');
  if (!colorRoot || !sizeSelect) return false;

  const buttons = [...colorRoot.querySelectorAll('[data-color-id]')];
  if (!buttons.length) return false;

  // Знімаємо picker ДО клонування опцій, щоб не чіпати зібраний UI.
  destroySizePicker(sizeSelect);
  const allOptions = cloneOptions(sizeSelect);

  buttons.forEach((button) => {
    const hex = button.dataset.colorHex || '#cccccc';
    button.style.setProperty('--swatch', hex);
  });

  function applyColor(colorId) {
    buttons.forEach((button) => {
      const active = button.dataset.colorId === colorId;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      if (active && colorLabel) {
        colorLabel.textContent = button.dataset.colorName || '—';
      }
    });

    destroySizePicker(sizeSelect);

    const placeholder = allOptions.find((option) => !option.value) || allOptions[0];
    const matching = allOptions.filter(
      (option) => option.value && String(option.dataset.colorId) === String(colorId),
    );

    sizeSelect.innerHTML = '';
    if (placeholder) {
      sizeSelect.appendChild(placeholder.cloneNode(true));
    }
    matching.forEach((option) => {
      sizeSelect.appendChild(option.cloneNode(true));
    });

    sizeSelect.value = '';
    refreshSizePicker(sizeSelect);
    applyVariantState(sizeSelect, sizeSelect.options[sizeSelect.selectedIndex]);
  }

  buttons.forEach((button) => {
    button.addEventListener('click', () => {
      applyColor(button.dataset.colorId);
    });
  });

  applyColor(buttons[0].dataset.colorId);
  return true;
}
