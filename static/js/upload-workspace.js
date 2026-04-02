(function () {
  'use strict';

  // ── Element refs ──────────────────────────────────────────────────────────
  var dropzone      = document.getElementById('dropzone');
  var fileInput     = document.getElementById('pdf-file-input');
  var dropzoneHint  = document.getElementById('dropzone-hint');
  var dropzoneName  = document.getElementById('dropzone-filename');
  var pdfError      = document.getElementById('pdf-error');
  var jdInput       = document.getElementById('job-description');
  var jdError       = document.getElementById('jd-error');
  var credRadios    = document.querySelectorAll('input[name="credential_mode"]');
  var userKeyField  = document.getElementById('user-key-field');
  var userKeyInput  = document.getElementById('user-key-input');
  var userKeyError  = document.getElementById('user-key-error');
  var modelSelect   = document.getElementById('model-select');
  var modelError    = document.getElementById('model-error');
  var startBtn      = document.getElementById('start-btn');
  var btnIcon       = document.getElementById('btn-icon');
  var btnSpinner    = document.getElementById('btn-spinner');
  var btnLabel      = document.getElementById('btn-label');
  var statusBanner  = document.getElementById('status-banner');

  var selectedFile = null;

  // ── CSRF ──────────────────────────────────────────────────────────────────
  function getCsrfToken() {
    var name = 'csrftoken';
    var cookieValue = '';
    if (document.cookie && document.cookie !== '') {
      var cookies = document.cookie.split(';');
      for (var i = 0; i < cookies.length; i++) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  // ── Error helpers ─────────────────────────────────────────────────────────
  function showFieldError(el, msg) {
    el.textContent = msg;
  }
  function clearFieldError(el) {
    el.textContent = '';
  }
  function showBanner(msg, isError) {
    statusBanner.textContent = msg;
    statusBanner.className = 'status-banner' + (isError ? ' status-banner--error' : ' status-banner--info');
    statusBanner.hidden = false;
  }
  function hideBanner() {
    statusBanner.hidden = true;
    statusBanner.textContent = '';
  }

  // ── Dropzone ──────────────────────────────────────────────────────────────
  function acceptFile(file) {
    if (!file) return;
    selectedFile = file;
    clearFieldError(pdfError);
    dropzoneName.textContent = file.name;
    dropzoneName.hidden = false;
    dropzoneHint.hidden = true;
    dropzone.classList.add('ready');
  }

  dropzone.addEventListener('click', function () { fileInput.click(); });
  dropzone.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fileInput.click();
    }
  });
  fileInput.addEventListener('change', function () {
    if (fileInput.files && fileInput.files[0]) {
      acceptFile(fileInput.files[0]);
    }
  });

  dropzone.addEventListener('dragover', function (e) {
    e.preventDefault();
    dropzone.classList.add('drag-active');
  });
  dropzone.addEventListener('dragleave', function () {
    dropzone.classList.remove('drag-active');
  });
  dropzone.addEventListener('drop', function (e) {
    e.preventDefault();
    dropzone.classList.remove('drag-active');
    var file = e.dataTransfer.files && e.dataTransfer.files[0];
    if (file) acceptFile(file);
  });

  // ── Credential toggle ─────────────────────────────────────────────────────
  credRadios.forEach(function (radio) {
    radio.addEventListener('change', function () {
      var isUserKey = document.querySelector('input[name="credential_mode"]:checked').value === 'user_key';
      if (isUserKey) {
        userKeyField.classList.add('visible');
      } else {
        userKeyField.classList.remove('visible');
        userKeyInput.value = '';
        clearFieldError(userKeyError);
      }
    });
  });

  // ── Loading state ─────────────────────────────────────────────────────────
  function setLoading(loading) {
    startBtn.disabled = loading;
    btnIcon.hidden = loading;
    btnSpinner.hidden = !loading;
    btnLabel.textContent = loading ? 'Tailoring\u2026' : 'Start Tailoring';
  }

  // ── Validate ──────────────────────────────────────────────────────────────
  function validate() {
    var ok = true;
    clearFieldError(pdfError);
    clearFieldError(jdError);
    clearFieldError(userKeyError);
    clearFieldError(modelError);
    hideBanner();

    if (!selectedFile) {
      showFieldError(pdfError, 'A PDF file is required.');
      ok = false;
    } else if (!selectedFile.name.toLowerCase().endsWith('.pdf')) {
      showFieldError(pdfError, 'Only PDF files are supported.');
      ok = false;
    } else if (selectedFile.size > 20 * 1024 * 1024) {
      showFieldError(pdfError, 'PDF must be 20 MB or smaller.');
      ok = false;
    }

    if (!jdInput.value.trim()) {
      showFieldError(jdError, 'Job description is required.');
      ok = false;
    }

    var credMode = document.querySelector('input[name="credential_mode"]:checked');
    if (credMode && credMode.value === 'user_key' && !userKeyInput.value.trim()) {
      showFieldError(userKeyError, 'GitHub Models API key is required.');
      ok = false;
    }

    if (!modelSelect.value) {
      showFieldError(modelError, 'Please select a model.');
      ok = false;
    }

    return ok;
  }

  // ── Submit ────────────────────────────────────────────────────────────────
  startBtn.addEventListener('click', function () {
    if (!validate()) return;

    var credMode = document.querySelector('input[name="credential_mode"]:checked').value;
    var genMode  = document.querySelector('input[name="generation_mode"]:checked').value;

    var fd = new FormData();
    fd.append('pdf_file', selectedFile);
    fd.append('job_description', jdInput.value.trim());
    fd.append('credential_mode', credMode);
    fd.append('selected_model', modelSelect.value);
    fd.append('generation_mode', genMode);
    if (credMode === 'user_key') {
      fd.append('user_key', userKeyInput.value.trim());
    }

    setLoading(true);

    fetch('/upload/', {
      method: 'POST',
      headers: { 'X-CSRFToken': getCsrfToken() },
      body: fd,
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { ok: res.ok, status: res.status, data: data };
        });
      })
      .then(function (result) {
        setLoading(false);
        if (!result.ok) {
          var errors = result.data.errors || {};
          if (errors.pdf_file)        showFieldError(pdfError, errors.pdf_file);
          if (errors.job_description) showFieldError(jdError, errors.job_description);
          if (errors.user_key)        showFieldError(userKeyError, errors.user_key);
          if (errors.selected_model)  showFieldError(modelError, errors.selected_model);
          if (!errors.pdf_file && !errors.job_description && !errors.user_key && !errors.selected_model) {
            var credModeNow = document.querySelector('input[name="credential_mode"]:checked').value;
            var timeoutMsg = credModeNow === 'user_key'
              ? 'Request timed out. Check your API key and retry.'
              : 'Request timed out. Retry the request.';
            showBanner(errors.general || timeoutMsg, true);
          }
          return;
        }
        // Success: redirect to review workspace
        var sessionId = result.data.session_id;
        window.location.href = '/sessions/' + sessionId + '/review/';
      })
      .catch(function () {
        setLoading(false);
        var credModeNow = document.querySelector('input[name="credential_mode"]:checked').value;
        var timeoutMsg = credModeNow === 'user_key'
          ? 'Request timed out. Check your API key and retry.'
          : 'Request timed out. Retry the request.';
        showBanner(timeoutMsg, true);
      });
  });

}());
