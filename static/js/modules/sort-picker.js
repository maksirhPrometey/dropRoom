const CHECK_SVG =
  '<svg viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2.5 6l2.5 2.5 4.5-5"/></svg>';

function buildSortPicker(root) {
  if (root.dataset.sortPickerReady === 'true') return;

  const select = root.querySelector('[data-sort-picker-native]');
  if (!select) return;

  root.dataset.sortPickerReady = 'true';
  select.classList.add('sort-picker__native');

  const trigger = document.createElement('button');
  trigger.type = 'button';
  trigger.className = 'sort-picker__trigger';
  trigger.setAttribute('aria-haspopup', 'listbox');
  trigger.setAttribute('aria-expanded', 'false');

  const label = document.createElement('span');
  label.className = 'sort-picker__label';
  label.textContent = 'Сортувати:';

  const valueEl = document.createElement('span');
  valueEl.className = 'sort-picker__value';

  const chevron = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  chevron.setAttribute('class', 'sort-picker__chevron');
  chevron.setAttribute('viewBox', '0 0 10 10');
  chevron.setAttribute('width', '10');
  chevron.setAttribute('height', '10');
  chevron.setAttribute('aria-hidden', 'true');
  const chevronPath = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  chevronPath.setAttribute('d', 'M2 4l3 3 3-3');
  chevronPath.setAttribute('stroke', 'currentColor');
  chevronPath.setAttribute('stroke-width', '1.4');
  chevronPath.setAttribute('fill', 'none');
  chevron.appendChild(chevronPath);

  trigger.append(label, valueEl, chevron);

  const list = document.createElement('ul');
  list.className = 'sort-picker__list';
  list.setAttribute('role', 'listbox');
  list.setAttribute('aria-label', 'Сортування');
  list.hidden = true;

  const options = [];

  [...select.options].forEach((option) => {
    const li = document.createElement('li');
    li.className = 'sort-picker__option';
    li.setAttribute('role', 'option');
    li.dataset.value = option.value;

    const check = document.createElement('span');
    check.className = 'sort-picker__check';
    check.innerHTML = CHECK_SVG;

    const text = document.createElement('span');
    text.className = 'sort-picker__text';
    text.textContent = option.text;

    li.append(check, text);
    list.appendChild(li);
    options.push({ li, option });
  });

  root.append(trigger, list);

  let focusedIndex = -1;

  function syncSelected() {
    const selected = select.options[select.selectedIndex];
    valueEl.textContent = selected?.text ?? '';

    options.forEach(({ li, option }) => {
      const isSelected = option.value === select.value;
      li.classList.toggle('is-selected', isSelected);
      li.setAttribute('aria-selected', isSelected ? 'true' : 'false');
    });
  }

  function closePicker() {
    root.classList.remove('is-open');
    trigger.setAttribute('aria-expanded', 'false');
    list.hidden = true;
    focusedIndex = -1;
    options.forEach(({ li }) => li.classList.remove('is-focused'));
  }

  function openPicker() {
    root.classList.add('is-open');
    trigger.setAttribute('aria-expanded', 'true');
    list.hidden = false;

    const selectedIndex = options.findIndex(({ option }) => option.value === select.value);
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

    select.value = entry.option.value;
    syncSelected();
    closePicker();
    trigger.focus();

    const form = document.getElementById(select.getAttribute('form') || 'filter-form');
    form?.requestSubmit();
  }

  trigger.addEventListener('click', () => {
    if (root.classList.contains('is-open')) {
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
    if (!root.contains(event.target)) closePicker();
  });

  document.addEventListener('keydown', (event) => {
    if (list.hidden) return;
    if (!root.contains(document.activeElement) && document.activeElement !== trigger) return;

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

  syncSelected();
}

export function initSortPicker() {
  document.querySelectorAll('[data-sort-picker]').forEach(buildSortPicker);
}
