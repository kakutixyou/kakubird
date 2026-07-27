<?php
/**
 * sandbox/basic/echo.php
 * PHPでの基本的な出力方法と、安全なエスケープ処理のサンプル
 */

// 1. 基本的な文字列と変数の出力
$greeting = 'Hello';
$name = 'World';

// 文字列連結（シングルクォート）
echo $greeting . ', ' . $name . "!\n";

// 変数展開（ダブルクォートの中括弧囲み・モダンな推奨記法）
echo "{$greeting}, {$name}!\n";


// 2. 【重要】HTMLへの安全な出力（XSS対策）
// ユーザー入力など、外部から来たデータをブラウザに出力する場合は必ずエスケープする
$maliciousInput = '<script>alert("XSS");</script>';
$safeOutput = htmlspecialchars($maliciousInput, ENT_QUOTES, 'UTF-8');
echo "安全な出力: {$safeOutput}\n";


// 3. 配列やデバッグ情報の出力
$user = [
    'id' => 1,
    'name' => 'Taro',
    'isActive' => true
];

// print_r: 人間が読みやすい形式で配列などを出力（主にデバッグ用）
// echo "<pre>";
// print_r($user);
// echo "</pre>";

// var_dump: 型情報も含めて詳細に出力（厳密なデバッグ用）
// var_dump($user);


// 4. HTMLへの埋め込み構文（ショートエコータグ）
// ※以下の部分はPHPモードを抜けてHTMLとして出力される想定のサンプル
?>
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Echo Sample</title>
</head>
<body>
    <h1><?= htmlspecialchars($name, ENT_QUOTES, 'UTF-8') ?> さんのマイページ</h1>
    
    <?php if ($user['isActive']): ?>
        <p>ステータス: アクティブ</p>
    <?php else: ?>
        <p>ステータス: 非アクティブ</p>
    <?php endif; ?>
</body>
</html>