<?php
/**
 * plugins/php_engine/sandbox/database/select_test.php
 *
 * SELECTパターン検証サンドボックス
 * ─────────────────────────────────────────────
 * 目的  : php_engineがSELECTパターンの動作確認・テンプレート参照に使うサンプル
 * 用途  : Phase B の sandbox参照 / 企画書のクエリ例として出力
 * 前提  : mysql_connect.php の get_pdo() を利用
 * 実行  : php select_test.php [--pattern all|basic|join|page|search|agg]
 */

declare(strict_types=1);

require_once __DIR__ . '/mysql_connect.php';

// ─────────────────────────────────────────────
// テスト用スキーマ・データセットアップ
// ─────────────────────────────────────────────

/**
 * テスト用の一時テーブルを作成してサンプルデータを投入する。
 * テーブルが既に存在する場合はスキップ。
 */
function setup_test_schema(PDO $pdo): void
{
    // users
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS _test_users (
            id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
            name       VARCHAR(100) NOT NULL,
            email      VARCHAR(255) NOT NULL,
            role       ENUM('admin','user','guest') NOT NULL DEFAULT 'user',
            age        TINYINT UNSIGNED NOT NULL DEFAULT 20,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME NULL,
            PRIMARY KEY (id),
            UNIQUE KEY uq_email (email)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // posts
    $pdo->exec("
        CREATE TABLE IF NOT EXISTS _test_posts (
            id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
            user_id    INT UNSIGNED NOT NULL,
            title      VARCHAR(255) NOT NULL,
            body       TEXT NOT NULL,
            status     ENUM('draft','published') NOT NULL DEFAULT 'draft',
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            deleted_at DATETIME NULL,
            PRIMARY KEY (id),
            INDEX idx_user_id (user_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    ");

    // 既にデータがあれば挿入しない
    $count = (int) $pdo->query('SELECT COUNT(*) FROM _test_users')->fetchColumn();
    if ($count > 0) {
        return;
    }

    // ── サンプルユーザー ──
    $users = [
        ['田中 太郎',   'taro@example.com',   'admin', 35],
        ['鈴木 花子',   'hanako@example.com', 'user',  28],
        ['佐藤 次郎',   'jiro@example.com',   'user',  42],
        ['高橋 三郎',   'saburo@example.com', 'guest', 19],
        ['渡辺 四郎',   'shiro@example.com',  'user',  31],
        ['伊藤 削除済', 'deleted@example.com','user',  25],
    ];

    $stmt_u = $pdo->prepare(
        'INSERT INTO _test_users (name, email, role, age) VALUES (?, ?, ?, ?)'
    );
    foreach ($users as $u) {
        $stmt_u->execute($u);
    }

    // 最後のユーザーを論理削除
    $pdo->exec("UPDATE _test_users SET deleted_at = NOW() WHERE email = 'deleted@example.com'");

    // ── サンプル投稿 ──
    $posts = [
        [1, 'PHPセキュリティ入門',      'SQLインジェクション対策の基本を解説します。',     'published'],
        [1, 'PDOの使い方',              'プリペアドステートメントのベストプラクティス。',   'published'],
        [2, 'MySQLインデックス最適化',  'クエリパフォーマンスを劇的に改善する方法。',       'published'],
        [2, '下書き記事',               'まだ公開していない記事です。',                     'draft'],
        [3, 'PHPとAIの連携',            'OllamaをPHPから呼び出す実装例。',                  'published'],
        [5, 'セッション管理のベスト',   '安全なセッション設計について。',                   'published'],
    ];

    $stmt_p = $pdo->prepare(
        'INSERT INTO _test_posts (user_id, title, body, status) VALUES (?, ?, ?, ?)'
    );
    foreach ($posts as $p) {
        $stmt_p->execute($p);
    }
}

/**
 * テスト終了後に一時テーブルを削除する。
 */
function teardown_test_schema(PDO $pdo): void
{
    $pdo->exec('DROP TABLE IF EXISTS _test_posts');
    $pdo->exec('DROP TABLE IF EXISTS _test_users');
}


// ─────────────────────────────────────────────
// SELECTパターン群
// ─────────────────────────────────────────────

/**
 * パターン1: 全件取得 + 論理削除除外
 */
function pattern_basic_select(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT id, name, email, role
         FROM _test_users
         WHERE deleted_at IS NULL
         ORDER BY id ASC'
    );
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン2: 単一条件・プリペアドステートメント
 */
function pattern_where_single(PDO $pdo, int $user_id): array|false
{
    $stmt = $pdo->prepare(
        'SELECT id, name, email, role, age
         FROM _test_users
         WHERE id = :id AND deleted_at IS NULL'
    );
    $stmt->execute([':id' => $user_id]);
    return $stmt->fetch();
}

/**
 * パターン3: 複数条件（role + age範囲）
 */
function pattern_where_multi(PDO $pdo, string $role, int $min_age, int $max_age): array
{
    $stmt = $pdo->prepare(
        'SELECT id, name, age, role
         FROM _test_users
         WHERE role = :role
           AND age BETWEEN :min_age AND :max_age
           AND deleted_at IS NULL
         ORDER BY age ASC'
    );
    $stmt->execute([
        ':role'    => $role,
        ':min_age' => $min_age,
        ':max_age' => $max_age,
    ]);
    return $stmt->fetchAll();
}

/**
 * パターン4: INNER JOIN（ユーザーと投稿の結合）
 */
function pattern_inner_join(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT u.id   AS user_id,
                u.name AS user_name,
                p.id   AS post_id,
                p.title,
                p.status,
                p.created_at
         FROM _test_users u
         INNER JOIN _test_posts p ON u.id = p.user_id
         WHERE p.status  = :status
           AND u.deleted_at IS NULL
           AND p.deleted_at IS NULL
         ORDER BY p.created_at DESC'
    );
    $stmt->bindValue(':status', 'published', PDO::PARAM_STR);
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン5: LEFT JOIN（投稿がないユーザーも取得）
 */
function pattern_left_join(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT u.id,
                u.name,
                COUNT(p.id) AS post_count
         FROM _test_users u
         LEFT JOIN _test_posts p
            ON u.id = p.user_id AND p.deleted_at IS NULL
         WHERE u.deleted_at IS NULL
         GROUP BY u.id, u.name
         ORDER BY post_count DESC'
    );
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン6: ページネーション（LIMIT + OFFSET）
 */
function pattern_pagination(PDO $pdo, int $page = 1, int $per_page = 3): array
{
    $offset = ($page - 1) * $per_page;

    // 総件数
    $total = (int) $pdo->query(
        'SELECT COUNT(*) FROM _test_posts WHERE deleted_at IS NULL'
    )->fetchColumn();

    // データ取得
    $stmt = $pdo->prepare(
        'SELECT id, title, status, created_at
         FROM _test_posts
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
 * パターン7: LIKE検索（タイトル・本文のあいまい検索）
 */
function pattern_like_search(PDO $pdo, string $keyword): array
{
    // % と _ と \ をエスケープ
    $escaped = str_replace(['\\', '%', '_'], ['\\\\', '\\%', '\\_'], $keyword);
    $like    = '%' . $escaped . '%';

    $stmt = $pdo->prepare(
        'SELECT p.id, p.title, u.name AS author
         FROM _test_posts p
         INNER JOIN _test_users u ON p.user_id = u.id
         WHERE (p.title LIKE :kw OR p.body LIKE :kw)
           AND p.status     = \'published\'
           AND p.deleted_at IS NULL
         ORDER BY p.created_at DESC
         LIMIT 20'
    );
    $stmt->bindValue(':kw', $like, PDO::PARAM_STR);
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン8: IN句（複数IDの一括取得）
 */
function pattern_in_clause(PDO $pdo, array $ids): array
{
    if (empty($ids)) {
        return [];
    }

    $placeholders = implode(',', array_fill(0, count($ids), '?'));
    $stmt = $pdo->prepare(
        "SELECT id, name, email
         FROM _test_users
         WHERE id IN ({$placeholders})
           AND deleted_at IS NULL"
    );
    $stmt->execute(array_values($ids));
    return $stmt->fetchAll();
}

/**
 * パターン9: 集計（COUNT + GROUP BY + HAVING）
 */
function pattern_aggregate(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT role,
                COUNT(*)    AS user_count,
                AVG(age)    AS avg_age,
                MIN(age)    AS min_age,
                MAX(age)    AS max_age
         FROM _test_users
         WHERE deleted_at IS NULL
         GROUP BY role
         HAVING COUNT(*) >= :min_count
         ORDER BY user_count DESC'
    );
    $stmt->bindValue(':min_count', 1, PDO::PARAM_INT);
    $stmt->execute();
    return $stmt->fetchAll();
}

/**
 * パターン10: サブクエリ（投稿を持つユーザーのみ取得）
 */
function pattern_subquery(PDO $pdo): array
{
    $stmt = $pdo->prepare(
        'SELECT id, name, email
         FROM _test_users u
         WHERE deleted_at IS NULL
           AND EXISTS (
               SELECT 1 FROM _test_posts p
               WHERE p.user_id    = u.id
                 AND p.status     = :status
                 AND p.deleted_at IS NULL
           )
         ORDER BY id ASC'
    );
    $stmt->execute([':status' => 'published']);
    return $stmt->fetchAll();
}


// ─────────────────────────────────────────────
// テストランナー
// ─────────────────────────────────────────────

/**
 * 全パターンを実行してレポートを構築する。
 */
function run_all_patterns(PDO $pdo): array
{
    $suite = [];

    // 1. 基本SELECT
    $suite[] = run_case('基本SELECT（論理削除除外）', function () use ($pdo) {
        $rows = pattern_basic_select($pdo);
        assert_count($rows, 5, '削除済み1件を除いた5件が返る');
        return $rows;
    });

    // 2. 単一WHERE
    $suite[] = run_case('単一条件 WHERE id=1', function () use ($pdo) {
        $row = pattern_where_single($pdo, 1);
        assert_equals($row['name'] ?? '', '田中 太郎', 'id=1は田中太郎');
        return $row ? [$row] : [];
    });

    // 3. 存在しないID
    $suite[] = run_case('存在しないID (id=999)', function () use ($pdo) {
        $row = pattern_where_single($pdo, 999);
        assert_equals($row, false, 'falseが返る');
        return [];
    });

    // 4. 複数条件
    $suite[] = run_case('複数条件 role=user AND age 20-35', function () use ($pdo) {
        $rows = pattern_where_multi($pdo, 'user', 20, 35);
        assert_min_count($rows, 1, '1件以上のuserが返る');
        return $rows;
    });

    // 5. INNER JOIN
    $suite[] = run_case('INNER JOIN（公開投稿+著者）', function () use ($pdo) {
        $rows = pattern_inner_join($pdo);
        assert_min_count($rows, 1, 'JOINで投稿が取得できる');
        assert_has_key($rows[0] ?? [], 'user_name', 'user_nameカラムが存在する');
        return $rows;
    });

    // 6. LEFT JOIN + 集計
    $suite[] = run_case('LEFT JOIN（投稿数カウント）', function () use ($pdo) {
        $rows = pattern_left_join($pdo);
        assert_min_count($rows, 1, '全ユーザーが返る');
        return $rows;
    });

    // 7. ページネーション
    $suite[] = run_case('ページネーション（page=1, per_page=3）', function () use ($pdo) {
        $result = pattern_pagination($pdo, 1, 3);
        assert_equals(count($result['data']), 3, 'page=1は3件');
        assert_equals($result['total_pages'], 2, '総ページ数=2');
        return $result['data'];
    });

    // 8. LIKE検索
    $suite[] = run_case('LIKE検索「PHP」', function () use ($pdo) {
        $rows = pattern_like_search($pdo, 'PHP');
        assert_min_count($rows, 1, 'PHPを含む投稿が返る');
        return $rows;
    });

    // 9. IN句
    $suite[] = run_case('IN句（id=[1,2,3]）', function () use ($pdo) {
        $rows = pattern_in_clause($pdo, [1, 2, 3]);
        assert_count($rows, 3, '3件返る');
        return $rows;
    });

    // 10. IN句に空配列
    $suite[] = run_case('IN句（空配列 → 空結果）', function () use ($pdo) {
        $rows = pattern_in_clause($pdo, []);
        assert_count($rows, 0, '空配列なら0件');
        return $rows;
    });

    // 11. 集計
    $suite[] = run_case('集計（role別 COUNT/AVG/MIN/MAX）', function () use ($pdo) {
        $rows = pattern_aggregate($pdo);
        assert_min_count($rows, 1, '1ロール以上が集計される');
        assert_has_key($rows[0] ?? [], 'avg_age', 'avg_ageカラムが存在する');
        return $rows;
    });

    // 12. サブクエリ
    $suite[] = run_case('サブクエリ EXISTS（公開投稿を持つユーザー）', function () use ($pdo) {
        $rows = pattern_subquery($pdo);
        assert_min_count($rows, 1, '1件以上返る');
        return $rows;
    });

    return $suite;
}


// ─────────────────────────────────────────────
// アサーション
// ─────────────────────────────────────────────

function assert_count(array $rows, int $expected, string $msg): void
{
    if (count($rows) !== $expected) {
        throw new AssertionError("{$msg} （期待: {$expected}, 実際: " . count($rows) . '）');
    }
}

function assert_min_count(array $rows, int $min, string $msg): void
{
    if (count($rows) < $min) {
        throw new AssertionError("{$msg} （期待: {$min}件以上, 実際: " . count($rows) . '）');
    }
}

function assert_equals(mixed $actual, mixed $expected, string $msg): void
{
    if ($actual !== $expected) {
        $a = is_bool($actual) ? ($actual ? 'true' : 'false') : (string)$actual;
        $e = is_bool($expected) ? ($expected ? 'true' : 'false') : (string)$expected;
        throw new AssertionError("{$msg} （期待: {$e}, 実際: {$a}）");
    }
}

function assert_has_key(array $row, string $key, string $msg): void
{
    if (!array_key_exists($key, $row)) {
        throw new AssertionError("{$msg} （キー '{$key}' が存在しない）");
    }
}


// ─────────────────────────────────────────────
// ケース実行ラッパー
// ─────────────────────────────────────────────

function run_case(string $label, callable $fn): array
{
    $t0 = microtime(true);
    try {
        $rows   = $fn();
        $ms     = round((microtime(true) - $t0) * 1000, 2);
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
        return [
            'label'  => $label,
            'status' => 'FAIL',
            'rows'   => [],
            'count'  => 0,
            'ms'     => $ms,
            'error'  => $e->getMessage(),
        ];
    } catch (Throwable $e) {
        $ms = round((microtime(true) - $t0) * 1000, 2);
        return [
            'label'  => $label,
            'status' => 'ERROR',
            'rows'   => [],
            'count'  => 0,
            'ms'     => $ms,
            'error'  => $e->getMessage(),
        ];
    }
}


// ─────────────────────────────────────────────
// 出力
// ─────────────────────────────────────────────

function print_report(array $suite): void
{
    $is_cli = (php_sapi_name() === 'cli');
    $pass   = count(array_filter($suite, fn($c) => $c['status'] === 'PASS'));
    $total  = count($suite);

    if ($is_cli) {
        echo "\n=== SELECT パターンテスト ===\n";
        printf("%-45s %-6s %6s %s\n", 'テストケース', '結果', '件数', '時間(ms)');
        echo str_repeat('─', 72) . "\n";

        foreach ($suite as $c) {
            $icon = $c['status'] === 'PASS' ? '✓' : '✗';
            printf(
                "%-45s [%s] %s %4d件  %5.1fms\n",
                mb_substr($c['label'], 0, 44),
                $c['status'],
                $icon,
                $c['count'],
                $c['ms']
            );
            if ($c['error']) {
                echo "    ↳ " . $c['error'] . "\n";
            }
            // 最初の3行だけプレビュー表示
            if (!empty($c['rows'])) {
                $preview = array_slice($c['rows'], 0, 2);
                foreach ($preview as $row) {
                    $line = implode(' | ', array_map(
                        fn($k, $v) => "{$k}=" . mb_substr((string)$v, 0, 20),
                        array_keys($row), $row
                    ));
                    echo "    " . mb_substr($line, 0, 68) . "\n";
                }
                if (count($c['rows']) > 2) {
                    echo "    ... 他 " . (count($c['rows']) - 2) . " 件\n";
                }
            }
        }

        echo str_repeat('─', 72) . "\n";
        echo "結果: {$pass} / {$total} PASS\n\n";

    } else {
        echo "<!DOCTYPE html><html lang='ja'><head><meta charset='UTF-8'>";
        echo "<title>SELECT パターンテスト</title>";
        echo "<style>
            body{font-family:monospace;padding:20px;background:#1e1e2e;color:#cdd6f4}
            h2{color:#89b4fa}
            .case{margin-bottom:18px;border:1px solid #313244;border-radius:6px;overflow:hidden}
            .case-header{padding:8px 14px;display:flex;gap:16px;align-items:center}
            .pass .case-header{background:#1e3a2f}
            .fail .case-header,.error .case-header{background:#3a1e1e}
            .label{flex:1;font-weight:bold}
            .badge{padding:2px 8px;border-radius:4px;font-size:0.85em}
            .pass .badge{background:#a6e3a1;color:#1e1e2e}
            .fail .badge,.error .badge{background:#f38ba8;color:#1e1e2e}
            .meta{color:#9399b2;font-size:0.85em}
            table{width:100%;border-collapse:collapse;font-size:0.85em}
            th,td{padding:5px 10px;border:1px solid #45475a;text-align:left}
            th{background:#313244;color:#89dceb}
            tr:nth-child(even){background:#181825}
            .error-msg{padding:8px 14px;color:#f38ba8;background:#2a1a1a}
            .summary{margin-top:20px;padding:12px;background:#313244;border-radius:6px}
        </style></head><body>";
        echo "<h2>SELECT パターンテスト</h2>";

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
                    $rest = count($c['rows']) - 5;
                    echo "<tr><td colspan='" . count($keys) . "' style='color:#9399b2'>... 他 {$rest} 件</td></tr>";
                }
                echo "</table>";
            }

            echo "</div>";
        }

        echo "<div class='summary'>{$pass} / {$total} PASS</div>";
        echo "</body></html>";
    }
}


// ─────────────────────────────────────────────
// エントリーポイント
// ─────────────────────────────────────────────

try {
    $pdo = get_pdo();
    setup_test_schema($pdo);
    $suite = run_all_patterns($pdo);
    print_report($suite);
} catch (RuntimeException $e) {
    $msg = htmlspecialchars($e->getMessage(), ENT_QUOTES, 'UTF-8');
    if (php_sapi_name() === 'cli') {
        echo "[ERROR] {$msg}\n";
    } else {
        echo "<p style='color:red'>{$msg}</p>";
    }
} finally {
    // テスト用テーブルを削除（不要な場合はコメントアウト）
    if (isset($pdo)) {
        teardown_test_schema($pdo);
    }
}