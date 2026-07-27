<?php
/**
 * plugins/php_engine/sandbox/database/sqlite_connect.php
 *
 * SQLite接続サンドボックス
 * ─────────────────────────────────────────────
 * 目的  : php_engineがSQLite接続パターンの動作確認・テンプレート参照に使うサンプル
 * 用途  : Phase B の sandbox参照 / XAMPPでMySQLなしでも動くプロトタイプ用
 * 環境  : PHP 8.0以上 / PDO + pdo_sqlite 拡張（XAMPPはデフォルト有効）
 * 実行  : php sqlite_connect.php
 *
 * ファイル配置:
 *   sandbox/database/sqlite_connect.php   ← このファイル
 *   generated/outputs/sandbox.sqlite      ← 実行時に自動生成されるDBファイル
 */

declare(strict_types=1);

// ─────────────────────────────────────────────
// 1. 設定
// ─────────────────────────────────────────────

// DBファイルの保存先（generated/outputs/ 以下に作成）
$db_path = __DIR__ . '/../../generated/outputs/sandbox.sqlite';

// インメモリDB（テストのみ・プロセス終了で消える）
// $db_path = ':memory:';

$pdo_options = [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
];

// ─────────────────────────────────────────────
// 2. 接続関数
// ─────────────────────────────────────────────

/**
 * SQLite PDO接続を生成して返す。
 *
 * @param  string $db_path DBファイルパスまたは ':memory:'
 * @param  array  $options PDOオプション
 * @return PDO
 * @throws RuntimeException 接続失敗時
 */
function create_sqlite_pdo(string $db_path, array $options): PDO
{
    // ディレクトリが存在しない場合は作成
    if ($db_path !== ':memory:') {
        $dir = dirname($db_path);
        if (!is_dir($dir)) {
            mkdir($dir, 0755, true);
        }
    }

    try {
        $pdo = new PDO('sqlite:' . $db_path, null, null, $options);

        // WALモード: 読み書き同時アクセス時のロック競合を大幅に削減
        $pdo->exec('PRAGMA journal_mode = WAL');

        // 外部キー制約を有効化（SQLiteはデフォルト無効）
        $pdo->exec('PRAGMA foreign_keys = ON');

        // キャッシュサイズを増やしてパフォーマンス向上（単位: ページ数）
        $pdo->exec('PRAGMA cache_size = -8000'); // 約8MB

        // 同期モード: NORMAL（デフォルトのFULLより高速、WALと組み合わせると安全）
        $pdo->exec('PRAGMA synchronous = NORMAL');

        return $pdo;

    } catch (PDOException $e) {
        error_log('[sqlite_connect] 接続エラー: ' . $e->getMessage());
        throw new RuntimeException(
            'SQLiteデータベースに接続できませんでした: ' . $e->getMessage(),
            (int)$e->getCode(),
            $e
        );
    }
}

// ─────────────────────────────────────────────
// 3. シングルトン
// ─────────────────────────────────────────────

/**
 * アプリ全体で共有するSQLite PDOインスタンスを返す。
 * get_pdo()（MySQL版）と同じインターフェースで差し替え可能にしている。
 */
function get_sqlite_pdo(): PDO
{
    static $instance = null;

    if ($instance === null) {
        global $db_path, $pdo_options;
        $instance = create_sqlite_pdo($db_path, $pdo_options);
    }

    return $instance;
}

// ─────────────────────────────────────────────
// 4. スキーマ初期化
// ─────────────────────────────────────────────

/**
 * テスト用テーブルとサンプルデータを作成する。
 * 既にデータが存在する場合はスキップ。
 */
