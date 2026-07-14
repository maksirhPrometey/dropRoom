import { initSizeSelect } from './modules/size-select.js';
import { initColorSelect } from './modules/color-select.js';
import { initFilterBlocks } from './modules/filter-blocks.js';
import { initBrandFilterMore } from './modules/brand-filter-more.js';
import { initSortPicker } from './modules/sort-picker.js';

document.addEventListener('DOMContentLoaded', () => {
  const usedColorFlow = initColorSelect();
  if (!usedColorFlow) {
    initSizeSelect();
  }
  initFilterBlocks();
  initBrandFilterMore();
  initSortPicker();
});
