// src/data/db_sets/hospital.js

export const hospitalExamples = [
  {
    category: "病院DB",
    title: "本日予約のある患者一覧を表示したい",
    description: "appointments テーブルから今日の予約を取得します。",
    sql: `SELECT p.patient_name,
       d.doctor_name,
       a.appointment_date,
       a.status
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors d ON a.doctor_id = d.doctor_id
WHERE a.appointment_date = CURRENT_DATE
ORDER BY d.doctor_name, p.patient_name;`
  },
  {
    category: "病院DB",
    title: "診療科ごとの医師数を表示したい",
    description: "department ごとに所属医師数を集計します。",
    sql: `SELECT department,
       COUNT(*) AS doctor_count
FROM doctors
GROUP BY department
ORDER BY doctor_count DESC;`
  },
  {
    category: "病院DB",
    title: "最も多くの患者を担当している医師",
    description: "appointments を集計して担当患者数の最多医師を取得します。",
    sql: `SELECT d.doctor_name,
       COUNT(DISTINCT a.patient_id) AS patient_count
FROM doctors d
JOIN appointments a ON d.doctor_id = a.doctor_id
GROUP BY d.doctor_id, d.doctor_name
ORDER BY patient_count DESC
LIMIT 1;`
  },
  {
    category: "病院DB",
    title: "高血圧の患者一覧を表示したい",
    description: "medical_records から diagnosis が高血圧の患者を取得します。",
    sql: `SELECT DISTINCT p.patient_name,
       p.birth_date
FROM patients p
JOIN medical_records m ON p.patient_id = m.patient_id
WHERE m.diagnosis = '高血圧';`
  },
  {
    category: "病院DB",
    title: "薬ごとの処方回数を表示したい",
    description: "prescriptions を medicine_name ごとに集計します。",
    sql: `SELECT medicine_name,
       COUNT(*) AS prescription_count
FROM prescriptions
GROUP BY medicine_name
ORDER BY prescription_count DESC;`
  },
  {
    category: "病院DB",
    title: "未受診の予約を表示したい",
    description: "status = '予約済み' の予約を抽出します。",
    sql: `SELECT a.appointment_id,
       p.patient_name,
       d.doctor_name,
       a.appointment_date
FROM appointments a
JOIN patients p ON a.patient_id = p.patient_id
JOIN doctors d ON a.doctor_id = d.doctor_id
WHERE a.status = '予約済み'
ORDER BY a.appointment_date;`
  },
  {
    category: "病院DB",
    title: "患者ごとの受診回数を表示したい",
    description: "appointments を患者ごとに集計します。",
    sql: `SELECT p.patient_name,
       COUNT(a.appointment_id) AS visit_count
FROM patients p
LEFT JOIN appointments a ON p.patient_id = a.patient_id
GROUP BY p.patient_id, p.patient_name
ORDER BY visit_count DESC;`
  },
  {
    category: "病院DB",
    title: "平均年齢以上の患者を表示したい",
    description: "生年月日から年齢を計算し、平均以上の患者を取得します。",
    sql: `SELECT patient_name,
       birth_date
FROM patients
WHERE EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_date)) >= (
  SELECT AVG(EXTRACT(YEAR FROM AGE(CURRENT_DATE, birth_date)))
  FROM patients
);`
  },
  {
    category: "病院DB",
    title: "担当患者がいない医師を表示したい",
    description: "LEFT JOIN で予約が存在しない医師を抽出します。",
    sql: `SELECT d.doctor_name
FROM doctors d
LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
WHERE a.appointment_id IS NULL;`
  },
  {
    category: "病院DB",
    title: "診療科ごとの平均受診回数",
    description: "各診療科の予約件数平均を計算します。",
    sql: `SELECT d.department,
       COUNT(a.appointment_id) AS total_appointments
FROM doctors d
LEFT JOIN appointments a ON d.doctor_id = a.doctor_id
GROUP BY d.department
ORDER BY total_appointments DESC;`
  },
  {
    category: "病院DB",
    title: "患者ごとの最新診断を表示したい",
    description: "最新の medical_records を取得します。",
    sql: `SELECT DISTINCT ON (p.patient_id)
       p.patient_name,
       m.diagnosis,
       m.record_date
FROM patients p
JOIN medical_records m ON p.patient_id = m.patient_id
ORDER BY p.patient_id, m.record_date DESC;`
  },
  {
    category: "病院DB",
    title: "今月の予約件数を表示したい",
    description: "今月の appointments 件数を集計します。",
    sql: `SELECT COUNT(*) AS monthly_appointments
FROM appointments
WHERE DATE_TRUNC('month', appointment_date)
      = DATE_TRUNC('month', CURRENT_DATE);`
  }
];

