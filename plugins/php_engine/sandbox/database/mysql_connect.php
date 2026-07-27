<?php
/**
 * plugins/php_engine/sandbox/database/mysql_connect.php
 *
 * MySQL接続サンドボックス
 * ─────────────────────────────────────────────
 * 目的  : php_engineが接続テスト・テンプレート参照に使うサンプル
 * 用途  : Phase B の sandbox参照 / 企画書のDB接続コード例として出力
 * 環境  : XAMPP (localhost) または .env 経由の本番設定
 * 依存  : PHP 8.0以上 / PDO + pdo_mysql 拡張
 */

declare(strict_types=1);

// ─────────────────────────────────────────────
// 1. 設定
//    優先順位: 環境変数(.env) > XAMPP デフォルト値
// ─────────────────────────────────────────────

$db_config = [
    'host'    => $_ENV['DB_HOST']     ?? 'localhost',
    'port'    => (int)($_ENV['DB_PORT']     ?? 3306),
    'dbname'  => $_ENV['DB_NAME']     ?? 'test',
    'user'    => $_ENV['DB_USER']     ?? 'root',
    'pass'    => $_ENV['DB_PASSWORD'] ?? '',
    'charset' => 'utf8mb4',
];

// ─────────────────────────────────────────────
// 2. PDO 接続オプション
// ─────────────────────────────────────────────

$pdo_options = [
    // エラーを例外で受け取る（必須）
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    // fetchAll/fetch のデフォルトを連想配列に
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    // ネイティブプリペアドを使う（SQLインジェクション対策を強化）
    PDO::ATTR_EMULATE_PREPULATES => false,
    // 接続タイムアウト（秒）
    PDO::ATTR_TIMEOUT            => 5,
    // 文字コードを確実に utf8mb4 に固定
    PDO::MYSQL_ATTR_INIT_COMMAND => "SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci",
];

// ─────────────────────────────────────────────
// 3. 接続関数
// ─────────────────────────────────────────────

/**
 * PDO接続を生成して返す。
 *
 * @param  array $config  db_config と同じ構造の配列
 * @param  array $options PDOオプション
 * @return PDO
 * @throws RuntimeException 接続失敗時
 */
function create_pdo(array $config, array $options): PDO
{
    $dsn = sprintf(
        'mysql:host=%s;port=%d;dbname=%s;charset=%s',
        $config['host'],
        $config['port'],
        $config['dbname'],
        $config['charset']
    );

    try {
        $pdo = new PDO($dsn, $config['user'], $config['pass'], $options);
        return $pdo;

    } catch (PDOException $e) {
        // 接続情報をログに残し、クライアントには詳細を見せない
        error_log('[mysql_connect] 接続エラー: ' . $e->getMessage());
        throw new RuntimeException(
            'データベースに接続できませんでした。設定を確認してください。',
            (int)$e->getCode(),
            $e
        );
    }
}

// ─────────────────────────────────────────────
// 4. シングルトン（同一リクエスト内で接続を使い回す）
// ─────────────────────────────────────────────

/**
 * アプリ全体で共有するPDOインスタンスを返す。
 * 初回呼び出し時のみ接続を確立する。
 *
 * 使い方:
 *   $pdo = get_pdo();
 *   $stmt = $pdo->prepare('SELECT ...');
 */
function get_pdo(): PDO
{
    static $instance = null;

    if ($instance === null) {
        global $db_config, $pdo_options;
        $instance = create_pdo($db_config, $pdo_options);
    }

    return $instance;
}

// ─────────────────────────────────────────────
// 5. 接続テスト（このファイルを直接実行した場合のみ動作）
// ─────────────────────────────────────────────

if (php_sapi_name() === 'cli' || (basename($_SERVER['SCRIPT_FILENAME'] ?? '') === basename(__FILE__))) {
    run_connection_test($db_config, $pdo_options);
}

/**
 * 接続・基本クエリ・文字コードを検証して結果を出力する。
 */
