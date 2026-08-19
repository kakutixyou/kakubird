<?php
/**
 * templates/login_template.php
 * セキュアなログイン・認証・セッション管理のベーステンプレート
 * (パスワードハッシュ、セッションID再生成、タイムアウト、総当たり攻撃対策を含む)
 */

// ====
// 1. セキュアなセッション設定
// ====
// session_start() の前に、Cookieのセキュリティ属性を強制する
session_set_cookie_params([
    'lifetime' => 0,             // ブラウザを閉じるまで
    'path'     => '/',
    'secure'   => true,          // 本番環境(HTTPS)では必須
    'httponly' => true,          // JavaScriptからのアクセスを禁止(XSS対策)
    'samesite' => 'Strict'       // CSRF対策
]);
session_start();

// CSRFトークン生成
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// XSS対策用ヘルパー
function h(?string $str): string {
    return htmlspecialchars((string)$str, ENT_QUOTES, 'UTF-8');
}

// ====
// 2. データベース接続設定 (PDO)
// ====
$dbFile = __DIR__ . '/auth_database.sqlite';
$pdo = new PDO("sqlite:{$dbFile}", null, null, [
    PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
    PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    PDO::ATTR_EMULATE_PREPARES   => false,
]);

// テーブル初期化のプレースホルダー (※実際の登録時は password_hash($pass, PASSWORD_BCRYPT) を使用すること)
$pdo->exec("CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    failed_attempts INTEGER DEFAULT 0,
    locked_until DATETIME DEFAULT NULL
)");

// ====
// 3. ルーティング & 認証処理
// ====
$action = $_GET['action'] ?? 'login';
$error = '';
$message = $_SESSION['message'] ?? '';
unset($_SESSION['message']);

// ---------------------------------------------------------
// タイムアウトチェック (保護されたページ向け)
// ---------------------------------------------------------
$timeout_duration = 1800; // 30分
if (isset($_SESSION['LAST_ACTIVITY']) && (time() - $_SESSION['LAST_ACTIVITY']) > $timeout_duration) {
    // タイムアウト時は強制ログアウト処理へ
    $action = 'logout';
    $_SESSION['message'] = 'セッションの有効期限が切れました。再度ログインしてください。';
}
$_SESSION['LAST_ACTIVITY'] = time(); // アクセスごとに時間を更新

// ---------------------------------------------------------
// POSTリクエスト: ログイン処理
// ---------------------------------------------------------
if ($action === 'login' && $_SERVER['REQUEST_METHOD'] === 'POST') {
    $token = filter_input(INPUT_POST, 'csrf_token');
    if (!$token || !hash_equals($_SESSION['csrf_token'], $token)) {
        http_response_code(403);
        exit('不正なリクエストです');
    }

    $email = filter_input(INPUT_POST, 'email', FILTER_VALIDATE_EMAIL);
    $password = filter_input(INPUT_POST, 'password') ?? '';

    if (!$email || $password === '') {
        $error = 'メールアドレスとパスワードを入力してください。';
    } else {
        // ユーザー取得とブルートフォース(総当たり)対策のチェック
        $stmt = $pdo->prepare("SELECT * FROM users WHERE email = :email");
        $stmt->execute([':email' => $email]);
        $user = $stmt->fetch();

        if ($user) {
            // アカウントロック状態の確認
            if ($user['failed_attempts'] >= 5 && strtotime($user['locked_until']) > time()) {
                $error = 'アカウントがロックされています。しばらく経ってから再試行してください。';
            } else {
                // パスワードの検証
                if (password_verify($password, $user['password_hash'])) {
                    // 【重要】ログイン成功時のセッション固定攻撃対策
                    session_regenerate_id(true);
                    
                    // 失敗カウントのリセット
                    $pdo->prepare("UPDATE users SET failed_attempts = 0, locked_until = NULL WHERE id = :id")
                        ->execute([':id' => $user['id']]);

                    // セッションにユーザー情報を保存
                    $_SESSION['user_id'] = $user['id'];
                    $_SESSION['user_email'] = $user['email'];
                    
                    header('Location: ?action=dashboard');
                    exit;
                } else {
                    // ログイン失敗: 失敗カウントを増やす
                    $stmt = $pdo->prepare("UPDATE users SET failed_attempts = failed_attempts + 1, locked_until = datetime('now', '+15 minutes') WHERE id = :id");
                    $stmt->execute([':id' => $user['id']]);
                    // セキュリティ上、どちらが間違っているかは教えない
                    $error = 'メールアドレスまたはパスワードが間違っています。';
                }
            }
        } else {
            // ユーザーが存在しない場合も同じエラーメッセージを返す (アカウント探索攻撃対策)
            $error = 'メールアドレスまたはパスワードが間違っています。';
        }
    }
}

