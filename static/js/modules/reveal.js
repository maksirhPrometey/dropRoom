export function initReveal() {
  const els = document.querySelectorAll('.reveal');
  if (!els.length) return;

  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach(({ isIntersecting, target }) => {
        if (!isIntersecting) return;
        target.classList.add('in');
        obs.unobserve(target);
      });
    },
    { threshold: 0.12 }
  );

  els.forEach((el) => obs.observe(el));
}
