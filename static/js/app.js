/**
 * STRATZ CUSTOM DRAFTER - CLIENT APPLICATION
 * Dota 2 counter-pick & team draft advisor with off-meta flexibility
 */

// Application State
const state = {
  allies: [
    { id: null, role: 'pos1', roleLabel: 'Керри' },
    { id: null, role: 'pos2', roleLabel: 'Мидер' },
    { id: null, role: 'pos3', roleLabel: 'Тройка' },
    { id: null, role: 'pos4', roleLabel: '4 поз' },
    { id: null, role: 'pos5', roleLabel: 'Саппорт' },
  ],
  enemies: [
    { id: null, label: 'Керри' },
    { id: null, label: 'Мидер' },
    { id: null, label: 'Тройка' },
    { id: null, label: '4 поз' },
    { id: null, label: 'Саппорт' },
  ],
  bans: [],
  activeSlot: { team: 'allies', index: 0 },
  weights: {
    counter: 70,
    synergy: 20,
    meta: 10,
  },
  bracket: 'LOW_RANK',
  allowOffMeta: true,
  useRoleWeights: true,
  viewMode: 'matrix', // 'matrix' or 'list'
  currentRoleFilter: 'all',
  heroes: [],
  heroesMap: {},
  matrixData: {},
  recsListData: [],
  searchQuery: '',
  recsSearchQuery: '',
  selectedAttr: 'all',
  fetchTimeout: null,
  user: null,
  activeAuthTab: 'login',
};

// DOM Elements
const elements = {
  counterWeight: document.getElementById('counterWeight'),
  synergyWeight: document.getElementById('synergyWeight'),
  metaWeight: document.getElementById('metaWeight'),
  counterVal: document.getElementById('counterVal'),
  synergyVal: document.getElementById('synergyVal'),
  metaVal: document.getElementById('metaVal'),
  offMetaToggle: document.getElementById('offMetaToggle'),
  roleWeightsToggle: document.getElementById('roleWeightsToggle'),
  bracketSelect: document.getElementById('bracketSelect'),
  statusBadge: document.getElementById('statusBadge'),
  statusText: document.getElementById('statusText'),
  alliesSlots: document.getElementById('alliesSlots'),
  enemiesSlots: document.getElementById('enemiesSlots'),
  alliesCount: document.getElementById('alliesCount'),
  enemiesCount: document.getElementById('enemiesCount'),
  alliesWinBar: document.getElementById('alliesWinBar'),
  enemiesWinBar: document.getElementById('enemiesWinBar'),
  alliesAdvScore: document.getElementById('alliesAdvScore'),
  enemiesAdvScore: document.getElementById('enemiesAdvScore'),
  alliesSynergy: document.getElementById('alliesSynergy'),
  enemiesSynergy: document.getElementById('enemiesSynergy'),
  draftInsight: document.getElementById('draftInsight'),
  bansList: document.getElementById('bansList'),
  clearBansBtn: document.getElementById('clearBansBtn'),
  teamMatrixContainer: document.getElementById('teamMatrixContainer'),
  recsListContainer: document.getElementById('recsListContainer'),
  roleFilterBar: document.getElementById('roleFilterBar'),
  viewModeTabs: document.getElementById('viewModeTabs'),
  recsHeroSearchInput: document.getElementById('recsHeroSearchInput'),
  clearRecsSearchBtn: document.getElementById('clearRecsSearchBtn'),
  heroPickerModal: document.getElementById('heroPickerModal'),
  heroPickerPopover: document.getElementById('heroPickerPopover'),
  popoverArrow: document.getElementById('popoverArrow'),
  modalBackdrop: document.getElementById('modalBackdrop'),
  closeModalBtn: document.getElementById('closeModalBtn'),
  modalTargetTitle: document.getElementById('modalTargetTitle'),
  heroSearchInput: document.getElementById('heroSearchInput'),
  clearSearchBtn: document.getElementById('clearSearchBtn'),
  attrFilterGroup: document.getElementById('attrFilterGroup'),
  heroesGrid: document.getElementById('heroesGrid'),
  resetDraftBtn: document.getElementById('resetDraftBtn'),
  copyDraftBtn: document.getElementById('copyDraftBtn'),
  toast: document.getElementById('toast'),

  // Site Activity Stats Elements
  onlineViewersCount: document.getElementById('onlineViewersCount'),
  totalDraftsCount: document.getElementById('totalDraftsCount'),
  footerOnlineCount: document.getElementById('footerOnlineCount'),
  footerDraftsCount: document.getElementById('footerDraftsCount'),

  // User Auth & Profile Elements
  authOpenBtn: document.getElementById('authOpenBtn'),
  userProfileBadge: document.getElementById('userProfileBadge'),
  userAvatarImg: document.getElementById('userAvatarImg'),
  userAvatarFallback: document.getElementById('userAvatarFallback'),
  userNameDisplay: document.getElementById('userNameDisplay'),
  userTokenStatusDot: document.getElementById('userTokenStatusDot'),

  authModal: document.getElementById('authModal'),
  authModalBackdrop: document.getElementById('authModalBackdrop'),
  closeAuthModalBtn: document.getElementById('closeAuthModalBtn'),
  authModalTitle: document.getElementById('authModalTitle'),
  authTabLogin: document.getElementById('authTabLogin'),
  authTabRegister: document.getElementById('authTabRegister'),
  loginForm: document.getElementById('loginForm'),
  loginEmail: document.getElementById('loginEmail'),
  loginPassword: document.getElementById('loginPassword'),
  loginErrorMsg: document.getElementById('loginErrorMsg'),
  loginSubmitBtn: document.getElementById('loginSubmitBtn'),
  registerForm: document.getElementById('registerForm'),
  regName: document.getElementById('regName'),
  regEmail: document.getElementById('regEmail'),
  regPassword: document.getElementById('regPassword'),
  registerErrorMsg: document.getElementById('registerErrorMsg'),
  registerSubmitBtn: document.getElementById('registerSubmitBtn'),

  profileModal: document.getElementById('profileModal'),
  profileModalBackdrop: document.getElementById('profileModalBackdrop'),
  closeProfileModalBtn: document.getElementById('closeProfileModalBtn'),
  closeProfileBtn2: document.getElementById('closeProfileBtn2'),
  cabinetAvatarImg: document.getElementById('cabinetAvatarImg'),
  cabinetAvatarFallback: document.getElementById('cabinetAvatarFallback'),
  cabinetUserName: document.getElementById('cabinetUserName'),
  cabinetUserEmail: document.getElementById('cabinetUserEmail'),
  cabinetStatusDot: document.getElementById('cabinetStatusDot'),
  cabinetStatusLabel: document.getElementById('cabinetStatusLabel'),
  stratzTokenInput: document.getElementById('stratzTokenInput'),
  toggleTokenVisibilityBtn: document.getElementById('toggleTokenVisibilityBtn'),
  saveStratzTokenBtn: document.getElementById('saveStratzTokenBtn'),
  deleteStratzTokenBtn: document.getElementById('deleteStratzTokenBtn'),
  tokenStatusBanner: document.getElementById('tokenStatusBanner'),
  tokenStatusBannerText: document.getElementById('tokenStatusBannerText'),
  syncUserTokenBtn: document.getElementById('syncUserTokenBtn'),
  logoutBtn: document.getElementById('logoutBtn'),
};

// Visitor ID and Stats Management
function getVisitorId() {
  let vid = sessionStorage.getItem('stratz_vid');
  if (!vid) {
    vid = 'v_' + Math.random().toString(36).substring(2, 10) + Date.now().toString(36);
    sessionStorage.setItem('stratz_vid', vid);
  }
  return vid;
}

function updateStatsUI(onlineViewers, totalDrafts) {
  if (onlineViewers !== undefined && onlineViewers !== null) {
    const formattedOnline = Number(onlineViewers).toLocaleString('ru-RU');
    if (elements.onlineViewersCount) elements.onlineViewersCount.textContent = formattedOnline;
    if (elements.footerOnlineCount) elements.footerOnlineCount.textContent = formattedOnline;
  }
  if (totalDrafts !== undefined && totalDrafts !== null) {
    const formattedDrafts = Number(totalDrafts).toLocaleString('ru-RU');
    if (elements.totalDraftsCount) elements.totalDraftsCount.textContent = formattedDrafts;
    if (elements.footerDraftsCount) elements.footerDraftsCount.textContent = formattedDrafts;
  }
}

async function fetchSiteStats() {
  try {
    const res = await fetch('/api/stats', {
      headers: { 'X-Visitor-Id': getVisitorId() }
    });
    const data = await res.json();
    if (data.success) {
      updateStatsUI(data.onlineViewers, data.totalDrafts);
    }
  } catch (err) {
    // Non-blocking
  }
}

