/**
 * STRATZ CUSTOM DRAFTER - CLIENT APPLICATION
 * Dota 2 counter-pick & team draft advisor with off-meta flexibility
 */

// Application State
const state = {
  allies: [
    { id: null, role: 'pos1', roleLabel: 'Позиция 1 (Керри)', friend: 'Поз 1 (Керри)' },
    { id: null, role: 'pos2', roleLabel: 'Позиция 2 (Мид)', friend: 'Поз 2 (Мид)' },
    { id: null, role: 'pos3', roleLabel: 'Позиция 3 (Тройка)', friend: 'Поз 3 (Оффлейн)' },
    { id: null, role: 'pos4', roleLabel: 'Позиция 4 (Четверка)', friend: 'Поз 4 (Семи-сап)' },
    { id: null, role: 'pos5', roleLabel: 'Позиция 5 (Пятерка)', friend: 'Поз 5 (Фулл-сап)' },
  ],
  enemies: [
    { id: null, label: 'Враг 1' },
    { id: null, label: 'Враг 2' },
    { id: null, label: 'Враг 3' },
    { id: null, label: 'Враг 4' },
    { id: null, label: 'Враг 5' },
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
  draftInsight: document.getElementById('draftInsight'),
  activeSlotName: document.getElementById('activeSlotName'),
  bansList: document.getElementById('bansList'),
  clearBansBtn: document.getElementById('clearBansBtn'),
  teamMatrixContainer: document.getElementById('teamMatrixContainer'),
  recsListContainer: document.getElementById('recsListContainer'),
  roleFilterBar: document.getElementById('roleFilterBar'),
  viewModeTabs: document.getElementById('viewModeTabs'),
  recsHeroSearchInput: document.getElementById('recsHeroSearchInput'),
  clearRecsSearchBtn: document.getElementById('clearRecsSearchBtn'),
  heroPickerModal: document.getElementById('heroPickerModal'),
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
};

// Init Application
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  renderSlots();
  renderBans();
  await loadHeroes();
  await triggerUpdate();
  pollStatus();
});

// Setup Events
function setupEventListeners() {
  // Sliders
  elements.counterWeight.addEventListener('input', (e) => {
    state.weights.counter = parseInt(e.target.value, 10);
    elements.counterVal.textContent = `${state.weights.counter}%`;
    debouncedUpdate();
  });

  elements.synergyWeight.addEventListener('input', (e) => {
    state.weights.synergy = parseInt(e.target.value, 10);
    elements.synergyVal.textContent = `${state.weights.synergy}%`;
    debouncedUpdate();
  });

  elements.metaWeight.addEventListener('input', (e) => {
    state.weights.meta = parseInt(e.target.value, 10);
    elements.metaVal.textContent = `${state.weights.meta}%`;
    debouncedUpdate();
  });

  // Off-meta toggle
  elements.offMetaToggle.addEventListener('change', (e) => {
    state.allowOffMeta = e.target.checked;
    showToast(state.allowOffMeta ? 'Офф-мета пики разрешены' : 'Только метовые герои');
    debouncedUpdate();
  });

  // Bracket select
  elements.bracketSelect.addEventListener('change', (e) => {
    state.bracket = e.target.value;
    showToast(`Выбран ранг: ${elements.bracketSelect.options[elements.bracketSelect.selectedIndex].text}`);
    debouncedUpdate();
  });

  // Reset Draft
  elements.resetDraftBtn.addEventListener('click', () => {
    state.allies.forEach(s => s.id = null);
    state.enemies.forEach(s => s.id = null);
    state.bans = [];
    state.activeSlot = { team: 'allies', index: 0 };
    renderSlots();
    renderBans();
    elements.alliesWinBar.style.width = '50%';
    elements.enemiesWinBar.style.width = '50%';
    elements.alliesAdvScore.textContent = '50.0% Наша';
    elements.enemiesAdvScore.textContent = '50.0% Враг';
    elements.draftInsight.textContent = 'Выберите героев врага или союзников для получения умных рекомендаций.';
    debouncedUpdate();
    showToast('Драфт сброшен');
  });

  // Clear Bans
  elements.clearBansBtn.addEventListener('click', () => {
    state.bans = [];
    renderBans();
    debouncedUpdate();
  });

  // Copy Draft to Clipboard for Discord
  elements.copyDraftBtn.addEventListener('click', copyDraftToDiscord);

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

  // Keyboard shortcut: Escape to close modal
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && elements.heroPickerModal.style.display !== 'none') {
      closeModal();
    }
  });
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
      <div class="draft-slot ${hero ? 'filled' : ''} ${isActive ? 'active-slot' : ''}" data-team="allies" data-index="${i}">
        <div class="slot-left">
          <div class="slot-portrait-wrapper">
            ${hero ? `<img class="slot-portrait-img" src="${hero.iconUrl}" alt="${hero.displayName}">` : `<span class="slot-empty-icon">+</span>`}
          </div>
          <div class="slot-info">
            <span class="slot-role-tag">${slot.roleLabel}</span>
            ${hero ? `<span class="slot-hero-name">${hero.displayName}</span>` : `<span class="slot-empty-text">Выбрать героя</span>`}
            <span class="slot-friend-name" title="Кликните чтобы изменить ник друга" onclick="editFriendName(event, ${i})">${slot.friend}</span>
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
      <div class="draft-slot ${hero ? 'filled' : ''} ${isActive ? 'active-slot' : ''}" data-team="enemies" data-index="${i}">
        <div class="slot-left">
          <div class="slot-portrait-wrapper">
            ${hero ? `<img class="slot-portrait-img" src="${hero.iconUrl}" alt="${hero.displayName}">` : `<span class="slot-empty-icon">+</span>`}
          </div>
          <div class="slot-info">
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
      if (e.target.classList.contains('slot-remove-btn') || e.target.classList.contains('slot-friend-name')) {
        return;
      }
      const team = el.dataset.team;
      const index = parseInt(el.dataset.index, 10);
      selectSlot(team, index);
    });
  });

  // Update active slot indicator
  updateActiveSlotIndicator();
}

