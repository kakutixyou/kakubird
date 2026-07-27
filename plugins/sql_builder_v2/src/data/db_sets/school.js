// src/data/db_sets/school.js

export const schoolExamples = [
  {
    category: "C. 学校成績DB",
    title: "平均点以上の生徒を表示",
    description: "サブクエリ（副問い合わせ）を使って、全体の平均点よりも高い点数を取った生徒を抽出します。",
    sql: "SELECT s.name, sc.score\nFROM students s\nJOIN scores sc ON s.id = sc.student_id\nWHERE sc.score >= (SELECT AVG(score) FROM scores);"
  },
  {
    category: "C. 学校成績DB",
    title: "教科ごとの平均点",
    description: "GROUP BYを使って教科ごとにグループ化し、それぞれの平均点を計算して高い順に並び替えます。",
    sql: "SELECT sub.name AS subject, ROUND(AVG(sc.score), 1) AS average_score\nFROM subjects sub\nJOIN scores sc ON sub.id = sc.subject_id\nGROUP BY sub.name\nORDER BY average_score DESC;"
  },
  {
    category: "C. 学校成績DB",
    title: "担任ごとの生徒数",
    description: "先生、クラス、生徒の3つのテーブルをJOINで繋ぎ、先生が受け持つ生徒の合計数を数えます。",
    sql: "SELECT t.name AS teacher, COUNT(s.id) AS student_count\nFROM teachers t\nJOIN classes c ON t.id = c.teacher_id\nJOIN students s ON c.id = s.class_id\nGROUP BY t.name;"
  },
  {
    category: "C. 学校成績DB",
    title: "特定のクラスの総合点ランキング",
    description: "生徒ごとの全教科の合計点（SUM）を計算し、点数が高い順（降順）に並び替えます。",
    sql: "SELECT s.name, SUM(sc.score) AS total_score\nFROM students s\nJOIN scores sc ON s.id = sc.student_id\nWHERE s.class_id = 1\nGROUP BY s.name\nORDER BY total_score DESC;"
  },
  {
    category: "C. 学校成績DB",
    title: "赤点（50点未満）を取った生徒の一覧",
    description: "WHERE句を使って特定の条件に合致するデータだけを絞り込みます。",
    sql: "SELECT s.name, sub.name AS subject, sc.score\nFROM students s\nJOIN scores sc ON s.id = sc.student_id\nJOIN subjects sub ON sc.subject_id = sub.id\nWHERE sc.score < 50;"
  }
];