// Init Application
document.addEventListener('DOMContentLoaded', async () => {
  renderSlots();
  renderBans();
  setupEventListeners();
  fetchSiteStats();
  await initAuth();
  await loadHeroes();
  await triggerUpdate();
  pollStatus();
  setInterval(fetchSiteStats, 10000);
});

// Setup Events
function setupEventListeners() {
  // Sliders
  if (elements.counterWeight) {
    elements.counterWeight.addEventListener('input', (e) => {
      state.weights.counter = parseInt(e.target.value, 10);
      if (elements.counterVal) elements.counterVal.textContent = `${state.weights.counter}%`;
      debouncedUpdate();
    });
  }

  if (elements.synergyWeight) {
    elements.synergyWeight.addEventListener('input', (e) => {
      state.weights.synergy = parseInt(e.target.value, 10);
      if (elements.synergyVal) elements.synergyVal.textContent = `${state.weights.synergy}%`;
      debouncedUpdate();
    });
  }

  if (elements.metaWeight) {
    elements.metaWeight.addEventListener('input', (e) => {
      state.weights.meta = parseInt(e.target.value, 10);
      if (elements.metaVal) elements.metaVal.textContent = `${state.weights.meta}%`;
      debouncedUpdate();
    });
  }

  // Off-meta toggle
  if (elements.offMetaToggle) {
    elements.offMetaToggle.addEventListener('change', (e) => {
      state.allowOffMeta = e.target.checked;
      showToast(state.allowOffMeta ? 'Офф-мета пики разрешены' : 'Только метовые герои');
      debouncedUpdate();
    });
  }

  // Role weights toggle (Core vs Support & Lane Priority)
  if (elements.roleWeightsToggle) {
    elements.roleWeightsToggle.addEventListener('change', (e) => {
      state.useRoleWeights = e.target.checked;
      showToast(state.useRoleWeights ? 'Ролевой вес врагов включен' : 'Равный вес всех врагов');
      debouncedUpdate();
    });
  }

  // Bracket select
  if (elements.bracketSelect) {
    elements.bracketSelect.addEventListener('change', (e) => {
      state.bracket = e.target.value;
      showToast(`Выбран ранг: ${elements.bracketSelect.options[elements.bracketSelect.selectedIndex].text}`);
      debouncedUpdate();
    });
  }

  // Reset Draft
  if (elements.resetDraftBtn) {
    elements.resetDraftBtn.addEventListener('click', () => {
      state.allies.forEach(s => s.id = null);
      state.enemies.forEach(s => s.id = null);
      state.bans = [];
      state.activeSlot = { team: 'allies', index: 0 };
      renderSlots();
      renderBans();
      if (elements.alliesWinBar) elements.alliesWinBar.style.width = '50%';
      if (elements.enemiesWinBar) elements.enemiesWinBar.style.width = '50%';
      if (elements.alliesAdvScore) elements.alliesAdvScore.textContent = '50.0% Наша';
      if (elements.enemiesAdvScore) elements.enemiesAdvScore.textContent = '50.0% Враг';
      if (elements.alliesSynergy) {
        elements.alliesSynergy.textContent = 'Синергия: 0.0%';
        elements.alliesSynergy.className = 'team-synergy-badge neutral';
      }
      if (elements.enemiesSynergy) {
        elements.enemiesSynergy.textContent = 'Синергия: 0.0%';
        elements.enemiesSynergy.className = 'team-synergy-badge neutral';
      }
      if (elements.draftInsight) {
        elements.draftInsight.textContent = 'Выберите героев врага или союзников для получения умных рекомендаций.';
      }
      debouncedUpdate();
      showToast('Драфт сброшен');
    });
  }

  // Clear Bans
  elements.clearBansBtn.addEventListener('click', () => {
    state.bans = [];
    renderBans();
    debouncedUpdate();
  });

  // Copy Draft to Clipboard for Discord
  if (elements.copyDraftBtn) {
    elements.copyDraftBtn.addEventListener('click', copyDraftToDiscord);
  }

  // Recommendations Hero Search
  if (elements.recsHeroSearchInput) {
    elements.recsHeroSearchInput.addEventListener('input', (e) => {
      state.recsSearchQuery = e.target.value.trim().toLowerCase();
      if (elements.clearRecsSearchBtn) {
        elements.clearRecsSearchBtn.style.display = state.recsSearchQuery ? 'block' : 'none';
      }
      renderCurrentRecommendations();
    });
  }

  if (elements.clearRecsSearchBtn) {
    elements.clearRecsSearchBtn.addEventListener('click', () => {
      elements.recsHeroSearchInput.value = '';
      state.recsSearchQuery = '';
      elements.clearRecsSearchBtn.style.display = 'none';
      elements.recsHeroSearchInput.focus();
      renderCurrentRecommendations();
    });
  }

  // View Mode Tabs
  elements.viewModeTabs.addEventListener('click', (e) => {
    const btn = e.target.closest('.tab-btn');
    if (!btn) return;
    const mode = btn.dataset.view;
    setViewMode(mode);
  });

  // Role Filters (List view)
  elements.roleFilterBar.addEventListener('click', (e) => {
    const pill = e.target.closest('.role-pill');
    if (!pill) return;
    elements.roleFilterBar.querySelectorAll('.role-pill').forEach(p => p.classList.remove('active'));
    pill.classList.add('active');
    state.currentRoleFilter = pill.dataset.role;
    loadDetailedRecs();
  });

  // Modal Events
  elements.closeModalBtn.addEventListener('click', closeModal);
  elements.modalBackdrop.addEventListener('click', closeModal);

  // Search input in modal
  elements.heroSearchInput.addEventListener('input', (e) => {
    state.searchQuery = e.target.value.trim().toLowerCase();
    elements.clearSearchBtn.style.display = state.searchQuery ? 'block' : 'none';
    filterAndRenderHeroesGrid();
  });

  // Pressing Enter picks the first available hero, Arrow keys navigate heroes
  elements.heroSearchInput.addEventListener('keydown', (e) => {
    const activeCells = Array.from(elements.heroesGrid.querySelectorAll('.hero-cell:not(.disabled-hero)'));
    if (e.key === 'ArrowDown' || e.key === 'ArrowRight') {
      e.preventDefault();
      if (!activeCells.length) return;
      let currentIndex = activeCells.findIndex(c => c.classList.contains('hero-cell-selected'));
      if (currentIndex === -1) currentIndex = 0;
      else currentIndex = (currentIndex + 1) % activeCells.length;
      activeCells.forEach((c, idx) => c.classList.toggle('hero-cell-selected', idx === currentIndex));
      activeCells[currentIndex]?.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') {
      e.preventDefault();
      if (!activeCells.length) return;
      let currentIndex = activeCells.findIndex(c => c.classList.contains('hero-cell-selected'));
      if (currentIndex === -1) currentIndex = 0;
      else currentIndex = (currentIndex - 1 + activeCells.length) % activeCells.length;
      activeCells.forEach((c, idx) => c.classList.toggle('hero-cell-selected', idx === currentIndex));
      activeCells[currentIndex]?.scrollIntoView({ block: 'nearest' });
      return;
    }
    if (e.key === 'Enter') {
      e.preventDefault();
      const selectedCell = elements.heroesGrid.querySelector('.hero-cell.hero-cell-selected:not(.disabled-hero)') ||
                           elements.heroesGrid.querySelector('.hero-cell:not(.disabled-hero)');
      if (selectedCell) {
        const heroId = parseInt(selectedCell.dataset.id, 10);
        if (heroId) {
          onHeroCellClick(heroId);
        }
      }
    }
  });

  elements.clearSearchBtn.addEventListener('click', () => {
    elements.heroSearchInput.value = '';
    state.searchQuery = '';
    elements.clearSearchBtn.style.display = 'none';
    elements.heroSearchInput.focus();
    filterAndRenderHeroesGrid();
  });

  // Attribute filters
  elements.attrFilterGroup.addEventListener('click', (e) => {
    const btn = e.target.closest('.attr-btn');
    if (!btn) return;
    elements.attrFilterGroup.querySelectorAll('.attr-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    state.selectedAttr = btn.dataset.attr;
    filterAndRenderHeroesGrid();
  });

  // User Auth & Cabinet Listeners
  if (elements.authOpenBtn) {
    elements.authOpenBtn.addEventListener('click', openAuthModal);
  }
  if (elements.userProfileBadge) {
    elements.userProfileBadge.addEventListener('click', openProfileModal);
  }
  if (elements.closeAuthModalBtn) {
    elements.closeAuthModalBtn.addEventListener('click', closeAuthModal);
  }
  if (elements.authModalBackdrop) {
    elements.authModalBackdrop.addEventListener('click', closeAuthModal);
  }
  if (elements.closeProfileModalBtn) {
    elements.closeProfileModalBtn.addEventListener('click', closeProfileModal);
  }
  if (elements.closeProfileBtn2) {
    elements.closeProfileBtn2.addEventListener('click', closeProfileModal);
  }
  if (elements.profileModalBackdrop) {
    elements.profileModalBackdrop.addEventListener('click', closeProfileModal);
  }
  if (elements.authTabLogin) {
    elements.authTabLogin.addEventListener('click', () => switchAuthTab('login'));
  }
  if (elements.authTabRegister) {
    elements.authTabRegister.addEventListener('click', () => switchAuthTab('register'));
  }
  if (elements.loginForm) {
    elements.loginForm.addEventListener('submit', handleLogin);
  }
  if (elements.registerForm) {
    elements.registerForm.addEventListener('submit', handleRegister);
  }
  if (elements.toggleTokenVisibilityBtn) {
    elements.toggleTokenVisibilityBtn.addEventListener('click', toggleTokenVisibility);
  }
  if (elements.saveStratzTokenBtn) {
    elements.saveStratzTokenBtn.addEventListener('click', handleSaveToken);
  }
  if (elements.deleteStratzTokenBtn) {
    elements.deleteStratzTokenBtn.addEventListener('click', handleDeleteToken);
  }
  if (elements.syncUserTokenBtn) {
    elements.syncUserTokenBtn.addEventListener('click', handleSyncToken);
  }
  if (elements.logoutBtn) {
    elements.logoutBtn.addEventListener('click', handleLogout);
  }

  // Keyboard shortcut: Escape, Arrow navigation between slots, and Quick-type to open hero picker
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (elements.heroPickerModal && elements.heroPickerModal.style.display !== 'none') {
        closeModal();
      } else if (elements.authModal && elements.authModal.style.display !== 'none') {
        closeAuthModal();
      } else if (elements.profileModal && elements.profileModal.style.display !== 'none') {
        closeProfileModal();
      }
      return;
    }

    // Do not intercept if user is typing in an active input or textarea
    const activeEl = document.activeElement;
    const isInputActive = activeEl && (
      activeEl.tagName === 'INPUT' ||
      activeEl.tagName === 'TEXTAREA' ||
      activeEl.isContentEditable
    );
    if (isInputActive) {
      return;
    }

    // Ignore if modal like Auth or Profile is currently open
    if (elements.authModal && elements.authModal.style.display !== 'none') return;
    if (elements.profileModal && elements.profileModal.style.display !== 'none') return;

    // Ignore modifier combinations (Ctrl, Alt, Meta)
    if (e.ctrlKey || e.altKey || e.metaKey) {
      return;
    }

    // If hero picker is already open, do not re-open
    if (elements.heroPickerModal && elements.heroPickerModal.style.display !== 'none') {
      return;
    }

    // Arrow keys to navigate between slots when picker is closed
    if (['ArrowDown', 'ArrowUp', 'ArrowLeft', 'ArrowRight'].includes(e.key)) {
      if (state.activeSlot) {
        e.preventDefault();
        let { team, index } = state.activeSlot;
        if (e.key === 'ArrowDown') {
          index = (index + 1) % 5;
        } else if (e.key === 'ArrowUp') {
          index = (index - 1 + 5) % 5;
        } else if (e.key === 'ArrowRight' && team === 'allies') {
          team = 'enemies';
        } else if (e.key === 'ArrowLeft' && team === 'enemies') {
          team = 'allies';
        }
        focusSlot(team, index);
        return;
      }
    }

    // Enter key when a slot is focused: open hero picker
    if (e.key === 'Enter') {
      if (state.activeSlot) {
        e.preventDefault();
        openModalForSlot(state.activeSlot.team, state.activeSlot.index);
        return;
      }
    }

    // Backspace / Delete: clear focused slot
    if (e.key === 'Delete' || e.key === 'Backspace') {
      if (state.activeSlot) {
        const slot = state.activeSlot.team === 'allies' ? state.allies[state.activeSlot.index] : state.enemies[state.activeSlot.index];
        if (slot && slot.id) {
          e.preventDefault();
          clearSlot(e, state.activeSlot.team, state.activeSlot.index);
          return;
        }
      }
    }

    // If typing any printable character (Russian, English, numbers) and a slot is focused:
    if (e.key && e.key.length === 1 && !e.key.match(/[\x00-\x1F]/)) {
      if (state.activeSlot && state.activeSlot.team !== undefined && state.activeSlot.index !== undefined) {
        e.preventDefault();
        openModalForSlot(state.activeSlot.team, state.activeSlot.index, e.key);
      }
    }
  });

  window.addEventListener('resize', () => {
    if (elements.heroPickerModal && elements.heroPickerModal.style.display !== 'none' && state.activeSlot) {
      positionPopoverForSlot(state.activeSlot.team, state.activeSlot.index);
    }
  });

  window.addEventListener('scroll', () => {
    if (elements.heroPickerModal && elements.heroPickerModal.style.display !== 'none' && state.activeSlot) {
      positionPopoverForSlot(state.activeSlot.team, state.activeSlot.index);
    }
  }, { passive: true });
}

