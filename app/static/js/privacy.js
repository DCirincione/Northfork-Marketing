(() => {
  const notice = document.getElementById('privacy-notice');
  const key = 'nofo-privacy-notice-v1';
  if (!notice || typeof notice.showModal !== 'function') return;
  try {
    if (localStorage.getItem(key) === 'dismissed') return;
  } catch (_) {
    // The notice remains dismissible when browser storage is unavailable.
  }
  const rememberDismissal = () => {
    try { localStorage.setItem(key, 'dismissed'); } catch (_) { /* Storage is optional. */ }
  };
  notice.addEventListener('submit', rememberDismissal);
  notice.addEventListener('cancel', rememberDismissal);
  notice.addEventListener('close', rememberDismissal);
  notice.showModal();
})();
