<?php
/**
 * templates/api_template.php
 * セキュアなREST APIのベーステンプレート
 * (CORS対応、JSONレスポンス、例外ハンドリング、認証プレースホルダーを含む)
 */
declare(strict_types=1);

// 1. レスポンスヘッダーの設定 (CORSとContent-Type)
// 許可するオリジンをホワイトリストで指定（本番環境に合わせて変更）
$allowedOrigins = ['http://localhost:3000', 'https://example.com'];
$origin = $_SERVER['HTTP_ORIGIN'] ?? '';

if (in_array($origin, $allowedOrigins, true)) {
    header("Access-Control-Allow-Origin: {$origin}");
    header('Access-Control-Allow-Credentials: true');
}

// 許可するメソッドとヘッダー
header('Access-Control-Allow-Methods: GET, POST, PUT, DELETE, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type, Authorization, X-Requested-With');
header('Content-Type: application/json; charset=UTF-8');

// OPTIONSリクエスト（プリフライト）の早期リターン
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}


// 2. JSONレスポンス出力用のヘルパー関数
/**
 * データをJSON形式で出力し、処理を終了する
 */
function sendJson(array $data, int $statusCode = 200): never {
    http_response_code($statusCode);
    // JSON_THROW_ON_ERROR により、エンコード失敗時に例外を投げる (PHP 7.3+)
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR);
    exit;
}


// 3. メイン処理 (Try-Catchによる安全なエラーハンドリング)
try {
    // --- A. 認証・認可プレースホルダー (必要に応じてコメントアウトを解除) ---
    /*
    $headers = getallheaders();
    $authHeader = $headers['Authorization'] ?? '';
    if (!preg_match('/^Bearer (.+)$/', $authHeader, $matches)) {
        sendJson(['error' => 'Unauthorized. Bearer token is missing.'], 401);
    }
    $token = $matches[1];
    // TODO: ここでトークン検証ロジックを実行
    */

    // --- B. リクエストメソッドと入力データの取得 ---
    $method = $_SERVER['REQUEST_METHOD'];
    $input = [];

    // POST/PUT/PATCHの場合はJSONペイロードをパースして取得
    if (in_array($method, ['POST', 'PUT', 'PATCH'], true)) {
        $rawBody = file_get_contents('php://input');
        $input = json_decode($rawBody, true) ?? [];
    } else {
        // GET/DELETEの場合はクエリパラメータを取得
        $input = filter_input_array(INPUT_GET) ?: [];
    }


    // ======================================================================
    // ↓↓↓ ここからAI生成コード (ビジネスロジック) 挿入エリア ↓↓↓
    // ======================================================================
    
    // AIは入力データ($input)を使ってデータベース処理等を行い、sendJson()で結果を返します。
    // 例:
    if ($method === 'GET') {
        sendJson([
            'status' => 'success',
            'message' => 'API is working.',
            'received_data' => $input
        ]);
    } else {
        sendJson(['error' => 'Method Not Allowed'], 405);
    }

    // ======================================================================
    // ↑↑↑ ここまでAI生成コード挿入エリア ↑↑↑
    // ======================================================================


} catch (PDOException $e) {
    // データベースエラー: ログには詳細を残し、クライアントには汎用メッセージを返す (情報漏洩対策)
    error_log('Database Error: ' . $e->getMessage());
    sendJson(['error' => 'Internal Server Error (Database)'], 500);

} catch (InvalidArgumentException $e) {
    // バリデーションエラーなど、クライアント側に起因するエラー (HTTP 400)
    sendJson(['error' => $e->getMessage()], 400);

} catch (Exception $e) {
    // その他の予期せぬエラー
    error_log('API Error: ' . $e->getMessage());
    // 例外コードがHTTPステータスコードの範囲(400-599)であればそれを使い、それ以外は500とする
    $code = ($e->getCode() >= 400 && $e->getCode() < 600) ? $e->getCode() : 500;
    sendJson(['error' => 'An unexpected error occurred.'], $code);
}