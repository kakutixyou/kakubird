// src/data/db_sets/ecommerce.js

export const ecommerceExamples = [
  {
    category: "ECサイトDB",
    title: "注文金額が10,000円以上の注文を表示したい",
    description: "高額注文のみを抽出します。",
    sql: `SELECT order_id, customer_id, total_amount, order_date
FROM orders
WHERE total_amount >= 10000
ORDER BY total_amount DESC;`
  },
  {
    category: "ECサイトDB",
    title: "一番売れている商品を知りたい",
    description: "注文詳細から販売数量を集計し、トップ1を取得します。",
    sql: `SELECT p.product_name, SUM(oi.quantity) AS total_sold
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY total_sold DESC
LIMIT 1;`
  },
  {
    category: "ECサイトDB",
    title: "顧客ごとの累計購入金額を表示したい",
    description: "顧客ごとの総購入額を計算します。",
    sql: `SELECT c.customer_name, SUM(o.total_amount) AS total_spent
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY total_spent DESC;`
  },
  {
    category: "ECサイトDB",
    title: "在庫が10個未満の商品を表示したい",
    description: "在庫が少ない商品を抽出します。",
    sql: `SELECT product_name, stock_quantity
FROM products
WHERE stock_quantity < 10
ORDER BY stock_quantity ASC;`
  },
  {
    category: "ECサイトDB",
    title: "カテゴリごとの商品数を表示したい",
    description: "各カテゴリに属する商品数を集計します。",
    sql: `SELECT category, COUNT(*) AS product_count
FROM products
GROUP BY category
ORDER BY product_count DESC;`
  },
  {
    category: "ECサイトDB",
    title: "未発送の注文を表示したい",
    description: "配送ステータスが未発送の注文一覧です。",
    sql: `SELECT order_id, customer_id, total_amount, order_date
FROM orders
WHERE status = '未発送'
ORDER BY order_date DESC;`
  },
  {
    category: "ECサイトDB",
    title: "最も高い商品を表示したい",
    description: "価格が最大の商品を取得します。",
    sql: `SELECT product_name, price
FROM products
ORDER BY price DESC
LIMIT 1;`
  },
  {
    category: "ECサイトDB",
    title: "2026年の注文件数を月別に集計したい",
    description: "月ごとの注文数を集計します。",
    sql: `SELECT DATE_TRUNC('month', order_date) AS month,
       COUNT(*) AS order_count
FROM orders
WHERE EXTRACT(YEAR FROM order_date) = 2026
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;`
  },
  {
    category: "ECサイトDB",
    title: "商品ごとの売上金額を表示したい",
    description: "販売数量 × 単価で売上を集計します。",
    sql: `SELECT p.product_name,
       SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC;`
  },
  {
    category: "ECサイトDB",
    title: "一度も注文していない顧客を表示したい",
    description: "LEFT JOIN を使って注文履歴のない顧客を抽出します。",
    sql: `SELECT c.customer_name
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
WHERE o.order_id IS NULL;`
  },
  {
    category: "ECサイトDB",
    title: "平均注文金額より高い注文を表示したい",
    description: "副問い合わせで平均以上の注文を抽出します。",
    sql: `SELECT order_id, customer_id, total_amount
FROM orders
WHERE total_amount > (
  SELECT AVG(total_amount)
  FROM orders
)
ORDER BY total_amount DESC;`
  },
  {
    category: "ECサイトDB",
    title: "顧客ごとの注文回数を表示したい",
    description: "注文数の多い顧客を確認します。",
    sql: `SELECT c.customer_name,
       COUNT(o.order_id) AS order_count
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY order_count DESC;`
  },
  {
    category: "ECサイトDB",
    title: "売上上位5商品を表示したい",
    description: "商品別売上のトップ5を取得します。",
    sql: `SELECT p.product_name,
       SUM(oi.quantity * oi.unit_price) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_id, p.product_name
ORDER BY revenue DESC
LIMIT 5;`
  },
  {
    category: "ECサイトDB",
    title: "最も多く注文した顧客を表示したい",
    description: "注文回数が最多の顧客を取得します。",
    sql: `SELECT c.customer_name,
       COUNT(o.order_id) AS order_count
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
GROUP BY c.customer_id, c.customer_name
ORDER BY order_count DESC
LIMIT 1;`
  },
  {
    category: "ECサイトDB",
    title: "注文ごとの商品数を表示したい",
    description: "各注文に含まれる商品の合計数量を集計します。",
    sql: `SELECT o.order_id,
       SUM(oi.quantity) AS total_items
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.order_id
ORDER BY o.order_id;`
  }
];

