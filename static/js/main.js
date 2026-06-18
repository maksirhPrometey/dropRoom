import { initReveal } from './modules/reveal.js';
import { initCountdown } from './modules/countdown.js';
import { initFAQ } from './modules/faq.js';
import { initAccordions } from './modules/accordions.js';
import { initGallery } from './modules/gallery.js';

document.addEventListener('DOMContentLoaded', () => {
  initReveal();
  initCountdown();
  initFAQ();
  initAccordions();
  initGallery();
});
