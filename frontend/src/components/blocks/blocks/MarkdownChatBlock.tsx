// frontend/src/components/blocks/MarkdownChatBlock.tsx
import React, { useState, useMemo } from 'react';
import { postLike } from '../../api/toApi'; // パスは実際の環境に合わせて調整してください
import HighRatedModal from '../HighRatedModal';

// ==========================================
// 1. いいね(👍)用のストレージ管理・定数
// ==========================================
const MAX_LEN = 2000;
const STORAGE_KEY = 'to_liked_texts';

const loadLiked = (): Set<string> => {
  try {
    return new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '[]'));
  } catch {
    return new Set();
  }
};

const saveLiked = (set: Set<string>) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify([...set].slice(-200)));
  } catch {
    /* 保存できなくても動作は継続 */
  }
};

// ==========================================
// 1.5 偉人・日本史・世界史 ＆ 実況者ポイントデータ（50音順対応）
// ==========================================
export interface HistoricalPersonaPoint {
  id: string;
  name: string;
  kana: string;
  category: '日本史' | '世界史' | 'YouTuber' | 'アニメ' | '方言';
  archetype: string;
  isExamTarget: boolean;
  points: string[];
  aiNote?: string;
}

const HISTORICAL_AND_PERSONA_DATA: HistoricalPersonaPoint[] = [
  {
    id: 'abehira_fu',
    name: '阿倍比羅夫',
    kana: 'あべのひらふ',
    category: '日本史',
    archetype: '開拓・交渉ストラテジスト型',
    isExamTarget: true,
    points: [
      '1. 飛鳥時代（斉明天皇朝）の将軍・越国守。658〜660年に水軍を率いて日本海側を北上し、蝦夷（えみし）や粛慎（みしはせ）を討伐した。',
      '2. 飽田（秋田）・渟代（能代）の蝦夷を服属させ、後方羊蹄（しりべし）に郡領を置いたとされる（『日本書紀』）。',
      '3. 663年の白村江の戦いにも水軍を率いて参戦したが、唐・新羅連合軍に敗れた。',
    ],
  },
  {
    id: 'igudon_ch',
    name: 'いぐどんch',
    kana: 'いぐどんちゃんねる',
    category: 'YouTuber',
    archetype: '超優しい友人 × 突発的発狂ギャップ型',
    isExamTarget: false,
    points: [],
    aiNote:
      '🌱 本当はすごく優しい友達なのに、理不尽な盤面でなぜか発狂モードに入るスタイルです！試験には出ないので、印象に残った神回や名言をあなた自身の言葉でポイント化してみてください✨',
  },
  {
    id: 'kukai',
    name: '空海',
    kana: 'くうかい',
    category: '日本史',
    archetype: '超越・宇宙観統合型',
    isExamTarget: true,
    points: [
      '1. 804年、最澄らとともに遣唐使（留学僧）として入唐し、長安の青龍寺で恵果から真言密教を授かる。',
      '2. 帰国後、嵯峨天皇から高野山を賜り金剛峯寺を創建、のち教王護国寺（東寺）を与えられ真言宗の拠点とした。',
      '3. 庶民も学べる教育機関『綜芸種智院』の設立や、讃岐国の『満濃池』の修築など社会・土木事業にも尽力した。',
      '4. 著書に儒・仏・道の優劣を戯曲風に論じた『三教指帰』や『十住心論』『文鏡秘府論』があり、三筆の一人としても知られる。',
    ],
  },
  {
    id: 'keichu',
    name: '契沖',
    kana: 'けいちゅう',
    category: '日本史',
    archetype: '実証・ストイック探究型',
    isExamTarget: true,
    points: [
      '1. 江戸時代前期（元禄文化期）の真言宗の僧・古典学者。大坂の円珠庵に隠棲し、古典の実証的研究により国学の先駆となった。',
      '2. 水戸藩主・徳川光圀の依頼を受け、『万葉集』の注釈書である『万葉代匠記』を著した。',
      '3. 文献実証主義に基づき古典の仮名遣いを調査し、『和字正濫鈔』で歴史的仮名遣い（契沖仮名遣）の基礎を確立した。',
    ],
  },
  {
    id: 'john_king',
    name: 'ジョン王',
    kana: 'じょんおう',
    category: '世界史',
    archetype: '記録・反面教師型',
    isExamTarget: true,
    points: [
      '1. イングランド・プランタジネット朝の王（在位1199〜1216）。リチャード1世の弟。',
      '2. フランス王フィリップ2世との戦いに敗れて大陸の領土の大半を失い、『欠地王（失地王）』と呼ばれた。また教皇インノケンティウス3世とも対立し破門された。',
      '3. 度重なる重税に反発した貴族たちにより、1215年に『マグナ・カルタ（大憲章）』への調印を余儀なくされ、王権の制限と立憲主義の礎となった。',
    ],
  },
  {
    id: 'shibukawa_harumi',
    name: '渋川春海',
    kana: 'しぶかわはるみ',
    category: '日本史',
    archetype: '実証・ストイック探究型',
    isExamTarget: true,
    points: [
      '1. 江戸時代前期の天文暦学者・囲碁棋士（安井算哲）。山崎闇斎に垂加神道や朱子学、数学・天文学を学んだ。',
      '2. 800年以上使われ約2日の誤差が生じていた中国伝来の『宣明暦』を改めるため、天体観測を行い元の授時暦を基に日本独自の『貞享暦』を作成した。',
      '3. 1684年（貞享元年）に幕府に採用され、初代幕府天文方に任命された。',
    ],
  },
  {
    id: 'bakumatsu_sakamoto',
    name: '幕末志士・坂本',
    kana: 'ばくまつししさかもと',
    category: 'YouTuber',
    archetype: '積極的・陽気 ＋ 制御不能時『ざーばあー』型',
    isExamTarget: false,
    points: [],
    aiNote:
      '🌱 優しくて積極的、そして操作が効かない絶体絶命の瞬間に『ざーばあー！！』と叫ぶ神プレイ実況スタイルです！歴史試験のポイントはないので、あなた自身の言葉で特徴や好きなシーンを作って追加してみてください✨',
  },
  {
    id: 'himiko',
    name: '卑弥呼',
    kana: 'ひみこ',
    category: '日本史',
    archetype: '超越・宇宙観統合型',
    isExamTarget: true,
    points: [
      '1. 『魏志』倭人伝に記される3世紀の邪馬台国の女王。倭国大乱を鎮めるため共立され、鬼道（呪術）を用いて統治した。',
      '2. 239年、大夫の難升米（なしめ）らを魏の皇帝に遣わし、『親魏倭王』の称号と金印、銅鏡100枚などを授かった。',
      '3. 狗奴国（男王・卑弥弓呼）との抗争中に死去し、径百余歩の巨大な塚が築かれた。跡を継いだ男王の代に再び乱れたが、壱与（台与）を立てて収まった。',
    ],
  },
  {
    id: 'fukushima_dialect',
    name: '福島県ことば',
    kana: 'ふくしまけんことば',
    category: '方言',
    archetype: '地域方言フィルター（会津・中通り・浜通り）',
    isExamTarget: false,
    points: [],
    aiNote:
      '🌱 『さすけねぇ（大丈夫）』『〜だべ』『なじょする？』など、温かみのある福島県の方言モードです。地元の言い回しや覚えておきたい方言フレーズがあれば、ぜひ自分でポイントを登録してみてください！',
  },
  {
    id: 'fujiwara_sanesuke',
    name: '藤原実資',
    kana: 'ふじわらのさねすけ',
    category: '日本史',
    archetype: '記録・辛口ウォッチャー型',
    isExamTarget: true,
    points: [
      '1. 平安時代中期の公卿（小野宮流）。有職故実に精通し、『賢人右府』と称された。',
      '2. 藤原道長が全盛を極めた時代にあっても道長に阿諛追従せず、筋を通した批判的な態度を貫いた。',
      '3. 彼の日記『小右記』は、道長の『御堂関白記』や藤原行成の『権記』と並び、摂関政治期の政治・社会を知る第一級史料。',
    ],
  },
  {
    id: 'fujiwara_seika',
    name: '藤原惺窩',
    kana: 'ふじわらせいか',
    category: '日本史',
    archetype: '超越・宇宙観統合型',
    isExamTarget: true,
    points: [
      '1. 安土桃山〜江戸時代初期の儒学者。京都・相国寺の禅僧であったが還俗し、仏教（五山禅林）に従属していた朱子学を独立させた『近世儒学の祖』。',
      '2. 徳川家康に招かれて進講したが自身は仕官せず、門弟の林羅山を幕府に推挙した。',
      '3. 門人には林羅山・松永尺五・那波活所・堀杏庵（惺窩門四天王）や石川丈山らがおり、著書に『寸鉄録』『四書五経倭訓』などがある。',
    ],
  },
  {
    id: 'min',
    name: '旻',
    kana: 'みん',
    category: '日本史',
    archetype: '制度設計・改革官僚型',
    isExamTarget: true,
    points: [
      '1. 飛鳥時代の学問僧（僧旻）。608年、小野妹子の第2回遣隋使に留学生として同行し、24年間（隋〜唐）滞在して仏教・律令・易学などを学んだ。',
      '2. 帰国後、蘇我入鹿や中大兄皇子らに学問を講じ、645年の乙巳の変（大化の改新）後に高向玄理とともに『国博士』に任じられ新政権の制度設計を担った。',
      '3. 650年、穴戸国から献上された白い雉を祥瑞と判定し、元号が『白雉』に改元される契機となった。',
    ],
  },
  {
    id: 'lassalle',
    name: 'ラッサール',
    kana: 'らっさーる',
    category: '世界史',
    archetype: '情熱・革命騎士型',
    isExamTarget: true,
    points: [
      '1. 19世紀ドイツの社会主義者・労働運動指導者。1863年にドイツ初の独立労働者政党『全ドイツ労働者同盟』を結成した。',
      '2. 自由放任主義国家を『夜警国家』と批判し、普通選挙権の獲得と国家の援助による生産協同組合の設立を主張した。',
      '3. のち1875年にゴータでマルクス派（アイゼナハ派）と合同し、『ドイツ社会主義労働者党（のちのSPD）』が結成された。',
    ],
  },
  {
    id: 'lafayette',
    name: 'ラファイエット',
    kana: 'らふぁいえっと',
    category: '世界史',
    archetype: '情熱・革命騎士型',
    isExamTarget: true,
    points: [
      '1. フランスの自由主義貴族・軍人。アメリカ独立戦争に義勇兵として参戦し、ワシントンを補佐して活躍した（『両大陸の英雄』）。',
      '2. 1789年のフランス革命勃発後、国民衛兵司令官に就任し、ジェファソンの助言も得て『人間と市民の権利の宣言（人権宣言）』を起草した。',
      '3. 立憲君主制を支持したが革命の急進化により亡命。のち1830年の七月革命でも国民衛兵を率い、ルイ＝フィリップの即位を支持した。',
    ],
  },
  {
    id: 'rezanov',
    name: 'レザーノフ',
    kana: 'れざーのふ',
    category: '日本史',
    archetype: '開拓・交渉ストラテジスト型',
    isExamTarget: true,
    points: [
      '1. ロシア帝国の外交官・露米会社（毛皮交易独占会社）の創設者。',
      '2. 1804年（文化元年）、かつて根室に来航したラクスマンが幕府から与えられた信牌を携え、アレクサンドル1世の使節として長崎に来航し通商を要求した。',
      '3. 幕府は半年間待たせた末に通商を拒絶。これに憤慨した部下のフヴォストフらが1806〜1807年に樺太・択捉島を襲撃した（文化露寇）。',
    ],
  },
  {
    id: 'locke',
    name: 'ロック',
    kana: 'ろっく',
    category: '世界史',
    archetype: '実証・ストイック探究型',
    isExamTarget: true,
    points: [
      '1. 17世紀イギリスの哲学者・政治思想家。『人間知性論』で人間の心を生まれつき白紙（タブラ・ラサ）と説き、イギリス経験論を確立した。',
      '2. 主著『統治二論（市民政府二論）』で名誉革命を理論的に正当化し、生命・自由・財産の自然権と社会契約説を唱えた。',
      '3. 政府が信託に背いた場合の『抵抗権（革命権）』や三権分立を主張し、アメリカ独立宣言やフランス人権宣言に多大な影響を与えた。',
    ],
  },
];