function run_connection_test(array $config, array $options): void
{
    $results = [];

    // ── テスト 1: 接続 ──────────────────────────────
    try {
        $pdo = create_pdo($config, $options);
        $results[] = ['test' => '接続',      'status' => 'OK',  'detail' => "host={$config['host']} dbname={$config['dbname']}"];
    } catch (RuntimeException $e) {
        $results[] = ['test' => '接続',      'status' => 'FAIL', 'detail' => $e->getMessage()];
        print_test_results($results);
        return; // 接続失敗時は以降のテストをスキップ
    }

    // ── テスト 2: バージョン確認 ────────────────────
    try {
        $version = $pdo->query('SELECT VERSION() AS v')->fetchColumn();
        $results[] = ['test' => 'バージョン', 'status' => 'OK',  'detail' => "MySQL {$version}"];
    } catch (PDOException $e) {
        $results[] = ['test' => 'バージョン', 'status' => 'FAIL', 'detail' => $e->getMessage()];
    }

    // ── テスト 3: 文字コード確認 ────────────────────
    try {
        $charset = $pdo->query("SHOW VARIABLES LIKE 'character_set_connection'")->fetch();
        $ok      = ($charset['Value'] ?? '') === 'utf8mb4';
        $results[] = [
            'test'   => '文字コード',
            'status' => $ok ? 'OK' : 'WARN',
            'detail' => "character_set_connection = " . ($charset['Value'] ?? '不明'),
        ];
    } catch (PDOException $e) {
        $results[] = ['test' => '文字コード', 'status' => 'FAIL', 'detail' => $e->getMessage()];
    }

    // ── テスト 4: プリペアドステートメント ──────────
    try {
        $stmt = $pdo->prepare('SELECT ? + ? AS result');
        $stmt->execute([3, 7]);
        $row  = $stmt->fetch();
        $ok   = ((int)($row['result'] ?? 0)) === 10;
        $results[] = [
            'test'   => 'プリペアド',
            'status' => $ok ? 'OK' : 'FAIL',
            'detail' => '3 + 7 = ' . ($row['result'] ?? '?'),
        ];
    } catch (PDOException $e) {
        $results[] = ['test' => 'プリペアド', 'status' => 'FAIL', 'detail' => $e->getMessage()];
    }

    // ── テスト 5: トランザクション ──────────────────
    try {
        $pdo->beginTransaction();
        $pdo->rollBack();
        $results[] = ['test' => 'トランザクション', 'status' => 'OK', 'detail' => 'beginTransaction / rollBack 正常'];
    } catch (PDOException $e) {
        $results[] = ['test' => 'トランザクション', 'status' => 'FAIL', 'detail' => $e->getMessage()];
    }

    // ── テスト 6: データベース一覧 ──────────────────
    try {
        $rows = $pdo->query('SHOW DATABASES')->fetchAll(PDO::FETCH_COLUMN);
        $results[] = [
            'test'   => 'DB一覧',
            'status' => 'OK',
            'detail' => implode(', ', $rows),
        ];
    } catch (PDOException $e) {
        $results[] = ['test' => 'DB一覧', 'status' => 'FAIL', 'detail' => $e->getMessage()];
    }

    print_test_results($results);
}

/**
 * テスト結果を CLI / ブラウザ両対応で整形出力する。
 */
function print_test_results(array $results): void
{
    $is_cli = (php_sapi_name() === 'cli');

    if (!$is_cli) {
        echo "<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>";
        echo "<title>MySQL接続テスト</title>";
        echo "<style>body{font-family:monospace;padding:20px;background:#1e1e2e;color:#cdd6f4}";
        echo "table{border-collapse:collapse;width:100%}";
        echo "th,td{padding:8px 14px;border:1px solid #45475a;text-align:left}";
        echo "th{background:#313244}.ok{color:#a6e3a1}.fail{color:#f38ba8}.warn{color:#f9e2af}";
        echo "</style></head><body>";
        echo "<h2>MySQL 接続テスト結果</h2><table>";
        echo "<tr><th>テスト項目</th><th>結果</th><th>詳細</th></tr>";
    } else {
        echo "\n=== MySQL 接続テスト ===\n";
        printf("%-20s %-6s %s\n", 'テスト項目', '結果', '詳細');
        echo str_repeat('-', 70) . "\n";
    }

    foreach ($results as $r) {
        $status = $r['status'];
        $class  = strtolower($status);

        if ($is_cli) {
            $icon = match($status) {
                'OK'   => '✓',
                'WARN' => '△',
                default => '✗',
            };
            printf("%-20s [%s] %s %s\n", $r['test'], $status, $icon, $r['detail']);
        } else {
            echo "<tr>";
            echo "<td>" . htmlspecialchars($r['test'],   ENT_QUOTES, 'UTF-8') . "</td>";
            echo "<td class='{$class}'>" . htmlspecialchars($status, ENT_QUOTES, 'UTF-8') . "</td>";
            echo "<td>" . htmlspecialchars($r['detail'], ENT_QUOTES, 'UTF-8') . "</td>";
            echo "</tr>";
        }
    }

    if (!$is_cli) {
        echo "</table></body></html>";
    } else {
        echo "\n";
    }
}