/* MediVault – drag & drop upload with validation, preview, progress, duplicate detection */
(function () {
  'use strict';
  const form = document.getElementById('uploadForm'); if (!form) return;
  const { $, csrf, reduceMotion } = window.MV;
  const dz = $('#dropzone'), input = $('#fileInput'), errBox = $('#uploadError'), card = $('#filePreview');
  const btn = $('#uploadBtn'), maxMb = parseInt(form.dataset.maxMb, 10) || 10;
  const bar = $('#progressBar'), pwrap = $('#progressWrap'), ptext = $('#progressText');
  const dupModal = $('#dupModal');
  const OK_EXT = ['pdf', 'jpg', 'jpeg', 'png'];
  let file = null, thumbUrl = null, uploading = false;

  const fmtSize = (n) => n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(2) + ' MB';
  function showError(msg) {
    errBox.innerHTML = window.MV.icon('alert') + ' ' + msg; errBox.hidden = false;
    dz.classList.remove('has-error'); void dz.offsetWidth; dz.classList.add('has-error'); window.toast(msg, 'error');
  }
  function clearError() { errBox.hidden = true; dz.classList.remove('has-error'); }
  function resetProgress() { pwrap.hidden = true; ptext.hidden = true; bar.style.width = '0'; }

  function setFile(f) {
    clearError();
    const ext = (f.name.split('.').pop() || '').toLowerCase();
    if (!OK_EXT.includes(ext)) return showError('Invalid file type. Please upload a PDF, JPG, JPEG or PNG file.');
    if (f.size === 0) return showError('The selected file is empty.');
    if (f.size > maxMb * 1048576) return showError('File size exceeds the allowed limit of ' + maxMb + ' MB.');
    file = f;
    $('#fileName').textContent = f.name; $('#fileMeta').textContent = ext.toUpperCase() + ' · ' + fmtSize(f.size);
    const th = $('#fileThumb'); th.innerHTML = '';
    if (thumbUrl) URL.revokeObjectURL(thumbUrl);
    if (ext === 'pdf') th.textContent = 'PDF';
    else { thumbUrl = URL.createObjectURL(f); const im = document.createElement('img'); im.src = thumbUrl; im.alt = 'Preview of selected file'; th.appendChild(im); }
    card.hidden = false; btn.disabled = false; resetProgress();
    const title = $('#title'); if (!title.value.trim()) title.value = f.name.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ');
  }
  function removeFile() { file = null; input.value = ''; card.hidden = true; btn.disabled = true; resetProgress(); clearError(); }

  $('#browseBtn').addEventListener('click', (e) => { e.stopPropagation(); input.click(); });
  dz.addEventListener('click', () => input.click());
  dz.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
  input.addEventListener('change', () => { if (input.files[0]) setFile(input.files[0]); });
  ['dragenter', 'dragover'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.add('dragover'); }));
  ['dragleave', 'drop'].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); dz.classList.remove('dragover'); }));
  dz.addEventListener('drop', (e) => { const f = e.dataTransfer.files[0]; if (f) setFile(f); });
  $('#removeFile').addEventListener('click', removeFile);

  function send(allowDuplicate) {
    if (uploading) return; uploading = true; btn.disabled = true;
    const fd = new FormData(form); fd.set('file', file); if (allowDuplicate) fd.set('allow_duplicate', '1');
    const xhr = new XMLHttpRequest();
    xhr.open('POST', form.dataset.action);
    xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest'); xhr.setRequestHeader('X-CSRF-Token', csrf());
    pwrap.hidden = false; ptext.hidden = false; bar.style.width = '0'; ptext.textContent = '0%';
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) { const p = Math.round(e.loaded / e.total * 100); bar.style.width = p + '%'; ptext.textContent = p < 100 ? 'Uploading… ' + p + '%' : 'Processing…'; } };
    xhr.onload = () => {
      uploading = false; let data = {};
      try { data = JSON.parse(xhr.responseText); } catch (e) {}
      if (xhr.status === 200 && data.ok) {
        bar.style.width = '100%'; ptext.textContent = 'Done';
        const so = $('#successOverlay'); so.hidden = false;
        setTimeout(() => { window.location = data.redirect; }, reduceMotion ? 300 : 1500);
      } else if (xhr.status === 409 && data.duplicate) {
        resetProgress(); btn.disabled = false;
        $('#dupTitle').textContent = data.existing.title; $('#dupView').href = data.existing.url; openModal(dupModal);
      } else {
        resetProgress(); btn.disabled = false;
        showError(data.message || (xhr.status === 413 ? 'File size exceeds the allowed limit of ' + maxMb + ' MB.' : 'Unable to upload report.'));
      }
    };
    xhr.onerror = () => { uploading = false; resetProgress(); btn.disabled = false; showError('Unable to upload report. Check your connection and try again.'); };
    xhr.send(fd);
  }
  form.addEventListener('submit', (e) => {
    e.preventDefault(); clearError();
    if (!file) return showError('Please choose a file to upload.');
    if (!form.reportValidity()) return;
    send(false);
  });
  $('#dupUpload').addEventListener('click', () => { closeModal(dupModal); send(true); });
  const cancelDup = () => { closeModal(dupModal); };
  $('#dupCancel').addEventListener('click', cancelDup); dupModal.addEventListener('mv:close', cancelDup);
  dupModal.addEventListener('click', (e) => { if (e.target === dupModal) cancelDup(); });
})();