// Edit friend nickname on slot
window.editFriendName = function(e, index) {
  e.stopPropagation();
  const current = state.allies[index].friend;
  const newName = prompt('Введите имя друга или роль для этого слота:', current);
  if (newName !== null && newName.trim() !== '') {
    state.allies[index].friend = newName.trim();
    renderSlots();
  }
};

// Select a slot
function selectSlot(team, index) {
  state.activeSlot = { team, index };
  renderSlots();

  // If slot is empty, open hero picker modal immediately
  const slot = team === 'allies' ? state.allies[index] : state.enemies[index];
  if (!slot.id) {
    openModalForSlot(team, index);
  } else {
    // If slot has a role, sync role filter for list view
    if (team === 'allies') {
      state.currentRoleFilter = slot.role;
      if (state.viewMode === 'list') {
        elements.roleFilterBar.querySelectorAll('.role-pill').forEach(p => {
          p.classList.toggle('active', p.dataset.role === slot.role);
        });
        loadDetailedRecs();
      }
    }
  }
}

// Update Active Slot Banner
function updateActiveSlotIndicator() {
  if (!elements.activeSlotName) return;
  if (!state.activeSlot) {
    elements.activeSlotName.textContent = 'Не выбран';
    return;
  }
  const { team, index } = state.activeSlot;
  if (team === 'allies') {
    const slot = state.allies[index];
    elements.activeSlotName.textContent = `${slot.roleLabel} (${slot.friend})`;
  } else {
    elements.activeSlotName.textContent = `Команда врага (Слот ${index + 1})`;
  }
}

