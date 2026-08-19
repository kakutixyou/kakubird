<?php
/**
 * templates/crud_template.php
 * セキュアな単一ファイルCRUDのベーステンプレート
 * (PDO, CSRF対策, XSS対策, PRGパターン実装済み)
 */
session_start();

// ====
// 1. 共通ヘルパー関数
// ====

/** XSS対策用エスケープ関数 */
function h(?string $str): string {
    return htmlspecialchars((string)$str, ENT_QUOTES, 'UTF-8');
}

/** CSRFトークン生成 */
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// ====
// 2. データベース接続設定 (PDO)
// ====
// ※ AIは要件に応じてここの接続情報やテーブル定義を書き換えます
$dbFile = __DIR__ . '/database.sqlite';
$pdo = new PDO("sqlite:{$dbFile}", null, null, [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
]);

// テーブル初期化のプレースホルダー
$pdo->exec("CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)");

// ====
// 3. ルーティング & コントローラー処理
// ====
$action = $_GET['action'] ?? 'index';
$errors = [];

// セッションメッセージの取得 (PRGパターン用)
$message = $_SESSION['message'] ?? '';
unset($_SESSION['message']);

// ---------------------------------------------------------
// POSTリクエスト処理 (Create, Update, Delete)
// ---------------------------------------------------------
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // 【重要】全POST処理共通のCSRFトークン検証
    $token = filter_input(INPUT_POST, 'csrf_token');
    if (!$token || !hash_equals($_SESSION['csrf_token'], $token)) {
        http_response_code(403);
        exit('不正なリクエストです (CSRF Token Mismatch)');
    }

    if ($action === 'create' || $action === 'edit') {
        // 入力値の取得
        $name = trim(filter_input(INPUT_POST, 'name') ?? '');
        $description = trim(filter_input(INPUT_POST, 'description') ?? '');
        
        // バリデーション
        if ($name === '') {
            $errors[] = '名前は必須です。';
        }

        if (empty($errors)) {
            if ($action === 'create') {
                $stmt = $pdo->prepare("INSERT INTO items (name, description) VALUES (:name, :desc)");
                $stmt->execute([':name' => $name, ':desc' => $description]);
                $_SESSION['message'] = '登録しました。';
            } else {
                $id = filter_input(INPUT_POST, 'id', FILTER_VALIDATE_INT);
                $stmt = $pdo->prepare("UPDATE items SET name = :name, description = :desc WHERE id = :id");
                $stmt->execute([':name' => $name, ':desc' => $description, ':id' => $id]);
                $_SESSION['message'] = '更新しました。';
            }
            header('Location: ?action=index');
            exit;
        }
    }

    if ($action === 'delete') {
        $id = filter_input(INPUT_POST, 'id', FILTER_VALIDATE_INT);
        if ($id) {
            $stmt = $pdo->prepare("DELETE FROM items WHERE id = :id");
            $stmt->execute([':id' => $id]);
            $_SESSION['message'] = '削除しました。';
        }
        header('Location: ?action=index');
        exit;
    }
}

// ---------------------------------------------------------
// GETリクエスト処理 (データ取得)
// ---------------------------------------------------------
$items = [];
$editTarget = null;

if ($action === 'index') {
    // 一覧データの取得
    $items = $pdo->query("SELECT * FROM items ORDER BY id DESC")->fetchAll();
} elseif ($action === 'edit') {
    // 編集対象データの取得
    $id = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
    if ($id) {
        $stmt = $pdo->prepare("SELECT * FROM items WHERE id = :id");
        $stmt->execute([':id' => $id]);
        $editTarget = $stmt->fetch();
    }
    if (!$editTarget) {
        $_SESSION['message'] = '対象のデータが見つかりません。';
        header('Location: ?action=index');
        exit;
    }
}

// ====
// 4. ビュー (HTML)
// ====
?>
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>CRUD Application</title>
    <style>
        body { font-family: sans-serif; margin: 20px; line-height: 1.6; }
        table { border-collapse: collapse; width: 100%; margin-bottom: 20px; }
        th, td { border: 1px solid #ccc; padding: 8px; text-align: left; }
        th { background-color: #f4f4f4; }
        .alert { padding: 10px; margin-bottom: 15px; border-radius: 4px; background-color: #d4edda; color: #155724; }
        .error { color: red; margin-bottom: 15px; }
        .form-group { margin-bottom: 15px; }
        .btn { padding: 5px 10px; cursor: pointer; text-decoration: none; border: 1px solid #ccc; background: #eee; color: #333; }
        .btn-danger { background: #f8d7da; color: #721c24; border-color: #f5c6cb; }
        /* 削除ボタンをリンクのように見せず、安全なPOSTフォームにするためのスタイル */
        .delete-form { display: inline; }
    </style>
</head>
<body>

    <h1>CRUD 管理画面</h1>

    <?php if ($message): ?>
        <div class="alert"><?= h($message) ?></div>
    <?php endif; ?>

    <?php if (!empty($errors)): ?>
        <div class="error">
            <ul>
                <?php foreach ($errors as $err): ?><li><?= h($err) ?></li><?php endforeach; ?>
            </ul>
        </div>
    <?php endif; ?>

    <?php if ($action === 'index'): ?>
        <div style="margin-bottom: 15px;">
            <a href="?action=create" class="btn">＋ 新規登録</a>
        </div>

        <table>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>名前</th>
                    <th>説明</th>
                    <th>登録日</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                <?php foreach ($items as $item): ?>
                    <tr>
                        <td><?= h($item['id']) ?></td>
                        <td><?= h($item['name']) ?></td>
                        <td><?= h($item['description']) ?></td>
                        <td><?= h($item['created_at']) ?></td>
                        <td>
                            <a href="?action=edit&id=<?= h($item['id']) ?>" class="btn">編集</a>
                            
                            <form action="?action=delete" method="POST" class="delete-form" onsubmit="return confirm('本当に削除しますか？');">
                                <input type="hidden" name="csrf_token" value="<?= h($_SESSION['csrf_token']) ?>">
                                <input type="hidden" name="id" value="<?= h($item['id']) ?>">
                                <button type="submit" class="btn btn-danger">削除</button>
                            </form>
                        </td>
                    </tr>
                <?php endforeach; ?>
                <?php if (empty($items)): ?>
                    <tr><td colspan="5">データがありません。</td></tr>
                <?php endif; ?>
            </tbody>
        </table>

    <?php elseif ($action === 'create' || $action === 'edit'): ?>
        <h2><?= $action === 'create' ? '新規登録' : '編集' ?></h2>
        
        <form action="?action=<?= h($action) ?>" method="POST">
            <input type="hidden" name="csrf_token" value="<?= h($_SESSION['csrf_token']) ?>">
            
            <?php if ($action === 'edit'): ?>
                <input type="hidden" name="id" value="<?= h($editTarget['id']) ?>">
            <?php endif; ?>

            <div class="form-group">
                <label>名前 (必須):</label><br>
                <input type="text" name="name" value="<?= h($_POST['name'] ?? $editTarget['name'] ?? '') ?>" required>
            </div>

            <div class="form-group">
                <label>説明:</label><br>
                <textarea name="description" rows="4"><?= h($_POST['description'] ?? $editTarget['description'] ?? '') ?></textarea>
            </div>

            <button type="submit" class="btn"><?= $action === 'create' ? '登録する' : '更新する' ?></button>
            <a href="?action=index" style="margin-left: 10px;">キャンセル</a>
        </form>
    <?php endif; ?>

</body>
</html>