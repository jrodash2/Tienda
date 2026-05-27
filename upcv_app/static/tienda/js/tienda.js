document.addEventListener('DOMContentLoaded', function () {
  const menuBtn = document.querySelector('[data-store-menu-toggle]');
  const chips = document.querySelector('#storeNavChips');
  if (menuBtn && chips) {
    menuBtn.addEventListener('click', function () {
      const expanded = menuBtn.getAttribute('aria-expanded') === 'true';
      menuBtn.setAttribute('aria-expanded', String(!expanded));
      chips.classList.toggle('d-none', expanded);
    });
    if (window.innerWidth < 768) chips.classList.add('d-none');
  }

  const currentPath = window.location.pathname;
  document.querySelectorAll('.store-nav-chips a').forEach(function (link) {
    if (link.getAttribute('href') && currentPath === '/tienda/' && link.textContent.includes('Catálogo')) return;
    if (link.href === window.location.href) link.classList.add('active');
  });

  document.querySelectorAll('[data-store-thumb]').forEach(function (thumb) {
    thumb.addEventListener('click', function () {
      const target = document.querySelector(thumb.dataset.storeTarget || '#storeGalleryMain');
      if (!target) return;
      target.src = thumb.dataset.storeSrc;
      target.alt = thumb.alt || '';
      document.querySelectorAll('[data-store-thumb]').forEach(function (item) { item.classList.remove('active'); });
      thumb.classList.add('active');
    });
  });

  document.querySelectorAll('[data-copy-text]').forEach(function (button) {
    button.addEventListener('click', function () {
      const text = button.dataset.copyText;
      const feedback = document.querySelector(button.dataset.copyFeedback || '');
      if (!text || !navigator.clipboard) return;
      navigator.clipboard.writeText(text).then(function () {
        if (feedback) {
          feedback.classList.remove('d-none');
          setTimeout(function () { feedback.classList.add('d-none'); }, 2500);
        }
      });
    });
  });

  document.querySelectorAll('input[type="file"][data-file-label]').forEach(function (input) {
    input.addEventListener('change', function () {
      const label = document.querySelector(input.dataset.fileLabel);
      if (!label) return;
      label.textContent = input.files.length ? Array.from(input.files).map(function (f) { return f.name; }).join(', ') : 'Ningún archivo seleccionado';
    });
  });
});
