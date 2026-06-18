export function initGallery() {
  document.addEventListener('click', (e) => {
    const thumb = e.target.closest('.gallery-thumb');
    if (!thumb) return;

    const src = thumb.dataset.src;
    if (!src) return;

    const main = thumb.closest('.gallery')?.querySelector('.gallery-main img');
    if (!main) return;

    main.src = src;
    thumb.closest('.gallery')
      ?.querySelectorAll('.gallery-thumb')
      .forEach((t) => t.classList.remove('active'));
    thumb.classList.add('active');
  });
}
