import React, { useState, useEffect } from "react";
import { NavLink, useNavigate } from "react-router-dom";
import clsx from "clsx";

// ==========================================
// 1. ナビゲーション & 型定義
// ==========================================

const NAV_ITEMS = [
  { path: "/", label: "ダッシュボード", icon: "📊", exact: true },
  { path: "/templates", label: "テンプレートを探す", icon: "🎨", sub: "HTMLサンプル集" },
  { path: "/builder", label: "HTMLビルダー", icon: "🏗", sub: "自由に編集する" },
  { path: "/databases", label: "データベース", icon: "🗄️", sub: "生成済みDB管理" },
  { path: "/settings-api", label: "API設定", icon: "🔌", sub: "データ連携" },
  { path: "/memory", label: "AIメモリー", icon: "🧠", sub: "会話履歴・メモ・タスク" },
  { path: "/relocation-map", label: "移住スコアリング", icon: "🗺️", sub: "住みやすさ可視化" },
];

interface AiMemo {
  id: string;
  title: string;
  date?: string;
}

export interface HistoricalPersonaPoint {
  id: string;
  name: string;
  kana: string; // 50音順ソート用
  category: "日本史" | "世界史" | "YouTuber" | "アニメ" | "方言";
  archetype: string;
  isExamTarget: boolean;
  points: string[];
  aiNote?: string;
}

interface TransactionRecord {
  id: string;
  timestamp: string;
  type: string;
  title: string;
  amount_jpy: number;
  fee_jpy: number;
  net_revenue_jpy: number;
  tickets_delta: number;
  method: string;
  note: string;
}

interface GachaItem {
  id: string;
  rarity: "UR" | "SSR" | "SR" | "R";
  name: string;
  genre: string;
  effect: string;
  obtained_at?: string;
}

interface SubscriptionState {
  plan: "free" | "pro_1yen";
  price_jpy: number;
  selected_model: string;
  subscribed_at: string | null;
  auto_renew: boolean;
  user_wallet_jpy: number;
  app_deposit_jpy: number;
  operator_revenue_jpy: number;
  gateway_fee_jpy: number;
  gacha_tickets: number;
  free_tickets_claimed: boolean;
  pro_tickets_claimed: boolean;
  gacha_inventory: GachaItem[];
  transactions: TransactionRecord[];
}

// ==========================================
// 2. 偉人・世界史・日本史 ＆ 実況者データ定義
// ==========================================

const HISTORICAL_AND_PERSONA_DATA: HistoricalPersonaPoint[] = [
  {
    id: "abehira_fu",
    name: "阿倍比羅夫",
    kana: "あべのひらふ",
    category: "日本史",
    archetype: "開拓・交渉ストラテジスト型",
    isExamTarget: true,
    points: [
      "1. 飛鳥時代（斉明天皇朝）の将軍・越国守。658〜660年に水軍を率いて日本海側を北上し、蝦夷（えみし）や粛慎（みしはせ）を討伐した。",
      "2. 飽田（秋田）・渟代（能代）の蝦夷を服属させ、後方羊蹄（しりべし）に郡領を置いたとされる（『日本書紀』）。",
      "3. 663年の白村江の戦いにも水軍を率いて参戦したが、唐・新羅連合軍に敗れた。"
    ],
  },
  {
    id: "igudon_ch",
    name: "いぐどんch（実況スタイル）",
    kana: "いぐどんちゃんねる",
    category: "YouTuber",
    archetype: "超優しい友人 × 突発的発狂ギャップ型",
    isExamTarget: false,
    points: [],
    aiNote: "🌱 本当はすごく優しい友達なのに、理不尽な盤面でなぜか発狂モードに入るスタイルです！試験には出ないので、印象に残った神回や名言をあなた自身の言葉でポイント化してみてください✨",
  },
  {
    id: "kukai",
    name: "空海",
    kana: "くうかい",
    category: "日本史",
    archetype: "超越・宇宙観統合型",
    isExamTarget: true,
    points: [
      "1. 804年、最澄らとともに遣唐使（留学僧）として入唐し、長安の青龍寺で恵果から真言密教を授かる。",
      "2. 帰国後、嵯峨天皇から高野山を賜り金剛峯寺を創建、のち教王護国寺（東寺）を与えられ真言宗の拠点とした。",
      "3. 庶民も学べる教育機関『綜芸種智院』の設立や、讃岐国の『満濃池』の修築など社会・土木事業にも尽力した。",
      "4. 著書に儒・仏・道の優劣を戯曲風に論じた『三教指帰』や『十住心論』『文鏡秘府論』があり、三筆の一人としても知られる。"
    ],
  },
  {
    id: "keichu",
    name: "契沖",
    kana: "けいちゅう",
    category: "日本史",
    archetype: "実証・ストイック探究型",
    isExamTarget: true,
    points: [
      "1. 江戸時代前期（元禄文化期）の真言宗の僧・古典学者。大坂の円珠庵に隠棲し、古典の実証的研究により国学の先駆となった。",
      "2. 水戸藩主・徳川光圀の依頼を受け、『万葉集』の注釈書である『万葉代匠記』を著した。",
      "3. 文献実証主義に基づき古典の仮名遣いを調査し、『和字正濫鈔』で歴史的仮名遣い（契沖仮名遣）の基礎を確立した。"
    ],
  },
  {
    id: "john_king",
    name: "ジョン王",
    kana: "じょんおう",
    category: "世界史",
    archetype: "記録・反面教師型",
    isExamTarget: true,
    points: [
      "1. イングランド・プランタジネット朝の王（在位1199〜1216）。リチャード1世の弟。",
      "2. フランス王フィリップ2世との戦いに敗れて大陸の領土の大半を失い、『欠地王（失地王）』と呼ばれた。また教皇インノケンティウス3世とも対立し破門された。",
      "3. 度重なる重税に反発した貴族たちにより、1215年に『マグナ・カルタ（大憲章）』への調印を余儀なくされ、王権の制限と立憲主義の礎となった。"
    ],
  },
  {
    id: "shibukawa_harumi",
    name: "渋川春海",
    kana: "しぶかわはるみ",
    category: "日本史",
    archetype: "実証・ストイック探究型",
    isExamTarget: true,
    points: [
      "1. 江戸時代前期の天文暦学者・囲碁棋士（安井算哲）。山崎闇斎に垂加神道や朱子学、数学・天文学を学んだ。",
      "2. 800年以上使われ約2日の誤差が生じていた中国伝来の『宣明暦』を改めるため、天体観測を行い元の授時暦を基に日本独自の『貞享暦』を作成した。",
      "3. 1684年（貞享元年）に幕府に採用され、初代幕府天文方に任命された。"
    ],
  },
  {
    id: "bakumatsu_sakamoto",
    name: "幕末志士・坂本（実況スタイル）",
    kana: "ばくまつししさかもと",
    category: "YouTuber",
    archetype: "積極的・陽気 ＋ 制御不能時『ざーばあー』型",
    isExamTarget: false,
    points: [],
    aiNote: "🌱 優しくて積極的、そして操作が効かない絶体絶命の瞬間に『ざーばあー！！』と叫ぶ神プレイ実況スタイルです！歴史試験のポイントはないので、あなた自身の言葉で特徴や好きなシーンを作って追加してみてください✨",
  },
  {
    id: "himiko",
    name: "卑弥呼",
    kana: "ひみこ",
    category: "日本史",
    archetype: "超越・宇宙観統合型",
    isExamTarget: true,
    points: [
      "1. 『魏志』倭人伝に記される3世紀の邪馬台国の女王。倭国大乱を鎮めるため共立され、鬼道（呪術）を用いて統治した。",
      "2. 239年、大夫の難升米（なしめ）らを魏の皇帝に遣わし、『親魏倭王』の称号と金印、銅鏡100枚などを授かった。",
      "3. 狗奴国（男王・卑弥弓呼）との抗争中に死去し、径百余歩の巨大な塚が築かれた。跡を継いだ男王の代に再び乱れたが、壱与（台与）を立てて収まった。"
    ],
  },
  {
    id: "fukushima_dialect",
    name: "福島県ことば（方言モード）",
    kana: "ふくしまけんことば",
    category: "方言",
    archetype: "地域方言フィルター（会津・中通り・浜通り）",
    isExamTarget: false,
    points: [],
    aiNote: "🌱 『さすけねぇ（大丈夫）』『〜だべ』『なじょする？』など、温かみのある福島県の方言モードです。地元の言い回しや覚えておきたい方言フレーズがあれば、ぜひ自分でポイントを登録してみてください！",
  },
  {
    id: "fujiwara_sanesuke",
    name: "藤原実資",
    kana: "ふじわらのさねすけ",
    category: "日本史",
    archetype: "記録・辛口ウォッチャー型",
    isExamTarget: true,
    points: [
      "1. 平安時代中期の公卿（小野宮流）。有職故実に精通し、『賢人右府』と称された。",
      "2. 藤原道長が全盛を極めた時代にあっても道長に阿諛追従せず、筋を通した批判的な態度を貫いた。",
      "3. 彼の日記『小右記』は、道長の『御堂関白記』や藤原行成の『権記』と並び、摂関政治期の政治・社会を知る第一級史料（道長の『この世をば…』の和歌も『小右記』に記録されている）。"
    ],
  },
  {
    id: "fujiwara_seika",
    name: "藤原惺窩",
    kana: "ふじわらせいか",
    category: "日本史",
    archetype: "超越・宇宙観統合型",
    isExamTarget: true,
    points: [
      "1. 安土桃山〜江戸時代初期の儒学者。京都・相国寺の禅僧であったが還俗し、仏教（五山禅林）に従属していた朱子学を独立させた『近世儒学の祖』。",
      "2. 徳川家康に招かれて進講したが自身は仕官せず、門弟の林羅山を幕府に推挙した。",
      "3. 門人には林羅山・松永尺五・那波活所・堀杏庵（惺窩門四天王）や石川丈山らがおり、著書に『寸鉄録』『四書五経倭訓』などがある。"
    ],
  },
  {
    id: "min",
    name: "旻",
    kana: "みん",
    category: "日本史",
    archetype: "制度設計・改革官僚型",
    isExamTarget: true,
    points: [
      "1. 飛鳥時代の学問僧（僧旻）。608年、小野妹子の第2回遣隋使に留学生として同行し、24年間（隋〜唐）滞在して仏教・律令・易学などを学んだ。",
      "2. 帰国後、蘇我入鹿や中大兄皇子らに学問を講じ、645年の乙巳の変（大化の改新）後に高向玄理とともに『国博士』に任じられ新政権の制度設計を担った。",
      "3. 650年、穴戸国から献上された白い雉を祥瑞と判定し、元号が『白雉』に改元される契機となった。"
    ],
  },
  {
    id: "lassalle",
    name: "ラッサール",
    kana: "らっさーる",
    category: "世界史",
    archetype: "情熱・革命騎士型",
    isExamTarget: true,
    points: [
      "1. 19世紀ドイツの社会主義者・労働運動指導者。1863年にドイツ初の独立労働者政党『全ドイツ労働者同盟』を結成した。",
      "2. 自由放任主義国家を『夜警国家』と批判し、普通選挙権の獲得と国家の援助による生産協同組合の設立（国家社会主義的改革）を主張した。",
      "3. のち1875年にゴータでマルクス派（アイゼナハ派）と合同し、『ドイツ社会主義労働者党（のちのドイツ社会民主党：SPD）』が結成された。"
    ],
  },
  {
    id: "lafayette",
    name: "ラファイエット",
    kana: "らふぁいえっと",
    category: "世界史",
    archetype: "情熱・革命騎士型",
    isExamTarget: true,
    points: [
      "1. フランスの自由主義貴族・軍人。アメリカ独立戦争に義勇兵として参戦し、ワシントンを補佐してヨークタウンの戦いなどで活躍した（『両大陸の英雄』）。",
      "2. 1789年のフランス革命勃発後、国民衛兵司令官に就任し、ジェファソンの助言も得て『人間と市民の権利の宣言（人権宣言）』を起草した。",
      "3. 立憲君主制を支持したが革命の急進化によりオーストリアへ亡命。のち1830年の七月革命でも国民衛兵を率い、ルイ＝フィリップの即位を支持した。"
    ],
  },
  {
    id: "rezanov",
    name: "レザーノフ",
    kana: "れざーのふ",
    category: "日本史",
    archetype: "開拓・交渉ストラテジスト型",
    isExamTarget: true,
    points: [
      "1. ロシア帝国の外交官・露米会社（毛皮交易独占会社）の創設者。",
      "2. 1804年（文化元年）、かつて根室に来航したラクスマンが幕府から与えられた信牌を携え、アレクサンドル1世の遣日使節として長崎に来航し通商を要求した。",
      "3. 幕府は半年間待たせた末に通商を拒絶。これに憤慨したレザーノフの命により、部下のフヴォストフらが1806〜1807年に樺太・択捉島を襲撃した（文化露寇）。"
    ],
  },
  {
    id: "locke",
    name: "ロック",
    kana: "ろっく",
    category: "世界史",
    archetype: "実証・ストイック探究型",
    isExamTarget: true,
    points: [
      "1. 17世紀イギリスの哲学者・政治思想家。『人間知性論』で人間の心を生まれつき白紙（タブラ・ラサ）と説き、イギリス経験論を確立した。",
      "2. 主著『統治二論（市民政府二論）』で名誉革命（1688〜89年）を理論的に正当化し、自然状態における生命・自由・財産の自然権と社会契約説を唱えた。",
      "3. 政府が信託に背いた場合の『抵抗権（革命権）』や三権分立（立法権の優位）を主張し、アメリカ独立宣言やフランス人権宣言に多大な影響を与えた。"
    ],
  },
];