// ---------------------------------------------------------
// ログアウト処理
// ---------------------------------------------------------
if ($action === 'logout') {
    // セッション変数のクリア
    $_SESSION = [];
    // セッションCookieの破棄
    if (ini_get('session.use_cookies')) {
        $params = session_get_cookie_params();
        setcookie(session_name(), '', time() - 42000,
            $params['path'], $params['domain'],
            $params['secure'], $params['httponly']
        );
    }
    // セッションファイルの破棄
    session_destroy();
    
    // ログアウト完了後は強制的に新規セッションを開始してメッセージを渡す
    session_start();
    $_SESSION['message'] = $message ?: 'ログアウトしました。';
    header('Location: ?action=login');
    exit;
}

// ---------------------------------------------------------
// 保護されたページ (ダッシュボード) のアクセス制御
// ---------------------------------------------------------
if ($action === 'dashboard') {
    if (empty($_SESSION['user_id'])) {
        $_SESSION['message'] = 'このページにアクセスするにはログインが必要です。';
        header('Location: ?action=login');
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
    <title>ログインシステム</title>
    <style>
        body { font-family: sans-serif; background-color: #f4f7f6; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; }
        .container { background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); width: 100%; max-width: 400px; }
        h1 { font-size: 20px; text-align: center; margin-bottom: 20px; }
        .form-group { margin-bottom: 15px; }
        .form-group label { display: block; margin-bottom: 5px; color: #555; }
        .form-group input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        .btn { width: 100%; padding: 10px; background: #0056b3; color: white; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
        .btn:hover { background: #004494; }
        .alert { padding: 10px; margin-bottom: 15px; border-radius: 4px; background-color: #d4edda; color: #155724; }
        .error { padding: 10px; margin-bottom: 15px; border-radius: 4px; background-color: #f8d7da; color: #721c24; }
        .logout-link { display: block; text-align: center; margin-top: 20px; color: #d9534f; text-decoration: none; }
    </style>
</head>
<body>

<div class="container">
    <?php if ($message): ?>
        <div class="alert"><?= h($message) ?></div>
    <?php endif; ?>

    <?php if ($action === 'login'): ?>
        <h1>ログイン</h1>
        
        <?php if ($error): ?>
            <div class="error"><?= h($error) ?></div>
        <?php endif; ?>

        <form action="?action=login" method="POST">
            <input type="hidden" name="csrf_token" value="<?= h($_SESSION['csrf_token']) ?>">
            
            <div class="form-group">
                <label for="email">メールアドレス</label>
                <input type="email" id="email" name="email" required autofocus>
            </div>
            
            <div class="form-group">
                <label for="password">パスワード</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit" class="btn">ログイン</button>
        </form>

    <?php elseif ($action === 'dashboard'): ?>
        <h1>ダッシュボード</h1>
        <p>ようこそ、<strong><?= h($_SESSION['user_email']) ?></strong> さん！</p>
        <p>認証が必要なセキュアなコンテンツがここに表示されます。</p>
        
        <a href="?action=logout" class="logout-link">ログアウト</a>
    <?php endif; ?>
</div>

</body>
</html>