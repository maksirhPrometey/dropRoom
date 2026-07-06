export function initBurgerMenu() {
  const toggle = document.getElementById('burger-toggle');
  const menu = document.getElementById('burger-menu');
  if (!toggle || !menu) return;

  function open() {
    menu.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    document.body.classList.add('modal-open');
  }

  function close() {
    menu.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('modal-open');
  }

  toggle.addEventListener('click', () => {
    if (menu.hidden) {
      open();
    } else {
      close();
    }
  });

  menu.querySelectorAll('[data-burger-close]').forEach((el) => {
    el.addEventListener('click', close);
  });

  menu.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', close);
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && !menu.hidden) close();
  });
}