// 💡 新しいブラウザウィンドウを立ち上げて50音順＋◁/▽＋クリックコピー画面を描画する共通関数
export function openHistoricalPointsBrowser(initialTargetId: string = 'fujiwara_seika') {
  const popup = window.open(
    '',
    'ToHistoryExamPointsBrowser',
    'width=820,height=860,menubar=no,toolbar=no,location=no,status=no,resizable=yes,scrollbars=yes'
  );

  if (!popup) {
    alert('ポップアップがブロックされました。ブラウザのポップアップ許可設定をご確認ください。');
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
          名前または右側の「◁」をクリックすると「▽」になり、1〜上限までポイントが表示されます。ポイントをクリックすると文章をコピーできます。
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
      if (customPointsMap[item.id]) {
        item.points = customPointsMap[item.id];
      }
    });

    const openState = {};
    if (INITIAL_TARGET) {
      openState[INITIAL_TARGET] = true;
    }

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
                title="クリックして文章をコピー（サイドバーのAI学習メモにも記録されます）"
              >
                <span>\${pt}</span>
                <span class="text-[10px] text-gray-500 group-hover:text-amber-400 shrink-0 font-bold">📋 コピー</span>
              </div>
            \`;
          }).join("");

          if (person.isExamTarget) {
            bodyHtml = \`
              <div class="px-4 pb-4 pt-2 border-t border-gray-800 bg-gray-950/70 space-y-2">
                <div class="text-[11px] text-gray-400 mb-1">💡 思考の型: <span class="text-gray-300 font-semibold">\${person.archetype}</span>（クリックでコピー＆サイドバーのAIメモに保存）</div>
                \${pointsListHtml}
              </div>
            \`;
          } else {
            bodyHtml = \`
              <div class="px-4 pb-4 pt-3 border-t border-gray-800 bg-gray-950/70 space-y-3">
                <div class="p-3 rounded-lg bg-indigo-950/50 border border-indigo-800/70 text-xs text-indigo-200 leading-relaxed">
                  \${person.aiNote || "🌱 YouTuber・アニメ枠のため公式の試験ポイントはありません！あなた自身でポイントを作って登録してみてください✨"}
                </div>
                \${pointsListHtml}
                <div class="flex gap-2 pt-1">
                  <input
                    id="custom-input-\${person.id}"
                    type="text"
                    placeholder="自分でポイントを1行作成して追加（例：操作不能時にざーばあーと叫ぶ）..."
                    class="flex-1 px-3 py-2 rounded bg-gray-900 border border-gray-700 text-xs text-white focus:outline-none focus:border-purple-500"
                  />
                  <button
                    onclick="addCustomPoint('\${person.id}')"
                    class="px-3 py-2 rounded bg-purple-600 hover:bg-purple-500 text-white text-xs font-bold shrink-0"
                  >
                    ＋ 自分で追加
                  </button>
                </div>
              </div>
            \`;
          }
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
              <span class="text-amber-400 font-bold text-base select-none ml-2">
                \${isOpen ? "▽" : "◁"}
              </span>
            </button>
            \${bodyHtml}
          </div>
        \`;
      }).join("");
    }

    document.getElementById("searchInput").addEventListener("input", renderList);
    renderList();

    if (INITIAL_TARGET) {
      setTimeout(() => {
        const targetEl = document.getElementById("card-" + INITIAL_TARGET);
        if (targetEl) targetEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }, 150);
    }
  </script>
</body>
</html>`;

  popup.document.open();
  popup.document.write(htmlContent);
  popup.document.close();
}

