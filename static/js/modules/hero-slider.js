export function initHeroSlider() {
  const root = document.querySelector('[data-hero-slider]');
  if (!root) return;

  const slides = [...root.querySelectorAll('[data-hero-slide]')];
  if (slides.length < 2) return;

  const dots = [...root.querySelectorAll('[data-hero-dot]')];
  const prevBtn = root.querySelector('[data-hero-prev]');
  const nextBtn = root.querySelector('[data-hero-next]');

  let index = 0;
  let timer = null;
  let resumeTimer = null;
  const interval = Number(root.dataset.autoplay) || 3000;
  const manualPauseMs = 10000;
  const canHover = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

  function goTo(nextIndex) {
    index = (nextIndex + slides.length) % slides.length;

    slides.forEach((slide, n) => {
      const active = n === index;
      slide.classList.toggle('is-active', active);
      slide.setAttribute('aria-hidden', active ? 'false' : 'true');
    });

    dots.forEach((dot, n) => {
      const active = n === index;
      dot.classList.toggle('is-active', active);
      dot.setAttribute('aria-selected', active ? 'true' : 'false');
    });
  }

  function stopAutoplay() {
    if (timer !== null) {
      window.clearTimeout(timer);
      timer = null;
    }
  }

  function scheduleAutoplay() {
    stopAutoplay();
    timer = window.setTimeout(() => {
      goTo(index + 1);
      scheduleAutoplay();
    }, interval);
  }

  function pauseAfterManual() {
    stopAutoplay();
    if (resumeTimer !== null) {
      window.clearTimeout(resumeTimer);
    }
    resumeTimer = window.setTimeout(scheduleAutoplay, manualPauseMs);
  }

  function prev() {
    goTo(index - 1);
    pauseAfterManual();
  }

  function next() {
    goTo(index + 1);
    pauseAfterManual();
  }

  prevBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    prev();
  });

  nextBtn?.addEventListener('click', (event) => {
    event.preventDefault();
    event.stopPropagation();
    next();
  });

  dots.forEach((dot, n) => {
    dot.addEventListener('click', (event) => {
      event.preventDefault();
      event.stopPropagation();
      goTo(n);
      pauseAfterManual();
    });
  });

  if (canHover) {
    root.addEventListener('mouseenter', stopAutoplay);
    root.addEventListener('mouseleave', scheduleAutoplay);
  }

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      stopAutoplay();
      return;
    }
    scheduleAutoplay();
  });

  window.addEventListener('pageshow', (event) => {
    if (event.persisted) scheduleAutoplay();
  });

  goTo(0);
  scheduleAutoplay();
}