// Set View Mode
function setViewMode(mode) {
  state.viewMode = mode;
  elements.viewModeTabs.querySelectorAll('.tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.view === mode);
  });

  if (mode === 'matrix') {
    elements.teamMatrixContainer.style.display = 'grid';
    elements.recsListContainer.style.display = 'none';
    elements.roleFilterBar.style.display = 'none';
  } else {
    elements.teamMatrixContainer.style.display = 'none';
    elements.recsListContainer.style.display = 'flex';
    elements.roleFilterBar.style.display = 'flex';
    loadDetailedRecs();
  }
}

// Load Heroes Constant Data
async function loadHeroes() {
  try {
    const res = await fetch('/api/heroes');
    const data = await res.json();
    if (data.success && data.heroes) {
      state.heroes = data.heroes;
      state.heroesMap = {};
      data.heroes.forEach(h => {
        state.heroesMap[h.id] = h;
      });
      filterAndRenderHeroesGrid();
    }
  } catch (err) {
    console.error('Failed to load heroes:', err);
    showToast('Ошибка загрузки базы героев', true);
  }
}

// Render Team Slots
function renderSlots() {
  // Allies
  elements.alliesSlots.innerHTML = state.allies.map((slot, i) => {
    const hero = slot.id ? state.heroesMap[slot.id] : null;
    const isActive = state.activeSlot && state.activeSlot.team === 'allies' && state.activeSlot.index === i;
    return `
      <div class="draft-slot ${hero ? 'filled' : ''} ${isActive ? 'active-slot' : ''}" data-team="allies" data-index="${i}" title="${isActive ? 'Текущая выбранная позиция' : 'Кликните сбоку для фокуса на эту позицию'}">
        <div class="slot-left">
          <div class="slot-portrait-wrapper" data-action="pick" title="${hero ? 'Нажмите, чтобы сменить героя' : 'Нажмите на плюс, чтобы выбрать героя'}">
            ${hero ? `<img class="slot-portrait-img" src="${hero.iconUrl}" alt="${hero.displayName}">` : `<span class="slot-empty-icon">+</span>`}
          </div>
          <div class="slot-info" title="Кликните сбоку для фокуса на эту позицию">
            <span class="slot-role-tag">${slot.roleLabel}</span>
            ${hero ? `<span class="slot-hero-name">${hero.displayName}</span>` : `<span class="slot-empty-text">Выбрать героя</span>`}
            ${slot.friend ? `<span class="slot-friend-name" title="Кликните чтобы изменить ник друга" onclick="editFriendName(event, ${i})">${slot.friend}</span>` : ''}
          </div>
        </div>
        ${hero ? `<button class="slot-remove-btn" onclick="clearSlot(event, 'allies', ${i})" title="Удалить">✕</button>` : ''}
      </div>
    `;
  }).join('');

  // Enemies
  elements.enemiesSlots.innerHTML = state.enemies.map((slot, i) => {
    const hero = slot.id ? state.heroesMap[slot.id] : null;
    const isActive = state.activeSlot && state.activeSlot.team === 'enemies' && state.activeSlot.index === i;
    return `
      <div class="draft-slot ${hero ? 'filled' : ''} ${isActive ? 'active-slot' : ''}" data-team="enemies" data-index="${i}" title="${isActive ? 'Текущая выбранная позиция' : 'Кликните сбоку для фокуса на эту позицию'}">
        <div class="slot-left">
          <div class="slot-portrait-wrapper" data-action="pick" title="${hero ? 'Нажмите, чтобы сменить героя' : 'Нажмите на плюс, чтобы выбрать героя'}">
            ${hero ? `<img class="slot-portrait-img" src="${hero.iconUrl}" alt="${hero.displayName}">` : `<span class="slot-empty-icon">+</span>`}
          </div>
          <div class="slot-info" title="Кликните сбоку для фокуса на эту позицию">
            <span class="slot-role-tag">${slot.label}</span>
            ${hero ? `<span class="slot-hero-name">${hero.displayName}</span>` : `<span class="slot-empty-text">Пик противника</span>`}
          </div>
        </div>
        ${hero ? `<button class="slot-remove-btn" onclick="clearSlot(event, 'enemies', ${i})" title="Удалить">✕</button>` : ''}
      </div>
    `;
  }).join('');

  // Update counts
  const alliesFilled = state.allies.filter(s => s.id !== null).length;
  const enemiesFilled = state.enemies.filter(s => s.id !== null).length;
  elements.alliesCount.textContent = `${alliesFilled} / 5`;
  elements.enemiesCount.textContent = `${enemiesFilled} / 5`;

  // Attach slot click listeners
  document.querySelectorAll('.draft-slot').forEach(el => {
    el.addEventListener('click', (e) => {
      if (e.target.closest('.slot-remove-btn') || e.target.closest('.slot-friend-name')) {
        return;
      }
      const team = el.dataset.team;
      const index = parseInt(el.dataset.index, 10);

      // If clicked specifically on the portrait / plus wrapper, open picker modal
      if (e.target.closest('.slot-portrait-wrapper')) {
        openModalForSlot(team, index);
      } else {
        // If clicked on the side (role, name, empty text, or slot background), set focus
        focusSlot(team, index);
      }
    });
  });

  updateMatrixColumnFocus();
}