// ==========================================
// 2. 型定義
// ==========================================
export interface MarkdownChatBlockProps {
  text?: string;
  role?: string;
  onOptionSelect?: (payload: any) => void;
}

interface DevActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  text: string;
  role: string;
  detectedPersona: HistoricalPersonaPoint;
  onOptionSelect?: (payload: any) => void; // 💡 追加: これがないとボタンのアクションが届きません
}

// ==========================================
// 3. 分離された開発者ツールモーダル（＋歴史ポイント起動統合）
// ==========================================
function DevActionModal({
  isOpen,
  onClose,
  text,
  role,
  detectedPersona,
  onOptionSelect,
}: DevActionModalProps) {
  const [selectedPersonaId, setSelectedPersonaId] = useState<string>(detectedPersona.id);

  if (!isOpen) return null;

  const activeTarget =
    HISTORICAL_AND_PERSONA_DATA.find((p) => p.id === selectedPersonaId) || detectedPersona;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4"
      onClick={onClose}
    >
      <div
        className="bg-slate-900 border border-slate-700 w-96 max-w-full rounded-xl shadow-2xl p-4 flex flex-col gap-2"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center border-b border-slate-700 pb-2 mb-1">
          <span className="font-bold text-slate-200 text-sm">🛠️ 開発者特権 ＆ 学習ポイントメニュー</span>
          <button onClick={onClose} className="text-slate-400 hover:text-white text-lg leading-none">
            ×
          </button>
        </div>

        <div className="text-xs text-slate-400 mb-1">
          対象: {role === 'user' ? 'ユーザーの入力' : 'AIの出力'}
        </div>

        {/* 💡 新規追加：歴史・偉人 試験ポイント呼び出しセクション */}
        <div className="p-3 rounded-lg bg-amber-950/30 border border-amber-500/40 space-y-2 mb-1">
          <div className="text-xs font-bold text-amber-300 flex items-center justify-between">
            <span>🎓 歴史・偉人 試験ポイント呼出</span>
            <span className="text-[10px] bg-amber-500/20 px-1.5 py-0.5 rounded">50音順・◁/▽</span>
          </div>

          <select
            value={selectedPersonaId}
            onChange={(e) => setSelectedPersonaId(e.target.value)}
            className="w-full px-2.5 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs text-white focus:outline-none focus:border-amber-500"
          >
            {[...HISTORICAL_AND_PERSONA_DATA]
              .sort((a, b) => a.kana.localeCompare(b.kana, 'ja'))
              .map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}（{p.category}）
                </option>
              ))}
          </select>

          {!activeTarget.isExamTarget && (
            <div className="text-[11px] text-indigo-200 bg-indigo-950/60 border border-indigo-800/60 p-2 rounded leading-relaxed">
              {activeTarget.aiNote}
            </div>
          )}

          <button
            onClick={() => {
              openHistoricalPointsBrowser(activeTarget.id);
              onClose();
            }}
            className="w-full text-center text-xs font-bold bg-amber-600 hover:bg-amber-500 text-white py-2 px-3 rounded transition-colors shadow"
          >
            🌐 新しいブラウザで「{activeTarget.name}」のポイントを開く
          </button>
        </div>

        <button className="text-left text-xs bg-slate-800 hover:bg-indigo-900/50 text-slate-300 p-2 rounded transition-colors border border-slate-700 hover:border-indigo-500">
          🐛 Fuzzingテストを実行 (WIP)
        </button>
        <button className="text-left text-xs bg-slate-800 hover:bg-emerald-900/50 text-slate-300 p-2 rounded transition-colors border border-slate-700 hover:border-emerald-500">
          🧠 他のAI連携用プロンプトを生成 (WIP)
        </button>
        <button className="text-left text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors border border-slate-700">
          💾 テストケースとしてエクスポート (WIP)
        </button>
        <button className="text-left text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors border border-slate-700">
          🔍 Raw JSONをインスペクト (WIP)
        </button>

        {/* 💡 onClickイベントを追加し、onOptionSelect経由でAIにチャット送信命令を出す */}
        <button
          onClick={() => {
            onOptionSelect?.({
              action: 'send_chat',
              text: '🔍 手相占いなど画像読み取り系の開発の仕方(振り返り用)',
            });
            onClose();
          }}
          className="text-left text-xs bg-slate-600 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors border border-slate-700"
        >
          🔍 手相占いなど画像読み取り系の開発の仕方(振り返り用)
        </button>

        <button
          onClick={() => {
            onOptionSelect?.({
              action: 'send_chat',
              text: '🔍 高評価ボタンの実装は大変(振り返り用)',
            });
            onClose();
          }}
          className="text-left text-xs bg-slate-600 hover:bg-slate-700 text-slate-300 p-2 rounded transition-colors border border-slate-700"
        >
          🔍 高評価ボタンの実装は大変(振り返り用)
        </button>
      </div>
    </div>
  );
}

