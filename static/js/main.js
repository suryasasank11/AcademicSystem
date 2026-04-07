/* ============================================================
   Academic Management System — main.js
   Sidebar toggle, AJAX helpers, UI enhancements
   ============================================================ */

'use strict';

/* ── DOM Ready ─────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', function () {
  initSidebar();
  initAlertAutoDismiss();
  initTooltips();
  initConfirmDialogs();
  initToggleUserActive();
  initScoreAutoGrade();
  initAttendanceCounter();
  initSearchHighlight();
  initFormDirtyGuard();
});

/* ── Sidebar ────────────────────────────────────────────────── */
function initSidebar() {
  const sidebar    = document.getElementById('sidebar');
  const overlay    = document.getElementById('sidebarOverlay');
  const openBtn    = document.getElementById('sidebarToggle');
  const closeBtn   = document.getElementById('sidebarClose');

  if (!sidebar) return;

  function openSidebar() {
    sidebar.classList.add('show');
    if (overlay) overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
  }

  function closeSidebar() {
    sidebar.classList.remove('show');
    if (overlay) overlay.classList.remove('show');
    document.body.style.overflow = '';
  }

  if (openBtn)  openBtn.addEventListener('click', openSidebar);
  if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
  if (overlay)  overlay.addEventListener('click', closeSidebar);

  // Keyboard: Escape closes sidebar on mobile
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && sidebar.classList.contains('show')) {
      closeSidebar();
    }
  });

  // Mark active nav link
  const currentPath = window.location.pathname;
  sidebar.querySelectorAll('.nav-link').forEach(function (link) {
    if (link.getAttribute('href') && link.getAttribute('href') !== '#') {
      if (currentPath.startsWith(link.getAttribute('href'))) {
        link.classList.add('active');
      }
    }
  });
}

/* ── Alert Auto-Dismiss ─────────────────────────────────────── */
function initAlertAutoDismiss() {
  const alerts = document.querySelectorAll('.messages-container .alert');
  alerts.forEach(function (alert) {
    setTimeout(function () {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) bsAlert.close();
    }, 6000);
  });
}

/* ── Bootstrap Tooltips ─────────────────────────────────────── */
function initTooltips() {
  document.querySelectorAll('[title]:not([data-bs-toggle])').forEach(function (el) {
    new bootstrap.Tooltip(el, { trigger: 'hover', placement: 'top' });
  });
}

/* ── Confirm Dialogs ────────────────────────────────────────── */
function initConfirmDialogs() {
  // data-confirm="Are you sure?" on any button/link
  document.querySelectorAll('[data-confirm]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      const msg = el.dataset.confirm || 'Are you sure?';
      if (!window.confirm(msg)) {
        e.preventDefault();
        e.stopPropagation();
      }
    });
  });

  // Delete buttons in tables always get a confirm
  document.querySelectorAll('a[href*="/delete/"]').forEach(function (el) {
    if (!el.dataset.confirm) {
      el.addEventListener('click', function (e) {
        if (!window.confirm('Are you sure you want to delete this item? This cannot be undone.')) {
          e.preventDefault();
        }
      });
    }
  });
}

/* ── AJAX: Toggle User Active ───────────────────────────────── */
function initToggleUserActive() {
  document.querySelectorAll('.js-toggle-active').forEach(function (btn) {
    btn.addEventListener('click', function () {
      const userId = btn.dataset.userId;
      const csrfToken = getCsrfToken();

      fetch(`/accounts/users/${userId}/toggle-active/`, {
        method: 'POST',
        headers: {
          'X-CSRFToken': csrfToken,
          'Content-Type': 'application/json',
        },
      })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.is_active !== undefined) {
          btn.textContent = data.is_active ? 'Deactivate' : 'Activate';
          btn.className = data.is_active
            ? 'btn btn-sm btn-outline-warning js-toggle-active'
            : 'btn btn-sm btn-outline-success js-toggle-active';
          showToast(data.is_active ? 'User activated.' : 'User deactivated.', 'success');
        }
      })
      .catch(function () {
        showToast('Failed to update user status.', 'danger');
      });
    });
  });
}