// Edit friend nickname on slot
window.editFriendName = function (e, index) {
  e.stopPropagation();
  const current = state.allies[index].friend;
  const newName = prompt('Введите имя друга или роль для этого слота:', current);
  if (newName !== null && newName.trim() !== '') {
    state.allies[index].friend = newName.trim();
    renderSlots();
  }
};

// Focus a slot without opening the hero picker modal
function focusSlot(team, index) {
  state.activeSlot = { team, index };
  renderSlots();

  // If slot has a role, sync role filter for list view
  const slot = team === 'allies' ? state.allies[index] : state.enemies[index];
  if (team === 'allies' && slot && slot.role) {
    state.currentRoleFilter = slot.role;
    if (state.viewMode === 'list' && elements.roleFilterBar) {
      elements.roleFilterBar.querySelectorAll('.role-pill').forEach(p => {
        p.classList.toggle('active', p.dataset.role === slot.role);
      });
      loadDetailedRecs();
    }
  }

  updateMatrixColumnFocus();
}

// Select a slot (backwards compatibility / general selector)
function selectSlot(team, index, openPicker = false) {
  if (openPicker) {
    openModalForSlot(team, index);
  } else {
    focusSlot(team, index);
  }
}

// Clear single slot
window.clearSlot = function (e, team, index) {
  e.stopPropagation();
  if (team === 'allies') {
    state.allies[index].id = null;
  } else {
    state.enemies[index].id = null;
  }
  renderSlots();
  debouncedUpdate();
};

// Render Banned Heroes
function renderBans() {
  if (state.bans.length === 0) {
    elements.bansList.innerHTML = `<span class="no-bans-hint">Кликните правой кнопкой на героя в поиске чтобы забанить</span>`;
    elements.clearBansBtn.style.display = 'none';
    return;
  }

  elements.clearBansBtn.style.display = 'inline-block';
  elements.bansList.innerHTML = state.bans.map(id => {
    const hero = state.heroesMap[id];
    if (!hero) return '';
    return `
      <div class="banned-chip" title="${hero.displayName}">
        <img src="${hero.iconUrl}" alt="${hero.displayName}">
        <span>${hero.displayName}</span>
        <span class="banned-chip-remove" onclick="removeBan(event, ${id})">✕</span>
      </div>
    `;
  }).join('');
}

// Remove Ban
window.removeBan = function (e, heroId) {
  e.stopPropagation();
  state.bans = state.bans.filter(id => id !== heroId);
  renderBans();
  filterAndRenderHeroesGrid();
  debouncedUpdate();
};

// Position popover relative to focused slot
function positionPopoverForSlot(team, index) {
  const slotEl = document.querySelector(`.draft-slot[data-team="${team}"][data-index="${index}"]`);
  const popover = elements.heroPickerPopover || document.getElementById('heroPickerPopover');
  const arrow = elements.popoverArrow || document.getElementById('popoverArrow');
  if (!slotEl || !popover) return;

  const rect = slotEl.getBoundingClientRect();
  const popoverWidth = Math.min(380, window.innerWidth - 20);
  const popoverHeight = 360;
  const margin = 8;

  // Horizontal position
  let left;
  let arrowLeft;
  if (team === 'allies') {
    left = Math.max(margin, Math.min(rect.left, window.innerWidth - popoverWidth - margin));
    arrowLeft = Math.max(16, Math.min(rect.left + 40 - left, popoverWidth - 24));
  } else {
    left = Math.max(margin, Math.min(rect.right - popoverWidth, window.innerWidth - popoverWidth - margin));
    arrowLeft = Math.max(16, Math.min(rect.left + 40 - left, popoverWidth - 24));
  }

  // Vertical position (check if enough space below slot, else place above)
  const spaceBelow = window.innerHeight - rect.bottom;
  let top;
  let isTopArrow = true;

  if (spaceBelow >= popoverHeight + margin || rect.top < popoverHeight + margin) {
    // Open below slot
    top = rect.bottom + 8;
    isTopArrow = true;
  } else {
    // Open above slot
    top = Math.max(margin, rect.top - popoverHeight - 8);
    isTopArrow = false;
  }

  popover.style.top = `${top}px`;
  popover.style.left = `${left}px`;
  popover.style.width = `${popoverWidth}px`;
  popover.classList.toggle('arrow-top', isTopArrow);
  popover.classList.toggle('arrow-bottom', !isTopArrow);

  if (arrow) {
    arrow.style.left = `${arrowLeft}px`;
  }
}

// Open Hero Picker Modal / Popover
function openModalForSlot(team, index, initialQuery = '') {
  state.activeSlot = { team, index };
  renderSlots();
  const slotName = team === 'allies'
    ? (state.allies[index].friend ? `${state.allies[index].roleLabel} (${state.allies[index].friend})` : state.allies[index].roleLabel)
    : `Вражеский пик ${index + 1}`;
  elements.modalTargetTitle.textContent = `Выбор: ${slotName}`;
  elements.heroPickerModal.style.display = 'block';
  positionPopoverForSlot(team, index);
  elements.heroSearchInput.value = initialQuery;
  state.searchQuery = initialQuery.trim().toLowerCase();
  elements.clearSearchBtn.style.display = initialQuery ? 'block' : 'none';
  filterAndRenderHeroesGrid();
  setTimeout(() => {
    positionPopoverForSlot(team, index);
    elements.heroSearchInput.focus();
    if (initialQuery) {
      elements.heroSearchInput.setSelectionRange(initialQuery.length, initialQuery.length);
    }
  }, 30);
}

// Close Modal / Popover
function closeModal() {
  elements.heroPickerModal.style.display = 'none';
}

// Filter and Render Heroes Grid in Modal
function filterAndRenderHeroesGrid() {
  const pickedIds = new Set([
    ...state.allies.map(s => s.id).filter(Boolean),
    ...state.enemies.map(s => s.id).filter(Boolean),
    ...state.bans
  ]);

  const filtered = state.heroes.filter(h => {
    // Attribute filter
    if (state.selectedAttr !== 'all') {
      if (state.selectedAttr === 'all_attr') {
        if (h.attribute !== 'all') return false;
      } else if (h.attribute !== state.selectedAttr) {
        return false;
      }
    }

    // Search query filter (matches English, shortName, Russian aliases)
    if (state.searchQuery) {
      const q = state.searchQuery;
      const inDisplay = h.displayName.toLowerCase().includes(q);
      const inShort = h.shortName.toLowerCase().includes(q);
      const inAliases = (h.russianAliases || []).some(a => a.toLowerCase().includes(q));
      if (!inDisplay && !inShort && !inAliases) return false;
    }

    return true;
  });

  const firstAvailableIdx = filtered.findIndex(h => !pickedIds.has(h.id));

  elements.heroesGrid.innerHTML = filtered.map((h, idx) => {
    const isPicked = pickedIds.has(h.id);
    const isSelected = !isPicked && idx === firstAvailableIdx;
    return `
      <div class="hero-cell ${isPicked ? 'disabled-hero' : ''} ${isSelected ? 'hero-cell-selected' : ''}" 
           data-id="${h.id}" 
           onclick="onHeroCellClick(${h.id})" 
           oncontextmenu="onHeroCellRightClick(event, ${h.id})"
           title="${h.displayName} (${(h.russianAliases || []).slice(0, 3).join(', ')})">
        <img class="hero-cell-portrait" src="${h.iconUrl}" alt="${h.displayName}" loading="lazy">
        <span class="hero-cell-name">${h.displayName}</span>
      </div>
    `;
  }).join('');
}

