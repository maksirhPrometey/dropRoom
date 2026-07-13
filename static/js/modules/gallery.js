const SWIPE_THRESHOLD = 48;

let activeGallery = null;
let lightboxShell = null;
let lastFocusedEl = null;

function collectSlides(galleryEl, mainImg) {
  const thumbs = [...galleryEl.querySelectorAll('.gallery-thumb')];
  if (thumbs.length) {
    return thumbs.map((thumb) => ({
      src: thumb.dataset.src || '',
      alt: mainImg.alt || thumb.getAttribute('aria-label') || '',
    })).filter((slide) => slide.src);
  }
  if (mainImg?.src) {
    return [{ src: mainImg.src, alt: mainImg.alt || '' }];
  }
  return [];
}

function setMainSlide(galleryEl, slides, index) {
  const mainImg = galleryEl.querySelector('.gallery-main img');
  const thumbs = [...galleryEl.querySelectorAll('.gallery-thumb')];
  const slide = slides[index];
  if (!mainImg || !slide) return;

  mainImg.src = slide.src;
  mainImg.alt = slide.alt;

  thumbs.forEach((thumb, thumbIndex) => {
    const isActive = thumbIndex === index;
    thumb.classList.toggle('active', isActive);
    thumb.setAttribute('aria-selected', isActive ? 'true' : 'false');
  });
}

function getActiveIndex(galleryEl) {
  const thumbs = [...galleryEl.querySelectorAll('.gallery-thumb')];
  const activeIndex = thumbs.findIndex((thumb) => thumb.classList.contains('active'));
  return activeIndex >= 0 ? activeIndex : 0;
}

function updateLightbox(index) {
  if (!lightboxShell || !activeGallery) return;

  const { slides } = activeGallery;
  const slide = slides[index];
  if (!slide) return;

  activeGallery.index = index;

  const img = lightboxShell.querySelector('.gallery-lightbox__img');
  const counter = lightboxShell.querySelector('[data-gallery-counter]');
  const prevBtn = lightboxShell.querySelector('[data-gallery-prev]');
  const nextBtn = lightboxShell.querySelector('[data-gallery-next]');

  img.src = slide.src;
  img.alt = slide.alt;

  if (counter) {
    counter.textContent = slides.length > 1 ? `${index + 1} / ${slides.length}` : '';
  }

  const hideNav = slides.length <= 1;
  if (prevBtn) prevBtn.hidden = hideNav;
  if (nextBtn) nextBtn.hidden = hideNav;

  setMainSlide(activeGallery.el, slides, index);
}

function openLightbox(galleryEl, slides, index = 0) {
  if (!lightboxShell || !slides.length) return;

  activeGallery = { el: galleryEl, slides, index };
  updateLightbox(index);

  lightboxShell.hidden = false;
  lightboxShell.setAttribute('aria-hidden', 'false');
  document.body.classList.add('modal-open');
  lastFocusedEl = document.activeElement;

  const closeBtn = lightboxShell.querySelector('.gallery-lightbox__close');
  closeBtn?.focus();
}

function closeLightbox() {
  if (!lightboxShell) return;

  lightboxShell.hidden = true;
  lightboxShell.setAttribute('aria-hidden', 'true');
  document.body.classList.remove('modal-open');
  activeGallery = null;

  if (lastFocusedEl && typeof lastFocusedEl.focus === 'function') {
    lastFocusedEl.focus();
  }
  lastFocusedEl = null;
}

function stepLightbox(delta) {
  if (!activeGallery || activeGallery.slides.length <= 1) return;
  const nextIndex =
    (activeGallery.index + delta + activeGallery.slides.length) %
    activeGallery.slides.length;
  updateLightbox(nextIndex);
}

function initLightboxShell(lightbox) {
  if (lightboxShell) return;
  lightboxShell = lightbox;

  lightbox.querySelectorAll('[data-gallery-close]').forEach((el) => {
    el.addEventListener('click', closeLightbox);
  });

  lightbox.querySelector('[data-gallery-prev]')?.addEventListener('click', () => {
    stepLightbox(-1);
  });

  lightbox.querySelector('[data-gallery-next]')?.addEventListener('click', () => {
    stepLightbox(1);
  });

  document.addEventListener('keydown', (event) => {
    if (lightbox.hidden) return;

    if (event.key === 'Escape') {
      closeLightbox();
      return;
    }
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      stepLightbox(-1);
      return;
    }
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      stepLightbox(1);
    }
  });

  const stage = lightbox.querySelector('.gallery-lightbox__stage');
  if (!stage) return;

  let touchStartX = 0;
  let touchStartY = 0;

  stage.addEventListener('touchstart', (event) => {
    const touch = event.changedTouches[0];
    touchStartX = touch.clientX;
    touchStartY = touch.clientY;
  }, { passive: true });

  stage.addEventListener('touchend', (event) => {
    if (!activeGallery || activeGallery.slides.length <= 1) return;

    const touch = event.changedTouches[0];
    const deltaX = touch.clientX - touchStartX;
    const deltaY = touch.clientY - touchStartY;

    if (Math.abs(deltaX) < SWIPE_THRESHOLD) return;
    if (Math.abs(deltaY) > Math.abs(deltaX)) return;

    stepLightbox(deltaX < 0 ? 1 : -1);
  }, { passive: true });
}

function initProductGallery(galleryEl) {
  const mainImg = galleryEl.querySelector('.gallery-main img');
  if (!mainImg) return;

  const slides = collectSlides(galleryEl, mainImg);
  if (!slides.length) return;

  galleryEl.querySelectorAll('.gallery-thumb').forEach((thumb, index) => {
    thumb.addEventListener('click', () => {
      setMainSlide(galleryEl, slides, index);
    });
  });

  const openTrigger = galleryEl.querySelector('[data-gallery-open]');
  if (openTrigger) {
    openTrigger.addEventListener('click', () => {
      openLightbox(galleryEl, slides, getActiveIndex(galleryEl));
    });
  }
}

export function initGallery() {
  const lightbox = document.querySelector('[data-gallery-lightbox]');
  if (lightbox) initLightboxShell(lightbox);

  document.querySelectorAll('.gallery').forEach((galleryEl) => {
    initProductGallery(galleryEl);
  });
}
