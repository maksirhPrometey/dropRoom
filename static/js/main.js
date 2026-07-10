import { initReveal } from './modules/reveal.js';
import { initCountdown } from './modules/countdown.js';
import { initFAQ } from './modules/faq.js';
import { initAccordions } from './modules/accordions.js';
import { initGallery } from './modules/gallery.js';
import { initBurgerMenu } from './modules/burger-menu.js';
import { initCartModal } from './modules/cart-modal.js';

import { initHeroSlider } from './modules/hero-slider.js';

document.addEventListener('DOMContentLoaded', () => {
  initReveal();
  initCountdown();
  initFAQ();
  initAccordions();
  initGallery();
  initBurgerMenu();
  initCartModal();
  initHeroSlider();
});
