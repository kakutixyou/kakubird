/**
 * CoinageHandler.ts
 * 造語・専門用語・プロジェクト固有の定義（コイネージ）を管理・デプロイするためのフロントエンド/TS側ハンドラー
 * * ProjectKnowledgeEngine v2 の正規表現スキャン（calculateScore / canHandle / handle / estimateSize）に完全適合。
 */

export interface CoinageSignal {
    last_used_handler?: string;
    active_context?: string;
    project_profile?: {
        tech_stack?: string[];
        core_philosophy?: string;
    };
}

export class CoinageHandler {
    /**
     * ProjectKnowledgeEngine v2 が検出するスコア計算ロジック
     * ユーザーのメッセージと現在のシグナルから、このハンドラーの適正度を 0~100 で返す
     */
    async calculateScore(msg: string, signals: CoinageSignal = {}): Promise<number> {
        const normalizedMsg = msg.toLowerCase();
        
        // 1. 強烈なトリガーワードがある場合は「100点ショートカット」を狙う
        if (
            normalizedMsg.includes("造語") || 
            normalizedMsg.includes("用語定義") || 
            normalizedMsg.includes("固有の表現") ||
            normalizedMsg.includes("辞書登録")
        ) {
            return 100;
        }
        
        // 2. アクティブな文脈が coinage（造語定義セッション中）であればスコアを引き上げる
        if (signals.active_context === "coinage_definition") {
            return 85;
        }
        
        // 3. ゆるいキーワードマッチ
        if (normalizedMsg.includes("言葉") || normalizedMsg.includes("意味") || normalizedMsg.includes("定義")) {
            return 45;
        }
        
        return 0;
    }

    /**
     * 競合マージ時の文字数制限チェック用（ProjectKnowledgeEngine v2 対応）
     */
    estimateSize(msg: string): number {
        // 造語の定義・辞書展開は比較的コンパクトなUI/テキストに収まることが多いため、デフォルトを500文字程度に設定
        return 500;
    }

    /**
     * メインの処理ロジック
     * 戻り値は ['text' | 'ui_code', content] の2値タプル（Python側の型定義と完全同期）
     */
    async handle(msg: string): Promise<[string, any] | null> {
        try {
            // 【仕様イメージ】
            // 1. IntentInspector や言語モデルを介して、ユーザーの発言から「造語（単語名）」と「その定義・思想」を抽出する
            // 2. 抽出したデータを「JSON図書館（Warehouse）」の project_profile.coinage_dictionary に蓄積する
            // 3. deployment フォルダーの TemplateEngine と連携し、コード内でその造語が安全に使われるようなマッピングを生成する
            
            // 簡易的な抽出模擬ロジック（実際にはLLM等の解析結果を充てます）
            const match = msg.match(/(?:「([^」]+)」|([^：]+))：(.+)/);
            
            if (match) {
                const word = (match[1] || match[2]).trim();
                const definition = match[3].trim();
                
                const uiBlockData = {
                    message: `新しくプロジェクト固有の造語「${word}」を認識し、記憶システム（JSON図書館）に登録する準備を整えました。`,
                    blocks: [
                        {
                            type: "card",
                            title: "📚 造語辞書の更新マニフェスト",
                            fields: [
                                { label: "登録単語 (Word)", value: word },
                                { label: "定義/思想 (Definition)", value: definition },
                                { label: "反映先コンテキスト", value: "backend/.ai_memory/user_signals.json" }
                            ]
                        }
                    ]
                };
                
                // UIブロックを含むデータを返すため、タイプは 'ui_code'
                return ["ui_code", uiBlockData];
            }
            
            // 抽出できなかった場合のフォールバックテキスト
            const fallbackText = `造語の登録リクエストとして受け付けました。「[単語名]：[その意味や思想]」の形式で入力いただくと、JSON図書館へ正確に棚卸しが可能です。`;
            return ["text", fallbackText];
            
        } catch (error) {
            console.error(" CoinageHandler の実行中にエラーが発生しました:", error);
            return ["text", "造語ハンドラーの内部処理でエラーが発生しました。"];
        }
    }
}
要修正！Handler.pyを読ませるべき