// Hero cell left-click
window.onHeroCellClick = function (heroId) {
  // If hero is already picked or banned, ignore
  const pickedIds = new Set([
    ...state.allies.map(s => s.id).filter(Boolean),
    ...state.enemies.map(s => s.id).filter(Boolean),
    ...state.bans
  ]);
  if (pickedIds.has(heroId)) {
    showToast('Герой уже выбран или забанен', true);
    return;
  }

  if (state.activeSlot) {
    const { team, index } = state.activeSlot;
    if (team === 'allies') {
      state.allies[index].id = heroId;
      // Advance to next empty ally slot
      const nextAllyIdx = state.allies.findIndex(s => s.id === null);
      if (nextAllyIdx !== -1) {
        state.activeSlot = { team: 'allies', index: nextAllyIdx };
      }
    } else {
      state.enemies[index].id = heroId;
      // Advance to next empty enemy slot
      const nextEnemyIdx = state.enemies.findIndex(s => s.id === null);
      if (nextEnemyIdx !== -1) {
        state.activeSlot = { team: 'enemies', index: nextEnemyIdx };
      }
    }
  }

  closeModal();
  renderSlots();
  debouncedUpdate();
};

// Hero cell right-click (Ban hero)
window.onHeroCellRightClick = function (e, heroId) {
  e.preventDefault();
  if (state.bans.includes(heroId)) {
    state.bans = state.bans.filter(id => id !== heroId);
    showToast(`Бан снят: ${state.heroesMap[heroId]?.displayName}`);
  } else {
    // Unassign if currently in slot
    state.allies.forEach(s => { if (s.id === heroId) s.id = null; });
    state.enemies.forEach(s => { if (s.id === heroId) s.id = null; });
    state.bans.push(heroId);
    showToast(`Забанен: ${state.heroesMap[heroId]?.displayName}`);
  }
  renderSlots();
  renderBans();
  filterAndRenderHeroesGrid();
  debouncedUpdate();
};

// Pick hero directly from recommendations card
window.pickHeroForPosition = function (heroId, posKey) {
  const allySlotIdx = state.allies.findIndex(s => s.role === posKey);
  const targetIdx = allySlotIdx !== -1 ? allySlotIdx : state.allies.findIndex(s => s.id === null);

  if (targetIdx !== -1) {
    state.allies[targetIdx].id = heroId;
    renderSlots();
    debouncedUpdate();
    showToast(`Выбран ${state.heroesMap[heroId]?.displayName} для ${state.allies[targetIdx].roleLabel}!`);
  } else {
    showToast('Все союзные слоты уже заняты!', true);
  }
};

// Debounce updates to avoid excessive API calls
function debouncedUpdate() {
  if (state.fetchTimeout) clearTimeout(state.fetchTimeout);
  state.fetchTimeout = setTimeout(triggerUpdate, 200);
}

// Trigger Calculations and API updates
async function triggerUpdate() {
  const alliesIds = state.allies.map(s => s.id).filter(Boolean);
  const enemiesIds = state.enemies.map(s => s.id).filter(Boolean);
  const alliesRoles = state.allies.filter(s => s.id !== null).map(s => ({ id: s.id, role: s.role }));

  const enemyRoleKeys = ['pos1', 'pos2', 'pos3', 'pos4', 'pos5'];
  const enemiesRoles = state.enemies
    .map((s, idx) => ({ id: s.id, role: s.role || enemyRoleKeys[idx] }))
    .filter(s => s.id !== null);

  const payload = {
    allies: alliesIds,
    enemies: enemiesIds,
    alliesRoles: alliesRoles,
    enemiesRoles: enemiesRoles,
    bans: state.bans,
    weights: state.weights,
    allowOffMeta: state.allowOffMeta,
    useRoleWeights: state.useRoleWeights,
    bracket: state.bracket
  };

  // Fetch Team Matrix (all 5 roles)
  try {
    const res = await fetch('/api/team_matrix', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Visitor-Id': getVisitorId()
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.onlineViewers !== undefined || data.totalDrafts !== undefined) {
      updateStatsUI(data.onlineViewers, data.totalDrafts);
    }
    if (data.success && data.matrix) {
      state.matrixData = data.matrix;
      renderCurrentRecommendations();
      if (data.analysis) {
        updateDraftMeter(data.analysis);
      }
    }
  } catch (err) {
    console.error('Error fetching team matrix:', err);
  }

  // If in list view, also update detailed recommendations
  if (state.viewMode === 'list') {
    loadDetailedRecs();
  }
}

// Render recommendations according to current active view mode
function renderCurrentRecommendations() {
  if (state.viewMode === 'matrix') {
    renderTeamMatrix(state.matrixData);
  } else {
    renderDetailedRecs(state.recsListData);
  }
}

// Render Team Matrix View (5 Columns)
function renderTeamMatrix(matrix) {
  const roles = [
    { key: 'pos1', title: 'КЕРРИ' },
    { key: 'pos2', title: 'МИД' },
    { key: 'pos3', title: 'ТРОЙКА' },
    { key: 'pos4', title: '4 ПОЗ' },
    { key: 'pos5', title: 'САППОРТ' },
  ];

  elements.teamMatrixContainer.innerHTML = roles.map(r => {
    let recs = matrix[r.key] || [];

    // Filter by recommendations search query if entered
    if (state.recsSearchQuery) {
      const q = state.recsSearchQuery;
      recs = recs.filter(h => {
        const fullHero = state.heroesMap[h.id] || {};
        const inDisplay = h.displayName.toLowerCase().includes(q);
        const inShort = (h.shortName || '').toLowerCase().includes(q);
        const inAliases = (fullHero.russianAliases || []).some(a => a.toLowerCase().includes(q));
        return inDisplay || inShort || inAliases;
      });
    } else {
      recs = recs.slice(0, 6);
    }

    const countLabel = state.recsSearchQuery ? `Найдено: ${recs.length}` : `Топ ${recs.length}`;
    const isFocused = state.activeSlot &&
      state.activeSlot.team === 'allies' &&
      state.allies[state.activeSlot.index]?.role === r.key;

    return `
      <div class="matrix-column ${isFocused ? 'focused-pos' : ''}" data-role="${r.key}">
        <div class="matrix-col-header">
          <span class="matrix-col-title">${r.title}</span>
          <span class="matrix-col-count">${countLabel}</span>
        </div>
        <div class="matrix-cards-list">
          ${recs.length > 0 ? recs.map(h => renderMatrixHeroCard(h, r.key)).join('') : '<div style="padding: 24px 8px; text-align: center; color: var(--text-muted); font-size: 12px; font-style: italic;">Не найдено по запросу</div>'}
        </div>
      </div>
    `;
  }).join('');
}

// Synchronize matrix column highlight with active ally slot
function updateMatrixColumnFocus() {
  if (!elements.teamMatrixContainer) return;
  const activeRole = (state.activeSlot && state.activeSlot.team === 'allies')
    ? state.allies[state.activeSlot.index]?.role
    : null;
  elements.teamMatrixContainer.querySelectorAll('.matrix-column').forEach(col => {
    col.classList.toggle('focused-pos', col.dataset.role === activeRole);
  });
}

function renderMatrixHeroCard(h, posKey) {
  const scoreClass = h.totalScore > 1 ? 'badge-positive' : (h.totalScore < -1 ? 'badge-negative' : 'badge-neutral');
  const scoreSign = h.totalScore > 0 ? '+' : '';

  // Top counters against enemy: if a severe counter exists, show best and worst for full clarity
  let displayedChips = [];
  if (h.counterBreakdown && h.counterBreakdown.length > 0) {
    const bestCounter = h.counterBreakdown[0];
    const worstCounter = h.counterBreakdown[h.counterBreakdown.length - 1];
    if (worstCounter && worstCounter.advantage <= -2.0 && worstCounter.enemyId !== bestCounter.enemyId) {
      displayedChips = [bestCounter, worstCounter];
    } else {
      displayedChips = h.counterBreakdown.slice(0, 2);
    }
  }

  return `
    <div class="matrix-hero-card">
      <div class="matrix-card-top">
        <img class="matrix-card-portrait" src="${h.iconUrl}" alt="${h.displayName}" loading="lazy">
        <div class="matrix-card-hero-info">
          <span class="matrix-hero-name" title="${h.displayName}">${h.displayName}</span>
          <div style="display:flex; gap:6px; align-items:center;">
            <span class="matrix-score-badge ${scoreClass}">${scoreSign}${h.totalScore}%</span>
            ${h.isOffMeta ? `<span class="off-meta-tag" title="Офф-мета пик с мощным контр-потенциалом">Офф-мета</span>` : ''}
          </div>
        </div>
      </div>

      <div class="matrix-chips-row">
        ${displayedChips.length > 0 ? displayedChips.map(c => `
          <div class="mini-chip">
            <span class="mini-chip-counter">vs ${c.enemyName}</span>
            <strong style="color: ${c.advantage >= 0 ? '#6ee7b7' : '#ff99b0'}">${c.advantage >= 0 ? '+' : ''}${c.advantage}%</strong>
          </div>
        `).join('') : `
          <div class="mini-chip">
            <span class="mini-chip-wr">Винрейт в патче</span>
            <strong>${h.baseWinRate}%</strong>
          </div>
        `}
      </div>

      <button class="matrix-pick-btn" onclick="pickHeroForPosition(${h.id}, '${posKey}')">
        Выбрать в драфт
      </button>
    </div>
  `;
}

