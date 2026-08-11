<?php
/**
 * sandbox/basic/variables.php
 * PHPの変数、定数、スコープ、およびスーパーグローバルの安全な扱い方のサンプル
 */

// 1. 変数の宣言と基本的なデータ型
// PHPの変数は $ から始まり、キャメルケース（camelCase）またはスネークケース（snake_case）で命名する
$stringVar = 'Hello PHP'; // 文字列 (String)
$intVar = 42;             // 整数 (Integer)
$floatVar = 3.14;         // 浮動小数点 (Float)
$boolVar = true;          // 論理値 (Boolean)
$arrayVar = [1, 2, 3];    // 配列 (Array)
$nullVar = null;          // ヌル (Null)


// 2. 定数 (Constants)
// スクリプトの実行中に値が変更されない変数。大文字とアンダースコアで命名する
// パターンA: const キーワード（推奨。クラス内でも使用可能でコンパイル時に定義される）
const MAX_UPLOAD_SIZE = 2048;

// パターンB: define 関数（動的に定数名を決める場合などに使用。グローバルスコープ）
define('APP_VERSION', '1.0.0');


// 3. 変数のスコープ (Scope) と static変数
function calculateTotal() {
    // ローカル変数: 関数内でのみ有効
    $taxRate = 0.1;
    
    // globalキーワードは非推奨（依存関係が不明確になるため、引数やDIで渡すこと）
    // global $intVar; 

    // static変数: 関数が終了しても値を保持し続ける変数
    static $callCount = 0;
    $callCount++;
    
    return $callCount;
}
calculateTotal();
calculateTotal(); // 2が返る


// 4. スーパーグローバル (Superglobals) の安全な取得
// PHPが自動的に定義するグローバルな配列。外部からの入力を含むため、直接アクセスせず安全に取得する

// ❌ 悪い例（未定義エラーの可能性あり、XSSのリスクあり）
// $userId = $_GET['id'];

// ⭕ 良い例1: Null合体演算子 (??) を使ってデフォルト値を設定する
$page = $_GET['page'] ?? 1;

// ⭕ 良い例2: filter_input を使って型検証を同時に行う（より安全）
$userId = filter_input(INPUT_GET, 'id', FILTER_VALIDATE_INT);
if ($userId === false) {
    // idが整数ではない場合の処理
}

// ⭕ 良い例3: POSTデータの取得とサニタイズ（文字列として受け取る場合）
$email = filter_input(INPUT_POST, 'email', FILTER_SANITIZE_EMAIL);


// 5. 変数の状態チェック (isset, empty)
$data = ['name' => 'Taro', 'age' => 0];

// isset: 変数が存在し、かつ null ではないかを判定する
if (isset($data['name'])) {
    // true
}

// empty: 変数が空であるか（0, '0', '', null, false, 空の配列）を判定する
// ※ 0 も true と判定されるため、数値の 0 を許容したい場合は要注意！
if (empty($data['age'])) {
    // $data['age'] は 0 なので、ここに入ってしまう
}


// 6. 型のキャスト (Type Casting)
// 外部からの入力は基本的に文字列として扱われるため、必要に応じて明示的にキャストする
$priceString = '1980';
$priceInt = (int)$priceString;

$isAccepted = '1';
$isAcceptedBool = (bool)$isAccepted;


// 7. 可変変数 (Variable variables)
// 変数の値を別の変数名として使う機能（※コードが追いにくくなるため多用は避ける）
$varName = 'greeting';
$$varName = 'こんにちは'; // $greeting = 'こんにちは'; と同義
// echo $greeting;