const GACHA_POOL: GachaItem[] = [
  { id: "ur_kukai", rarity: "UR", name: "空海（曼荼羅オーケストレーター）", genre: "ローグライク / 歴史RPG", effect: "全ハンドラーの通信エラー率を0%にし、毎ターンMP+15回復" },
  { id: "ur_himiko", rarity: "UR", name: "卑弥呼（鬼道ログ予言者）", genre: "カード / タワーディフェンス", effect: "敵の次ターンの行動ルートを100%可視化＆全体バリア付与" },
  { id: "ssr_shibukawa", rarity: "SSR", name: "渋川春海（貞享暦スターナビゲーター）", genre: "すごろく / パーティ", effect: "サイコロの出目を±2まで自在に補正し、イベントマス報酬2倍" },
  { id: "ssr_rezanov", rarity: "SSR", name: "レザーノフ（極東開国ブレイカー）", genre: "タワーディフェンス", effect: "404防壁を一撃で貫通する氷砕砲撃（攻撃力+180%）" },
  { id: "ssr_lafayette", rarity: "SSR", name: "ラファイエット（自由の騎士ガード）", genre: "ローグライク / カード", effect: "味方ユニット全員のクリティカル率+35%・士気上限突破" },
  { id: "sr_takeshi_onix", rarity: "SR", name: "イワーク級ロックディフェンダー", genre: "モンスターシミュレーション", effect: "物理ダメージを70%軽減（バッジ0個でも命令を聞く特別仕様）" },
  { id: "sr_min", rarity: "SR", name: "僧旻（大化API律令アーキテクト）", genre: "カード / 戦略シム", effect: "手札のコストを1下げ、フロントとバックエンドの連携速度2倍" },
  { id: "r_seika", rarity: "R", name: "藤原惺窩（朱子学デバッガー）", genre: "ローグライク", effect: "状態異常（バグ・無限ループ）を即座に解除" },
  { id: "r_dice_boost", rarity: "R", name: "黄金の二進数ダイス (7/32 = 0.00111₂)", genre: "すごろく", effect: "すごろくマップでぴったり止まりたいマスへワープ" },
];

const INITIAL_SUB_STATE: SubscriptionState = {
  plan: "free",
  price_jpy: 0,
  selected_model: "to_model_local",
  subscribed_at: null,
  auto_renew: false,
  user_wallet_jpy: 1000,
  app_deposit_jpy: 0,
  operator_revenue_jpy: 0,
  gateway_fee_jpy: 0,
  gacha_tickets: 10,
  free_tickets_claimed: true,
  pro_tickets_claimed: false,
  gacha_inventory: [],
  transactions: [
    {
      id: "tx_init_free",
      timestamp: "初期状態",
      type: "free_signup_bonus",
      title: "🌱 無料プラン登録特典（ガチャ券10枚付与）",
      amount_jpy: 0,
      fee_jpy: 0,
      net_revenue_jpy: 0,
      tickets_delta: 10,
      method: "local_free",
      note: "決済なし（0円）でゲームシミュレーション用ガチャ券10枚をプレゼント！",
    },
  ],
};

const ENV_API_BASE_URL: string = String(
  (import.meta as any).env?.VITE_API_BASE_URL || "http://localhost:8765"
).replace(/\/+$/, "");