// Load Detailed Recommendations (List View)
async function loadDetailedRecs() {
  const alliesIds = state.allies.map(s => s.id).filter(Boolean);
  const enemiesIds = state.enemies.map(s => s.id).filter(Boolean);
  const alliesRoles = state.allies.filter(s => s.id !== null).map(s => ({ id: s.id, role: s.role }));

  const enemyRoleKeys = ['pos1', 'pos2', 'pos3', 'pos4', 'pos5'];
  const enemiesRoles = state.enemies
    .map((s, idx) => ({ id: s.id, role: s.role || enemyRoleKeys[idx] }))
    .filter(s => s.id !== null);

  const payload = {
    allies: alliesIds,
    enemies: enemiesIds,
    alliesRoles: alliesRoles,
    enemiesRoles: enemiesRoles,
    bans: state.bans,
    weights: state.weights,
    role: state.currentRoleFilter,
    allowOffMeta: state.allowOffMeta,
    useRoleWeights: state.useRoleWeights,
    bracket: state.bracket
  };

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Visitor-Id': getVisitorId()
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.onlineViewers !== undefined || data.totalDrafts !== undefined) {
      updateStatsUI(data.onlineViewers, data.totalDrafts);
    }
    if (data.success && data.recommendations) {
      state.recsListData = data.recommendations;
      renderDetailedRecs(data.recommendations);
      if (data.analysis) {
        updateDraftMeter(data.analysis);
      }
    }
  } catch (err) {
    console.error('Error fetching recommendations:', err);
  }
}

// Render Detailed Recommendations List
function renderDetailedRecs(recs) {
  let list = recs || [];

  // Filter by recommendations search query if entered
  if (state.recsSearchQuery) {
    const q = state.recsSearchQuery;
    list = list.filter(h => {
      const fullHero = state.heroesMap[h.id] || {};
      const inDisplay = h.displayName.toLowerCase().includes(q);
      const inShort = (h.shortName || '').toLowerCase().includes(q);
      const inAliases = (fullHero.russianAliases || []).some(a => a.toLowerCase().includes(q));
      return inDisplay || inShort || inAliases;
    });
  }

  if (list.length === 0) {
    elements.recsListContainer.innerHTML = `<div style="text-align:center; padding: 40px; color: var(--text-muted);">Нет подходящих героев по заданным фильтрам</div>`;
    return;
  }

  elements.recsListContainer.innerHTML = list.map(h => {
    const scoreClass = h.totalScore > 1 ? 'badge-positive' : (h.totalScore < -1 ? 'badge-negative' : 'badge-neutral');
    const scoreSign = h.totalScore > 0 ? '+' : '';

    // Lane score display and tooltip
    let laneDisplay = '—';
    let laneColor = 'var(--text-muted)';
    let laneTooltip = 'Герои на эту линию еще не выбраны';

    if (h.laneScore !== null && h.laneScore !== undefined) {
      const laneSign = h.laneScore > 0 ? '+' : '';
      laneDisplay = `${laneSign}${h.laneScore}%`;
      laneColor = h.laneScore > 0 ? '#6ee7b7' : (h.laneScore < 0 ? '#ff99b0' : 'var(--text-main)');

      const details = [];
      const laneName = h.laneBreakdown?.laneName || 'Линия';
      if (h.laneBreakdown?.opponents && h.laneBreakdown.opponents.length > 0) {
        const oppsStr = h.laneBreakdown.opponents
          .map(o => `vs ${o.enemyName}: ${o.advantage > 0 ? '+' : ''}${o.advantage}%`)
          .join(', ');
        details.push(oppsStr);
      }
      if (h.laneBreakdown?.partner) {
        const p = h.laneBreakdown.partner;
        details.push(`с ${p.allyName}: ${p.synergy > 0 ? '+' : ''}${p.synergy}%`);
      }
      if (details.length > 0) {
        laneTooltip = `${laneName}: ${details.join(' | ')}`;
      } else {
        laneTooltip = `${laneName}: ${laneDisplay}`;
      }
    }

    return `
      <div class="rec-detail-card">
        <img class="card-portrait-large" src="${h.iconUrl}" alt="${h.displayName}">

        <div class="card-hero-meta">
          <div class="card-hero-title-row">
            <h4 class="card-hero-name">${h.displayName}</h4>
            ${h.isOffMeta ? `<span class="off-meta-tag" title="Офф-мета: ${h.roleShare}% игр в этой роли, но отличный контрпик">ОФФ-МЕТА (${h.roleShare}%)</span>` : ''}
          </div>
          <div class="card-scores-row">
            <span class="score-item">Контр: <strong>${h.counterScore > 0 ? '+' : ''}${h.counterScore}%</strong></span>
            ${(h.worstAdvantage !== undefined && h.worstAdvantage <= -2.0) ? `<span class="score-item" style="color: #ff99b0;" title="Опасный контрпик врага (учитывается формулой)">Худший: <strong>${h.worstAdvantage}%</strong></span>` : ''}
            <span class="score-item">Синергия: <strong>${h.synergyScore > 0 ? '+' : ''}${h.synergyScore}%</strong></span>
            <span class="score-item" title="${laneTooltip}">Линия: <strong style="color: ${laneColor};">${laneDisplay}</strong></span>
            <span class="score-item">Винрейт: <strong>${h.baseWinRate}%</strong> (${h.posMatches?.toLocaleString() || 0} матчей)</span>
          </div>
        </div>

        <div class="card-chips-column">
          <!-- Counters breakdown -->
          ${h.counterBreakdown && h.counterBreakdown.length > 0 ? `
            <div class="card-chips-row">
              ${h.counterBreakdown.map(c => `
                <span class="matchup-chip ${c.advantage >= 0 ? 'chip-counter-good' : 'chip-counter-bad'}">
                  vs ${c.enemyName}: ${c.advantage >= 0 ? '+' : ''}${c.advantage}% (${c.winRate}% WR)
                </span>
              `).join('')}
            </div>
          ` : '<span style="font-size:12px; color:var(--text-muted); font-style:italic;">Враги еще не выбраны</span>'}

          <!-- Synergies breakdown -->
          ${h.synergyBreakdown && h.synergyBreakdown.length > 0 ? `
            <div class="card-chips-row">
              ${h.synergyBreakdown.map(s => `
                <span class="matchup-chip chip-synergy">
                  с ${s.allyName}: ${s.synergy >= 0 ? '+' : ''}${s.synergy}%
                </span>
              `).join('')}
            </div>
          ` : ''}
        </div>

        <div class="card-action-column">
          <div class="card-total-badge ${scoreClass}">${scoreSign}${h.totalScore}%</div>
          <button class="btn-pick-hero" onclick="onHeroCellClick(${h.id})">
            Выбрать
          </button>
        </div>
      </div>
    `;
  }).join('');
}

