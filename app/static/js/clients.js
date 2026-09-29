(() => {
  const clients = JSON.parse(document.querySelector('#client-data').textContent);
  const carousel = document.querySelector('.client-carousel');
  if (!carousel || !clients.length) return;
  const slides = [...carousel.querySelectorAll('.client-slide')];
  const dialog = document.querySelector('#client-dialog');
  const narrow = matchMedia('(max-width: 700px)');
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');
  let active = Math.min(1, clients.length - 1);
  let paused = reducedMotion.matches;
  let keyboardMode = false;
  let timer;
  carousel.classList.add('is-enhanced');
  const pause = document.querySelector('#carousel-pause');
  const previous = document.querySelector('#clients-previous');
  const next = document.querySelector('#clients-next');
  previous.hidden = next.hidden = clients.length < 2;
  carousel.querySelector('.carousel-controls').hidden = false;

  function schedule() {
    clearTimeout(timer);
    if (clients.length < 2 || paused || dialog.open || document.hidden || (keyboardMode && carousel.contains(document.activeElement))) return;
    timer = setTimeout(() => move(1, false), 6500);
  }
  function render(announce = false) {
    slides.forEach((slide, index) => {
      let slot = (index - active + clients.length) % clients.length;
      if (slot > clients.length / 2) slot -= clients.length;
      const visible = Math.abs(slot) <= (narrow.matches ? 0 : 1);
      slide.style.setProperty('--slot', slot);
      slide.classList.toggle('is-current', index === active);
      slide.classList.toggle('is-visible', visible);
      slide.inert = !visible;
      slide.setAttribute('aria-hidden', String(!visible));
    });
    document.querySelector('#carousel-position').textContent = `${active + 1} / ${clients.length}`;
    if (announce) document.querySelector('#carousel-announcement').textContent = clients[active].name;
    pause.textContent = paused ? 'Play slideshow' : 'Pause slideshow';
    pause.setAttribute('aria-pressed', String(paused));
    schedule();
  }
  function move(direction, announce = true) {
    active = (active + direction + clients.length) % clients.length;
    render(announce);
  }
  previous.addEventListener('click', () => move(-1));
  next.addEventListener('click', () => move(1));
  pause.addEventListener('click', () => { paused = !paused; render(); });
  carousel.addEventListener('keydown', (event) => {
    if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      event.preventDefault();
      // Keep focus on the carousel if the focused card is about to move offscreen.
      if (event.target.closest('.client-card')) carousel.focus();
      move(event.key === 'ArrowRight' ? 1 : -1);
    }
  });
  // Mouse hover and retained mouse focus must not stop autoplay indefinitely.
  document.addEventListener('pointerdown', () => { keyboardMode = false; schedule(); });
  document.addEventListener('keydown', event => {
    if (event.key === 'Tab' || event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
      keyboardMode = true;
      schedule();
    }
  });
  carousel.addEventListener('focusin', schedule);
  carousel.addEventListener('focusout', () => setTimeout(schedule, 0));
  document.addEventListener('visibilitychange', schedule);
  narrow.addEventListener('change', () => render());
  reducedMotion.addEventListener('change', () => { paused = reducedMotion.matches; render(); });

  function imageNode(src, alt, kind = 'artwork') {
    const wrapper = document.createElement('div');
    wrapper.className = `client-art client-art-${kind}`;
    const img = document.createElement('img');
    img.src = src;
    img.alt = alt;
    wrapper.append(img);
    return wrapper;
  }
  carousel.querySelectorAll('.client-card').forEach(card => card.addEventListener('click', () => {
    const client = clients[Number(card.dataset.clientIndex)];
    document.querySelector('#client-dialog-name').textContent = client.name;
    document.querySelector('#client-dialog-location').textContent = client.location;
    document.querySelector('#client-dialog-description').textContent = client.description;
    document.querySelector('#client-project').hidden = !client.project_details;
    document.querySelector('#client-dialog-project').textContent = client.project_details;
    const media = document.querySelector('#client-dialog-media');
    media.replaceChildren(imageNode(client.image, client.name, client.image_kind));
    client.gallery.forEach((src, index) => media.append(imageNode(src, `${client.name} — project photo ${index + 1}`)));
    const links = document.querySelector('#client-dialog-links');
    links.replaceChildren();
    for (const [field, label] of [['website_url', 'Website'], ['instagram_url', 'Instagram'], ['tiktok_url', 'TikTok']]) {
      if (!client[field]) continue;
      const link = document.createElement('a');
      link.href = client[field];
      link.textContent = `${label} ↗`;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      link.setAttribute('aria-label', `${client.name} ${label} (opens in a new tab)`);
      links.append(link);
    }
    dialog.showModal();
    document.body.classList.add('client-dialog-open');
    schedule();
  }));
  dialog.querySelector('.dialog-close').addEventListener('click', () => dialog.close());
  dialog.addEventListener('click', event => {
    const bounds = dialog.getBoundingClientRect();
    if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
  });
  dialog.addEventListener('close', () => { document.body.classList.remove('client-dialog-open'); schedule(); });
  render();
})();
