function applyVariantState(select, chosen) {
  const variantId = chosen?.dataset.variantId ?? chosen?.value ?? '';
  const price = chosen?.dataset.price ?? '';
  const inStock = chosen?.dataset.inStock === 'true';

  const priceEl = document.querySelector('[data-product-price]');
  if (priceEl && price) {
    const priceTarget = priceEl.querySelector('b') || priceEl.querySelector('span');
    if (priceTarget) {
      priceTarget.textContent = price;
    } else {
      priceEl.textContent = price;
    }
  }

  const addBtn = document.querySelector('[data-add-btn]');
  if (addBtn) {
    const hiddenInput = document.querySelector('[data-variant-input]');
    if (hiddenInput) hiddenInput.value = variantId;

    const labelEl = addBtn.querySelector('[data-add-btn-label]');
    const labelStock = addBtn.dataset.labelStock ?? 'Додати до кошика';
    const labelOrder = addBtn.dataset.labelOrder ?? 'Під замовлення';
    const labelChoose = addBtn.dataset.labelChoose ?? 'Оберіть розмір';

    if (variantId) {
      addBtn.removeAttribute('disabled');
      const text = inStock ? labelStock : labelOrder;
      if (labelEl) labelEl.textContent = text;
      else addBtn.childNodes[0].textContent = text;
    } else {
      addBtn.setAttribute('disabled', '');
      if (labelEl) labelEl.textContent = labelChoose;
      else addBtn.childNodes[0].textContent = labelChoose;
    }
  }

  const stockStatus = document.querySelector('[data-stock-status]');
  if (stockStatus) {
    const dot = stockStatus.querySelector('.stock-dot');
    const label = stockStatus.querySelector('[data-stock-label]');
    if (!variantId) {
      if (dot) {
        dot.classList.remove('in-stock', 'out-of-stock');
      }
      if (label) label.textContent = 'Оберіть розмір';
      return;
    }
    if (dot) {
      dot.classList.toggle('in-stock', inStock);
      dot.classList.toggle('out-of-stock', !inStock);
    }
    if (label) {
      const etaIn = stockStatus.dataset.etaInStock ?? 'Орієнтовно 3 робочі дні';
      const etaPre = stockStatus.dataset.etaPreorder ?? 'Орієнтовно 14 днів';
      label.textContent = inStock ? `В наявності · ${etaIn}` : `Під замовлення · ${etaPre}`;
    }
  }
}

function parseOptionLabel(text) {
  const parts = text.split(' — ');
  if (parts.length > 1) {
    return { size: parts[0].trim(), suffix: parts.slice(1).join(' — ').trim() };
  }
  return { size: text.trim(), suffix: '' };
}