// Update Draft Win Meter from analytical model
function updateDraftMeter(analysis) {
  const alliesFilled = state.allies.filter(s => s.id !== null);
  const enemiesFilled = state.enemies.filter(s => s.id !== null);

  const updateSynergyBadges = (alliesSynVal, enemiesSynVal) => {
    if (elements.alliesSynergy) {
      const val = Number(alliesSynVal ?? 0);
      const sign = val > 0 ? '+' : '';
      elements.alliesSynergy.textContent = `Синергия: ${sign}${val.toFixed(1)}%`;
      elements.alliesSynergy.className = 'team-synergy-badge ' + (val > 0.05 ? 'positive' : val < -0.05 ? 'negative' : 'neutral');
    }
    if (elements.enemiesSynergy) {
      const val = Number(enemiesSynVal ?? 0);
      const sign = val > 0 ? '+' : '';
      elements.enemiesSynergy.textContent = `Синергия: ${sign}${val.toFixed(1)}%`;
      elements.enemiesSynergy.className = 'team-synergy-badge ' + (val > 0.05 ? 'positive' : val < -0.05 ? 'negative' : 'neutral');
    }
  };

  if (enemiesFilled.length === 0 && alliesFilled.length === 0) {
    elements.alliesWinBar.style.width = '50%';
    elements.enemiesWinBar.style.width = '50%';
    elements.alliesAdvScore.textContent = '50.0% Наша';
    elements.enemiesAdvScore.textContent = '50.0% Враг';
    elements.draftInsight.textContent = 'Выберите героев врага или союзников для получения умных рекомендаций.';
    updateSynergyBadges(0, 0);
    return;
  }

  if (!analysis) return;

  updateSynergyBadges(analysis.alliesSynergy, analysis.enemiesSynergy);

  const alliesPercent = Math.min(85.0, Math.max(15.0, Number(analysis.alliesWinRate ?? 50.0)));
  const enemiesPercent = 100.0 - alliesPercent;

  elements.alliesWinBar.style.width = `${alliesPercent.toFixed(1)}%`;
  elements.enemiesWinBar.style.width = `${enemiesPercent.toFixed(1)}%`;
  elements.alliesAdvScore.textContent = `${alliesPercent.toFixed(1)}% Наша`;
  elements.enemiesAdvScore.textContent = `${enemiesPercent.toFixed(1)}% Враг`;

  if (analysis.insight) {
    elements.draftInsight.textContent = analysis.insight;
  }
}

// Copy Draft Recommendations to Discord / Telegram Format
function copyDraftToDiscord() {
  const enemiesFilled = state.enemies.filter(s => s.id !== null).map(s => state.heroesMap[s.id]?.displayName);
  const alliesFilled = state.allies.filter(s => s.id !== null).map(s => `${state.heroesMap[s.id]?.displayName} (${s.roleLabel})`);

  let text = `**DOTA 2 DRAFT RECOMMENDATIONS (Stratz)**\n`;
  if (enemiesFilled.length > 0) {
    text += `**Враги:** ${enemiesFilled.join(', ')}\n`;
  }
  if (alliesFilled.length > 0) {
    text += `**Наши пики:** ${alliesFilled.join(', ')}\n`;
  }
  text += `**Настройки:** Контрпики 70% | Синергия 20% | Мета 10%\n\n`;

  const roles = [
    { key: 'pos1', name: 'ПОЗ 1 (КЕРРИ)' },
    { key: 'pos2', name: 'ПОЗ 2 (МИД)' },
    { key: 'pos3', name: 'ПОЗ 3 (ТРОЙКА)' },
    { key: 'pos4', name: 'ПОЗ 4 (4 ПОЗ)' },
    { key: 'pos5', name: 'ПОЗ 5 (САППОРТ ОПУЩЕННЫЙ)' },
  ];

  roles.forEach(r => {
    const picks = state.matrixData[r.key] || [];
    const topPicksStr = picks.slice(0, 3).map(h => {
      const sign = h.totalScore > 0 ? '+' : '';
      const offStr = h.isOffMeta ? ' *(Офф-мета)*' : '';
      return `${h.displayName} (${sign}${h.totalScore}%)${offStr}`;
    }).join(' • ');

    text += `[${r.name}] ${topPicksStr || 'Нет данных'}\n`;
  });

  navigator.clipboard.writeText(text).then(() => {
    showToast('Готовый драфт скопирован для Discord');
  }).catch(() => {
    showToast('Не удалось скопировать в буфер', true);
  });
}

let wasPreloading = false;

// Poll status of API, live visitors, draft count and Background Preloading
async function pollStatus() {
  try {
    const res = await fetch('/api/status', {
      headers: { 'X-Visitor-Id': getVisitorId() }
    });
    const data = await res.json();

    if (data.onlineViewers !== undefined || data.totalDrafts !== undefined) {
      updateStatsUI(data.onlineViewers, data.totalDrafts);
    }

    if (data.isPreloading) {
      wasPreloading = true;
      elements.statusText.textContent = `Синхронизация: ${data.preloadProgress}%`;
      setTimeout(pollStatus, 1500);
    } else {
      if (wasPreloading) {
        wasPreloading = false;
        showToast(`Синхронизация завершена! Все ${data.cachedMatchupsCount} героев успешно обновлены.`);
        triggerUpdate();
      }

      if (data.authMode === 'personal_token') {
        elements.statusText.textContent = `Stratz API: Мой токен (${data.cachedMatchupsCount} героев)`;
        if (elements.statusBadge) elements.statusBadge.title = 'Авторизован: используется персональный токен Stratz API';
      } else if (data.authMode === 'server_token' || data.hasToken) {
        elements.statusText.textContent = `Stratz API: Онлайн (${data.cachedMatchupsCount} героев)`;
        if (elements.statusBadge) elements.statusBadge.title = 'Stratz API подключен. База данных актуальна.';
      } else {
        elements.statusText.textContent = `База актуальна (${data.cachedMatchupsCount} героев)`;
        if (elements.statusBadge) elements.statusBadge.title = 'Локальный кэш: 127 героев загружено. Запросы к API не расходуются.';
      }

      setTimeout(pollStatus, 10000);
    }
  } catch (err) {
    elements.statusText.textContent = 'Stratz API: Готово';
    setTimeout(pollStatus, 10000);
  }
}

// Show Toast
function showToast(msg, isError = false) {
  elements.toast.textContent = msg;
  elements.toast.style.borderColor = isError ? 'var(--dire-red)' : 'var(--gold-accent)';
  elements.toast.classList.add('show');
  setTimeout(() => {
    elements.toast.classList.remove('show');
  }, 2500);
}

// ==========================================
// USER AUTHENTICATION & STRATZ TOKEN CABINET
// ==========================================

async function initAuth() {
  try {
    const res = await fetch('/api/auth/me');
    const data = await res.json();
    if (data.authenticated && data.user) {
      state.user = data.user;
    } else {
      state.user = null;
    }
    updateUserUI();
  } catch (err) {
    console.error('Failed to init auth:', err);
    state.user = null;
    updateUserUI();
  }
}

function updateUserUI() {
  if (state.user) {
    if (elements.authOpenBtn) elements.authOpenBtn.style.display = 'none';
    if (elements.userProfileBadge) {
      elements.userProfileBadge.style.display = 'flex';
      const displayName = state.user.name || state.user.email.split('@')[0];
      if (elements.userNameDisplay) elements.userNameDisplay.textContent = displayName;

      if (state.user.avatarUrl && elements.userAvatarImg) {
        elements.userAvatarImg.src = state.user.avatarUrl;
        elements.userAvatarImg.style.display = 'block';
        if (elements.userAvatarFallback) elements.userAvatarFallback.style.display = 'none';
      } else {
        if (elements.userAvatarImg) elements.userAvatarImg.style.display = 'none';
        if (elements.userAvatarFallback) {
          elements.userAvatarFallback.textContent = (displayName[0] || 'U').toUpperCase();
          elements.userAvatarFallback.style.display = 'inline-flex';
        }
      }

      if (elements.userTokenStatusDot) {
        if (state.user.hasStratzToken) {
          elements.userTokenStatusDot.className = 'user-token-dot active';
          elements.userTokenStatusDot.title = 'STRATZ API: Персональный токен активен';
        } else {
          elements.userTokenStatusDot.className = 'user-token-dot';
          elements.userTokenStatusDot.title = 'Оффлайн-кэш: токен не указан';
        }
      }
    }
  } else {
    if (elements.authOpenBtn) elements.authOpenBtn.style.display = 'inline-flex';
    if (elements.userProfileBadge) elements.userProfileBadge.style.display = 'none';
  }
}

function openAuthModal() {
  switchAuthTab('login');
  if (elements.loginErrorMsg) elements.loginErrorMsg.style.display = 'none';
  if (elements.registerErrorMsg) elements.registerErrorMsg.style.display = 'none';
  if (elements.authModal) elements.authModal.style.display = 'flex';
  setTimeout(() => elements.loginEmail?.focus(), 50);
}

function closeAuthModal() {
  if (elements.authModal) elements.authModal.style.display = 'none';
}

function switchAuthTab(tab) {
  state.activeAuthTab = tab;
  if (tab === 'login') {
    elements.authTabLogin?.classList.add('active');
    elements.authTabRegister?.classList.remove('active');
    if (elements.loginForm) elements.loginForm.style.display = 'flex';
    if (elements.registerForm) elements.registerForm.style.display = 'none';
    if (elements.authModalTitle) elements.authModalTitle.textContent = 'Вход в аккаунт';
  } else {
    elements.authTabLogin?.classList.remove('active');
    elements.authTabRegister?.classList.add('active');
    if (elements.loginForm) elements.loginForm.style.display = 'none';
    if (elements.registerForm) elements.registerForm.style.display = 'flex';
    if (elements.authModalTitle) elements.authModalTitle.textContent = 'Создание аккаунта';
  }
}

