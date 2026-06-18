export function initFilterBlocks() {
  document.querySelectorAll('.filter-block').forEach((block) => {
    const head = block.querySelector('.filter-head');
    if (!head) return;
    head.addEventListener('click', () => block.classList.toggle('is-open'));
    block.classList.add('is-open');
  });
}
