<?php
/**
 * sandbox/ui/upload.php
 * 安全なファイルアップロードのサンプル
 * （拡張子偽装対策、ディレクトリトラバーサル対策、CSRF対策を含む）
 */
session_start();

// 1. CSRFトークンの生成
if (empty($_SESSION['csrf_token'])) {
    $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
}

// アプリケーションの設定
const MAX_FILE_SIZE = 1024 * 1024 * 2; // 最大2MB
const UPLOAD_DIR = __DIR__ . '/uploads/';

// 保存先ディレクトリが存在しない場合は作成
if (!is_dir(UPLOAD_DIR)) {
    mkdir(UPLOAD_DIR, 0755, true);
}

// PRG（Post/Redirect/Get）パターン用のメッセージ取得
$message = '';
$isSuccess = false;
if (isset($_SESSION['upload_message'])) {
    $message = $_SESSION['upload_message'];
    $isSuccess = $_SESSION['upload_success'];
    unset($_SESSION['upload_message'], $_SESSION['upload_success']);
}

// 2. アップロード処理の実行
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    try {
        // --- A. セキュリティ検証 ---
        $token = filter_input(INPUT_POST, 'csrf_token');
        if (!$token || !hash_equals($_SESSION['csrf_token'], $token)) {
            throw new RuntimeException('不正なリクエストです (CSRF Token Mismatch)');
        }

        // 未定義、複数ファイル攻撃、ファイル破損攻撃のチェック
        if (!isset($_FILES['upfile']['error']) || !is_int($_FILES['upfile']['error'])) {
            throw new RuntimeException('パラメータが不正です');
        }

        // --- B. アップロードエラーコードの確認 ---
        switch ($_FILES['upfile']['error']) {
            case UPLOAD_ERR_OK: // 成功
                break;
            case UPLOAD_ERR_NO_FILE:
                throw new RuntimeException('ファイルが選択されていません');
            case UPLOAD_ERR_INI_SIZE:
            case UPLOAD_ERR_FORM_SIZE:
                throw new RuntimeException('ファイルサイズが大きすぎます');
            default:
                throw new RuntimeException('予期せぬエラーが発生しました');
        }

        // --- C. ファイルサイズの検証 ---
        if ($_FILES['upfile']['size'] > MAX_FILE_SIZE) {
            throw new RuntimeException('ファイルサイズは2MB以下にしてください');
        }

        // --- D. MIMEタイプの厳格なチェック (超重要) ---
        // ※ $_FILES['upfile']['type'] はブラウザが送信する値なので絶対に信用しない
        // finfoを使ってサーバー側で実際のファイルの中身からMIMEタイプを判定する
        $finfo = new finfo(FILEINFO_MIME_TYPE);
        $mime = $finfo->file($_FILES['upfile']['tmp_name']);

        // 許可するMIMEタイプと対応する安全な拡張子を定義
        $allowedTypes = [
            'jpg' => 'image/jpeg',
            'png' => 'image/png',
            'gif' => 'image/gif',
        ];
        
        $ext = array_search($mime, $allowedTypes, true);
        if ($ext === false) {
            throw new RuntimeException('許可されていないファイル形式です。画像(JPG, PNG, GIF)のみアップロード可能です');
        }

        // --- E. 安全なファイル名の生成 ---
        // オリジナルのファイル名($_FILES['upfile']['name'])はディレクトリトラバーサルや
        // XSSの危険があるため完全に破棄する。代わりにファイルの中身のハッシュ値を使う。
        $newFilename = sprintf('%s.%s', sha1_file($_FILES['upfile']['tmp_name']), $ext);
        $destination = UPLOAD_DIR . $newFilename;

        // --- F. ファイルの移動 ---
        if (!move_uploaded_file($_FILES['upfile']['tmp_name'], $destination)) {
            throw new RuntimeException('ファイルの保存に失敗しました');
        }

        // 成功時の処理
        $_SESSION['upload_message'] = "ファイルのアップロードに成功しました！ (保存名: {$newFilename})";
        $_SESSION['upload_success'] = true;

    } catch (RuntimeException $e) {
        // エラー時の処理
        $_SESSION['upload_message'] = $e->getMessage();
        $_SESSION['upload_success'] = false;
    }

    // 二重送信防止のためのリダイレクト (PRGパターン)
    header('Location: upload.php');
    exit;
}
?>
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>セキュアなファイルアップロード</title>
    <style>
        .message { padding: 10px; margin-bottom: 15px; border-radius: 5px; }
        .success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
        .form-group { margin-bottom: 15px; }
    </style>
</head>
<body>
    <h1>画像アップロード</h1>

    <?php if ($message): ?>
        <div class="message <?= $isSuccess ? 'success' : 'error' ?>">
            <?= htmlspecialchars($message, ENT_QUOTES, 'UTF-8') ?>
        </div>
    <?php endif; ?>

    <form action="upload.php" method="POST" enctype="multipart/form-data">
        <input type="hidden" name="csrf_token" value="<?= htmlspecialchars($_SESSION['csrf_token'], ENT_QUOTES, 'UTF-8') ?>">
        
        <input type="hidden" name="MAX_FILE_SIZE" value="<?= MAX_FILE_SIZE ?>">

        <div class="form-group">
            <label for="upfile">アップロードする画像 (2MBまで):</label><br>
            <input type="file" id="upfile" name="upfile" accept="image/jpeg, image/png, image/gif" required>
        </div>

        <button type="submit">アップロード</button>
    </form>
</body>
</html>