const ecommerce = {
  id: "ecommerce",
  name: "ECサイトデータベース",
  description:
    "顧客、商品、注文、注文詳細、配送情報を扱うサンプルDB。JOIN、集計、サブクエリ、売上分析の学習に最適。",

  schema: [
    {
      table: "customers",
      description: "顧客情報",
      columns: [
        { name: "customer_id", type: "serial primary key", description: "顧客ID" },
        { name: "customer_name", type: "varchar(100)", description: "顧客名" },
        { name: "email", type: "varchar(255)", description: "メールアドレス" },
        { name: "phone", type: "varchar(20)", description: "電話番号" },
        { name: "created_at", type: "timestamp default now()", description: "登録日時" }
      ]
    },
    {
      table: "products",
      description: "商品情報",
      columns: [
        { name: "product_id", type: "serial primary key", description: "商品ID" },
        { name: "product_name", type: "varchar(100)", description: "商品名" },
        { name: "category", type: "varchar(50)", description: "カテゴリ" },
        { name: "price", type: "numeric(10,2)", description: "価格" },
        { name: "stock_quantity", type: "integer", description: "在庫数" }
      ]
    },
    {
      table: "orders",
      description: "注文情報",
      columns: [
        { name: "order_id", type: "serial primary key", description: "注文ID" },
        {
          name: "customer_id",
          type: "integer references customers(customer_id)",
          description: "顧客ID"
        },
        { name: "order_date", type: "timestamp default now()", description: "注文日時" },
        { name: "status", type: "varchar(30)", description: "注文ステータス" },
        { name: "total_amount", type: "numeric(10,2)", description: "合計金額" }
      ]
    },
    {
      table: "order_items",
      description: "注文詳細",
      columns: [
        { name: "order_item_id", type: "serial primary key", description: "注文詳細ID" },
        {
          name: "order_id",
          type: "integer references orders(order_id)",
          description: "注文ID"
        },
        {
          name: "product_id",
          type: "integer references products(product_id)",
          description: "商品ID"
        },
        { name: "quantity", type: "integer", description: "数量" },
        { name: "unit_price", type: "numeric(10,2)", description: "単価" }
      ]
    },
    {
      table: "shipments",
      description: "配送情報",
      columns: [
        { name: "shipment_id", type: "serial primary key", description: "配送ID" },
        {
          name: "order_id",
          type: "integer references orders(order_id)",
          description: "注文ID"
        },
        { name: "shipped_date", type: "date", description: "発送日" },
        { name: "delivery_date", type: "date", description: "配達日" },
        { name: "carrier", type: "varchar(50)", description: "配送業者" },
        { name: "tracking_number", type: "varchar(100)", description: "追跡番号" }
      ]
    }
  ],

  examples: ecommerceExamples,

  systemPrompt: `
あなたはECサイトデータベースのSQL講師です。

利用可能テーブル:
- customers(customer_id, customer_name, email, phone, created_at)
- products(product_id, product_name, category, price, stock_quantity)
- orders(order_id, customer_id, order_date, status, total_amount)
- order_items(order_item_id, order_id, product_id, quantity, unit_price)
- shipments(shipment_id, order_id, shipped_date, delivery_date, carrier, tracking_number)

ユーザーの質問に対して:
1. SQLを生成
2. 日本語でわかりやすく説明
3. 使用したSQL構文を解説
4. 必要なら別解や最適化案を提示
`
};

export default ecommerce;