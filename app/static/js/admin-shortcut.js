// Preserve ordinary Home navigation; count quick clicks across page loads in this tab.
(() => {
  const logo = document.querySelector('.site-header .wordmark');
  if (!logo) return;
  logo.addEventListener('click', event => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    try {
      const now = Date.now();
      const previous = JSON.parse(sessionStorage.getItem('nofo-logo-clicks') || '{}');
      const count = now - previous.started < 6000 ? (Number(previous.count) || 0) + 1 : 1;
      if (count >= 5) {
        event.preventDefault();
        sessionStorage.removeItem('nofo-logo-clicks');
        window.location.assign('/admin');
      } else {
        sessionStorage.setItem('nofo-logo-clicks', JSON.stringify({count, started: count === 1 ? now : previous.started}));
        // On Home, avoid unnecessary reloads between taps.
        if (window.location.pathname === '/') event.preventDefault();
      }
    } catch {
      // If session storage is disabled, the logo remains an ordinary Home link.
    }
  });
})();