async function handleLogin(e) {
  e.preventDefault();
  const email = elements.loginEmail.value.trim();
  const password = elements.loginPassword.value;
  elements.loginErrorMsg.style.display = 'none';
  elements.loginSubmitBtn.disabled = true;
  elements.loginSubmitBtn.textContent = 'Вход...';

  try {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json();
    if (data.success && data.user) {
      state.user = data.user;
      updateUserUI();
      closeAuthModal();
      showToast(`Добро пожаловать, ${data.user.name || 'друг'}!`);
      pollStatus();
    } else {
      elements.loginErrorMsg.textContent = data.message || 'Ошибка авторизации';
      elements.loginErrorMsg.style.display = 'block';
    }
  } catch (err) {
    elements.loginErrorMsg.textContent = 'Ошибка соединения с сервером';
    elements.loginErrorMsg.style.display = 'block';
  } finally {
    elements.loginSubmitBtn.disabled = false;
    elements.loginSubmitBtn.textContent = 'Войти';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const name = elements.regName.value.trim();
  const email = elements.regEmail.value.trim();
  const password = elements.regPassword.value;
  elements.registerErrorMsg.style.display = 'none';
  elements.registerSubmitBtn.disabled = true;
  elements.registerSubmitBtn.textContent = 'Регистрация...';

  try {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, email, password }),
    });
    const data = await res.json();
    if (data.success && data.user) {
      state.user = data.user;
      updateUserUI();
      closeAuthModal();
      showToast('Аккаунт создан! Добавьте ваш токен STRATZ API в кабинете.');
      pollStatus();
      openProfileModal();
    } else {
      elements.registerErrorMsg.textContent = data.message || 'Ошибка регистрации';
      elements.registerErrorMsg.style.display = 'block';
    }
  } catch (err) {
    elements.registerErrorMsg.textContent = 'Ошибка соединения с сервером';
    elements.registerErrorMsg.style.display = 'block';
  } finally {
    elements.registerSubmitBtn.disabled = false;
    elements.registerSubmitBtn.textContent = 'Зарегистрироваться';
  }
}

function openProfileModal() {
  if (!state.user) return;
  const displayName = state.user.name || state.user.email.split('@')[0];
  if (elements.cabinetUserName) elements.cabinetUserName.textContent = displayName;
  if (elements.cabinetUserEmail) elements.cabinetUserEmail.textContent = state.user.email;

  if (state.user.avatarUrl && elements.cabinetAvatarImg) {
    elements.cabinetAvatarImg.src = state.user.avatarUrl;
    elements.cabinetAvatarImg.style.display = 'block';
    if (elements.cabinetAvatarFallback) elements.cabinetAvatarFallback.style.display = 'none';
  } else {
    if (elements.cabinetAvatarImg) elements.cabinetAvatarImg.style.display = 'none';
    if (elements.cabinetAvatarFallback) {
      elements.cabinetAvatarFallback.textContent = (displayName[0] || 'U').toUpperCase();
      elements.cabinetAvatarFallback.style.display = 'inline-flex';
    }
  }

  updateProfileTokenView();
  if (elements.profileModal) elements.profileModal.style.display = 'flex';
}

function closeProfileModal() {
  if (elements.profileModal) elements.profileModal.style.display = 'none';
}

function updateProfileTokenView() {
  if (!state.user) return;
  const hasToken = !!state.user.hasStratzToken;

  if (hasToken) {
    elements.cabinetStatusDot.className = 'cabinet-status-dot active';
    elements.cabinetStatusLabel.textContent = 'Режим: Персональный STRATZ API';
    elements.stratzTokenInput.value = '';
    elements.stratzTokenInput.placeholder = state.user.maskedToken ? `Текущий токен: ${state.user.maskedToken}` : 'Токен сохранен';
    elements.deleteStratzTokenBtn.style.display = 'inline-flex';

    elements.tokenStatusBanner.className = 'token-status-banner active';
    elements.tokenStatusBannerText.textContent = `Токен активен (${state.user.maskedToken || 'персональный'}). Live-запросы и обновление идут через ваш аккаунт.`;
  } else {
    elements.cabinetStatusDot.className = 'cabinet-status-dot';
    elements.cabinetStatusLabel.textContent = 'Режим: Оффлайн-кэш';
    elements.stratzTokenInput.value = '';
    elements.stratzTokenInput.placeholder = 'Вставьте ваш STRATZ Bearer токен...';
    elements.deleteStratzTokenBtn.style.display = 'none';

    elements.tokenStatusBanner.className = 'token-status-banner neutral';
    elements.tokenStatusBannerText.textContent = 'Токен не установлен. Приложение использует оффлайн-кэш и не расходует лимиты Stratz.';
  }
}

function toggleTokenVisibility() {
  const isPass = elements.stratzTokenInput.type === 'password';
  elements.stratzTokenInput.type = isPass ? 'text' : 'password';
  elements.toggleTokenVisibilityBtn.textContent = isPass ? '🔒' : '👁';
}

async function handleSaveToken() {
  const token = elements.stratzTokenInput.value.trim();
  if (!token) {
    if (state.user && state.user.hasStratzToken) {
      showToast('Токен уже сохранен. Введите новый токен для замены.', true);
    } else {
      showToast('Пожалуйста, вставьте ваш STRATZ Bearer токен', true);
    }
    return;
  }

  elements.saveStratzTokenBtn.disabled = true;
  elements.saveStratzTokenBtn.textContent = 'Проверка токена...';
  elements.tokenStatusBannerText.textContent = 'Проверка токена через Stratz GraphQL API...';
  elements.tokenStatusBanner.className = 'token-status-banner neutral';

  try {
    const res = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    const data = await res.json();
    if (data.success) {
      if (data.user) state.user = data.user;
      state.user.hasStratzToken = true;
      state.user.maskedToken = (data.user && data.user.maskedToken) || data.maskedToken;
      updateUserUI();
      updateProfileTokenView();
      showToast('Токен STRATZ API успешно проверен и сохранен!');
      pollStatus();
    } else {
      elements.tokenStatusBanner.className = 'token-status-banner error';
      elements.tokenStatusBannerText.textContent = data.message || 'Ошибка валидации токена';
      showToast(data.message || 'Недействительный токен STRATZ API', true);
    }
  } catch (err) {
    elements.tokenStatusBanner.className = 'token-status-banner error';
    elements.tokenStatusBannerText.textContent = 'Ошибка связи с сервером при валидации';
    showToast('Ошибка при отправке токена', true);
  } finally {
    elements.saveStratzTokenBtn.disabled = false;
    elements.saveStratzTokenBtn.textContent = 'Проверить и сохранить токен';
  }
}

async function handleDeleteToken() {
  if (!confirm('Вы уверены, что хотите удалить свой STRATZ токен? Драфтер вернется в режим оффлайн-кэша.')) {
    return;
  }

  try {
    const res = await fetch('/api/auth/token', { method: 'DELETE' });
    const data = await res.json();
    if (data.success) {
      state.user.hasStratzToken = false;
      state.user.maskedToken = '';
      updateUserUI();
      updateProfileTokenView();
      showToast('Токен удален. Включен оффлайн-кэш.');
      pollStatus();
    }
  } catch (err) {
    showToast('Ошибка при удалении токена', true);
  }
}

async function handleSyncToken() {
  if (!state.user || !state.user.hasStratzToken) {
    showToast('Сначала введите и сохраните свой STRATZ API токен!', true);
    return;
  }

  elements.syncUserTokenBtn.disabled = true;
  elements.syncUserTokenBtn.textContent = 'Синхронизация...';

  try {
    const res = await fetch('/api/preload', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bracket: state.bracket || 'LOW_RANK', force: true }),
    });
    const data = await res.json();
    if (res.ok && data.success) {
      showToast(data.message || 'Синхронизация запущена через ваш токен API!');
      pollStatus();
    } else {
      showToast(data.message || 'Не удалось запустить синхронизацию', true);
    }
  } catch (err) {
    console.error('Preload sync error:', err);
    showToast('Ошибка запуска синхронизации', true);
  } finally {
    setTimeout(() => {
      elements.syncUserTokenBtn.disabled = false;
      elements.syncUserTokenBtn.textContent = 'Обновить базу через мой API';
    }, 2000);
  }
}

async function handleLogout() {
  try {
    await fetch('/api/auth/logout', { method: 'POST' });
    state.user = null;
    updateUserUI();
    closeProfileModal();
    showToast('Вы вышли из системы. Включен анонимный оффлайн-режим.');
    pollStatus();
  } catch (err) {
    showToast('Ошибка выхода из аккаунта', true);
  }
}

