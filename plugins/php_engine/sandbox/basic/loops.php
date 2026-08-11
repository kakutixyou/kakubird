<?php
/**
 * sandbox/basic/loops.php
 * PHPでの反復処理（ループ）と、HTMLテンプレート内での記述方法のサンプル
 */

// 1. foreach - 配列やオブジェクトの反復処理（最も頻繁に使う）
$fruits = ['Apple', 'Banana', 'Cherry'];
echo "--- foreach (値のみ) ---\n";
foreach ($fruits as $fruit) {
    echo "- {$fruit}\n";
}

$userRoles = [
    'taro' => 'Admin',
    'jiro' => 'Editor',
    'saburo' => 'Viewer'
];
echo "\n--- foreach (キーと値) ---\n";
foreach ($userRoles as $username => $role) {
    echo "{$username}さんの権限は {$role} です\n";
}

// 【重要】参照渡し(&)を使った場合の注意点
// ループ内で値を直接変更する場合、ループ後に unset($value) をしないと予期せぬバグを引き起こす
$numbers = [1, 2, 3];
foreach ($numbers as &$num) {
    $num *= 2; // 元の配列の値を2倍にする
}
unset($num); // 参照を解除（必須のベストプラクティス）


// 2. for - 回数が決まっている反復処理
echo "\n--- forループ ---\n";
for ($i = 1; $i <= 3; $i++) {
    echo "カウント: {$i}\n";
}


// 3. while / do-while - 条件に基づく反復処理
echo "\n--- whileループ ---\n";
$count = 3;
while ($count > 0) {
    echo "残り: {$count}\n";
    $count--;
}


// 4. break と continue による制御
echo "\n--- break と continue ---\n";
foreach (['A', 'B', 'SKIP', 'C', 'STOP', 'D'] as $item) {
    if ($item === 'SKIP') {
        continue; // 現在のループ処理をスキップして次の要素へ
    }
    if ($item === 'STOP') {
        break; // ループ全体を直ちに終了
    }
    echo "{$item} ";
}
echo "\n";


// 5. HTMLへの埋め込み構文（代替構文）
// ※以下の部分はPHPモードを抜けてHTMLとして出力される想定のサンプル
?>
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>Loops Sample</title>
</head>
<body>
    <h2>ユーザーリスト</h2>
    <ul>
        <?php foreach ($userRoles as $username => $role): ?>
            <li>
                <strong><?= htmlspecialchars($username, ENT_QUOTES, 'UTF-8') ?></strong>
                <span class="badge"><?= htmlspecialchars($role, ENT_QUOTES, 'UTF-8') ?></span>
            </li>
        <?php endforeach; ?>
    </ul>

    <h2>ページネーション例</h2>
    <div class="pagination">
        <?php for ($p = 1; $p <= 5; $p++): ?>
            <a href="?page=<?= $p ?>" class="page-link"><?= $p ?></a>
        <?php endfor; ?>
    </div>
</body>
</html>