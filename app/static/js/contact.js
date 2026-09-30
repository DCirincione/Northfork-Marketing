const form = document.querySelector('#contact-form');
const status = document.querySelector('#contact-status');
const button = form.querySelector('button');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (button.disabled || !form.reportValidity()) return;
  const payload = Object.fromEntries(new FormData(form));
  for (const key of Object.keys(payload)) payload[key] = payload[key].trim();
  if (!payload.name || !payload.message) {
    status.textContent = 'Please enter your name and a message.';
    status.focus();
    return;
  }
  button.disabled = true;
  button.textContent = 'SAVING…';
  status.textContent = '';
  try {
    const response = await fetch('/api/contact', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) {
      throw new Error(response.status === 422
        ? 'Please check your name, email, phone, and message, then try again.'
        : 'We couldn’t confirm your message was saved. Please try again or contact us directly.');
    }
    status.textContent = result.message;
    form.reset();
  } catch (error) {
    status.textContent = error instanceof TypeError
      ? 'We couldn’t connect. Please try again or contact us directly.'
      : error.message;
  } finally {
    button.disabled = false;
    button.textContent = 'SUBMIT MESSAGE';
    status.focus();
  }
});
