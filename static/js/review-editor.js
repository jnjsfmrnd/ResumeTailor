/* ============================================================
   ResumeTailor — Review Editor (review-editor.js)
   Autosave logic for the review and edit workspace.
   ============================================================ */
(function () {
  'use strict';

  var DEBOUNCE_MS = 800;
  var timers = {};

  /**
   * Read the CSRF token from the browser cookie.
   * @returns {string}
   */
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

  /**
   * Update a save-indicator element.
   * @param {HTMLElement} el
   * @param {string} state  — 'saving' | 'saved' | 'error' | ''
   * @param {string} text
   */
  function setIndicator(el, state, text) {
    el.textContent = text;
    el.className = 'save-indicator' + (state ? ' ' + state : '');
  }

  /**
   * POST the updated section content to the section-edit endpoint.
   * @param {HTMLTextAreaElement} textarea
   */
  function saveSection(textarea) {
    var sectionId = textarea.dataset.sectionId;
    var editUrl   = textarea.dataset.editUrl;
    var indicator = document.getElementById('save-' + sectionId);
    if (!indicator) return;

    setIndicator(indicator, 'saving', 'Saving\u2026');

    fetch(editUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ user_edited_content: textarea.value }),
    })
      .then(function (res) {
        return res.ok
          ? res.json()
          : Promise.reject(new Error('HTTP ' + res.status));
      })
      .then(function () {
        setIndicator(indicator, 'saved', 'Saved');
        setTimeout(function () {
          if (indicator.textContent === 'Saved') {
            setIndicator(indicator, '', '');
          }
        }, 2500);
      })
      .catch(function () {
        setIndicator(indicator, 'error', 'Save failed \u2014 retry');
      });
  }

  /**
   * POST the updated cover-letter content to the cover-letter-edit endpoint.
   * @param {HTMLTextAreaElement} textarea
   */
  function saveCoverLetter(textarea) {
    var coverLetterUrl = textarea.dataset.coverLetterUrl;
    var indicator      = document.getElementById('save-cover-letter');
    if (!indicator) return;

    setIndicator(indicator, 'saving', 'Saving\u2026');

    fetch(coverLetterUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': getCsrfToken(),
      },
      body: JSON.stringify({ user_edited_content: textarea.value }),
    })
      .then(function (res) {
        return res.ok
          ? res.json()
          : Promise.reject(new Error('HTTP ' + res.status));
      })
      .then(function () {
        setIndicator(indicator, 'saved', 'Saved');
        setTimeout(function () {
          if (indicator.textContent === 'Saved') {
            setIndicator(indicator, '', '');
          }
        }, 2500);
      })
      .catch(function () {
        setIndicator(indicator, 'error', 'Save failed \u2014 retry');
      });
  }

  /**
   * Debounced input handler — dispatches to saveSection or saveCoverLetter.
   * @param {InputEvent} e
   */
  function onInput(e) {
    var textarea = e.target;
    var key = textarea.id;
    if (timers[key]) clearTimeout(timers[key]);
    timers[key] = setTimeout(function () {
      if (textarea.dataset.sectionId) {
        saveSection(textarea);
      } else if (textarea.dataset.coverLetterUrl) {
        saveCoverLetter(textarea);
      }
    }, DEBOUNCE_MS);
  }

  /* Attach debounced input listeners to all edit areas.
   * Guard against the case where DOMContentLoaded already fired (e.g. the
   * script is loaded dynamically or document.readyState is already
   * 'interactive' / 'complete'). */
  function attachListeners() {
    document.querySelectorAll('.edit-area').forEach(function (el) {
      el.addEventListener('input', onInput);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', attachListeners);
  } else {
    attachListeners();
  }
}());