// ==========================================
// 4. メインコンポーネント (テキスト描画とツールバー)
// ==========================================
export default function MarkdownChatBlock({
  text,
  role = 'ai',
  onOptionSelect,
}: MarkdownChatBlockProps) {
  const [copied, setCopied] = useState(false);
  const [showProgress, setShowProgress] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isHighRatedOpen, setIsHighRatedOpen] = useState(false);

  // --- いいね(👍)用のState ---
  const trimmed = text?.trim() || '';
  const [liked, setLiked] = useState(() => loadLiked().has(trimmed));
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);

  // 💡 会話テキスト内に登場している歴史人物・実況者を自動検出（無ければデフォルトで藤原惺窩）
  const detectedPersona = useMemo(() => {
    const found = HISTORICAL_AND_PERSONA_DATA.find((p) => trimmed.includes(p.name));
    return (
      found ||
      HISTORICAL_AND_PERSONA_DATA.find((p) => p.id === 'fujiwara_seika') ||
      HISTORICAL_AND_PERSONA_DATA[0]
    );
  }, [trimmed]);

  if (!text) return null;

  const isUser = role === 'user';

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      console.error('Failed to copy', e);
    }
  };

  const handleLikeClick = async () => {
    if (liked || busy || !trimmed) return;
    setBusy(true);
    setFailed(false);
    try {
      await postLike(trimmed.slice(0, MAX_LEN));
      const set = loadLiked();
      set.add(trimmed);
      saveLiked(set);
      setLiked(true);
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div
      className={`w-full leading-relaxed space-y-2 text-sm md:text-base ${
        isUser ? 'text-white' : 'text-slate-800 dark:text-slate-200'
      }`}
    >
      <div className="whitespace-pre-wrap break-words">{text}</div>

      <div
        className={`pt-2 flex flex-wrap items-center gap-4 mt-2 border-t ${
          isUser ? 'border-indigo-400/50' : 'border-slate-100 dark:border-slate-700/50'
        }`}
      >
        <button
          onClick={handleCopy}
          className={`mt-1 text-xs flex items-center gap-1 transition-colors ${
            isUser
              ? 'text-indigo-200 hover:text-white'
              : 'text-slate-500 hover:text-indigo-600 dark:hover:text-indigo-400'
          }`}
        >
          {copied ? '✅ コピー完了' : '📋 コピー'}
        </button>

        {!isUser && (
          <>
            <button
              type="button"
              onClick={handleLikeClick}
              disabled={liked || busy}
              aria-pressed={liked}
              className={`mt-1 flex items-center gap-1 rounded-md px-2 py-0.5 text-xs transition disabled:cursor-default ${
                liked
                  ? 'bg-amber-100 font-semibold text-amber-700 dark:bg-amber-950 dark:text-amber-300'
                  : 'text-slate-500 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-700 dark:hover:text-slate-200'
              }`}
            >
              {liked ? '👍 済' : busy ? '…' : '👍'}
              {failed && <span className="ml-1 text-red-500">失敗</span>}
            </button>

            <button
              type="button"
              onClick={() => setIsHighRatedOpen(true)}
              className="mt-1 text-xs flex items-center gap-1 text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 transition-colors"
            >
              ⭐ 高評価リスト
            </button>

            <button
              onClick={() => setShowProgress(!showProgress)}
              className="mt-1 text-xs flex items-center gap-1 text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors"
            >
              📊 進捗解析 (Dev)
            </button>
          </>
        )}

        <button
          onClick={() => setIsModalOpen(true)}
          className={`mt-1 text-xs flex items-center gap-1 transition-colors ${
            isUser
              ? 'text-emerald-200 hover:text-white'
              : 'text-slate-500 hover:text-emerald-600 dark:hover:text-emerald-400'
          }`}
        >
          🛠️ Dev Actions / 🎓 ポイント
        </button>
      </div>

      {!isUser && showProgress && (
        <div className="mt-3 p-3 bg-slate-950 text-emerald-400 font-mono text-xs rounded-lg border border-slate-800 shadow-inner">
          <p className="font-bold text-slate-300 mb-2">🚀 to_model Internal Status</p>
          <ul className="space-y-1">
            <li>[✓] 1番の目標: 単純計算モジュール - 77%達成</li>
            <li>[↻] 2番の目標: ローカル KnowledgeRouter 統合 - 45%達成</li>
            <li>[ ] 3番の目標: 自動UI構築と自己修復 - 12%達成</li>
          </ul>
        </div>
      )}

      {/* 💡 onOptionSelect と 自動検出した人物(detectedPersona) を確実に渡す */}
      <DevActionModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        text={text}
        role={role}
        detectedPersona={detectedPersona}
        onOptionSelect={onOptionSelect}
      />

      <HighRatedModal
        isOpen={isHighRatedOpen}
        onClose={() => setIsHighRatedOpen(false)}
        fixed={true}
      />
    </div>
  );
}