function buildPicker(select) {
  if (select.dataset.pickerReady === 'true') return;
  select.dataset.pickerReady = 'true';
  select.classList.add('size-picker__native');
  select.removeAttribute('name');

  const wrapper = document.createElement('div');
  wrapper.className = 'size-picker';
  select.parentNode.insertBefore(wrapper, select);
  wrapper.appendChild(select);

  const placeholder = select.options[0]?.text?.trim() || '— Обрати розмір';

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'size-picker__trigger';
  trigger.setAttribute('aria-haspopup', 'listbox');
  trigger.setAttribute('aria-expanded', 'false');

  const valueEl = document.createElement('span');
  valueEl.className = 'size-picker__value is-placeholder';
  valueEl.textContent = placeholder;

  const chevron = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  chevron.setAttribute('class', 'size-picker__chevron');
  chevron.setAttribute('viewBox', '0 0 12 8');
  chevron.setAttribute('width', '12');
  chevron.setAttribute('height', '8');
  chevron.setAttribute('aria-hidden', 'true');
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', 'M1 1l5 5 5-5');
  path.setAttribute('stroke', 'currentColor');
  path.setAttribute('stroke-width', '1.5');
  path.setAttribute('fill', 'none');
  chevron.appendChild(path);

  trigger.appendChild(valueEl);
  trigger.appendChild(chevron);

  const list = document.createElement('ul');
  list.className = 'size-picker__list';
  list.setAttribute('role', 'listbox');
  list.setAttribute('aria-label', 'Розміри');
  list.hidden = true;

  const options = [];

  [...select.options].forEach((option, index) => {
    if (index === 0 && !option.value) return;

    const inStock = option.dataset.inStock === 'true';
    const { size, suffix } = parseOptionLabel(option.text);
    const li = document.createElement('li');
    li.className = `size-picker__option${inStock ? ' size-picker__option--stock' : ' size-picker__option--order'}`;
    li.setAttribute('role', 'option');
    li.dataset.index = String(option.index);

    const sizeSpan = document.createElement('span');
    sizeSpan.className = 'size-picker__size';
    sizeSpan.textContent = size;

    const badge = document.createElement('span');
    badge.className = 'size-picker__badge';
    badge.textContent = suffix || (inStock ? 'В наявності' : 'Під замовлення');

    li.appendChild(sizeSpan);
    li.appendChild(badge);
    list.appendChild(li);
    options.push({ li, option });
  });

  wrapper.appendChild(trigger);
  wrapper.appendChild(list);

  let focusedIndex = -1;

  function closePicker() {
    wrapper.classList.remove('is-open');
    trigger.setAttribute('aria-expanded', 'false');
    list.hidden = true;
    focusedIndex = -1;
    options.forEach(({ li }) => li.classList.remove('is-focused'));
  }

  function openPicker() {
    wrapper.classList.add('is-open');
    trigger.setAttribute('aria-expanded', 'true');
    list.hidden = false;
    const selectedIndex = options.findIndex(
      ({ option }) => option.value === select.value,
    );
    focusedIndex = selectedIndex >= 0 ? selectedIndex : 0;
    focusOption(focusedIndex);
  }

  function focusOption(index) {
    options.forEach(({ li }, i) => {
      li.classList.toggle('is-focused', i === index);
    });
    options[index]?.li.scrollIntoView({ block: 'nearest' });
  }

  function selectOption(index) {
    const entry = options[index];
    if (!entry) return;

    const { option, li } = entry;
    select.value = option.value;
    select.dispatchEvent(new Event('change', { bubbles: true }));

    const { size } = parseOptionLabel(option.text);
    valueEl.textContent = size;
    valueEl.classList.remove('is-placeholder');

    options.forEach(({ li: item }) => item.classList.remove('is-selected'));
    li.classList.add('is-selected');

    applyVariantState(select, option);
    closePicker();
    trigger.focus();
  }

  trigger.addEventListener('click', () => {
    if (wrapper.classList.contains('is-open')) {
      closePicker();
    } else {
      openPicker();
    }
  });

  options.forEach(({ li }, index) => {
    li.addEventListener('click', () => selectOption(index));
    li.addEventListener('mousemove', () => {
      focusedIndex = index;
      focusOption(index);
    });
  });

  document.addEventListener('click', (event) => {
    if (!wrapper.contains(event.target)) closePicker();
  });

  document.addEventListener('keydown', (event) => {
    if (list.hidden) return;
    if (!wrapper.contains(document.activeElement) && document.activeElement !== trigger) return;

    if (event.key === 'Escape') {
      event.preventDefault();
      closePicker();
      trigger.focus();
      return;
    }

    if (event.key === 'ArrowDown') {
      event.preventDefault();
      focusedIndex = Math.min(focusedIndex + 1, options.length - 1);
      focusOption(focusedIndex);
      return;
    }

    if (event.key === 'ArrowUp') {
      event.preventDefault();
      focusedIndex = Math.max(focusedIndex - 1, 0);
      focusOption(focusedIndex);
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      if (focusedIndex >= 0) selectOption(focusedIndex);
    }
  });

  select.addEventListener('change', () => {
    const chosen = select.options[select.selectedIndex];
    applyVariantState(select, chosen);
  });
}

export function initSizeSelect() {
  document.querySelectorAll('[data-size-select]').forEach(buildPicker);
}