/* ── Grade: Auto Letter from Score ─────────────────────────── */
function initScoreAutoGrade() {
  const scoreInput  = document.getElementById('id_numeric_score');
  const letterSelect = document.getElementById('id_letter_grade');
  if (!scoreInput || !letterSelect) return;

  scoreInput.addEventListener('input', function () {
    const score = parseFloat(scoreInput.value);
    if (isNaN(score)) return;

    let letter = '';
    if (score >= 97)      letter = 'A+';
    else if (score >= 93) letter = 'A';
    else if (score >= 90) letter = 'A-';
    else if (score >= 87) letter = 'B+';
    else if (score >= 83) letter = 'B';
    else if (score >= 80) letter = 'B-';
    else if (score >= 77) letter = 'C+';
    else if (score >= 73) letter = 'C';
    else if (score >= 70) letter = 'C-';
    else if (score >= 67) letter = 'D+';
    else if (score >= 63) letter = 'D';
    else if (score >= 60) letter = 'D-';
    else                   letter = 'F';

    // Only auto-fill if the field is empty or was previously auto-filled
    if (!letterSelect.dataset.manuallySet) {
      for (let i = 0; i < letterSelect.options.length; i++) {
        if (letterSelect.options[i].value === letter) {
          letterSelect.selectedIndex = i;
          break;
        }
      }
    }
  });

  letterSelect.addEventListener('change', function () {
    letterSelect.dataset.manuallySet = '1';
  });
}

/* ── Attendance Live Counter ────────────────────────────────── */
function initAttendanceCounter() {
  const table = document.getElementById('attendanceTable');
  if (!table) return;

  function count() {
    const selects = table.querySelectorAll('select[name$="_status"]');
    let present = 0, absent = 0, late = 0, other = 0;
    selects.forEach(function (s) {
      switch (s.value) {
        case 'present': present++; break;
        case 'absent':  absent++;  break;
        case 'late':    late++;    break;
        default:        other++;   break;
      }
    });
    const pc = document.getElementById('presentCount');
    const ac = document.getElementById('absentCount');
    const lc = document.getElementById('lateCount');
    if (pc) pc.textContent = present;
    if (ac) ac.textContent = absent;
    if (lc) lc.textContent = late;
  }

  table.addEventListener('change', count);
  count();
}

/* ── Search Highlight ───────────────────────────────────────── */
function initSearchHighlight() {
  const params = new URLSearchParams(window.location.search);
  const q = params.get('q');
  if (!q || q.length < 2) return;

  const walker = document.createTreeWalker(
    document.querySelector('.main-content') || document.body,
    NodeFilter.SHOW_TEXT,
    null
  );

  const regex = new RegExp(`(${escapeRegex(q)})`, 'gi');
  const textNodes = [];
  let node;
  while ((node = walker.nextNode())) {
    if (node.nodeValue.match(regex) && !['SCRIPT','STYLE','INPUT','TEXTAREA'].includes(node.parentNode.tagName)) {
      textNodes.push(node);
    }
  }

  textNodes.slice(0, 30).forEach(function (tn) {
    const span = document.createElement('span');
    span.innerHTML = tn.nodeValue.replace(regex, '<mark class="bg-warning px-0">$1</mark>');
    tn.parentNode.replaceChild(span, tn);
  });
}

/* ── Dirty Form Guard ───────────────────────────────────────── */
function initFormDirtyGuard() {
  const forms = document.querySelectorAll('form[data-dirty-guard]');
  forms.forEach(function (form) {
    let isDirty = false;
    form.addEventListener('change', function () { isDirty = true; });
    form.addEventListener('submit', function () { isDirty = false; });
    window.addEventListener('beforeunload', function (e) {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
      }
    });
  });
}

/* ── Toast Helper ───────────────────────────────────────────── */
function showToast(message, type) {
  type = type || 'info';
  const container = document.getElementById('toast-container') || createToastContainer();
  const toast = document.createElement('div');
  toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
  toast.setAttribute('role', 'alert');
  toast.innerHTML = `
    <div class="d-flex">
      <div class="toast-body">${message}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
    </div>`;
  container.appendChild(toast);
  setTimeout(function () { toast.remove(); }, 4000);
}

function createToastContainer() {
  const c = document.createElement('div');
  c.id = 'toast-container';
  c.className = 'toast-container position-fixed bottom-0 end-0 p-3';
  c.style.zIndex = '9999';
  document.body.appendChild(c);
  return c;
}

/* ── CSRF ────────────────────────────────────────────────────── */
function getCsrfToken() {
  const cookie = document.cookie.split(';').find(function (c) {
    return c.trim().startsWith('csrftoken=');
  });
  return cookie ? cookie.trim().split('=')[1] : '';
}

/* ── Utils ───────────────────────────────────────────────────── */
function escapeRegex(str) {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/* ── Expose globally if needed ──────────────────────────────── */
window.AMS = { showToast, getCsrfToken };