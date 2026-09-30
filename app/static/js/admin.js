(() => {
  const $ = selector => document.querySelector(selector);
  function node(tag, text, className) {
    const element = document.createElement(tag);
    if (text !== undefined) element.textContent = text;
    if (className) element.className = className;
    return element;
  }
  async function api(path, {method = 'GET', data, file} = {}) {
    const headers = {'X-Admin-Request': '1'};
    if (file) headers['Content-Type'] = file.type;
    else if (data !== undefined) headers['Content-Type'] = 'application/json';
    let response;
    try {
      response = await fetch(`/admin/api/${path}`, {method, headers, credentials: 'same-origin', body: file || (data === undefined ? undefined : JSON.stringify(data))});
    } catch { throw new Error('Connection failed. Your changes have not been confirmed. Please try again.'); }
    const result = await response.json().catch(() => ({}));
    if (!response.ok) {
      if (response.status === 401) throw new Error('Your session expired. Sign in again at /admin/login.');
      if (Array.isArray(result.detail)) throw new Error('Check the form fields and image URLs, then try again.');
      throw new Error(result.detail || 'The request could not be completed. Please try again.');
    }
    return result;
  }
  const login = $('#admin-login');
  if (login) {
    login.addEventListener('submit', async event => {
      event.preventDefault();
      const button = login.querySelector('button');
      button.disabled = true;
      $('#login-status').textContent = '';
      try {
        await api('login', {method: 'POST', data: Object.fromEntries(new FormData(login))});
        location.assign('/admin');
      } catch (error) { $('#login-status').textContent = error.message; $('#login-status').focus(); }
      finally { button.disabled = false; }
    });
    return;
  }
  if (!$('#admin-dashboard')) return;
  let clients = [], messages = [], offset = 0, selectedMessage, editingId = null, orderDirty = false, uploads = 0, editorDirty = false, saving = false;
  let messageLoad = 0;
  const status = text => { $('#dashboard-status').textContent = text; };
  const date = value => new Date(value).toLocaleString(undefined, {dateStyle: 'medium', timeStyle: 'short'});
  const editor = $('#client-editor');
  const form = $('#client-form');

  $('#logout').addEventListener('click', async () => {
    if ((orderDirty || editorDirty) && !confirm('Discard your unsaved changes and sign out?')) return;
    try { await api('logout', {method: 'POST'}); location.assign('/admin/login'); }
    catch (error) { status(error.message); }
  });
  const tabs = [$('#messages-tab'), $('#clients-tab')];
  function selectTab(tab) {
    tabs.forEach(item => {
      const active = item === tab;
      item.setAttribute('aria-selected', String(active)); item.tabIndex = active ? 0 : -1;
      document.getElementById(item.getAttribute('aria-controls')).hidden = !active;
    });
    status('');
    if (tab.id === 'clients-tab') { if (!orderDirty) loadClients(); }
    else loadMessages();
  }
  tabs.forEach((tab, index) => {
    tab.addEventListener('click', () => selectTab(tab));
    tab.addEventListener('keydown', event => {
      if (['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) {
        event.preventDefault();
        const next = tabs[event.key === 'Home' ? 0 : event.key === 'End' ? 1 : 1 - index];
        next.focus(); selectTab(next);
      }
    });
  });

  async function loadMessages() {
    const version = ++messageLoad;
    $('#message-list').textContent = 'Loading messages…';
    $('#messages-next').disabled = $('#messages-previous').disabled = true;
    try {
      const result = await api(`messages?offset=${offset}&unread=${$('#unread-only').checked}`);
      if (version !== messageLoad) return;
      messages = result.items;
      const list = $('#message-list'); list.replaceChildren();
      if (!messages.length) list.append(node('p', 'No messages here yet.', 'empty-state'));
      messages.forEach(message => {
        const button = node('button', undefined, `message-card${message.is_read ? '' : ' unread'}`);
        button.type = 'button';
        const body = node('div');
        body.append(node('strong', message.name), node('span', message.email), node('span', message.message.slice(0, 140), 'message-preview'));
        const meta = node('div', undefined, 'message-meta');
        meta.append(node('span', date(message.created_at)), node('span', message.is_read ? 'Read' : 'Unread', 'badge'));
        button.append(body, meta); button.addEventListener('click', () => openMessage(message)); list.append(button);
      });
      $('#messages-previous').disabled = offset === 0;
      $('#messages-next').disabled = !result.has_more;
      $('#messages-page').textContent = `Page ${Math.floor(offset / 25) + 1}`;
    } catch (error) { if (version === messageLoad) { $('#message-list').textContent = ''; status(error.message); } }
  }
  function openMessage(message) {
    selectedMessage = message;
    $('#message-title').textContent = message.name;
    $('#message-date').textContent = date(message.created_at);
    $('#message-body').textContent = message.message;
    $('#message-status').textContent = '';
    const details = $('#message-contact'); details.replaceChildren();
    const email = node('a', message.email); email.href = `mailto:${encodeURIComponent(message.email)}`; details.append(email);
    if (message.phone) { const phone = node('a', message.phone); phone.href = `tel:${message.phone.replace(/[^0-9+]/g, '')}`; details.append(phone); }
    $('#toggle-message-read').textContent = message.is_read ? 'Mark unread' : 'Mark read';
    $('#message-dialog').showModal();
  }
  $('#toggle-message-read').addEventListener('click', async event => {
    event.target.disabled = true;
    try {
      await api(`messages/${selectedMessage.id}`, {method: 'PATCH', data: {is_read: !selectedMessage.is_read}});
      selectedMessage.is_read = !selectedMessage.is_read;
      event.target.textContent = selectedMessage.is_read ? 'Mark unread' : 'Mark read';
      $('#message-status').textContent = 'Updated.';
      loadMessages();
    } catch (error) { $('#message-status').textContent = error.message; }
    finally { event.target.disabled = false; }
  });
  $('#unread-only').addEventListener('change', () => { offset = 0; loadMessages(); });
  $('#refresh-messages').addEventListener('click', () => { status(''); loadMessages(); });
  $('#messages-next').addEventListener('click', () => { offset += 25; loadMessages(); });
  $('#messages-previous').addEventListener('click', () => { offset = Math.max(0, offset - 25); loadMessages(); });

  async function loadClients() {
    $('#client-list').textContent = 'Loading clients…';
    try { clients = await api('clients'); orderDirty = false; renderClients(); }
    catch (error) { $('#client-list').textContent = ''; status(error.message); }
  }
  let draggedId = null;
  function moveClient(from, to) {
    if (from < 0 || to < 0 || to >= clients.length || from === to) return;
    const positions = new Map([...$('#client-list').children].map(el => [el.dataset.id, el.getBoundingClientRect().top]));
    clients.splice(to, 0, clients.splice(from, 1)[0]); orderDirty = true; renderClients();
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      [...$('#client-list').children].forEach(el => {
        const delta = positions.get(el.dataset.id) - el.getBoundingClientRect().top;
        if (delta) el.animate([{transform: `translateY(${delta}px)`}, {transform: 'translateY(0)'}], {duration: 220, easing: 'ease-out'});
      });
    }
  }
  function renderClients() {
    const list = $('#client-list'); list.replaceChildren();
    if (!clients.length) list.append(node('p', 'Add your first client to start the showcase.', 'empty-state'));
    clients.forEach((client, index) => {
      const row = node('div', undefined, 'admin-client-row'); row.draggable = true; row.dataset.id = client.id;
      const handle = node('span', '⠿', 'drag-handle'); handle.setAttribute('aria-hidden', 'true');
      const image = node('img'); image.src = client.image; image.alt = ''; image.draggable = false;
      const info = node('div', undefined, 'client-row-info'); info.append(node('strong', client.name), node('span', client.published ? 'Published' : 'Draft', 'badge'));
      const actions = node('div', undefined, 'row-actions');
      for (const [label, text, target] of [['Move up', '↑', index - 1], ['Move down', '↓', index + 1]]) {
        const button = node('button', text); button.type = 'button'; button.setAttribute('aria-label', `${label}: ${client.name}`); button.disabled = target < 0 || target >= clients.length;
        button.addEventListener('click', () => { moveClient(index, target); const moved = [...list.children].find(el => el.dataset.id === client.id); moved?.querySelector('button:not(:disabled)')?.focus(); }); actions.append(button);
      }
      const edit = node('button', 'Edit'); edit.type = 'button'; edit.setAttribute('aria-label', `Edit ${client.name}`); edit.addEventListener('click', () => openClient(client)); actions.append(edit);
      row.append(handle, image, info, actions);
      row.addEventListener('dragstart', event => { draggedId = client.id; event.dataTransfer.setData('text/plain', client.id); event.dataTransfer.effectAllowed = 'move'; row.classList.add('dragging'); });
      row.addEventListener('dragend', () => { draggedId = null; document.querySelectorAll('.dragging,.drag-over').forEach(el => el.classList.remove('dragging', 'drag-over')); });
      row.addEventListener('dragover', event => { if (!draggedId) return; event.preventDefault(); row.classList.add('drag-over'); });
      row.addEventListener('dragleave', () => row.classList.remove('drag-over'));
      row.addEventListener('drop', event => { event.preventDefault(); if (!draggedId) return; moveClient(clients.findIndex(c => c.id === draggedId), index); draggedId = null; });
      list.append(row);
    });
    $('#save-order').disabled = !orderDirty;
    $('#order-status').textContent = orderDirty ? 'Unsaved order changes.' : 'Order is saved.';
  }
  $('#save-order').addEventListener('click', async event => {
    event.target.disabled = true;
    // Disable reordering while the current order is being saved.
    $('#client-list').inert = true;
    try { await api('clients/reorder', {method: 'POST', data: {ids: clients.map(c => c.id)}}); orderDirty = false; renderClients(); status(''); }
    catch (error) { status(error.message); event.target.disabled = false; }
    finally { $('#client-list').inert = false; }
  });
  function previewCover() {
    const value = form.elements.image.value.trim();
    const image = $('#client-cover-preview');
    const valid = value.startsWith('/static/') || /^https?:\/\//i.test(value);
    image.hidden = !valid;
    if (valid) image.src = value; else image.removeAttribute('src');
  }
  function openClient(client = null) {
    if (orderDirty) { status('Save your new client order before opening the editor.'); return; }
    form.reset(); delete form.elements.id.dataset.custom; editingId = client?.id || null;
    $('#editor-title').textContent = client ? 'Edit client' : 'Add client';
    for (const key of ['id', 'name', 'location', 'image', 'description', 'project_details', 'website_url', 'instagram_url', 'tiktok_url']) {
      form.elements[key].value = client?.[key] || '';
    }
    form.elements.id.readOnly = !!client;
    form.elements.published.checked = client?.published || false;
    $('#delete-client').hidden = !client;
    $('#editor-status').textContent = ''; editorDirty = false; previewCover(); editor.showModal();
  }
  $('#add-client').addEventListener('click', () => openClient());
  form.addEventListener('input', () => { editorDirty = true; });
  form.elements.name.addEventListener('input', () => {
    if (!editingId && !form.elements.id.dataset.custom) form.elements.id.value = form.elements.name.value.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100);
  });
  form.elements.id.addEventListener('input', () => { form.elements.id.dataset.custom = 'true'; });
  async function uploadImage(input) {
    const file = input.files[0];
    if (!file) return;
    uploads++; $('#save-client').disabled = true; $('#delete-client').disabled = true;
    $('#editor-status').textContent = 'Uploading…';
    try {
      if (file.size > 4 * 1024 * 1024) throw new Error('The image must be 4 MB or smaller.');
      if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) throw new Error('Choose a PNG, JPEG, or WebP image.');
      const result = await api('uploads', {method: 'POST', file});
      form.elements.image.value = result.url;
      previewCover(); editorDirty = true;
      $('#editor-status').textContent = 'Uploaded. Save the client to keep these changes.';
    } catch (error) { $('#editor-status').textContent = error.message; }
    finally { uploads--; input.value = ''; $('#save-client').disabled = $('#delete-client').disabled = uploads > 0; }
  }
  $('#client-cover-upload').addEventListener('change', event => uploadImage(event.target));
  form.addEventListener('submit', async event => {
    event.preventDefault(); if (uploads) return;
    const data = Object.fromEntries(new FormData(form));
    data.published = form.elements.published.checked;
    if (!data.image) { $('#editor-status').textContent = 'Upload a square card image before saving.'; $('#client-cover-upload').focus(); return; }
    data.image_kind = 'artwork';
    data.gallery = editingId ? (clients.find(c => c.id === editingId).gallery || []) : [];
    for (const key of ['website_url', 'instagram_url', 'tiktok_url']) data[key] = data[key].trim() || null;
    data.display_order = editingId ? clients.find(c => c.id === editingId).display_order : Math.max(0, ...clients.map(c => c.display_order)) + 10;
    $('#save-client').disabled = $('#delete-client').disabled = true; saving = true; form.inert = true;
    try {
      await api(editingId ? `clients/${editingId}` : 'clients', {method: editingId ? 'PUT' : 'POST', data});
      editorDirty = false; editor.close(); await loadClients(); status('Client saved.');
    } catch (error) { $('#editor-status').textContent = error.message; $('#editor-status').focus(); }
    finally { saving = false; form.inert = false; $('#save-client').disabled = $('#delete-client').disabled = false; }
  });
  $('#delete-client').addEventListener('click', async event => {
    if (!editingId || !confirm('Delete this client from the showcase? Uploaded images will remain in storage.')) return;
    event.target.disabled = true; saving = true; form.inert = true;
    try { await api(`clients/${editingId}`, {method: 'DELETE'}); editorDirty = false; editor.close(); await loadClients(); status('Client deleted.'); }
    catch (error) { $('#editor-status').textContent = error.message; }
    finally { saving = false; form.inert = false; event.target.disabled = false; }
  });
  function canCloseEditor() { return !uploads && !saving && (!editorDirty || confirm('Discard unsaved client changes?')); }
  document.querySelectorAll('.close-dialog').forEach(button => button.addEventListener('click', () => {
    const dialog = button.closest('dialog');
    if (dialog !== editor || canCloseEditor()) { if (dialog === editor) editorDirty = false; dialog.close(); }
  }));
  editor.addEventListener('cancel', event => { if (!canCloseEditor()) event.preventDefault(); else editorDirty = false; });
  window.addEventListener('beforeunload', event => { if (orderDirty || editorDirty || uploads) { event.preventDefault(); event.returnValue = ''; } });
  loadMessages();
})();
