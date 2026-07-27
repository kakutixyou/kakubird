<?php
/**
 * sandbox/ui/form.php
 * 安全なフォーム処理のサンプル（CSRF対策、XSS対策、バリデーション、PRGパターン）
 */
session_start();

// 1. CSRFトークンの生成（フォームに埋め込む用）
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// メッセージ格納用変数
$errors = [];
$successMessage = '';

// セッションに保存されたメッセージ（PRGパターン用）の取得と破棄
if (isset($_SESSION['success'])) {
    $successMessage = $_SESSION['success'];
    unset($_SESSION['success']);
}
if (isset($_SESSION['errors'])) {
    $errors = $_SESSION['errors'];
    unset($_SESSION['errors']);
}

// 2. POSTリクエストの処理
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // CSRFトークンの検証
    $token = filter_input(INPUT_POST, 'csrf_token');
    if (!$token || !hash_equals($_SESSION['csrf_token'], $token)) {
        // トークンが一致しない場合は処理を中断（セキュリティ対策）
        http_response_code(403);
        exit('不正なリクエストです (CSRF Token Mismatch)');
    }

    // 入力値の取得とバリデーション (filter_inputを使用)
    $name = filter_input(INPUT_POST, 'name', FILTER_DEFAULT) ?? '';
    $name = trim($name);
    
    $email = filter_input(INPUT_POST, 'email', FILTER_VALIDATE_EMAIL);
    
    $age = filter_input(INPUT_POST, 'age', FILTER_VALIDATE_INT);

    // バリデーションチェック
    if ($name === '') {
        $errors[] = '名前を入力してください。';
    }
    if (!$email) {
        $errors[] = '有効なメールアドレスを入力してください。';
    }
    if ($age === false || $age < 0 || $age > 150) {
        $errors[] = '正しい年齢を入力してください。';
    }

    // 3. エラーがなければ処理を実行してリダイレクト（PRGパターン）
    if (empty($errors)) {
        // --- ここにDB保存(INSERT)などのビジネスロジックを書く ---
        
        // 処理成功メッセージをセッションに入れてリダイレクト（二重送信防止）
        $_SESSION['success'] = "{$name}さんのデータを登録しました！";
        header('Location: form.php');
        exit;
    } else {
        // エラーがある場合もセッションに入れてリダイレクト
        $_SESSION['errors'] = $errors;
        header('Location: form.php');
        exit;
    }
}
?>
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>セキュアなフォーム入力</title>
    <style>
        .error { color: red; margin-bottom: 10px; }
        .success { color: green; font-weight: bold; margin-bottom: 10px; }
        .form-group { margin-bottom: 15px; }
    </style>
</head>
<body>
    <h1>ユーザー登録フォーム</h1>

    <?php if ($successMessage): ?>
        <div class="success"><?= htmlspecialchars($successMessage, ENT_QUOTES, 'UTF-8') ?></div>
    <?php endif; ?>

    <?php if (!empty($errors)): ?>
        <div class="error">
            <ul>
                <?php foreach ($errors as $err): ?>
                    <li><?= htmlspecialchars($err, ENT_QUOTES, 'UTF-8') ?></li>
                <?php endforeach; ?>
            </ul>
        </div>
    <?php endif; ?>

    <form action="form.php" method="POST">
        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($_SESSION['csrf_token'], ENT_QUOTES, 'UTF-8') ?>">

        <div class="form-group">
            <label for="name">名前:</label>
            <input type="text" id="name" name="name" required>
        </div>

        <div class="form-group">
            <label for="email">メールアドレス:</label>
            <input type="email" id="email" name="email" required>
        </div>

        <div class="form-group">
            <label for="age">年齢:</label>
            <input type="number" id="age" name="age" min="0" max="150" required>
        </div>

        <button type="submit">登録する</button>
    </form>
</body>
</html>