// src/data/db_sets/game_guild.js

export const gameGuildExamples = [
  {
    category: "ゲームギルドDB",
    title: "レベル50以上のプレイヤーを表示したい",
    description: "高レベルのプレイヤー一覧を取得します。",
    sql: `SELECT player_name, level, class_name
FROM players
WHERE level >= 50
ORDER BY level DESC;`
  },
  {
    category: "ゲームギルドDB",
    title: "ギルドごとの所属人数を表示したい",
    description: "各ギルドのメンバー数を集計します。",
    sql: `SELECT g.guild_name, COUNT(p.player_id) AS member_count
FROM guilds g
LEFT JOIN players p ON g.guild_id = p.guild_id
GROUP BY g.guild_id, g.guild_name
ORDER BY member_count DESC;`
  },
  {
    category: "ゲームギルドDB",
    title: "最も戦闘力が高いプレイヤーを表示したい",
    description: "combat_power が最大のプレイヤーを取得します。",
    sql: `SELECT player_name, combat_power
FROM players
ORDER BY combat_power DESC
LIMIT 1;`
  },
  {
    category: "ゲームギルドDB",
    title: "レイド参加回数が多いプレイヤーTOP5",
    description: "raid_logs を集計して参加回数上位を取得します。",
    sql: `SELECT p.player_name, COUNT(r.raid_log_id) AS raid_count
FROM players p
JOIN raid_logs r ON p.player_id = r.player_id
GROUP BY p.player_id, p.player_name
ORDER BY raid_count DESC
LIMIT 5;`
  },
  {
    category: "ゲームギルドDB",
    title: "職業ごとの平均レベルを表示したい",
    description: "class_name ごとに平均レベルを計算します。",
    sql: `SELECT class_name, AVG(level) AS avg_level
FROM players
GROUP BY class_name
ORDER BY avg_level DESC;`
  },
  {
    category: "ゲームギルドDB",
    title: "伝説装備を持っているプレイヤーを表示したい",
    description: "rarity = 'Legendary' の装備所有者を取得します。",
    sql: `SELECT DISTINCT p.player_name, i.item_name
FROM players p
JOIN inventory inv ON p.player_id = inv.player_id
JOIN items i ON inv.item_id = i.item_id
WHERE i.rarity = 'Legendary';`
  },
  {
    category: "ゲームギルドDB",
    title: "未所属のプレイヤーを表示したい",
    description: "guild_id が NULL のプレイヤーを取得します。",
    sql: `SELECT player_name, level
FROM players
WHERE guild_id IS NULL;`
  },
  {
    category: "ゲームギルドDB",
    title: "ギルドごとの総戦闘力を表示したい",
    description: "各ギルドの combat_power 合計を計算します。",
    sql: `SELECT g.guild_name,
       SUM(p.combat_power) AS total_power
FROM guilds g
JOIN players p ON g.guild_id = p.guild_id
GROUP BY g.guild_id, g.guild_name
ORDER BY total_power DESC;`
  },
  {
    category: "ゲームギルドDB",
    title: "一度もレイドに参加していないプレイヤー",
    description: "LEFT JOIN で raid_logs が存在しないプレイヤーを取得します。",
    sql: `SELECT p.player_name
FROM players p
LEFT JOIN raid_logs r ON p.player_id = r.player_id
WHERE r.raid_log_id IS NULL;`
  },
  {
    category: "ゲームギルドDB",
    title: "プレイヤーごとの装備アイテム数を表示したい",
    description: "inventory の件数を集計します。",
    sql: `SELECT p.player_name,
       COUNT(inv.inventory_id) AS item_count
FROM players p
LEFT JOIN inventory inv ON p.player_id = inv.player_id
GROUP BY p.player_id, p.player_name
ORDER BY item_count DESC;`
  },
  {
    category: "ゲームギルドDB",
    title: "平均戦闘力以上のプレイヤーを表示したい",
    description: "副問い合わせで平均 combat_power を利用します。",
    sql: `SELECT player_name, combat_power
FROM players
WHERE combat_power >= (
  SELECT AVG(combat_power)
  FROM players
)
ORDER BY combat_power DESC;`
  },
  {
    category: "ゲームギルドDB",
    title: "レア度ごとのアイテム数を表示したい",
    description: "items テーブルを rarity ごとに集計します。",
    sql: `SELECT rarity, COUNT(*) AS item_count
FROM items
GROUP BY rarity
ORDER BY item_count DESC;`
  }
];

