
/**
 * SQL文字列から文字列リテラル（'...' や "..."）をダミーに置換する。
 * これにより、例えば以下のようなクエリでの誤検知を防ぐ。
 * ❌ 誤検知防止: SELECT * FROM logs WHERE message = 'Please drop this'
 * * @param {string} sql - 元のSQL文
 * @returns {string} 文字列リテラルが除去されたSQL文
 */
function stripStringLiterals(sql) {
  // シングルクォートまたはダブルクォートで囲まれた文字列を空文字に置き換える
  // （エスケープされたクォートの厳密な判定は正規表現だけでは限界がありますが、
  // 簡易的なフロントエンドの警告用としてはこれで十分に機能します）
  return sql
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")
    .replace(/"(?:[^"\\]|\\.)*"/g, '""');
}

/**
 * 実行しようとしているSQLが危険（破壊的）かどうかを判定する
 *  @param {string} sql - 実行予定のSQL文
 * @returns {{ isDangerous: boolean, type: string | null, message: string | null }}
 */
export function checkDangerousQuery(sql) {
  if (!sql || typeof sql !== "string") {
    return { isDangerous: false, type: null, message: null };
  }

  // 1. コメントを除去（-- から行末まで、および /* ... */）
  let cleanSql = sql.replace(/--.*$/gm, "").replace(/\/\*[\s\S]*?\*\//g, "");
  
  // 2. 文字列リテラルを除去
  cleanSql = stripStringLiterals(cleanSql);

  // 3. 破壊的キーワードの定義（単語の境界 \b を使って部分一致を防ぐ）
  // 　 例: "DROP" は検知するが、"DROP_COUNT" というカラム名には反応しない
  const DANGEROUS_PATTERNS = [
    { type: "DROP", regex: /\bDROP\b/i },
    { type: "TRUNCATE", regex: /\bTRUNCATE\b/i },
    { type: "DELETE", regex: /\bDELETE\b/i },
    { type: "ALTER", regex: /\bALTER\b/i }
  ];

  for (const pattern of DANGEROUS_PATTERNS) {
    if (pattern.regex.test(cleanSql)) {
      return {
        isDangerous: true,
        type: pattern.type,
        message: ` データベースの構造やデータを破壊・変更する可能性のある「${pattern.type}」文が含まれています。\n本当に実行してもよろしいですか？`
      };
    }
  }

  return { isDangerous: false, type: null, message: null };
}