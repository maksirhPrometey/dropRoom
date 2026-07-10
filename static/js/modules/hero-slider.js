export function initHeroSlider() {
  const root = document.querySelector('[data-hero-slider]');
  if (!root) return;

  const slides = [...root.querySelectorAll('[data-hero-slide]')];
  const dots = [...root.querySelectorAll('[data-hero-dot]')];
  if (slides.length < 2) return;

  let index = 0;
  let timer = null;
  const interval = Number(root.dataset.autoplay) || 5500;
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

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

  function next() {
    goTo(index + 1);
  }

  function stop() {
    if (timer !== null) {
      window.clearInterval(timer);
      timer = null;
    }
  }

  function start() {
    if (reducedMotion || root.dataset.paused === 'true') return;
    stop();
    timer = window.setInterval(next, interval);
  }

  dots.forEach((dot, n) => {
    dot.addEventListener('click', () => {
      goTo(n);
      start();
    });
  });

  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', start);
  root.addEventListener('focusin', stop);
  root.addEventListener('focusout', start);
  root.addEventListener('touchstart', stop, { passive: true });
  root.addEventListener('touchend', () => {
    window.setTimeout(start, 3500);
  }, { passive: true });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) stop();
    else start();
  });

  goTo(0);
  start();
}
