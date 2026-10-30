window.SHOOTER_GAME_CONFIG = {
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
