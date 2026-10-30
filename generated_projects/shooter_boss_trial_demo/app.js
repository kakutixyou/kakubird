const canvas = document.getElementById('gameCanvas');
const ctx = canvas.getContext('2d');

const hpText = document.getElementById('hpText');
const attackText = document.getElementById('attackText');
const livesText = document.getElementById('livesText');
const bossHpText = document.getElementById('bossHpText');
const shieldText = document.getElementById('shieldText');
const restartButton = document.getElementById('restartButton');

const FALLBACK_GAME_CONFIG = {
  projectName: 'shooter_boss_trial',
  dropIntervalMs: 3000,
  bossMaxHp: 200,
  playerLives: 2,
  playerBaseHp: 100,
  playerMaxHp: 100,
  playerBaseAttack: 10,
  playerFireRateMs: 180,
  bossDamage: 12,
  itemConfigs: {
    attack_plus_3: {
      id: 'attack_plus_3',
      name: '攻撃力UP',
      type: 'persistent',
      effect: 'attack +3',
      value: 3,
      durationMs: null,
    },
    damage_nullify_10s: {
      id: 'damage_nullify_10s',
      name: 'ダメージ無効化',
      type: 'temporary',
      effect: 'all_damage_nullified',
      value: 0,
      durationMs: 10000,
    },
  },
};

const GAME_CONFIG = window.SHOOTER_GAME_CONFIG || FALLBACK_GAME_CONFIG;
window.__shooterEvents = [];

function recordEvent(eventName, payload = {}) {
  const entry = {
    timestamp: Date.now(),
    event: eventName,
    ...payload,
  };
  window.__shooterEvents.push(entry);
  console.log('[ShooterEvent]', entry);
}

window.exportShooterLog = function exportShooterLog() {
  return JSON.stringify(window.__shooterEvents, null, 2);
};

const keys = {};
const bullets = [];
const enemies = [];
const enemyBullets = [];
const items = [];
const particles = [];

const player = {
  x: canvas.width / 2,
  y: canvas.height - 80,
  width: 26,
  height: 26,
  speed: 5,
  hp: GAME_CONFIG.playerBaseHp,
  maxHp: GAME_CONFIG.playerMaxHp,
  attack: GAME_CONFIG.playerBaseAttack,
  lives: GAME_CONFIG.playerLives,
  fireCooldown: 0,
  invulnerableUntil: 0,
  shieldUntil: 0,
};

const boss = {
  x: canvas.width / 2,
  y: 90,
  w: 180,
  h: 40,
  hp: GAME_CONFIG.bossMaxHp,
  maxHp: GAME_CONFIG.bossMaxHp,
  fireCooldown: 0,
};

let lastTime = 0;
let dropTimer = 0;
let running = true;
let message = '';

