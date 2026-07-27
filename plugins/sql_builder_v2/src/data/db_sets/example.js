export const Examples = [

  // ─────────────────────────────
  // 基礎SELECT
  // ─────────────────────────────
  {
    category: "SELECT基礎",
    title: "社員一覧を全部表示したい",
    description: "表の中身をすべて表示する基本形",
    sql: `SELECT * FROM employees;`
  },
  {
    category: "SELECT基礎",
    title: "社員名と年齢だけ表示したい",
    description: "必要な列だけ取り出す",
    sql: `SELECT name, age FROM employees;`
  },
  {
    category: "SELECT基礎",
    title: "年齢が30歳以上の社員を表示したい",
    description: "条件に一致する社員だけ表示",
    sql: `SELECT * FROM employees
WHERE age >= 30;`
  },
  {
    category: "SELECT基礎",
    title: "名前に田が含まれる社員を表示したい",
    description: "LIKEを使った文字検索",
    sql: `SELECT * FROM employees
WHERE name LIKE '%田%';`
  },

  // ─────────────────────────────
  // JOIN系
  // ─────────────────────────────
  {
    category: "JOIN系",
    title: "社員ごとに対応する部署名を表示したい",
    description: "社員の部署番号と部署表を照合して部署名を取得",
    sql: `SELECT e.name, d.department_name
FROM employees e
JOIN departments d
ON e.department_id = d.department_id;`
  },
  {
    category: "JOIN系",
    title: "全社員を表示して対応する部署名があれば横に付けたい",
    description: "社員は全員残して部署情報を追加",
    sql: `SELECT e.name, d.department_name
FROM employees e
LEFT JOIN departments d
ON e.department_id = d.department_id;`
  },
  {
    category: "JOIN系",
    title: "全部署を表示して所属社員がいれば追加したい",
    description: "部署を基準に社員情報を追加",
    sql: `SELECT e.name, d.department_name
FROM employees e
RIGHT JOIN departments d
ON e.department_id = d.department_id;`
  },

  // ─────────────────────────────
  // 集計
  // ─────────────────────────────
  {
    category: "集計",
    title: "社員が何人いるか知りたい",
    description: "COUNTで件数を数える",
    sql: `SELECT COUNT(*) FROM employees;`
  },
  {
    category: "集計",
    title: "部署ごとの社員数を表示したい",
    description: "GROUP BYで部署別に人数集計",
    sql: `SELECT department_id, COUNT(*)
FROM employees
GROUP BY department_id;`
  }
]
const example = {
  id: "example",
  name: "SQL基礎サンプルデータベース",
  description:
    "employees と departments を使って SELECT、WHERE、LIKE、JOIN、GROUP BY を学習するための基本データセット。",

  // Supabase にそのまま作成できるテーブル定義
  schema: [
    {
      table: "departments",
      description: "部署マスタ",
      columns: [
        {
          name: "department_id",
          type: "serial primary key",
          description: "部署ID"
        },
        {
          name: "department_name",
          type: "varchar(100) not null",
          description: "部署名"
        }
      ]
    },
    {
      table: "employees",
      description: "社員情報",
      columns: [
        {
          name: "employee_id",
          type: "serial primary key",
          description: "社員ID"
        },
        {
          name: "name",
          type: "varchar(100) not null",
          description: "社員名"
        },
        {
          name: "age",
          type: "integer",
          description: "年齢"
        },
        {
          name: "salary",
          type: "numeric(10,2)",
          description: "給与"
        },
        {
          name: "hire_date",
          type: "date",
          description: "入社日"
        },
        {
          name: "department_id",
          type: "integer references departments(department_id)",
          description: "所属部署ID"
        }
      ]
    }
  ]}
    // 学習用SQL例
  examples: Examples,

  // AIへの指示
  systemPrompt `
あなたはSQL初心者向けの講師です。

利用可能テーブル:
- departments(department_id, department_name)
- employees(employee_id, name, age, salary, hire_date, department_id)

ユーザーの質問に対して:
1. SQLを生成
2. SQLの意味を日本語で説明
3. 使用した構文（SELECT, WHERE, JOIN, GROUP BY など）を解説
4. 初心者にもわかるように丁寧に説明
5. 必要に応じて別解を提示
`

export default example;