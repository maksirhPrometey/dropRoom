import { initSizeSelect } from './modules/size-select.js';
import { initColorSelect } from './modules/color-select.js';
import { initFilterBlocks } from './modules/filter-blocks.js';
import { initBrandFilterMore } from './modules/brand-filter-more.js';
import { initSortPicker } from './modules/sort-picker.js';

document.addEventListener('DOMContentLoaded', () => {
  // Спочатку колір (перебудовує size-picker), інакше звичайний size-select.
  const hasColors = Boolean(
    document.querySelector('[data-variant-block][data-has-colors="true"]'),
  );
  if (hasColors) {
    initColorSelect();
  } else {
    initSizeSelect();
  }
  initFilterBlocks();
  initBrandFilterMore();
  initSortPicker();
});