// Clear single slot
window.clearSlot = function(e, team, index) {
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
window.removeBan = function(e, heroId) {
  e.stopPropagation();
  state.bans = state.bans.filter(id => id !== heroId);
  renderBans();
  filterAndRenderHeroesGrid();
  debouncedUpdate();
};

// Open Hero Picker Modal
function openModalForSlot(team, index) {
  state.activeSlot = { team, index };
  const slotName = team === 'allies' ? `${state.allies[index].roleLabel} (${state.allies[index].friend})` : `Вражеский пик ${index + 1}`;
  elements.modalTargetTitle.textContent = `Выбор героя для: ${slotName}`;
  elements.heroPickerModal.style.display = 'flex';
  elements.heroSearchInput.value = '';
  state.searchQuery = '';
  elements.clearSearchBtn.style.display = 'none';
  filterAndRenderHeroesGrid();
  setTimeout(() => elements.heroSearchInput.focus(), 50);
}

// Close Modal
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

  elements.heroesGrid.innerHTML = filtered.map(h => {
    const isPicked = pickedIds.has(h.id);
    return `
      <div class="hero-cell ${isPicked ? 'disabled-hero' : ''}" 
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
window.onHeroCellClick = function(heroId) {
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
window.onHeroCellRightClick = function(e, heroId) {
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
window.pickHeroForPosition = function(heroId, posKey) {
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

  const payload = {
    allies: alliesIds,
    enemies: enemiesIds,
    alliesRoles: alliesRoles,
    bans: state.bans,
    weights: state.weights,
    allowOffMeta: state.allowOffMeta,
    bracket: state.bracket
  };

  // Fetch Team Matrix (all 5 roles)
  try {
    const res = await fetch('/api/team_matrix', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
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
    { key: 'pos1', title: 'ПОЗ 1 • КЕРРИ', tag: '1' },
    { key: 'pos2', title: 'ПОЗ 2 • МИД', tag: '2' },
    { key: 'pos3', title: 'ПОЗ 3 • ОФФЛЕЙН', tag: '3' },
    { key: 'pos4', title: 'ПОЗ 4 • СЕМИ-САП', tag: '4' },
    { key: 'pos5', title: 'ПОЗ 5 • ФУЛЛ-САП', tag: '5' },
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

    return `
      <div class="matrix-column">
        <div class="matrix-col-header">
          <span class="matrix-col-title">[${r.tag}] ${r.title}</span>
          <span class="matrix-col-count">${countLabel}</span>
        </div>
        <div class="matrix-cards-list">
          ${recs.length > 0 ? recs.map(h => renderMatrixHeroCard(h, r.key)).join('') : '<div style="padding: 24px 8px; text-align: center; color: var(--text-muted); font-size: 12px; font-style: italic;">Не найдено по запросу</div>'}
        </div>
      </div>
    `;
  }).join('');
}

function renderMatrixHeroCard(h, posKey) {
  const scoreClass = h.totalScore > 1 ? 'badge-positive' : (h.totalScore < -1 ? 'badge-negative' : 'badge-neutral');
  const scoreSign = h.totalScore > 0 ? '+' : '';

  // Top 2 counters against enemy
  const topCounters = (h.counterBreakdown || []).slice(0, 2);

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
        ${topCounters.length > 0 ? topCounters.map(c => `
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

  const payload = {
    allies: alliesIds,
    enemies: enemiesIds,
    alliesRoles: alliesRoles,
    bans: state.bans,
    weights: state.weights,
    role: state.currentRoleFilter,
    allowOffMeta: state.allowOffMeta,
    bracket: state.bracket
  };

  try {
    const res = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
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
            <span class="score-item">Синергия: <strong>${h.synergyScore > 0 ? '+' : ''}${h.synergyScore}%</strong></span>
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

  if (enemiesFilled.length === 0 && alliesFilled.length === 0) {
    elements.alliesWinBar.style.width = '50%';
    elements.enemiesWinBar.style.width = '50%';
    elements.alliesAdvScore.textContent = '50.0% Наша';
    elements.enemiesAdvScore.textContent = '50.0% Враг';
    elements.draftInsight.textContent = 'Выберите героев врага или союзников для получения умных рекомендаций.';
    return;
  }

  if (!analysis) return;

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
    { key: 'pos3', name: 'ПОЗ 3 (ОФФЛЕЙН)' },
    { key: 'pos4', name: 'ПОЗ 4 (САППОРТ)' },
    { key: 'pos5', name: 'ПОЗ 5 (ФУЛЛ-САП)' },
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

// Poll status of API and Background Preloading
async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    if (data.isPreloading) {
      elements.statusText.textContent = `Кэширование: ${data.preloadProgress}%`;
      setTimeout(pollStatus, 2000);
    } else {
      elements.statusText.textContent = `Stratz API: Онлайн (${data.cachedMatchupsCount} героев)`;
    }
  } catch (err) {
    elements.statusText.textContent = 'Stratz API: Локальный режим';
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