function resetGame() {
  window.__shooterEvents = [];
  player.x = canvas.width / 2;
  player.y = canvas.height - 80;
  player.hp = GAME_CONFIG.playerBaseHp;
  player.maxHp = GAME_CONFIG.playerMaxHp;
  player.attack = GAME_CONFIG.playerBaseAttack;
  player.lives = GAME_CONFIG.playerLives;
  player.invulnerableUntil = 0;
  player.shieldUntil = 0;
  player.fireCooldown = 0;
  boss.hp = GAME_CONFIG.bossMaxHp;
  boss.fireCooldown = 0;
  bullets.length = 0;
  enemies.length = 0;
  enemyBullets.length = 0;
  items.length = 0;
  particles.length = 0;
  dropTimer = 0;
  message = '';
  running = true;
  recordEvent('game_reset', {
    project_name: GAME_CONFIG.projectName,
    player_lives: player.lives,
    base_hp: player.hp,
    boss_hp: boss.hp,
    attack: player.attack,
  });
  updateHud();
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function createExplosion(x, y, color = '#fbbf24') {
  for (let i = 0; i < 14; i += 1) {
    particles.push({
      x,
      y,
      vx: (Math.random() - 0.5) * 6,
      vy: (Math.random() - 0.5) * 6,
      r: 2 + Math.random() * 3,
      color,
      life: 30 + Math.random() * 20,
    });
  }
}

function updateHud() {
  hpText.textContent = String(player.hp);
  attackText.textContent = String(player.attack);
  livesText.textContent = String(player.lives);
  bossHpText.textContent = String(Math.max(0, boss.hp));
  shieldText.textContent = performance.now() < player.shieldUntil ? 'ON' : 'OFF';
}

function spawnEnemy() {
  const side = Math.random() < 0.5 ? -1 : 1;
  enemies.push({
    x: Math.random() * (canvas.width - 40) + 20,
    y: -20,
    w: 24,
    h: 24,
    speed: 1.4 + Math.random() * 1.2,
    hp: 1,
    dir: side,
  });
}

function shootPlayerBullet() {
  const bullet = {
    x: player.x,
    y: player.y - 14,
    w: 5,
    h: 14,
    speed: 9,
    damage: player.attack,
    from: 'player',
  };
  bullets.push(bullet);
  recordEvent('player_shot', {
    x: bullet.x,
    y: bullet.y,
    damage: bullet.damage,
  });
}

function shootBossBullet() {
  const dirX = player.x - boss.x;
  const dirY = player.y - boss.y;
  const len = Math.hypot(dirX, dirY) || 1;
  const bullet = {
    x: boss.x,
    y: boss.y + boss.h,
    w: 8,
    h: 18,
    speed: 3.2,
    vx: (dirX / len) * 3.2,
    vy: (dirY / len) * 3.2,
    from: 'enemy',
  };
  enemyBullets.push(bullet);
  recordEvent('boss_shot', {
    x: bullet.x,
    y: bullet.y,
    target_x: player.x,
    target_y: player.y,
  });
}

function dropRandomItem(x, y) {
  const ids = Object.keys(GAME_CONFIG.itemConfigs);
  const itemId = ids[Math.floor(Math.random() * ids.length)];
  items.push({
    id: itemId,
    x,
    y,
    r: 11,
    speed: 2.2,
  });
  recordEvent('item_dropped', {
    item_id: itemId,
    x,
    y,
  });
}

function applyItem(item) {
  const itemConfig = GAME_CONFIG.itemConfigs[item.id];
  if (!itemConfig) return;

  if (itemConfig.id === 'attack_plus_3') {
    player.attack += itemConfig.value;
    recordEvent('attack_boost_applied', {
      item_id: item.id,
      attack_after: player.attack,
      attack_delta: itemConfig.value,
    });
  }

  if (itemConfig.id === 'damage_nullify_10s') {
    player.shieldUntil = performance.now() + (itemConfig.durationMs || 0);
    recordEvent('damage_nullify_started', {
      item_id: item.id,
      started_at: player.shieldUntil,
      duration_ms: itemConfig.durationMs,
    });
  }

  recordEvent('item_collected', {
    item_id: item.id,
    attack: player.attack,
    shield_until: player.shieldUntil,
  });
  updateHud();
}

function takeDamage(amount) {
  const now = performance.now();
  if (now < player.invulnerableUntil) return;
  if (now < player.shieldUntil) {
    createExplosion(player.x, player.y, '#7dd3fc');
    recordEvent('damage_blocked_by_shield', {
      amount,
      shield_remaining_ms: Math.max(0, player.shieldUntil - now),
    });
    return;
  }

  const prevHp = player.hp;
  player.hp -= amount;
  player.invulnerableUntil = now + 1000;
  recordEvent('damage_taken', {
    previous_hp: prevHp,
    damage: amount,
    current_hp: player.hp,
  });

  if (player.hp <= 0) {
    const prevLives = player.lives;
    player.lives -= 1;
    player.hp = player.maxHp;
    player.invulnerableUntil = now + 1500;
    recordEvent('life_lost', {
      previous_lives: prevLives,
      current_lives: player.lives,
      remaining_hp: player.hp,
    });
    if (player.lives <= 0) {
      running = false;
      message = 'ゲームオーバー';
      recordEvent('game_over', {
        reason: 'player_defeated',
        remaining_lives: player.lives,
      });
    }
  }
  updateHud();
}

function handleInput(dt) {
  if (!running) return;

  if (keys['ArrowLeft'] || keys['a']) player.x -= player.speed * dt;
  if (keys['ArrowRight'] || keys['d']) player.x += player.speed * dt;
  if (keys['ArrowUp'] || keys['w']) player.y -= player.speed * dt;
  if (keys['ArrowDown'] || keys['s']) player.y += player.speed * dt;

  player.x = clamp(player.x, player.width / 2, canvas.width - player.width / 2);
  player.y = clamp(player.y, 20, canvas.height - player.height / 2 - 10);

  if (keys[' '] && player.fireCooldown <= 0) {
    shootPlayerBullet();
    player.fireCooldown = GAME_CONFIG.playerFireRateMs;
  }

  player.fireCooldown = Math.max(0, player.fireCooldown - dt * 1000);
}

function updateBullets(dt) {
  for (let i = bullets.length - 1; i >= 0; i -= 1) {
    const bullet = bullets[i];
    bullet.y -= bullet.speed * dt * 60;

    if (bullet.y < -40) {
      bullets.splice(i, 1);
      continue;
    }

    if (bullet.y < boss.y + boss.h && bullet.y + bullet.h > boss.y &&
        bullet.x > boss.x - boss.w / 2 && bullet.x < boss.x + boss.w / 2) {
      const prevBossHp = boss.hp;
      boss.hp -= bullet.damage;
      bullets.splice(i, 1);
      createExplosion(bullet.x, bullet.y, '#f97316');
      recordEvent('boss_hp_changed', {
        previous_hp: prevBossHp,
        new_hp: boss.hp,
        damage: bullet.damage,
      });
      if (boss.hp <= 0) {
        boss.hp = 0;
        running = false;
        message = 'ボス撃破!';
        recordEvent('game_over', {
          reason: 'boss_defeated',
          boss_hp: boss.hp,
        });
      }
      updateHud();
    }
  }

  for (let i = enemyBullets.length - 1; i >= 0; i -= 1) {
    const bullet = enemyBullets[i];
    bullet.x += bullet.vx * dt * 60;
    bullet.y += bullet.vy * dt * 60;

    if (bullet.x < 0 || bullet.x > canvas.width || bullet.y > canvas.height) {
      enemyBullets.splice(i, 1);
      continue;
    }

    if (bullet.x > player.x - player.width / 2 && bullet.x < player.x + player.width / 2 &&
        bullet.y > player.y - player.height / 2 && bullet.y < player.y + player.height / 2) {
      enemyBullets.splice(i, 1);
      takeDamage(GAME_CONFIG.bossDamage);
    }
  }
}

function updateEnemies(dt) {
  for (let i = enemies.length - 1; i >= 0; i -= 1) {
    const enemy = enemies[i];
    enemy.y += enemy.speed * dt * 60;
    enemy.x += enemy.dir * (0.8 + Math.random() * 0.8) * dt * 60;

    if (enemy.y > canvas.height + 30) {
      enemies.splice(i, 1);
      continue;
    }

    if (enemy.x > player.x - player.width / 2 && enemy.x < player.x + player.width / 2 &&
        enemy.y > player.y - player.height / 2 && enemy.y < player.y + player.height / 2) {
      enemies.splice(i, 1);
      createExplosion(enemy.x, enemy.y, '#ef4444');
      takeDamage(20);
      continue;
    }

    if (Math.random() < 0.01) {
      enemyBullets.push({
        x: enemy.x,
        y: enemy.y + 20,
        w: 6,
        h: 12,
        speed: 4,
        vx: 0,
        vy: 4,
        from: 'enemy',
      });
    }
  }
}

function updateItems(dt) {
  for (let i = items.length - 1; i >= 0; i -= 1) {
    const item = items[i];
    item.y += item.speed * dt * 60;

    if (item.y > canvas.height + 30) {
      items.splice(i, 1);
      continue;
    }

    const dx = item.x - player.x;
    const dy = item.y - player.y;
    const dist = Math.hypot(dx, dy);
    if (dist < 24) {
      applyItem(item);
      items.splice(i, 1);
      continue;
    }
  }
}

function updateParticles(dt) {
  for (let i = particles.length - 1; i >= 0; i -= 1) {
    const p = particles[i];
    p.x += p.vx * dt * 60;
    p.y += p.vy * dt * 60;
    p.life -= dt * 60;
    if (p.life <= 0) particles.splice(i, 1);
  }
}

function updateBoss(dt) {
  boss.x += Math.sin(performance.now() / 600) * 1.8;
  boss.fireCooldown -= dt * 1000;
  if (boss.fireCooldown <= 0) {
    shootBossBullet();
    boss.fireCooldown = 1300 + Math.random() * 500;
  }
}

function update(dt) {
  if (!running) {
    updateParticles(dt);
    updateHud();
    return;
  }

  handleInput(dt);
  updateBullets(dt);
  updateEnemies(dt);
  updateItems(dt);
  updateBoss(dt);
  updateParticles(dt);

  dropTimer += dt * 1000;
  if (dropTimer > GAME_CONFIG.dropIntervalMs) {
    dropTimer = 0;
    dropRandomItem(Math.random() * (canvas.width - 60) + 30, 30);
  }

  if (Math.random() < 0.025) {
    spawnEnemy();
  }

  updateHud();
}

function drawPlayer() {
  ctx.fillStyle = '#60a5fa';
  ctx.fillRect(player.x - player.width / 2, player.y - player.height / 2, player.width, player.height);

  if (performance.now() < player.shieldUntil) {
    ctx.strokeStyle = '#7dd3fc';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(player.x, player.y, 22, 0, Math.PI * 2);
    ctx.stroke();
  }
}

function drawBoss() {
  ctx.fillStyle = '#f87171';
  ctx.fillRect(boss.x - boss.w / 2, boss.y, boss.w, boss.h);

  const hpRatio = boss.hp / boss.maxHp;
  ctx.fillStyle = '#111827';
  ctx.fillRect(boss.x - 100, boss.y + 50, 200, 8);
  ctx.fillStyle = '#facc15';
  ctx.fillRect(boss.x - 100, boss.y + 50, 200 * hpRatio, 8);
}

function drawBullets() {
  ctx.fillStyle = '#f8fafc';
  for (const bullet of bullets) {
    ctx.fillRect(bullet.x - bullet.w / 2, bullet.y - bullet.h / 2, bullet.w, bullet.h);
  }

  ctx.fillStyle = '#fb7185';
  for (const bullet of enemyBullets) {
    ctx.fillRect(bullet.x - bullet.w / 2, bullet.y - bullet.h / 2, bullet.w, bullet.h);
  }
}

function drawEnemies() {
  ctx.fillStyle = '#f59e0b';
  for (const enemy of enemies) {
    ctx.fillRect(enemy.x - enemy.w / 2, enemy.y - enemy.h / 2, enemy.w, enemy.h);
  }
}

function drawItems() {
  for (const item of items) {
    const itemColor = item.id === 'attack_plus_3' ? '#22c55e' : '#a78bfa';
    ctx.fillStyle = itemColor;
    ctx.beginPath();
    ctx.arc(item.x, item.y, item.r, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawParticles() {
  for (const p of particles) {
    ctx.fillStyle = p.color;
    ctx.globalAlpha = Math.max(0, p.life / 50);
    ctx.fillRect(p.x, p.y, p.r, p.r);
    ctx.globalAlpha = 1;
  }
}

function drawMessage() {
  if (!message) return;
  ctx.fillStyle = '#f8fafc';
  ctx.font = 'bold 32px sans-serif';
  ctx.textAlign = 'center';
  ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

function render() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  ctx.fillStyle = '#0b1120';
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  drawBoss();
  drawEnemies();
  drawItems();
  drawBullets();
  drawPlayer();
  drawParticles();
  drawMessage();
}

function gameLoop(timestamp) {
  const dt = Math.min(0.033, (timestamp - lastTime) / 1000 || 0.016);
  lastTime = timestamp;
  update(dt);
  render();
  requestAnimationFrame(gameLoop);
}

window.addEventListener('keydown', (event) => {
  keys[event.key] = true;
  if (event.key === ' ') {
    event.preventDefault();
  }
});

window.addEventListener('keyup', (event) => {
  keys[event.key] = false;
});

restartButton.addEventListener('click', () => {
  resetGame();
});

resetGame();
requestAnimationFrame(gameLoop);