// ==========================================
// 3. SidebarDefault 本体
// ==========================================

export default function SidebarDefault(): React.ReactElement {
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const navigate = useNavigate();

  // 💡 AIが「メモしておきます」と記録した学習ノート・メモ一覧
  const [memos, setMemos] = useState<AiMemo[]>([
    { id: "1", title: "表層解析：MZヘッダの確認手順", date: "今日" },
    { id: "2", title: "INetSim：Ubuntuダミー局の構築", date: "今日" },
    { id: "3", title: "Host-Onlyネットワーク隔離設定", date: "昨日" },
  ]);

  // 💡 歴史・偉人ポイント呼び出しモーダル用のState
  const [isPointModalOpen, setIsPointModalOpen] = useState(false);
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>("fujiwara_seika");

  // =========================================================================
  // ⚙️ 左下「設定（⚙️）」ポップアップメニュー ＆ 定期購入の管理（サブスク）用State
  // =========================================================================
  const [isGearMenuOpen, setIsGearMenuOpen] = useState(false);
  const [activeSettingsModal, setActiveSettingsModal] = useState<
    | null
    | "subscription"
    | "personal_intelligence"
    | "skills"
    | "gemini"
    | "theme"
    | "tasks"
    | "browser"
    | "watermark"
    | "download_data"
    | "public_links"
  >(null);

  const [subState, setSubState] = useState<SubscriptionState>(INITIAL_SUB_STATE);
  const [subToast, setSubToast] = useState<string | null>(null);
  const [personalIntelEnabled, setPersonalIntelEnabled] = useState(true);
  const [watermarkEnabled, setWatermarkEnabled] = useState(true);
  const [currentThemeName, setCurrentThemeName] = useState("Default (標準テーマ)");
  const [publicLinks, setPublicLinks] = useState<Array<{ id: string; title: string; url: string; createdAt: string }>>([
    { id: "lnk_1", title: "歴史ポイント50音順リスト共有スナップショット", url: "http://127.0.0.1:5173/share/history-points-01", createdAt: "2026-11-16" },
    { id: "lnk_2", title: "ゲームシミュレーション（すごろく＆ローグライク）試遊リンク", url: "http://127.0.0.1:5173/share/game-sim-demo", createdAt: "2026-11-16" },
  ]);

  const currentPersona =
    HISTORICAL_AND_PERSONA_DATA.find((p) => p.id === selectedPersonaId) ||
    HISTORICAL_AND_PERSONA_DATA[0];

  // バックエンドのメモAPI & サブスク状態APIから取得
  useEffect(() => {
    async function fetchInitialData() {
      try {
        const res = await fetch(`${ENV_API_BASE_URL}/api/to/memory/notes?limit=5`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data.notes) && data.notes.length > 0) {
            setMemos(
              data.notes.map((n: any) => ({
                id: String(n.id),
                title: String(n.title),
                date: String(n.created_at || "").slice(5, 10),
              }))
            );
          }
        }
      } catch {}

      try {
        const subRes = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/status`);
        if (subRes.ok) {
          const sData = await subRes.json();
          if (sData && sData.plan) {
            setSubState((prev) => ({ ...prev, ...sData }));
          }
        }
      } catch {}
    }
    fetchInitialData();
  }, []);

  // 別ウィンドウでコピーされたポイントをサイドバーのAI学習メモにも反映する通信チャネル
  useEffect(() => {
    if (typeof BroadcastChannel === "undefined") return;
    const channel = new BroadcastChannel("to_exam_points_channel");

    channel.onmessage = async (event) => {
      const payload = event.data;
      if (payload && payload.type === "SAVE_EXAM_MEMO" && payload.title) {
        const newMemo: AiMemo = {
          id: `exam-${Date.now()}`,
          title: payload.title,
          date: "今",
        };
        setMemos((prev) => [newMemo, ...prev.slice(0, 7)]);

        try {
          await fetch(`${ENV_API_BASE_URL}/api/to/memory/notes`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              title: payload.title,
              content: payload.content || payload.title,
              category: "history_exam",
              tags: ["歴史ポイント", payload.personName || "偉人"],
            }),
          });
        } catch {}
      }
    };

    return () => channel.close();
  }, []);

  // =========================================================================
  // 💳 ローカル擬似決済 ＆ デポジットチャージ ＆ ガチャ券10枚処理
  // =========================================================================
  const handleChargeDeposit = async (amount: number) => {
    if (amount < 50) {
      setSubToast("🚫 カード決済APIエラー体験：日本円のカード決済は最低50円からの制限があるため、1円単発のカード決済は拒否されます！");
      setSubState((prev) => ({
        ...prev,
        transactions: [
          {
            id: `tx_${Date.now()}`,
            timestamp: new Date().toLocaleTimeString("ja-JP"),
            type: "gateway_rejected",
            title: "🚫 カード会社APIで1円直接決済が拒否 (amount_too_small)",
            amount_jpy: 0,
            fee_jpy: 0,
            net_revenue_jpy: 0,
            tickets_delta: 0,
            method: "stripe_min_50yen_rule",
            note: "最低決済金額50円未満のため拒否。①ローカル擬似決済か②50円以上のデポジットチャージを使ってください。",
          },
          ...prev.transactions,
        ],
      }));
      return;
    }

    if (subState.user_wallet_jpy < amount) {
      setSubToast("⚠️ ユーザー財布の所持金が不足しています！");
      return;
    }

    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "charge_deposit", charge_amount_jpy: amount }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    const fee = Math.max(1, Math.round(amount * 0.036));
    const net = amount - fee;
    setSubState((prev) => ({
      ...prev,
      user_wallet_jpy: prev.user_wallet_jpy - amount,
      app_deposit_jpy: prev.app_deposit_jpy + amount,
      gateway_fee_jpy: prev.gateway_fee_jpy + fee,
      operator_revenue_jpy: prev.operator_revenue_jpy + net,
      transactions: [
        {
          id: `tx_${Date.now()}`,
          timestamp: new Date().toLocaleTimeString("ja-JP"),
          type: "deposit_charge",
          title: `💳 デポジット事前チャージ (+¥${amount})`,
          amount_jpy: amount,
          fee_jpy: fee,
          net_revenue_jpy: net,
          tickets_delta: 0,
          method: "stripe_deposit_sim",
          note: `最低50円ルールをクリアして決済成功。手数料3.6%(¥${fee})が引かれ、運営へ¥${net}入金・残高+${amount}pt！`,
        },
        ...prev.transactions,
      ],
    }));
    setSubToast(`💳 ¥${amount}をチャージしました！（手数料3.6%: ¥${fee} / 運営売上: +¥${net}）`);
  };

  const handleSubscribeOneYen = async (method: "demo_instant" | "deposit_wallet") => {
    if (method === "deposit_wallet" && subState.app_deposit_jpy < 1) {
      setSubToast("⚠️ デポジット残高が0ptです。先に「+¥50チャージ」または「+¥100チャージ」を押してください！");
      return;
    }
    if (method === "demo_instant" && subState.user_wallet_jpy < 1) {
      setSubToast("⚠️ ユーザー財布の残高が不足しています！");
      return;
    }

    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "subscribe_1yen", payment_method: method }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    const nowStr = new Date().toLocaleTimeString("ja-JP");
    setSubState((prev) => ({
      ...prev,
      plan: "pro_1yen",
      price_jpy: 1,
      subscribed_at: nowStr,
      auto_renew: true,
      selected_model: "to_model_pro_hybrid",
      user_wallet_jpy: method === "demo_instant" ? prev.user_wallet_jpy - 1 : prev.user_wallet_jpy,
      app_deposit_jpy: method === "deposit_wallet" ? prev.app_deposit_jpy - 1 : prev.app_deposit_jpy,
      operator_revenue_jpy: method === "demo_instant" ? prev.operator_revenue_jpy + 1 : prev.operator_revenue_jpy,
      gacha_tickets: prev.gacha_tickets + 10,
      pro_tickets_claimed: true,
      transactions: [
        {
          id: `tx_${Date.now()}`,
          timestamp: nowStr,
          type: "subscribe_1yen",
          title: "👑 月額1円 Proサブスク契約 ＋ ガチャ券10枚付与",
          amount_jpy: 1,
          fee_jpy: 0,
          net_revenue_jpy: method === "demo_instant" ? 1 : 0,
          tickets_delta: 10,
          method,
          note:
            method === "demo_instant"
              ? "ローカル擬似決済により手数料0円で財布から運営金庫へ1円が直接移動！ガチャ券10枚を追加付与。"
              : "事前チャージ済みのデポジット残高から1pt(1円)を引き落とし！ガチャ券10枚を追加付与。",
        },
        ...prev.transactions,
      ],
    }));
    setSubToast("🎉 月額1円サブスク（Proプラン）登録完了！ガチャ券10枚が追加付与されました！");
  };

  const handleCancelSubscription = async () => {
    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/checkout`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "cancel" }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    setSubState((prev) => ({
      ...prev,
      plan: "free",
      price_jpy: 0,
      auto_renew: false,
      selected_model: "to_model_local",
    }));
    setSubToast("🌱 無料プラン（To_model Standard）へ戻しました。獲得済みのガチャ券はそのまま使えます！");
  };

  const handlePullGacha = async (count: number) => {
    if (subState.gacha_tickets < count) {
      setSubToast(`⚠️ ガチャ券が足りません（必要: ${count}枚 / 所持: ${subState.gacha_tickets}枚）。1円サブスク決済で+10枚補充できます！`);
      return;
    }

    try {
      const res = await fetch(`${ENV_API_BASE_URL}/api/to/subscription/gacha-pull`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ count }),
      });
      if (res.ok) {
        const data = await res.json();
        setSubState((prev) => ({ ...prev, ...data.state }));
        setSubToast(data.message);
        return;
      }
    } catch {}

    const nowStr = new Date().toLocaleTimeString("ja-JP");
    const pulled: GachaItem[] = [];
    for (let i = 0; i < count; i++) {
      const pick = GACHA_POOL[Math.floor(Math.random() * GACHA_POOL.length)];
      pulled.push({ ...pick, obtained_at: nowStr });
    }

    setSubState((prev) => ({
      ...prev,
      gacha_tickets: prev.gacha_tickets - count,
      gacha_inventory: [...pulled, ...prev.gacha_inventory],
      transactions: [
        {
          id: `tx_${Date.now()}`,
          timestamp: nowStr,
          type: "gacha_pull",
          title: `🎰 ゲームシミュレーション ${count === 10 ? "10連" : "単発"}ガチャ実行`,
          amount_jpy: 0,
          fee_jpy: 0,
          net_revenue_jpy: 0,
          tickets_delta: -count,
          method: "gacha_ticket",
          note: `獲得: ${pulled.slice(0, 2).map((p) => `[${p.rarity}]${p.name}`).join(", ")}`,
        },
        ...prev.transactions,
      ],
    }));
    setSubToast(`🎰 ${count}回ガチャを引きました！ [${pulled[0].rarity}] ${pulled[0].name} などを獲得！`);
  };

  // 大事なデータをJSONファイルとして一括ダウンロード
  const handleDownloadImportantData = () => {
    const bundle = {
      exported_at: new Date().toISOString(),
      project: "Project To v1.0",
      subscription_and_gacha_state: subState,
      ai_learning_memos: memos,
      historical_exam_points_count: HISTORICAL_AND_PERSONA_DATA.length,
      settings: {
        usage_limit: "unlimited",
        personal_intelligence: personalIntelEnabled,
        synthid_watermark: watermarkEnabled,
        theme: currentThemeName,
      },
    };
    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `project_to_backup_${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    setSubToast("📥 大事なデータ（学習メモ・サブスク台帳・ガチャ所持枠・設定）をJSONファイルとしてダウンロードしました！");
  };

  // 💡 モーダルのボタンクリック時：新しくブラウザウィンドウを立ち上げ、50音順＋◁/▽＋クリックコピー画面を描画する
  const handleLaunchPointsBrowser = (initialTargetId: string) => {
    const popup = window.open(
      "",
      "ToHistoryExamPointsBrowser",
      "width=820,height=860,menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes"
    );

    if (!popup) {
      alert("ポップアップがブロックされました。ブラウザのポップアップ許可設定をご確認ください。");
      return;
    }

    const serializedData = JSON.stringify(HISTORICAL_AND_PERSONA_DATA);

    const htmlContent = `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>🎓 歴史・偉人 重要ポイントブラウザ（50音順） - Project To</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    body { background-color: #030712; color: #f3f4f6; font-family: ui-sans-serif, system-ui, -apple-system, sans-serif; }
    .point-card:active { transform: scale(0.99); }
  </style>
</head>
<body class="p-6 min-h-screen">
  <div class="max-w-3xl mx-auto space-y-5">
    <div class="border-b border-gray-800 pb-4 flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-amber-400 flex items-center gap-2">
          <span>🎓</span> 日本史・世界史・人物 重要ポイント一覧（50音順）
        </h1>
        <p class="text-xs text-gray-400 mt-1">
          名前または右側の「◁」をクリックすると「▽」に変わり、1〜上限までポイントが表示されます。ポイントをクリックすると文章をコピーできます。
        </p>
      </div>
    </div>
    <div class="relative">
      <input
        id="searchInput"
        type="text"
        placeholder="🔍 名前・よみがな・キーワード（例：ふじわらせいか、朱子学、空海、長崎）で検索..."
        class="w-full px-4 py-3 rounded-lg bg-gray-900 border border-gray-700 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-amber-500 shadow-inner"
      />
    </div>
    <div id="toast" class="hidden fixed bottom-5 right-5 bg-emerald-600 text-white text-xs font-bold px-4 py-3 rounded-lg shadow-2xl border border-emerald-400 z-50"></div>
    <div id="listContainer" class="space-y-2.5"></div>
  </div>
  <script>
    const RAW_DATA = ${serializedData};
    const INITIAL_TARGET = "${initialTargetId}";
    const channel = typeof BroadcastChannel !== "undefined" ? new BroadcastChannel("to_exam_points_channel") : null;
    const customPointsMap = JSON.parse(localStorage.getItem("to_custom_persona_points") || "{}");
    RAW_DATA.forEach(item => {
      if (customPointsMap[item.id]) item.points = customPointsMap[item.id];
    });
    const openState = {};
    if (INITIAL_TARGET) openState[INITIAL_TARGET] = true;
    function showToast(msg) {
      const t = document.getElementById("toast");
      t.textContent = msg;
      t.classList.remove("hidden");
      clearTimeout(window.__toastTimer);
      window.__toastTimer = setTimeout(() => t.classList.add("hidden"), 2400);
    }
    window.toggleItem = function(id) {
      openState[id] = !openState[id];
      renderList();
    };
    window.copyPointText = function(personName, text) {
      navigator.clipboard.writeText(text).then(() => {
        showToast("📋 コピーしました: " + text.slice(0, 32) + "...");
        if (channel) {
          channel.postMessage({
            type: "SAVE_EXAM_MEMO",
            personName: personName,
            title: personName + "：" + text.replace(/^[0-9]+\\.\\s*/, "").slice(0, 18) + "...",
            content: text
          });
        }
      });
    };
    window.addCustomPoint = function(id) {
      const inputEl = document.getElementById("custom-input-" + id);
      if (!inputEl || !inputEl.value.trim()) return;
      const target = RAW_DATA.find(p => p.id === id);
      if (!target) return;
      const nextNum = target.points.length + 1;
      const formatted = nextNum + ". " + inputEl.value.trim();
      target.points.push(formatted);
      customPointsMap[id] = target.points;
      localStorage.setItem("to_custom_persona_points", JSON.stringify(customPointsMap));
      inputEl.value = "";
      showToast("✨ 自分のポイントを追加しました！");
      renderList();
    };
    function renderList() {
      const query = (document.getElementById("searchInput").value || "").trim().toLowerCase();
      const container = document.getElementById("listContainer");
      const filtered = [...RAW_DATA]
        .sort((a, b) => a.kana.localeCompare(b.kana, "ja"))
        .filter(item => {
          if (!query) return true;
          return (
            item.name.toLowerCase().includes(query) ||
            item.kana.toLowerCase().includes(query) ||
            item.category.toLowerCase().includes(query) ||
            item.points.some(pt => pt.toLowerCase().includes(query))
          );
        });
      if (filtered.length === 0) {
        container.innerHTML = '<div class="text-center py-10 text-gray-500 text-sm">該当する人物・ポイントが見つかりませんでした。</div>';
        return;
      }
      container.innerHTML = filtered.map(person => {
        const isOpen = !!openState[person.id];
        const badgeColor =
          person.category === "日本史" ? "bg-amber-500/20 text-amber-300 border-amber-500/40" :
          person.category === "世界史" ? "bg-blue-500/20 text-blue-300 border-blue-500/40" :
          "bg-purple-500/20 text-purple-300 border-purple-500/40";
        let bodyHtml = "";
        if (isOpen) {
          const pointsListHtml = person.points.map(pt => {
            const escapedPt = pt.replace(/'/g, "\\'").replace(/"/g, "&quot;");
            return \`
              <div
                onclick="copyPointText('\${person.name}', '\${escapedPt}')"
                class="point-card p-3 rounded-lg bg-gray-900 hover:bg-gray-800 border border-gray-800 hover:border-amber-500/60 text-xs text-gray-200 leading-relaxed cursor-pointer transition-all flex items-start justify-between gap-3 group"
              >
                <span>\${pt}</span>
                <span class="text-[10px] text-gray-500 group-hover:text-amber-400 shrink-0 font-bold">📋 コピー</span>
              </div>
            \`;
          }).join("");
          bodyHtml = \`
            <div class="px-4 pb-4 pt-2 border-t border-gray-800 bg-gray-950/70 space-y-2">
              <div class="text-[11px] text-gray-400 mb-1">💡 思考の型: <span class="text-gray-300 font-semibold">\${person.archetype}</span></div>
              \${pointsListHtml}
            </div>
          \`;
        }
        return \`
          <div id="card-\${person.id}" class="border border-gray-800 rounded-lg bg-gray-900/70 overflow-hidden shadow">
            <button
              onclick="toggleItem('\${person.id}')"
              class="w-full px-4 py-3.5 flex items-center justify-between hover:bg-gray-800/80 transition-colors text-left"
            >
              <div class="flex items-center gap-3 flex-wrap">
                <span class="font-bold text-base text-gray-100">\${person.name}</span>
                <span class="text-xs text-gray-400">（\${person.kana}）</span>
                <span class="text-[10px] px-2 py-0.5 rounded border \${badgeColor}">\${person.category}</span>
              </div>
              <span class="text-amber-400 font-bold text-base select-none ml-2">\${isOpen ? "▽" : "◁"}</span>
            </button>
            \${bodyHtml}
          </div>
        \`;
      }).join("");
    }
    document.getElementById("searchInput").addEventListener("input", renderList);
    renderList();
  </script>
</body>
</html>`;

    popup.document.open();
    popup.document.write(htmlContent);
    popup.document.close();
    setIsPointModalOpen(false);
  };

  return (
    <>
      {/* スマホ用トグルボタン */}
      <button
        className="md:hidden fixed top-3 left-3 z-40 p-2 bg-gray-900 text-white rounded-md shadow-lg"
        onClick={() => setIsMobileOpen(true)}
      >
        ☰
      </button>

      {/* 背景オーバーレイ */}
      {isMobileOpen && (
        <div
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsMobileOpen(false)}
        />
      )}

      {/* サイドバー本体 */}
      <aside
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-64 bg-gray-900 text-gray-100 flex flex-col h-screen flex-shrink-0 border-r border-gray-800 transition-transform duration-300 ease-in-out",
          "md:relative md:translate-x-0",
          isMobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        {/* Logo */}
        <div className="p-4 border-b border-gray-800 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-2xl">✨</span>
            <span className="font-bold text-lg">Project To</span>
          </div>
          <button
            className="md:hidden text-gray-400 hover:text-white text-2xl leading-none"
            onClick={() => setIsMobileOpen(false)}
          >
            ×
          </button>
        </div>

        {/* New Chat */}
        <div className="p-4 pb-2">
          <button
            onClick={() => navigate("/")}
            className="flex items-center justify-center gap-2 w-full py-2.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-medium transition-colors"
          >
            <span className="text-xl leading-none">+</span>
            <span>新しいチャット</span>
          </button>
        </div>

        {/* Body (スクロール領域) */}
        <div className="flex-1 overflow-y-auto flex flex-col px-2 space-y-4">
          {/* 偉人・日本史・世界史 試験ポイント呼び出しセクション */}
          <div className="mt-2 px-1">
            <button
              onClick={() => setIsPointModalOpen(true)}
              className="w-full py-2.5 px-3 rounded-lg bg-amber-500/15 hover:bg-amber-500/25 border border-amber-500/40 text-amber-300 text-xs font-bold flex items-center justify-between transition-all shadow-sm"
            >
              <span className="flex items-center gap-1.5">
                <span>🎓</span>
                <span>偉人・歴史ポイント呼出</span>
              </span>
              <span className="text-[10px] bg-amber-500/30 text-amber-200 px-1.5 py-0.5 rounded">
                50音順
              </span>
            </button>
          </div>

          {/* AIが記録した学習メモセクション */}
          <div className="mt-1">
            <div className="flex items-center justify-between px-2 mb-1.5">
              <span className="text-xs font-bold text-emerald-400 tracking-wider flex items-center gap-1">
                📝 AI学習メモ・ノート
              </span>
              <NavLink
                to="/memory"
                className="text-[10px] text-gray-400 hover:text-emerald-300 underline"
              >
                すべて見る
              </NavLink>
            </div>
            <div className="space-y-1">
              {memos.map((memo) => (
                <button
                  key={memo.id}
                  onClick={() => navigate("/memory")}
                  className="w-full text-left px-2.5 py-1.5 rounded bg-gray-800/40 hover:bg-gray-800 text-xs text-gray-300 hover:text-emerald-300 transition-colors flex items-center justify-between group"
                >
                  <span className="truncate">📌 {memo.title}</span>
                  {memo.date && (
                    <span className="text-[10px] text-gray-500 group-hover:text-gray-400 shrink-0 ml-1">
                      {memo.date}
                    </span>
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Recent Chat */}
          <div>
            <div className="text-xs font-bold text-gray-500 px-2 mb-1.5 tracking-wider">
              最近のチャット
            </div>
            <div className="space-y-1"></div>
          </div>

          {/* Menu */}
          <nav className="border-t border-gray-800 pt-3 pb-2">
            <div className="text-xs font-bold text-gray-500 px-2 mb-2 tracking-wider">
              システムメニュー
            </div>
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                end={item.exact}
                onClick={() => setIsMobileOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors mb-0.5",
                    isActive
                      ? "bg-blue-600/15 text-blue-400 font-medium"
                      : "text-gray-300 hover:bg-gray-800 hover:text-white"
                  )
                }
              >
                <span className="text-base w-5 text-center">{item.icon}</span>
                <div>
                  <div className="leading-tight">{item.label}</div>
                  {item.sub && (
                    <div className="text-[10px] opacity-50 mt-0.5">{item.sub}</div>
                  )}
                </div>
              </NavLink>
            ))}
          </nav>
        </div>

        {/* ================================================================= */}
        {/* ⚙️ Footer + 設定ポップアップメニュー（12項目すべて搭載）            */}
        {/* ================================================================= */}
        <div className="relative p-3 border-t border-gray-800 text-xs text-gray-400 flex justify-between items-center bg-gray-900">
          <div className="flex items-center gap-2">
            <span>Project To v1.0</span>
            <span
              onClick={() => setActiveSettingsModal("subscription")}
              className="cursor-pointer px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/40 text-amber-300 text-[10px] font-bold hover:bg-amber-500/30"
              title="クリックしてサブスク・ガチャ券を確認"
            >
              🎫 {subState.gacha_tickets}枚
            </span>
          </div>

          <button
            type="button"
            onClick={() => setIsGearMenuOpen((prev) => !prev)}
            className={clsx(
              "p-1.5 rounded-lg transition-colors flex items-center gap-1 text-sm",
              isGearMenuOpen
                ? "bg-blue-600 text-white shadow-lg"
                : "hover:bg-gray-800 text-gray-300 hover:text-white"
            )}
            title="設定とサブスクリプション・データ管理を開く"
          >
            <span>⚙️</span>
          </button>

          {/* ⚙️ ポップアップサイドメニュー */}
          {isGearMenuOpen && (
            <div className="absolute bottom-14 left-2 w-72 rounded-2xl bg-gray-950 border border-gray-700 shadow-2xl py-2 z-50 text-gray-100 space-y-0.5 max-h-[82vh] overflow-y-auto">
              <div className="px-3.5 py-2 border-b border-gray-800 flex items-center justify-between">
                <span className="font-bold text-xs text-amber-400">⚙️ 設定・システム管理メニュー</span>
                <button
                  type="button"
                  onClick={() => setIsGearMenuOpen(false)}
                  className="text-gray-400 hover:text-white text-sm"
                >
                  ×
                </button>
              </div>

              {/* 1. 使用量上限 (無限大) */}
              <div className="px-3.5 py-2.5 flex items-center justify-between bg-gray-900/60 border-b border-gray-800/80">
                <div className="flex items-center gap-2.5">
                  <span className="text-base">♾️</span>
                  <div>
                    <div className="text-xs font-bold text-white">使用量上限</div>
                    <div className="text-[10px] text-emerald-400">ローカル＆ハイブリッド無制限</div>
                  </div>
                </div>
                <span className="px-2 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 font-extrabold text-xs">
                  ∞ 無限大
                </span>
              </div>

              {/* 2. 定期購入の管理（ここからサブスク・擬似決済・ガチャ券10枚を確認！） */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("subscription");
                }}
                className="w-full px-3.5 py-2.5 text-left hover:bg-amber-500/15 flex items-center justify-between transition group border-b border-gray-800/60"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">💳</span>
                  <div>
                    <div className="text-xs font-bold text-amber-300 group-hover:text-amber-200">
                      定期購入の管理（サブスク確認）
                    </div>
                    <div className="text-[10px] text-gray-400">
                      無料/1円サブスク・資金移動・ガチャ券10枚
                    </div>
                  </div>
                </div>
                <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 font-bold">
                  {subState.plan === "pro_1yen" ? "👑 1円Pro" : "🌱 無料"}
                </span>
              </button>

              {/* 3. アップグレード機能はないです */}
              <div className="px-3.5 py-2 flex items-center justify-between text-gray-400 bg-gray-900/30 border-b border-gray-800/60">
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🚫</span>
                  <div>
                    <div className="text-xs font-medium text-gray-300">アップグレード機能はないです</div>
                    <div className="text-[10px] text-gray-500">高額プランなし（無料/1円で全開放）</div>
                  </div>
                </div>
                <span className="text-[10px] text-gray-500">固定</span>
              </div>

              {/* 4. パーソナルインテリジェンス */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("personal_intelligence");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🧠</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">パーソナルインテリジェンス</div>
                    <div className="text-[10px] text-gray-400">記憶・学習ノート自動反映</div>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-400 font-bold">
                  {personalIntelEnabled ? "ON" : "OFF"}
                </span>
              </button>

              {/* 5. スキル (Skills) */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("skills");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🧩</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">スキル (Skills)</div>
                    <div className="text-[10px] text-gray-400">OCR・ゲームシム・コード分割</div>
                  </div>
                </div>
                <span className="text-[10px] text-blue-400">6個有効</span>
              </button>

              {/* 6. Gemini */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("gemini");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">✨</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">Gemini 連携設定</div>
                    <div className="text-[10px] text-gray-400">ハイブリッド推論＆ローカル切替</div>
                  </div>
                </div>
                <span className="text-[10px] text-indigo-300">設定</span>
              </button>

              {/* 7. テーマ */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("theme");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🎨</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">テーマ</div>
                    <div className="text-[10px] text-gray-400">Default / Future Purple / Alexandros</div>
                  </div>
                </div>
                <span className="text-[10px] text-gray-400">変更</span>
              </button>

              {/* 8. タスクの設定 */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("tasks");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">✅</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">タスクの設定</div>
                    <div className="text-[10px] text-gray-400">バックグラウンドAIタスク管理</div>
                  </div>
                </div>
                <span className="text-[10px] text-gray-400">管理</span>
              </button>

              {/* 9. ブラウザ */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("browser");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🌐</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">ブラウザ連携</div>
                    <div className="text-[10px] text-gray-400">50音順サブブラウザ・SSRF安全検証</div>
                  </div>
                </div>
                <span className="text-[10px] text-gray-400">開く</span>
              </button>

              {/* 10. 電子透かし (SynthID / ステガノグラフィー) */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("watermark");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🔍</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">電子透かし (LSB / SynthID)</div>
                    <div className="text-[10px] text-gray-400">画像・PSDステガノグラフィー検証</div>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-400">
                  {watermarkEnabled ? "有効" : "無効"}
                </span>
              </button>

              {/* 11. 大事なデータのダウンロード */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("download_data");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">📥</span>
                  <div>
                    <div className="text-xs font-medium text-emerald-300">大事なデータのダウンロード</div>
                    <div className="text-[10px] text-gray-400">記憶・ノート・決済＆ガチャ台帳保存</div>
                  </div>
                </div>
                <span className="text-[10px] text-emerald-400">JSON</span>
              </button>

              {/* 12. 公開リンク */}
              <button
                type="button"
                onClick={() => {
                  setIsGearMenuOpen(false);
                  setActiveSettingsModal("public_links");
                }}
                className="w-full px-3.5 py-2 text-left hover:bg-gray-800 flex items-center justify-between transition"
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-base">🔗</span>
                  <div>
                    <div className="text-xs font-medium text-gray-200">公開リンクの管理</div>
                    <div className="text-[10px] text-gray-400">共有URL・スナップショット一覧</div>
                  </div>
                </div>
                <span className="text-[10px] text-gray-400">{publicLinks.length}件</span>
              </button>
            </div>
          )}
        </div>
      </aside>

      {/* ===================================================================== */}
      {/* 💳 「定期購入の管理」サブスク確認・ローカル擬似決済・ガチャ券10枚モーダル */}
      {/* ===================================================================== */}
      {activeSettingsModal === "subscription" && (
        <div
          onClick={() => setActiveSettingsModal(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-sm overflow-y-auto"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-gray-900 border border-amber-500/40 rounded-2xl max-w-4xl w-full p-5 text-gray-100 shadow-2xl space-y-5 max-h-[92vh] overflow-y-auto"
          >
            {/* モーダルヘッダー */}
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-gray-800 pb-3">
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xl">👑</span>
                  <h3 className="font-extrabold text-base sm:text-lg text-amber-400">
                    定期購入の管理（ローカル擬似決済 ＆ ガチャ券10枚シミュレーター）
                  </h3>
                  <span
                    className={clsx(
                      "px-2.5 py-0.5 rounded-full text-xs font-bold",
                      subState.plan === "pro_1yen"
                        ? "bg-amber-500/20 border border-amber-400/50 text-amber-300"
                        : "bg-emerald-500/20 border border-emerald-500/40 text-emerald-300"
                    )}
                  >
                    {subState.plan === "pro_1yen" ? "👑 Proプラン契約中 (月額1円)" : "🌱 無料プラン契約中 (0円)"}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  無料プランでガチャ券10枚、月額1円サブスクでさらにガチャ券10枚を付与！実際のお金の動き（50円下限・手数料3.6% vs ローカル0円決済）もここで実験できます。
                </p>
              </div>
              <button
                type="button"
                onClick={() => setActiveSettingsModal(null)}
                className="px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 font-bold"
              >
                ✕ 閉じる
              </button>
            </div>

            {/* トースト通知 */}
            {subToast && (
              <div className="rounded-xl bg-emerald-950/80 border border-emerald-500/50 px-4 py-2.5 text-xs text-emerald-200 flex items-center justify-between">
                <span>{subToast}</span>
                <button
                  type="button"
                  onClick={() => setSubToast(null)}
                  className="text-emerald-300 hover:text-white font-bold ml-3"
                >
                  閉じる
                </button>
              </div>
            )}

            {/* 1. お金のやり取り可視化モニター */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-gray-950 border border-gray-800 rounded-xl p-3.5">
              <div className="p-2.5 rounded-lg bg-gray-900 border border-sky-500/30">
                <div className="text-[11px] text-sky-300 font-bold">👛 ① ユーザー財布 (所持金)</div>
                <div className="text-xl font-extrabold text-white mt-1">
                  ¥{subState.user_wallet_jpy.toLocaleString()}
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">初期残高 ¥1,000</div>
              </div>

              <div className="p-2.5 rounded-lg bg-gray-900 border border-indigo-500/30">
                <div className="text-[11px] text-indigo-300 font-bold">🏦 ② アプリ内デポジット残高</div>
                <div className="text-xl font-extrabold text-indigo-300 mt-1">
                  {subState.app_deposit_jpy.toLocaleString()} pt
                </div>
                <div className="flex gap-1 mt-1.5">
                  <button
                    type="button"
                    onClick={() => handleChargeDeposit(50)}
                    className="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold"
                  >
                    +¥50チャージ
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChargeDeposit(100)}
                    className="px-2 py-0.5 rounded bg-indigo-600 hover:bg-indigo-500 text-white text-[10px] font-bold"
                  >
                    +¥100
                  </button>
                  <button
                    type="button"
                    onClick={() => handleChargeDeposit(1)}
                    className="px-1.5 py-0.5 rounded bg-rose-950 border border-rose-700 text-rose-300 text-[10px]"
                    title="1円直接カード決済エラーの実験"
                  >
                    ¥1実験
                  </button>
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-gray-900 border border-rose-500/30">
                <div className="text-[11px] text-rose-300 font-bold">🏢 ③ 決済代行手数料 (3.6%)</div>
                <div className="text-xl font-extrabold text-rose-400 mt-1">
                  ¥{subState.gateway_fee_jpy.toLocaleString()}
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">ローカル決済時は ¥0</div>
              </div>

              <div className="p-2.5 rounded-lg bg-gray-900 border border-emerald-500/30">
                <div className="text-[11px] text-emerald-300 font-bold">💰 ④ 運営金庫 (純売上)</div>
                <div className="text-xl font-extrabold text-emerald-400 mt-1">
                  ¥{subState.operator_revenue_jpy.toLocaleString()}
                </div>
                <div className="text-[10px] text-gray-400 mt-0.5">あなたの手取り累計</div>
              </div>
            </div>

            {/* 2. 無料プラン vs 月額1円Proプラン ＆ ガチャコーナー */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* プラン選択・1円決済枠 */}
              <div className="rounded-xl bg-gray-950 border border-gray-800 p-4 space-y-3">
                <div className="text-xs font-bold text-amber-300">
                  📋 プラン比較 ＆ ガチャ券10枚特典（無料10枚 ＋ 1円Pro10枚）
                </div>

                <div className="p-3 rounded-lg bg-gray-900 border border-emerald-500/40 flex items-center justify-between">
                  <div>
                    <div className="text-xs font-bold text-emerald-300">🌱 無料プラン (Free - ¥0/月)</div>
                    <div className="text-[11px] text-gray-400">初回ガチャ券10枚配布済・標準ローカルAI</div>
                  </div>
                  <span className="text-[11px] font-bold text-emerald-400">✅ 10枚受取済</span>
                </div>

                <div className="p-3 rounded-lg bg-gray-900 border border-amber-500/50 space-y-2.5">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-xs font-bold text-amber-300">👑 Pro 1円サブスク (¥1/月)</div>
                      <div className="text-[11px] text-gray-400">
                        契約ごとにゲームシミュレーション用ガチャ券10枚を追加プレゼント！
                      </div>
                    </div>
                    <span className="text-sm font-extrabold text-amber-300">¥1 / 月</span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => handleSubscribeOneYen("demo_instant")}
                      className="py-2 px-3 rounded-lg bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 text-gray-950 text-xs font-extrabold shadow"
                    >
                      ⚡ ① ローカル1円決済 (+🎫10枚)
                    </button>
                    <button
                      type="button"
                      onClick={() => handleSubscribeOneYen("deposit_wallet")}
                      className="py-2 px-3 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold shadow"
                    >
                      🏦 ② デポジットから1円 (+🎫10枚)
                    </button>
                  </div>

                  {subState.plan === "pro_1yen" && (
                    <button
                      type="button"
                      onClick={handleCancelSubscription}
                      className="w-full py-1.5 rounded-lg border border-gray-700 hover:border-rose-600 text-[11px] text-gray-300 hover:text-rose-300"
                    >
                      無料プランへ解約する（ガチャ券は維持されます）
                    </button>
                  )}
                </div>
              </div>

              {/* ゲームシミュレーション連動ガチャ枠 */}
              <div className="rounded-xl bg-gray-950 border border-indigo-500/40 p-4 flex flex-col justify-between space-y-3">
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-indigo-300">
                      🎰 ゲームシミュレーション連動ガチャ
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full bg-amber-500/20 border border-amber-500/40 text-amber-300 text-xs font-extrabold">
                      🎫 所持: {subState.gacha_tickets}枚
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => handlePullGacha(1)}
                      className="py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs font-bold text-white"
                    >
                      🎫 1回引く (1枚)
                    </button>
                    <button
                      type="button"
                      onClick={() => handlePullGacha(10)}
                      className="py-2 rounded-lg bg-gradient-to-r from-indigo-600 to-amber-500 hover:from-indigo-500 hover:to-amber-400 text-xs font-extrabold text-white shadow"
                    >
                      ✨ 10連ガチャ (10枚)
                    </button>
                  </div>

                  <div className="space-y-1.5 max-h-40 overflow-y-auto pr-1 pt-1">
                    {subState.gacha_inventory.length === 0 ? (
                      <div className="text-[11px] text-gray-500 text-center py-6">
                        無料特典の10枚で今すぐ「✨ 10連ガチャ」を引けます！
                      </div>
                    ) : (
                      subState.gacha_inventory.slice(0, 8).map((item, idx) => (
                        <div
                          key={`${item.id}_${idx}`}
                          className="p-2 rounded bg-gray-900 border border-gray-800 flex items-center justify-between text-[11px]"
                        >
                          <div>
                            <span className="font-bold text-amber-300 mr-1">[{item.rarity}]</span>
                            <span className="font-semibold text-white">{item.name}</span>
                            <div className="text-[10px] text-gray-400">{item.effect}</div>
                          </div>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-800 text-indigo-300 shrink-0">
                            {item.genre}
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </div>

            {/* 3. 直近の取引台帳 */}
            <div className="rounded-xl bg-gray-950 border border-gray-800 p-3.5 space-y-2">
              <div className="text-xs font-bold text-gray-300">📒 お金のやり取り・ガチャ券取引台帳</div>
              <div className="space-y-1.5 max-h-36 overflow-y-auto text-xs">
                {subState.transactions.map((tx) => (
                  <div
                    key={tx.id}
                    className="p-2 rounded bg-gray-900/80 border border-gray-800 flex flex-wrap items-center justify-between gap-2"
                  >
                    <div>
                      <span className="text-[10px] text-gray-500 mr-2">{tx.timestamp}</span>
                      <span className="font-bold text-white">{tx.title}</span>
                      <div className="text-[11px] text-gray-400">{tx.note}</div>
                    </div>
                    <div className="flex items-center gap-3 font-mono text-[11px]">
                      <span className="text-sky-300">支払:¥{tx.amount_jpy}</span>
                      <span className="text-rose-400">手数料:¥{tx.fee_jpy}</span>
                      <span className="text-emerald-400">売上:+¥{tx.net_revenue_jpy}</span>
                      {tx.tickets_delta !== 0 && (
                        <span className="text-amber-300 font-bold">
                          🎫{tx.tickets_delta > 0 ? `+${tx.tickets_delta}` : tx.tickets_delta}枚
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* ⚙️ その他の設定メニュー項目（パーソナル知能 / スキル / 電子透かし / 保存等） */}
      {/* ===================================================================== */}
      {activeSettingsModal && activeSettingsModal !== "subscription" && (
        <div
          onClick={() => setActiveSettingsModal(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="bg-gray-900 border border-gray-700 rounded-2xl max-w-lg w-full p-5 text-gray-100 shadow-2xl space-y-4"
          >
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <h3 className="font-bold text-base text-amber-300">
                {activeSettingsModal === "personal_intelligence" && "🧠 パーソナルインテリジェンス設定"}
                {activeSettingsModal === "skills" && "🧩 スキル (Skills) 管理"}
                {activeSettingsModal === "gemini" && "✨ Gemini ＆ AIモデル連携"}
                {activeSettingsModal === "theme" && "🎨 テーマ設定"}
                {activeSettingsModal === "tasks" && "✅ タスクの設定"}
                {activeSettingsModal === "browser" && "🌐 ブラウザ連携設定"}
                {activeSettingsModal === "watermark" && "🔍 電子透かし (SynthID / LSBステガノグラフィー)"}
                {activeSettingsModal === "download_data" && "📥 大事なデータのダウンロード（一括バックアップ）"}
                {activeSettingsModal === "public_links" && "🔗 公開リンクの管理"}
              </h3>
              <button
                type="button"
                onClick={() => setActiveSettingsModal(null)}
                className="text-gray-400 hover:text-white text-lg"
              >
                ✕
              </button>
            </div>

            {activeSettingsModal === "personal_intelligence" && (
              <div className="space-y-3 text-xs text-gray-300">
                <p>過去の会話履歴・AI学習メモ・高評価リスト（ダジャレ判定含む）・価値観レーダー診断の結果を回答へ自動反映します。</p>
                <label className="flex items-center justify-between p-3 rounded-xl bg-gray-800 border border-gray-700 cursor-pointer">
                  <span className="font-bold text-white">パーソナルインテリジェンスを有効化</span>
                  <input
                    type="checkbox"
                    checked={personalIntelEnabled}
                    onChange={(e) => setPersonalIntelEnabled(e.target.checked)}
                    className="w-4 h-4 accent-emerald-500"
                  />
                </label>
              </div>
            )}

            {activeSettingsModal === "skills" && (
              <div className="space-y-2 text-xs">
                {[
                  { name: "CodeChunker (AST/RAG分割)", status: "有効 (フォールバック内蔵)" },
                  { name: "Zero-Shot 5大構造特徴OCR・解答採点", status: "有効" },
                  { name: "ゲームシミュレーション (ローグライク/すごろく/TD)", status: "有効" },
                  { name: "歴史・偉人ポイント 50音順サブブラウザ", status: "有効" },
                  { name: "PSD / 2D→3D ステガノグラフィー抽出", status: "有効" },
                  { name: "ローカル擬似決済 ＆ ガチャ券10枚台帳", status: "有効" },
                ].map((sk) => (
                  <div key={sk.name} className="p-2.5 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-between">
                    <span className="font-semibold text-white">{sk.name}</span>
                    <span className="text-[11px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-bold">{sk.status}</span>
                  </div>
                ))}
              </div>
            )}

            {activeSettingsModal === "gemini" && (
              <div className="space-y-3 text-xs text-gray-300">
                <p>現在選択中の推論モデル: <strong className="text-amber-300">{subState.selected_model}</strong></p>
                <div className="p-3 rounded-lg bg-gray-800 border border-gray-700 space-y-1.5">
                  <div>・無料枠: <code className="text-emerald-300">to_model_local</code> / <code className="text-emerald-300">ollama_qwen_local</code></div>
                  <div>・1円Pro枠: <code className="text-amber-300">to_model_pro_hybrid</code> / <code className="text-amber-300">to_model_ultra_agent</code></div>
                </div>
                <button
                  type="button"
                  onClick={() => setActiveSettingsModal("subscription")}
                  className="w-full py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold"
                >
                  定期購入の管理（モデル切替）へ移動
                </button>
              </div>
            )}

            {activeSettingsModal === "theme" && (
              <div className="space-y-2.5 text-xs">
                {["Default (標準テーマ)", "Future Purple (近未来UI)", "Alexandros (古代ギリシャ風UI)"].map((t) => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => {
                      setCurrentThemeName(t);
                      navigate("/settings-api");
                      setActiveSettingsModal(null);
                    }}
                    className={clsx(
                      "w-full p-3 rounded-lg border text-left flex items-center justify-between",
                      currentThemeName === t
                        ? "bg-blue-600/20 border-blue-500 text-white font-bold"
                        : "bg-gray-800 border-gray-700 text-gray-300 hover:bg-gray-750"
                    )}
                  >
                    <span>{t}</span>
                    <span>{currentThemeName === t ? "適用中" : "選択"}</span>
                  </button>
                ))}
              </div>
            )}

            {activeSettingsModal === "tasks" && (
              <div className="space-y-3 text-xs text-gray-300">
                <p>バックグラウンドAIタスク（RAGインデックス作成・OCR解析・自己分析）の実行状態を確認します。</p>
                <button
                  type="button"
                  onClick={() => {
                    setActiveSettingsModal(null);
                    navigate("/memory");
                  }}
                  className="w-full py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold"
                >
                  AIメモリー＆タスク画面を開く
                </button>
              </div>
            )}

            {activeSettingsModal === "browser" && (
              <div className="space-y-3 text-xs text-gray-300">
                <p>50音順の歴史・偉人ポイント専用サブブラウザや、SSRF保護つきリモートAPIプローバーを起動できます。</p>
                <button
                  type="button"
                  onClick={() => {
                    setActiveSettingsModal(null);
                    handleLaunchPointsBrowser(selectedPersonaId);
                  }}
                  className="w-full py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold"
                >
                  🌐 歴史・偉人ポイント一覧ブラウザを別窓で開く
                </button>
              </div>
            )}

            {activeSettingsModal === "watermark" && (
              <div className="space-y-3 text-xs text-gray-300">
                <p>
                  生成した画像・図解OCRチャンク・2D→3D変換用PSDファイル（<code>psd_handler.py</code>）にLSBステガノグラフィー（電子透かし・AI意図メタデータ）を埋め込み・検証します。
                </p>
                <label className="flex items-center justify-between p-3 rounded-xl bg-gray-800 border border-gray-700 cursor-pointer">
                  <span className="font-bold text-white">LSB電子透かし・メタデータ自動付与</span>
                  <input
                    type="checkbox"
                    checked={watermarkEnabled}
                    onChange={(e) => setWatermarkEnabled(e.target.checked)}
                    className="w-4 h-4 accent-emerald-500"
                  />
                </label>
              </div>
            )}

            {activeSettingsModal === "download_data" && (
              <div className="space-y-3 text-xs text-gray-300">
                <p>
                  AI学習メモ、歴史ポイント、サブスクリプション＆ローカル擬似決済の取引台帳、ガチャ所持ユニット一覧を1つのJSONファイルとして手元にダウンロード保存できます。
                </p>
                <button
                  type="button"
                  onClick={handleDownloadImportantData}
                  className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold shadow-lg"
                >
                  📥 今すぐ大事なデータをJSONでダウンロード保存
                </button>
              </div>
            )}

            {activeSettingsModal === "public_links" && (
              <div className="space-y-2.5 text-xs">
                {publicLinks.map((lnk) => (
                  <div key={lnk.id} className="p-3 rounded-lg bg-gray-800 border border-gray-700 flex items-center justify-between gap-2">
                    <div className="truncate">
                      <div className="font-bold text-white">{lnk.title}</div>
                      <div className="text-[11px] text-blue-400 truncate">{lnk.url}</div>
                    </div>
                    <button
                      type="button"
                      onClick={() => setPublicLinks((prev) => prev.filter((x) => x.id !== lnk.id))}
                      className="px-2 py-1 rounded bg-rose-950/80 border border-rose-700 text-rose-300 text-[10px] shrink-0"
                    >
                      削除
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 🎓 歴史人物・ペルソナ 重要ポイント呼び出しモーダル                     */}
      {/* ===================================================================== */}
      {isPointModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-xs">
          <div className="bg-gray-900 border border-gray-700 rounded-xl max-w-md w-full p-5 text-gray-100 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-gray-800 pb-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">🎓</span>
                <h3 className="font-bold text-base text-amber-300">
                  歴史・偉人 試験ポイント呼び出し
                </h3>
              </div>
              <button
                onClick={() => setIsPointModalOpen(false)}
                className="text-gray-400 hover:text-white text-xl leading-none"
              >
                ×
              </button>
            </div>

            <div className="space-y-2">
              <label className="block text-xs text-gray-400">
                現在呼び出し中（または確認したい）人物・スタイルを選択：
              </label>
              <select
                value={selectedPersonaId}
                onChange={(e) => setSelectedPersonaId(e.target.value)}
                className="w-full px-3 py-2 rounded-lg bg-gray-800 border border-gray-700 text-sm text-white focus:outline-none focus:border-amber-500"
              >
                {[...HISTORICAL_AND_PERSONA_DATA]
                  .sort((a, b) => a.kana.localeCompare(b.kana, "ja"))
                  .map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name}（{p.category}）
                    </option>
                  ))}
              </select>
            </div>

            <div className="p-3.5 rounded-lg bg-gray-800/70 border border-gray-700 space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-amber-300">
                  {currentPersona.name}
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-gray-700 text-gray-300">
                  {currentPersona.archetype}
                </span>
              </div>

              {currentPersona.isExamTarget ? (
                <p className="text-xs text-gray-300 leading-relaxed">
                  試験に出る重要ポイントが <strong>{currentPersona.points.length}件</strong> 登録されています。下のボタンを押すと別ブラウザが立ち上がり、50音順リスト（◁ / ▽）からワンクリックで文章をコピーできます。
                </p>
              ) : (
                <div className="text-xs text-indigo-200 bg-indigo-950/60 border border-indigo-800/70 p-2.5 rounded leading-relaxed">
                  {currentPersona.aiNote}
                </div>
              )}
            </div>

            <div className="flex items-center justify-end gap-2 pt-2 border-t border-gray-800">
              <button
                onClick={() => setIsPointModalOpen(false)}
                className="px-3.5 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-xs text-gray-300 transition-colors"
              >
                キャンセル
              </button>
              <button
                onClick={() => handleLaunchPointsBrowser(currentPersona.id)}
                className="px-4 py-2 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-1.5 shadow-lg transition-colors"
              >
                <span>🌐</span>
                <span>新しいブラウザでポイント一覧を開く</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
