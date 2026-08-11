export const corporate = {
  id: "corporate",
  name: "企業経営・株主総会データベース",
  description:
    "株主、企業、保有株式、配当金、役員情報を扱うサンプルデータセット。JOIN、GROUP BY、HAVING、副問い合わせの学習に最適。",

  // Supabase 用テーブル定義
  schema: [
    {
      table: "shareholders",
      description: "株主情報",
      columns: [
        { name: "shareholder_id", type: "serial primary key", description: "株主ID" },
        { name: "shareholder_name", type: "varchar(100)", description: "株主名" },
        { name: "age", type: "integer", description: "年齢" },
        { name: "region", type: "varchar(50)", description: "居住地域" }
      ]
    },
    {
      table: "companies",
      description: "企業情報",
      columns: [
        { name: "company_id", type: "serial primary key", description: "企業ID" },
        { name: "company_name", type: "varchar(100)", description: "企業名" },
        { name: "industry", type: "varchar(50)", description: "業界" }
      ]
    },
    {
      table: "holdings",
      description: "株式保有情報",
      columns: [
        {
          name: "holding_id",
          type: "serial primary key",
          description: "保有ID"
        },
        {
          name: "shareholder_id",
          type: "integer references shareholders(shareholder_id)",
          description: "株主ID"
        },
        {
          name: "company_id",
          type: "integer references companies(company_id)",
          description: "企業ID"
        },
        {
          name: "shares_owned",
          type: "integer",
          description: "保有株数"
        }
      ]
    },
    {
      table: "dividends",
      description: "配当金情報",
      columns: [
        {
          name: "dividend_id",
          type: "serial primary key",
          description: "配当ID"
        },
        {
          name: "shareholder_id",
          type: "integer references shareholders(shareholder_id)",
          description: "株主ID"
        },
        {
          name: "company_id",
          type: "integer references companies(company_id)",
          description: "企業ID"
        },
        {
          name: "dividend_amount",
          type: "numeric(12,2)",
          description: "配当金額"
        },
        {
          name: "payment_date",
          type: "date",
          description: "支払日"
        }
      ]
    },
    {
      table: "board_members",
      description: "役員情報",
      columns: [
        {
          name: "board_member_id",
          type: "serial primary key",
          description: "役員ID"
        },
        {
          name: "shareholder_id",
          type: "integer references shareholders(shareholder_id)",
          description: "株主ID"
        },
        {
          name: "role",
          type: "varchar(50)",
          description: "役職"
        }
      ]
    }
  ],
}
  sampleQueries: [
    {
      category: "A. 株主総会・企業経営DB",
      title: "配当金が100万円以上の株主",
      description: "配当金テーブルから、金額が1,000,000以上の株主を抽出します。",
      sql: "SELECT shareholder_name, dividend_amount\nFROM dividends\nWHERE dividend_amount >= 1000000;"
  },
  {
    category: "A. 株主総会・企業経営DB",
    title: "一番多く株を持つ株主",
    description: "保有株数テーブルを降順で並び替え、トップ1を取得します。",
    sql: "SELECT shareholder_name, total_shares\nFROM holdings\nORDER BY total_shares DESC\nLIMIT 1;"
  },
  {
    category: "株主総会DB",
    title: "株主ごとに保有している企業名を表示したい",
    description: "株主と企業の保有情報を一覧表示",
    sql: `SELECT s.shareholder_name, c.company_name, h.shares_owned
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
JOIN companies c ON h.company_id = c.company_id;`
  },
  {
    category: "株主総会DB",
    title: "一番多く株を持っている株主を知りたい",
    description: "保有株数が最大の株主を表示",
    sql: `SELECT s.shareholder_name, SUM(h.shares_owned) AS total_shares
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
GROUP BY s.shareholder_id
ORDER BY total_shares DESC
LIMIT 1;`
  },
  {
    category: "株主総会DB",
    title: "配当金が最も高い株主を表示したい",
    description: "受け取った配当総額の最大値",
    sql: `SELECT s.shareholder_name, SUM(d.dividend_amount) AS total_dividend
FROM shareholders s
JOIN dividends d ON s.shareholder_id = d.shareholder_id
GROUP BY s.shareholder_id
ORDER BY total_dividend DESC
LIMIT 1;`
  },
  {
    category: "株主総会DB",
    title: "企業ごとの総保有株数を表示したい",
    description: "企業別に何株保有されているか集計",
    sql: `SELECT c.company_name, SUM(h.shares_owned) AS total_shares
FROM companies c
JOIN holdings h ON c.company_id = h.company_id
GROUP BY c.company_id;`
  },
  {
    category: "株主総会DB",
    title: "IT企業の株を持つ株主を表示したい",
    description: "業界がITの企業に投資している株主一覧",
    sql: `SELECT DISTINCT s.shareholder_name
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
JOIN companies c ON h.company_id = c.company_id
WHERE c.industry = 'IT';`
  },
  {
    category: "株主総会DB",
    title: "役員を兼任している株主を表示したい",
    description: "board_membersに登録されている株主",
    sql: `SELECT DISTINCT s.shareholder_name, b.role
FROM shareholders s
JOIN board_members b ON s.shareholder_id = b.shareholder_id;`
  },
  {
    category: "株主総会DB",
    title: "配当金50万円以上の株主を表示したい",
    description: "高配当受取者を検索",
    sql: `SELECT s.shareholder_name, d.dividend_amount
FROM shareholders s
JOIN dividends d ON s.shareholder_id = d.shareholder_id
WHERE d.dividend_amount >= 500000;`
  },
  {
    category: "株主総会DB",
    title: "地域ごとの株主人数を表示したい",
    description: "地域別の株主数を集計",
    sql: `SELECT region, COUNT(*) AS shareholder_count
FROM shareholders
GROUP BY region;`
  },
  {
    category: "株主総会DB",
    title: "株主の平均年齢を知りたい",
    description: "AVGを使った平均計算",
    sql: `SELECT AVG(age) AS average_age
FROM shareholders;`
  },
  {
    category: "株主総会DB",
    title: "株を2社以上保有している株主を表示したい",
    description: "複数企業へ投資している株主",
    sql: `SELECT s.shareholder_name, COUNT(h.company_id) AS company_count
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
GROUP BY s.shareholder_id
HAVING COUNT(h.company_id) >= 2;`
  },
  {
    category: "株主総会DB",
    title: "企業別の配当総額を表示したい",
    description: "会社ごとの配当支払総額",
    sql: `SELECT c.company_name, SUM(d.dividend_amount) AS total_dividend
FROM companies c
JOIN dividends d ON c.company_id = d.company_id
GROUP BY c.company_id;`
  },
  {
    category: "株主総会DB",
    title: "役職が会長の株主を表示したい",
    description: "board_membersから会長だけ取得",
    sql: `SELECT s.shareholder_name, b.role
FROM shareholders s
JOIN board_members b ON s.shareholder_id = b.shareholder_id
WHERE b.role = '会長';`
  },
  {
    category: "株主総会DB",
    title: "東京在住の株主保有一覧を表示したい",
    description: "東京在住者の投資先一覧",
    sql: `SELECT s.shareholder_name, c.company_name, h.shares_owned
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
JOIN companies c ON h.company_id = c.company_id
WHERE s.region = '東京';`
  },
  {
    category: "株主総会DB",
    title: "食品業界株を保有している株主を表示したい",
    description: "食品業界企業への投資者",
    sql: `SELECT DISTINCT s.shareholder_name
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
JOIN companies c ON h.company_id = c.company_id
WHERE c.industry = '食品';`
  },
  {
    category: "株主総会DB",
    title: "1万株以上保有している情報を表示したい",
    description: "大量保有株を検索",
    sql: `SELECT s.shareholder_name, c.company_name, h.shares_owned
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
JOIN companies c ON h.company_id = c.company_id
WHERE h.shares_owned >= 10000;`
  },
  {
    category: "株主総会DB",
    title: "平均配当以上の株主を表示したい",
    description: "副問い合わせで平均より上を取得",
    sql: `SELECT s.shareholder_name, d.dividend_amount
FROM shareholders s
JOIN dividends d ON s.shareholder_id = d.shareholder_id
WHERE d.dividend_amount > (
  SELECT AVG(dividend_amount) FROM dividends
);`
  },
  {
    category: "株主総会DB",
    title: "役員かつ高配当株主を表示したい",
    description: "役員登録があり配当50万以上",
    sql: `SELECT DISTINCT s.shareholder_name
FROM shareholders s
JOIN board_members b ON s.shareholder_id = b.shareholder_id
JOIN dividends d ON s.shareholder_id = d.shareholder_id
WHERE d.dividend_amount >= 500000;`
  },
  {
    category: "株主総会DB",
    title: "保有企業数ランキングを表示したい",
    description: "何社に投資しているか順位付け",
    sql: `SELECT s.shareholder_name, COUNT(h.company_id) AS company_count
FROM shareholders s
JOIN holdings h ON s.shareholder_id = h.shareholder_id
GROUP BY s.shareholder_id
ORDER BY company_count DESC;`
  },
  {
    category: "株主総会DB",
    title: "企業ごとの役員人数を表示したい",
    description: "各企業に何人の役員株主がいるか",
    sql: `SELECT c.company_name, COUNT(b.member_id) AS board_count
FROM companies c
LEFT JOIN board_members b ON c.company_id = b.company_id
GROUP BY c.company_id;`
  },
  {
    category: "株主総会DB",
    title: "一社も役員になっていない株主を表示したい",
    description: "役員登録が存在しない株主",
    sql: `SELECT s.shareholder_name
FROM shareholders s
LEFT JOIN board_members b ON s.shareholder_id = b.shareholder_id
WHERE b.member_id IS NULL;`
  }

];