function setup_sqlite_schema(PDO $pdo): void
{
    // ── users テーブル ──
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS users (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            name       TEXT    NOT NULL,
            email      TEXT    NOT NULL UNIQUE,
            role       TEXT    NOT NULL DEFAULT 'user'
                           CHECK(role IN ('admin','user','guest')),
            age        INTEGER NOT NULL DEFAULT 20
                           CHECK(age >= 0 AND age <= 150),
            created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            deleted_at TEXT    NULL
        )
    ");

    // ── posts テーブル ──
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS posts (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            title      TEXT    NOT NULL,
            body       TEXT    NOT NULL DEFAULT '',
            status     TEXT    NOT NULL DEFAULT 'draft'
                           CHECK(status IN ('draft','published')),
            created_at TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
            deleted_at TEXT    NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    ");

    // ── settings テーブル（KVストア）──
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS settings (
            key        TEXT PRIMARY KEY,
            value      TEXT NOT NULL,
            updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        )
    ");

    // 既にデータがあれば挿入しない
    $count = (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn();
    if ($count > 0) {
        return;
    }

    // ── サンプルデータ投入（トランザクションで一括）──
    $pdo->beginTransaction();
    try {
        $stmt_u = $pdo->prepare(
            'INSERT INTO users (name, email, role, age) VALUES (?, ?, ?, ?)'
        );
        $users = [
            ['田中 太郎',   'taro@example.com',    'admin', 35],
            ['鈴木 花子',   'hanako@example.com',  'user',  28],
            ['佐藤 次郎',   'jiro@example.com',    'user',  42],
            ['高橋 三郎',   'saburo@example.com',  'guest', 19],
            ['渡辺 削除済', 'deleted@example.com', 'user',  30],
        ];
        foreach ($users as $u) {
            $stmt_u->execute($u);
        }

        // 論理削除
        $pdo->exec("
            UPDATE users SET deleted_at = datetime('now','localtime')
            WHERE email = 'deleted@example.com'
        ");

        $stmt_p = $pdo->prepare(
            'INSERT INTO posts (user_id, title, body, status) VALUES (?, ?, ?, ?)'
        );
        $posts = [
            [1, 'SQLiteの基本',         'ファイルベースのDBとして手軽に使える。',       'published'],
            [1, 'PHP+SQLite実践',       'XAMPPなしでも動くDB設計のコツ。',              'published'],
            [2, 'WALモードとは',        '書き込みと読み込みを同時に行うための設定。',   'published'],
            [2, '下書き記事',           'まだ公開していません。',                        'draft'],
            [3, 'SQLiteの制限事項',     '同時書き込みはMySQL/PgSQLに劣る点に注意。',   'published'],
        ];
        foreach ($posts as $p) {
            $stmt_p->execute($p);
        }

        // KVストア初期値
        $pdo->exec("
            INSERT OR IGNORE INTO settings (key, value) VALUES
                ('app_version', '1.0.0'),
                ('theme',       'dark'),
                ('language',    'ja')
        ");

        $pdo->commit();

    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }
}

/**
 * テスト用テーブルを削除する。
 */
function teardown_sqlite_schema(PDO $pdo): void
{
    $pdo->exec('DROP TABLE IF EXISTS posts');
    $pdo->exec('DROP TABLE IF EXISTS users');
    $pdo->exec('DROP TABLE IF EXISTS settings');
}

// ─────────────────────────────────────────────
// 5. SQLite固有パターン集
// ─────────────────────────────────────────────

/**
 * パターン1: 基本SELECT（論理削除除外）
 */
function sqlite_select_basic(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT id, name, email, role
         FROM users
         WHERE deleted_at IS NULL
         ORDER BY id ASC'
    );
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン2: UPSERT（INSERT OR REPLACE）
 * SQLiteはON DUPLICATE KEY UPDATEの代わりにINSERT OR REPLACEを使う。
 */
function sqlite_upsert_setting(PDO $pdo, string $key, string $value): void
{
    $stmt = $pdo->prepare(
        "INSERT INTO settings (key, value, updated_at)
         VALUES (:key, :value, datetime('now','localtime'))
         ON CONFLICT(key) DO UPDATE SET
             value      = excluded.value,
             updated_at = excluded.updated_at"
    );
    $stmt->execute([':key' => $key, ':value' => $value]);
}

/**
 * パターン3: JSON関数（SQLite 3.38以上）
 * カラムにJSON文字列を持つ場合の読み書き。
 */
function sqlite_json_example(PDO $pdo): void
{
    // metaカラムがある場合のUPSERT例（実際のテーブルがなければスキップ）
    // $pdo->exec("UPDATE users SET meta = json_set(meta, '$.score', 100) WHERE id = 1");
}

/**
 * パターン4: ページネーション
 */
function sqlite_pagination(PDO $pdo, int $page = 1, int $per_page = 3): array
{
    $offset = ($page - 1) * $per_page;

    $total = (int) $pdo->query(
        'SELECT COUNT(*) FROM posts WHERE deleted_at IS NULL'
    )->fetchColumn();

    $stmt = $pdo->prepare(
        'SELECT id, title, status, created_at
         FROM posts
         WHERE deleted_at IS NULL
         ORDER BY created_at DESC
         LIMIT :limit OFFSET :offset'
    );
    $stmt->bindValue(':limit',  $per_page, PDO::PARAM_INT);
    $stmt->bindValue(':offset', $offset,   PDO::PARAM_INT);
    $stmt->execute();

    return [
        'data'        => $stmt->fetchAll(),
        'total'       => $total,
        'per_page'    => $per_page,
        'current'     => $page,
        'total_pages' => (int) ceil($total / $per_page),
    ];
}

/**
 * パターン5: LEFT JOIN + 集計
 */
function sqlite_join_aggregate(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT u.id,
                u.name,
                COUNT(p.id)  AS post_count,
                MAX(p.created_at) AS latest_post
         FROM users u
         LEFT JOIN posts p
             ON u.id = p.user_id AND p.deleted_at IS NULL
         WHERE u.deleted_at IS NULL
         GROUP BY u.id, u.name
         ORDER BY post_count DESC'
    );
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン6: KVストア読み書き（settings テーブル）
 * php_engineのキャッシュや設定値の保存に使えるパターン。
 */
function sqlite_kv_get(PDO $pdo, string $key, string $default = ''): string
{
    $stmt = $pdo->prepare('SELECT value FROM settings WHERE key = :key');
    $stmt->execute([':key' => $key]);
    $row = $stmt->fetch();
    return $row ? $row['value'] : $default;
}

function sqlite_kv_set(PDO $pdo, string $key, string $value): void
{
    sqlite_upsert_setting($pdo, $key, $value);
}

// ─────────────────────────────────────────────
// 6. 接続テスト
// ─────────────────────────────────────────────

function run_sqlite_tests(PDO $pdo, string $db_path): array
{
    $suite = [];

    // ── テスト 1: PRAGMA確認 ──────────────────────
    $suite[] = run_sqlite_case('PRAGMA journal_mode=WAL', function () use ($pdo) {
        $row = $pdo->query("PRAGMA journal_mode")->fetch();
        if (($row['journal_mode'] ?? '') !== 'wal') {
            throw new AssertionError('journal_modeがwalでない: ' . ($row['journal_mode'] ?? '?'));
        }
        return [['journal_mode' => $row['journal_mode']]];
    });

    // ── テスト 2: 外部キー制約 ───────────────────
    $suite[] = run_sqlite_case('PRAGMA foreign_keys=ON', function () use ($pdo) {
        $row = $pdo->query("PRAGMA foreign_keys")->fetch();
        if ((int)($row['foreign_keys'] ?? 0) !== 1) {
            throw new AssertionError('外部キー制約が有効でない');
        }
        return [['foreign_keys' => $row['foreign_keys']]];
    });

    // ── テスト 3: バージョン確認 ─────────────────
    $suite[] = run_sqlite_case('SQLiteバージョン', function () use ($pdo) {
        $ver = $pdo->query("SELECT sqlite_version() AS v")->fetchColumn();
        return [['version' => $ver]];
    });

    // ── テスト 4: 基本SELECT ──────────────────────
    $suite[] = run_sqlite_case('基本SELECT（論理削除除外）', function () use ($pdo) {
        $rows = sqlite_select_basic($pdo);
        if (count($rows) < 1) {
            throw new AssertionError('1件以上返るはず');
        }
        return $rows;
    });

    // ── テスト 5: UPSERT ──────────────────────────
    $suite[] = run_sqlite_case('UPSERT（ON CONFLICT DO UPDATE）', function () use ($pdo) {
        sqlite_kv_set($pdo, 'theme', 'light');
        $val = sqlite_kv_get($pdo, 'theme');
        if ($val !== 'light') {
            throw new AssertionError("themeがlightでない: {$val}");
        }
        sqlite_kv_set($pdo, 'theme', 'dark'); // 元に戻す
        return [['key' => 'theme', 'value' => $val]];
    });

    // ── テスト 6: ページネーション ────────────────
    $suite[] = run_sqlite_case('ページネーション（page=1, per_page=3）', function () use ($pdo) {
        $result = sqlite_pagination($pdo, 1, 3);
        if (count($result['data']) > 3) {
            throw new AssertionError('3件超が返ってきた');
        }
        return $result['data'];
    });

    // ── テスト 7: LEFT JOIN + 集計 ────────────────
    $suite[] = run_sqlite_case('LEFT JOIN + 集計（投稿数）', function () use ($pdo) {
        $rows = sqlite_join_aggregate($pdo);
        if (empty($rows)) {
            throw new AssertionError('集計結果が空');
        }
        if (!array_key_exists('post_count', $rows[0])) {
            throw new AssertionError('post_countカラムがない');
        }
        return $rows;
    });

    // ── テスト 8: KVストア ────────────────────────
    $suite[] = run_sqlite_case('KVストア GET（存在するキー）', function () use ($pdo) {
        $val = sqlite_kv_get($pdo, 'app_version', 'none');
        if ($val === 'none') {
            throw new AssertionError('app_versionが取得できなかった');
        }
        return [['key' => 'app_version', 'value' => $val]];
    });

    // ── テスト 9: KVストア（存在しないキー）────────
    $suite[] = run_sqlite_case('KVストア GET（存在しないキー→デフォルト）', function () use ($pdo) {
        $val = sqlite_kv_get($pdo, 'no_such_key', 'DEFAULT');
        if ($val !== 'DEFAULT') {
            throw new AssertionError("デフォルト値が返らなかった: {$val}");
        }
        return [['key' => 'no_such_key', 'value' => $val]];
    });

    // ── テスト 10: トランザクション ──────────────
    $suite[] = run_sqlite_case('トランザクション（commit / rollback）', function () use ($pdo) {
        $before = (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn();

        // ロールバックテスト
        $pdo->beginTransaction();
        $pdo->exec("INSERT INTO users (name, email, role, age) VALUES ('一時ユーザー','tmp@example.com','guest',20)");
        $during = (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn();
        $pdo->rollBack();

        $after = (int) $pdo->query('SELECT COUNT(*) FROM users')->fetchColumn();

        if ($during <= $before) {
            throw new AssertionError('トランザクション内でINSERTが反映されていない');
        }
        if ($after !== $before) {
            throw new AssertionError('ROLLBACKが正常に動作していない');
        }
        return [['before' => $before, 'during' => $during, 'after' => $after]];
    });

    // ── テスト 11: DBファイルのパス確認 ──────────
    $suite[] = run_sqlite_case('DBファイルパス確認', function () use ($db_path) {
        if ($db_path === ':memory:') {
            return [['path' => ':memory: (インメモリ)']];
        }
        if (!file_exists($db_path)) {
            throw new AssertionError('DBファイルが存在しない: ' . $db_path);
        }
        $size_kb = round(filesize($db_path) / 1024, 1);
        return [['path' => realpath($db_path), 'size' => "{$size_kb} KB"]];
    });

    return $suite;
}

// ─────────────────────────────────────────────
// 7. ケース実行ラッパー・出力（select_test.phpと共通構造）
// ─────────────────────────────────────────────

function run_sqlite_case(string $label, callable $fn): array
{
    $t0 = microtime(true);
    try {
        $rows = $fn();
        $ms   = round((microtime(true) - $t0) * 1000, 2);
        return [
            'label'  => $label,
            'status' => 'PASS',
            'rows'   => is_array($rows) ? $rows : [],
            'count'  => is_array($rows) ? count($rows) : 0,
            'ms'     => $ms,
            'error'  => null,
        ];
    } catch (AssertionError $e) {
        $ms = round((microtime(true) - $t0) * 1000, 2);
        return ['label' => $label, 'status' => 'FAIL',  'rows' => [], 'count' => 0, 'ms' => $ms, 'error' => $e->getMessage()];
    } catch (Throwable $e) {
        $ms = round((microtime(true) - $t0) * 1000, 2);
        return ['label' => $label, 'status' => 'ERROR', 'rows' => [], 'count' => 0, 'ms' => $ms, 'error' => $e->getMessage()];
    }
}

function print_sqlite_report(array $suite, string $db_path): void
{
    $is_cli = (php_sapi_name() === 'cli');
    $pass   = count(array_filter($suite, fn($c) => $c['status'] === 'PASS'));
    $total  = count($suite);
    $db_label = $db_path === ':memory:' ? ':memory:' : basename($db_path);

    if ($is_cli) {
        echo "\n=== SQLite 接続・パターンテスト ({$db_label}) ===\n";
        printf("%-42s %-6s %5s %s\n", 'テストケース', '結果', '件数', '時間(ms)');
        echo str_repeat('─', 68) . "\n";

        foreach ($suite as $c) {
            $icon = $c['status'] === 'PASS' ? '✓' : '✗';
            printf(
                "%-42s [%s] %s %3d件  %5.1fms\n",
                mb_substr($c['label'], 0, 41),
                $c['status'], $icon, $c['count'], $c['ms']
            );
            if ($c['error']) {
                echo "    ↳ " . $c['error'] . "\n";
            }
            foreach (array_slice($c['rows'], 0, 2) as $row) {
                $line = implode(' | ', array_map(
                    fn($k, $v) => "{$k}=" . mb_substr((string)$v, 0, 24),
                    array_keys($row), $row
                ));
                echo "    " . mb_substr($line, 0, 66) . "\n";
            }
            if (count($c['rows']) > 2) {
                echo "    ... 他 " . (count($c['rows']) - 2) . " 件\n";
            }
        }
        echo str_repeat('─', 68) . "\n";
        echo "結果: {$pass} / {$total} PASS\n\n";

    } else {
        echo "<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>";
        echo "<title>SQLite テスト ({$db_label})</title>";
        echo "<style>
            body{font-family:monospace;padding:20px;background:#1e1e2e;color:#cdd6f4}
            h2{color:#89b4fa}
            .case{margin-bottom:16px;border:1px solid #313244;border-radius:6px;overflow:hidden}
            .case-header{padding:8px 14px;display:flex;gap:16px;align-items:center}
            .pass .case-header{background:#1e3a2f}
            .fail .case-header,.error .case-header{background:#3a1e1e}
            .label{flex:1;font-weight:bold}
            .badge{padding:2px 8px;border-radius:4px;font-size:.85em}
            .pass .badge{background:#a6e3a1;color:#1e1e2e}
            .fail .badge,.error .badge{background:#f38ba8;color:#1e1e2e}
            .meta{color:#9399b2;font-size:.85em}
            table{width:100%;border-collapse:collapse;font-size:.85em}
            th,td{padding:5px 10px;border:1px solid #45475a;text-align:left}
            th{background:#313244;color:#89dceb}
            tr:nth-child(even){background:#181825}
            .error-msg{padding:8px 14px;color:#f38ba8;background:#2a1a1a}
            .summary{margin-top:20px;padding:12px;background:#313244;border-radius:6px}
        </style></head><body>";
        echo "<h2>SQLite 接続・パターンテスト <small style='color:#9399b2'>{$db_label}</small></h2>";

        foreach ($suite as $c) {
            $cls = strtolower($c['status']);
            echo "<div class='case {$cls}'>";
            echo "<div class='case-header'>";
            echo "<span class='label'>" . htmlspecialchars($c['label'], ENT_QUOTES, 'UTF-8') . "</span>";
            echo "<span class='badge'>" . $c['status'] . "</span>";
            echo "<span class='meta'>{$c['count']}件 / {$c['ms']}ms</span>";
            echo "</div>";
            if ($c['error']) {
                echo "<div class='error-msg'>" . htmlspecialchars($c['error'], ENT_QUOTES, 'UTF-8') . "</div>";
            }
            if (!empty($c['rows'])) {
                $keys = array_keys($c['rows'][0]);
                echo "<table><tr>";
                foreach ($keys as $k) {
                    echo "<th>" . htmlspecialchars($k, ENT_QUOTES, 'UTF-8') . "</th>";
                }
                echo "</tr>";
                foreach (array_slice($c['rows'], 0, 5) as $row) {
                    echo "<tr>";
                    foreach ($row as $val) {
                        echo "<td>" . htmlspecialchars((string)$val, ENT_QUOTES, 'UTF-8') . "</td>";
                    }
                    echo "</tr>";
                }
                if (count($c['rows']) > 5) {
                    echo "<tr><td colspan='" . count($keys) . "' style='color:#9399b2'>... 他 " . (count($c['rows']) - 5) . " 件</td></tr>";
                }
                echo "</table>";
            }
            echo "</div>";
        }
        echo "<div class='summary'>{$pass} / {$total} PASS</div></body></html>";
    }
}

// ─────────────────────────────────────────────
// 8. エントリーポイント
// ─────────────────────────────────────────────

try {
    $pdo = create_sqlite_pdo($db_path, $pdo_options);
    setup_sqlite_schema($pdo);
    $suite = run_sqlite_tests($pdo, $db_path);
    print_sqlite_report($suite, $db_path);
} catch (RuntimeException $e) {
    $msg = htmlspecialchars($e->getMessage(), ENT_QUOTES, 'UTF-8');
    echo (php_sapi_name() === 'cli') ? "[ERROR] {$msg}\n" : "<p style='color:red'>{$msg}</p>";
} finally {
    // テーブルを残したい場合はコメントアウト
    if (isset($pdo)) {
        teardown_sqlite_schema($pdo);
    }
}