const hospital = {
  id: "hospital",
  name: "病院・診療管理データベース",
  description:
    "患者、医師、予約、診療記録、処方情報を扱う医療機関向けサンプルDB。JOIN、集計、サブクエリの学習に最適。",

  schema: [
    {
      table: "patients",
      description: "患者情報",
      columns: [
        { name: "patient_id", type: "serial primary key", description: "患者ID" },
        { name: "patient_name", type: "varchar(100) not null", description: "患者名" },
        { name: "birth_date", type: "date", description: "生年月日" },
        { name: "gender", type: "varchar(10)", description: "性別" },
        { name: "phone", type: "varchar(20)", description: "電話番号" }
      ]
    },
    {
      table: "doctors",
      description: "医師情報",
      columns: [
        { name: "doctor_id", type: "serial primary key", description: "医師ID" },
        { name: "doctor_name", type: "varchar(100) not null", description: "医師名" },
        { name: "department", type: "varchar(100)", description: "診療科" }
      ]
    },
    {
      table: "appointments",
      description: "診療予約",
      columns: [
        { name: "appointment_id", type: "serial primary key", description: "予約ID" },
        {
          name: "patient_id",
          type: "integer references patients(patient_id)",
          description: "患者ID"
        },
        {
          name: "doctor_id",
          type: "integer references doctors(doctor_id)",
          description: "医師ID"
        },
        { name: "appointment_date", type: "date", description: "予約日" },
        { name: "status", type: "varchar(20)", description: "状態" }
      ]
    },
    {
      table: "medical_records",
      description: "診療記録",
      columns: [
        { name: "record_id", type: "serial primary key", description: "記録ID" },
        {
          name: "patient_id",
          type: "integer references patients(patient_id)",
          description: "患者ID"
        },
        {
          name: "doctor_id",
          type: "integer references doctors(doctor_id)",
          description: "医師ID"
        },
        { name: "record_date", type: "date", description: "診療日" },
        { name: "diagnosis", type: "text", description: "診断内容" },
        { name: "notes", type: "text", description: "診療メモ" }
      ]
    },
    {
      table: "prescriptions",
      description: "処方情報",
      columns: [
        { name: "prescription_id", type: "serial primary key", description: "処方ID" },
        {
          name: "record_id",
          type: "integer references medical_records(record_id)",
          description: "診療記録ID"
        },
        { name: "medicine_name", type: "varchar(100)", description: "薬品名" },
        { name: "dosage", type: "varchar(100)", description: "用量" },
        { name: "days", type: "integer", description: "日数" }
      ]
    }
  ],

  examples: hospitalExamples,

  systemPrompt: `
あなたは病院・診療管理データベースのSQL講師です。

利用可能テーブル:
- patients(patient_id, patient_name, birth_date, gender, phone)
- doctors(doctor_id, doctor_name, department)
- appointments(appointment_id, patient_id, doctor_id, appointment_date, status)
- medical_records(record_id, patient_id, doctor_id, record_date, diagnosis, notes)
- prescriptions(prescription_id, record_id, medicine_name, dosage, days)

ユーザーの質問に対して:
1. SQLを生成
2. 日本語でわかりやすく説明
3. 使用したSQL構文を解説
4. 必要なら別解や実務での注意点も提示
`
};

export default hospital;