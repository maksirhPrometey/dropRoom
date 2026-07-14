import { initSizeSelect } from './modules/size-select.js';
import { initColorSelect } from './modules/color-select.js';
import { initFilterBlocks } from './modules/filter-blocks.js';
import { initBrandFilterMore } from './modules/brand-filter-more.js';
import { initSortPicker } from './modules/sort-picker.js';

document.addEventListener('DOMContentLoaded', () => {
  // Колір перебудовує size-picker; initSizeSelect безпечний, якщо picker вже готовий.
  initColorSelect();
  initSizeSelect();
  initFilterBlocks();
  initBrandFilterMore();
  initSortPicker();
});