const gameGuild = {
  id: "game_guild",
  name: "オンラインゲーム ギルド管理データベース",
  description:
    "プレイヤー、ギルド、アイテム、インベントリ、レイド参加履歴を扱うゲーム用DB。JOIN、集計、ランキング分析の学習に最適。",

  schema: [
    {
      table: "guilds",
      description: "ギルド情報",
      columns: [
        { name: "guild_id", type: "serial primary key", description: "ギルドID" },
        { name: "guild_name", type: "varchar(100) not null", description: "ギルド名" },
        { name: "server_name", type: "varchar(50)", description: "所属サーバー" },
        { name: "founded_date", type: "date", description: "設立日" }
      ]
    },
    {
      table: "players",
      description: "プレイヤー情報",
      columns: [
        { name: "player_id", type: "serial primary key", description: "プレイヤーID" },
        { name: "player_name", type: "varchar(100) not null", description: "プレイヤー名" },
        { name: "class_name", type: "varchar(50)", description: "職業" },
        { name: "level", type: "integer", description: "レベル" },
        { name: "combat_power", type: "integer", description: "戦闘力" },
        {
          name: "guild_id",
          type: "integer references guilds(guild_id)",
          description: "所属ギルドID"
        }
      ]
    },
    {
      table: "items",
      description: "アイテムマスタ",
      columns: [
        { name: "item_id", type: "serial primary key", description: "アイテムID" },
        { name: "item_name", type: "varchar(100) not null", description: "アイテム名" },
        { name: "item_type", type: "varchar(50)", description: "種別" },
        { name: "rarity", type: "varchar(20)", description: "レア度" }
      ]
    },
    {
      table: "inventory",
      description: "プレイヤー所持アイテム",
      columns: [
        { name: "inventory_id", type: "serial primary key", description: "所持ID" },
        {
          name: "player_id",
          type: "integer references players(player_id)",
          description: "プレイヤーID"
        },
        {
          name: "item_id",
          type: "integer references items(item_id)",
          description: "アイテムID"
        },
        { name: "quantity", type: "integer default 1", description: "所持数" }
      ]
    },
    {
      table: "raid_logs",
      description: "レイド参加履歴",
      columns: [
        { name: "raid_log_id", type: "serial primary key", description: "レイド履歴ID" },
        {
          name: "player_id",
          type: "integer references players(player_id)",
          description: "プレイヤーID"
        },
        { name: "raid_name", type: "varchar(100)", description: "レイド名" },
        { name: "clear_time", type: "integer", description: "クリア時間（秒）" },
        { name: "raid_date", type: "date", description: "参加日" }
      ]
    }
  ],

  examples: gameGuildExamples,

  systemPrompt: `
あなたはオンラインゲームのギルド管理データベースのSQL講師です。

利用可能テーブル:
- guilds(guild_id, guild_name, server_name, founded_date)
- players(player_id, player_name, class_name, level, combat_power, guild_id)
- items(item_id, item_name, item_type, rarity)
- inventory(inventory_id, player_id, item_id, quantity)
- raid_logs(raid_log_id, player_id, raid_name, clear_time, raid_date)

ユーザーの質問に対して:
1. SQLを生成
2. 日本語でわかりやすく説明
3. 使用したSQL構文を解説
4. 必要なら別解や応用例も提示
`
};

export default gameGuild;