// src/constants/pillarMeta.js

// ----------------------------------------------------------------
// 1. 定数（タイポ防止 & 自動補完用）
// ----------------------------------------------------------------
export const METRIC_KEYS = {
  PARK: 'park',
  DISASTER: 'disaster',
  AED: 'aed',
  SPORTS: 'sports',
  CHILDCARE: 'childcare',
  COMMERCE_LIFE: 'commerce_life',
  COMMERCE_CBD: 'commerce_cbd',
  LIBRARY: 'library',
  COMMERCE: 'commerce',
  POPULATION: 'population',
  SAFETY: 'safety',
};

export const CATEGORY_KEYS = {
  ALL: 'all',
  CHILDCARE: 'childcare_group',
  EDUCATION: 'education_group',
  POPULATION: 'population_group',
  SAFETY: 'safety_group',
};

// ----------------------------------------------------------------
// 1.5. フロントの METRIC_KEYS ⇔ バックエンドの theme(YAML) 名の対応表
// ----------------------------------------------------------------
// バックエンド(orchestrator/themes/*.yaml)の名前とフロントの METRIC_KEYS は
// 完全には一致していない。ここで1箇所にまとめておくことで、
// 「どのAPIテーマを叩けばどのpillarが埋まるか」が一目でわかるようにする。
//
// null のキーは、対応するテーマYAMLがまだ存在しない（＝バックエンドから
// データを取得しようがない）ことを明示している。ここが null のpillarは
// buildDistrictsFromApiScores() で常に null（データなし）になる。
export const METRIC_KEY_TO_BACKEND_THEME = {
  [METRIC_KEYS.PARK]: 'park',
  [METRIC_KEYS.DISASTER]: 'disaster',
  [METRIC_KEYS.AED]: 'aed',
  [METRIC_KEYS.SPORTS]: 'sports',
  [METRIC_KEYS.CHILDCARE]: 'childcare',
  [METRIC_KEYS.LIBRARY]: 'library',
  [METRIC_KEYS.COMMERCE_LIFE]: 'shopping',   // バックエンドでは "shopping" という名前
  [METRIC_KEYS.COMMERCE_CBD]: 'downtown',    // バックエンドでは "downtown" という名前
  [METRIC_KEYS.COMMERCE]: null,              // 未実装（対応テーマYAML無し）
  [METRIC_KEYS.POPULATION]: null,            // 未実装（人口"増加率"の指標は現状バックエンドに無い）
  [METRIC_KEYS.SAFETY]: null,                // 未実装（対応テーマYAML無し）
};

// バックエンドで取得可能な（=nullでない）pillarキーだけの一覧
export const IMPLEMENTED_METRIC_KEYS = Object.values(METRIC_KEYS).filter(
  (key) => METRIC_KEY_TO_BACKEND_THEME[key] !== null
);

// ----------------------------------------------------------------
// 1.6. 区の「地図上の位置」メタ情報（スコアではない静的データ）
// ----------------------------------------------------------------
// x, y はイラストマップ上の配置（デザイン上の固定値）であり、
// オープンデータから取得するものではないので、スコアとは別に保持する。
// scores はここには含めない（buildDistrictsFromApiScores() が埋める）。
export const DISTRICT_MAP_META = [
  { code: '13101', name: '千代田区', bestEmoji: '🏢', description: '日本の中心。皇居の緑と圧倒的な利便性。', x: 55, y: 55 },
  { code: '13102', name: '中央区', bestEmoji: '🛍️', description: '銀座や日本橋を擁し、人口増加が著しいエリア。', x: 65, y: 60 },
  { code: '13103', name: '港区', bestEmoji: '🗼', description: '国際色豊かで、ハイエンドな商業施設が集積。', x: 55, y: 70 },
  { code: '13104', name: '新宿区', bestEmoji: '🏙️', description: '日本有数の繁華街と、静かな住宅街が混在。', x: 40, y: 45 },
  { code: '13105', name: '文京区', bestEmoji: '🎓', description: '治安が非常に良く、教育環境が抜群の文教地区。', x: 55, y: 40 },
  { code: '13106', name: '台東区', bestEmoji: '🏮', description: '浅草や上野など、下町情緒と文化が息づく街。', x: 65, y: 35 },
  { code: '13107', name: '墨田区', bestEmoji: '🗼', description: 'スカイツリーを中心に再開発が進む水辺の街。', x: 75, y: 40 },
  { code: '13108', name: '江東区', bestEmoji: '🌊', description: '豊洲などの湾岸エリアにファミリー層が急増中。', x: 75, y: 65 },
  { code: '13109', name: '品川区', bestEmoji: '🚄', description: '交通アクセスが抜群で、独自の子育て支援も充実。', x: 55, y: 85 },
  { code: '13110', name: '目黒区', bestEmoji: '☕', description: 'おしゃれなカフェやお店が多く、閑静な住宅街。', x: 40, y: 75 },
  { code: '13111', name: '大田区', bestEmoji: '✈️', description: '面積が広く、羽田空港を擁する。町工場の活気も。', x: 50, y: 95 },
  { code: '13112', name: '世田谷区', bestEmoji: '🌳', description: 'みどりが多く、のびのび子育てができる人気エリア。', x: 20, y: 65 },
  { code: '13113', name: '渋谷区', bestEmoji: '🎵', description: '若者文化の発信地でありながら、代々木公園の自然も。', x: 40, y: 55 },
  { code: '13114', name: '中野区', bestEmoji: '👾', description: 'サブカルチャーの聖地。単身者に人気の高い街。', x: 30, y: 40 },
  { code: '13115', name: '杉並区', bestEmoji: '🚲', description: '中央線沿線の文化が根付く、住みやすい住宅街。', x: 15, y: 45 },
  { code: '13116', name: '豊島区', bestEmoji: '🦉', description: '池袋を中心とした大繁華街と、再開発による住みやすさ。', x: 40, y: 30 },
  { code: '13117', name: '北区', bestEmoji: '🌸', description: '飛鳥山公園など自然豊かで、下町の温かさが残る。', x: 55, y: 15 },
  { code: '13118', name: '荒川区', bestEmoji: '🚋', description: '都電が走り、物価が安く生活しやすい下町。', x: 65, y: 25 },
  { code: '13119', name: '板橋区', bestEmoji: '🏞️', description: '公園が多く、ファミリー層にとってコスパの良い街。', x: 35, y: 15 },
  { code: '13120', name: '練馬区', bestEmoji: '🥬', description: '23区で最も緑被率が高く、都市農業も盛ん。', x: 15, y: 25 },
  { code: '13121', name: '足立区', bestEmoji: '🚲', description: '物価が安く、近年は治安改善・大学誘致が進む。', x: 70, y: 10 },
  { code: '13122', name: '葛飾区', bestEmoji: '🎬', description: 'こち亀や寅さんの舞台。人情味あふれる街並み。', x: 85, y: 20 },
  { code: '13123', name: '江戸川区', bestEmoji: '👶', description: '子育て支援が手厚く、水と緑の豊かな公園が多数。', x: 90, y: 50 },
];

// ----------------------------------------------------------------
// 1.7. API実データから districts 配列を組み立てる
// ----------------------------------------------------------------
/**
 * apiScoresByTheme: { [backendThemeName]: { [wardName]: totalScore } }
 * 例: { park: { "世田谷区": 83.4, ... }, aed: { "世田谷区": 61.2, ... } }
 *
 * useMatchingData.js 側で、IMPLEMENTED_METRIC_KEYS を元に
 * `GET /api/scores?theme=<backendThemeName>` を並列fetchし、
 * `{city_name, total_score}` の配列を { [city_name]: total_score } に
 * 詰め替えたものを渡すことを想定している。
 *
 * 🚫 ここでは Math.random() のようなダミー埋めは一切行わない。
 *    対応データが無い pillar は必ず null になる（UI側で「データなし」表示にする）。
 */
export function buildDistrictsFromApiScores(apiScoresByTheme = {}) {
  const MIN_RAW_COUNT = 3; // これ未満は「資料なし」扱い

  return DISTRICT_MAP_META.map((meta) => {
    const scores = {};
    const scoreStatus = {}; // 'not_implemented' | 'no_data' | 'ok'

    Object.values(METRIC_KEYS).forEach((key) => {
      const backendTheme = METRIC_KEY_TO_BACKEND_THEME[key];
      if (!backendTheme) {
        scores[key] = null;
        scoreStatus[key] = 'not_implemented';
        return;
      }
      const themeScores = apiScoresByTheme[backendTheme];
      const entry = themeScores ? themeScores[meta.name] : undefined;

      if (!entry || entry.raw_count < MIN_RAW_COUNT) {
        scores[key] = null;
        scoreStatus[key] = 'no_data';
      } else {
        scores[key] = entry.score;
        scoreStatus[key] = 'ok';
      }
    });

    return { ...meta, scores, scoreStatus };
  });
}
// ----------------------------------------------------------------
// 2. 各指標のメタ情報（基本データ）
// ----------------------------------------------------------------
export const PILLAR_META = {
  [METRIC_KEYS.PARK]: {
    emoji: '🌳',
    label: 'みどり・公園',
    color: '#2ecc71',
    unit: '箇所',
    chip: true,
    desc: '公園の多さや自然環境の豊かさ',
    mapsQuery: n => `${n} 公園`
  },
  [METRIC_KEYS.DISASTER]: {
    emoji: '🏠',
    label: '防災・避難所',
    color: '#e67e22',
    unit: '箇所',
    chip: true,
    desc: '避難所や防災拠点のアクセス性',
    mapsQuery: n => `${n} 避難所`
  },
  [METRIC_KEYS.AED]: {
    emoji: '💗',
    label: 'AED・救急対応',
    color: '#e74c3c',
    unit: '台',
    chip: true,
    desc: 'AED設置数や医療救急体制',
    mapsQuery: n => `${n} AED`
  },
  [METRIC_KEYS.SPORTS]: {
    emoji: '⚽',
    label: 'スポーツ・運動',
    color: '#3498db',
    unit: '施設',
    chip: true,
    desc: '体育館や運動場の充実度',
    mapsQuery: n => `${n} スポーツ施設`
  },
  [METRIC_KEYS.CHILDCARE]: {
    emoji: '👶',
    label: '子育て・保育園',
    color: '#f1c40f',
    unit: '園',
    chip: true,
    desc: '保育園数や子育て支援体制',
    mapsQuery: n => `${n} 保育園`
  },
  [METRIC_KEYS.COMMERCE_LIFE]: {
    emoji: '🛍️',
    label: '普段の買い物',
    color: '#9b59b6',
    unit: '店舗',
    chip: true,
    desc: 'スーパーや日常使いの商店街',
    mapsQuery: n => `${n} 商店街`
  },
  [METRIC_KEYS.COMMERCE_CBD]: {
    emoji: '🌆',
    label: '繁華街の賑わい',
    color: '#8e44ad',
    unit: 'エリア',
    chip: true,
    desc: '大型商業施設や賑わいスポット',
    mapsQuery: n => `${n} 繁華街`
  },
  [METRIC_KEYS.LIBRARY]: {
    emoji: '📚',
    label: '図書館',
    color: '#1abc9c',
    unit: '館',
    chip: true,
    desc: '図書館や学習環境の充実度',
    mapsQuery: n => `${n} 図書館`
  },
  [METRIC_KEYS.COMMERCE]: {
    emoji: '🏪',
    label: '商業・お店の多さ',
    color: '#34495e',
    unit: '店',
    chip: false,
    desc: '店舗の総数や利便性',
    mapsQuery: n => `${n} 商店街`
  },
  [METRIC_KEYS.POPULATION]: {
    emoji: '📈',
    label: '人口増加率',
    color: '#16a085',
    unit: '%',
    chip: true,
    desc: '街の活気や将来性',
    mapsQuery: n => `${n} 街並み`
  },
  [METRIC_KEYS.SAFETY]: {
    emoji: '🛡️',
    label: '治安・防犯',
    color: '#2980b9',
    unit: '件',
    chip: true,
    desc: '交番の多さや防犯対策',
    mapsQuery: n => `${n} 交番`
  },
};

export function getMetricMeta(key) {
  return PILLAR_META[key] || {
    emoji: '✨',
    label: key || '指標',
    color: '#7f8c8d',
    unit: '点',
    chip: true,
    desc: '詳細データ',
    mapsQuery: n => `${n}`
  };
}

// ----------------------------------------------------------------
// 3. カテゴリ定義（重み付け weights を追加可能に）
// ----------------------------------------------------------------
export const CATEGORIES = {
  [CATEGORY_KEYS.ALL]: {
    id: CATEGORY_KEYS.ALL,
    label: '総合バランス',
    emoji: '✨',
    desc: 'あらゆる生活指標をバランスよく考慮',
    metrics: [
      METRIC_KEYS.PARK, METRIC_KEYS.DISASTER, METRIC_KEYS.AED,
      METRIC_KEYS.SPORTS, METRIC_KEYS.CHILDCARE, METRIC_KEYS.COMMERCE_LIFE,
      METRIC_KEYS.LIBRARY, METRIC_KEYS.SAFETY
    ]
  },
  [CATEGORY_KEYS.CHILDCARE]: {
    id: CATEGORY_KEYS.CHILDCARE,
    label: '保育・防災安心',
    emoji: '👶',
    desc: '子育てファミリーや万が一の備えを重視',
    metrics: [METRIC_KEYS.CHILDCARE, METRIC_KEYS.DISASTER, METRIC_KEYS.AED],
    weights: { [METRIC_KEYS.CHILDCARE]: 0.5, [METRIC_KEYS.DISASTER]: 0.3, [METRIC_KEYS.AED]: 0.2 }
  },
  [CATEGORY_KEYS.EDUCATION]: {
    id: CATEGORY_KEYS.EDUCATION,
    label: '教育・育成',
    emoji: '📚',
    desc: '子どもの習い事や学習・運動環境が充実',
    metrics: [METRIC_KEYS.LIBRARY, METRIC_KEYS.SPORTS, METRIC_KEYS.COMMERCE]
  },
  // [CATEGORY_KEYS.POPULATION]: {
  //   id: CATEGORY_KEYS.POPULATION,
  //   label: '人口推移',
  //   emoji: '📈',
  //   desc: '若い世代が集まる将来性と賑わい',
  //   metrics: [METRIC_KEYS.POPULATION, METRIC_KEYS.COMMERCE_CBD]
  // },
  [CATEGORY_KEYS.SAFETY]: {
    id: CATEGORY_KEYS.SAFETY,
    label: '治安・防犯',
    emoji: '🛡️',
    desc: '一人暮らしやシニアも安心な街づくり',
    metrics: [METRIC_KEYS.SAFETY, METRIC_KEYS.DISASTER, METRIC_KEYS.AED]
  }
};

export const CATEGORIES_LIST = Object.values(CATEGORIES);
export const METRIC_LIST = Object.values(PILLAR_META);
export const CHIP_METRIC_LIST = METRIC_LIST.filter(m => m.chip);

// ----------------------------------------------------------------
// 4. スコア計算 ＆ ランクスタイル定義
// ----------------------------------------------------------------
export const RANK_CONFIG = {
  S: { label: '25.1~点', color: '#22f10f', bg: '#fef9e7', border: '#f39c12' },
  A: { label: '4.1~25点', color: '#ccbf2e', bg: '#e8f8f5', border: '#27ae60' },
  B: { label: '1.1~4点', color: '#3498db', bg: '#ebf5fb', border: '#2980b9' },
  C: { label: '~1点', color: '#e94c4c', bg: '#f2f4f4', border: '#7f8c8d' },
};
// export const RANK_CONFIG = {
//   S: { label: '85〜100点', ... },
//   A: { label: '70〜84点', ... },
//   B: { label: '55〜69点', ... },
//   C: { label: '〜54点', ... },
// };
/**
 * [パッチ] scores[key] が null/undefined（＝データ未取得）のキーは
 * 「0点」として計算に混ぜるのではなく、計算対象そのものから除外する。
 * 以前は `scores[key] || 0` で欠損値を0点扱いしていたため、
 * 未実装のpillar（commerce/population/safety等）が交ざると
 * どの区も一律に不利になり、実装済みpillarの差が見えにくくなっていた。
 */
export function calculateCategoryScore(scores = {}, metricKeys = [], maxSnapshotItems = 2, categoryKey = null) {
  const availableKeys = metricKeys.filter((key) => scores[key] !== null && scores[key] !== undefined);

  if (!availableKeys.length) {
    return {
      total: 0,
      normalizedScore: 0,
      rank: 'C',
      rankMeta: RANK_CONFIG.C,
      snapshotText: 'データ準備中',
      missingCount: metricKeys.length,
    };
  }

  const category = categoryKey ? CATEGORIES[categoryKey] : null;
  const weights = category?.weights;

  let total = 0;
  let weightedTotal = 0;
  let weightSum = 0;
  const itemScores = [];

  availableKeys.forEach((key) => {
    const meta = getMetricMeta(key);
    const score = scores[key];
    total += score;

    const weight = weights?.[key] ?? (1 / availableKeys.length);
    weightedTotal += score * weight;
    weightSum += weight;

    itemScores.push({ key, meta, score });
  });

  const topItems = [...itemScores]
    .sort((a, b) => b.score - a.score)
    .slice(0, maxSnapshotItems);

  const snapshotParts = topItems.map(item => `${item.meta.label} ${item.score}点`);
  let snapshotText = snapshotParts.join(' + ');
  const missingCount = metricKeys.length - availableKeys.length;
  if (availableKeys.length > maxSnapshotItems) {
    snapshotText += ` (+他${availableKeys.length - maxSnapshotItems}項目)`;
  }
  if (missingCount > 0) {
    snapshotText += ` ※${missingCount}項目データ準備中`;
  }

  // weightSumで正規化することで、重み付けカテゴリで一部pillarが欠損していても
  // 残りの重みの合計を100%とみなして計算する
  const normalizedScore = weights
    ? Math.round(weightSum > 0 ? weightedTotal / weightSum : 0)
    : Math.round(total / availableKeys.length);

  let rank = 'C';
  if (normalizedScore >= 25) rank = 'S';
  else if (normalizedScore >= 5) rank = 'A';
  else if (normalizedScore >= 1) rank = 'B';

  return {
    total,
    normalizedScore,
    rank,
    rankMeta: RANK_CONFIG[rank],
    snapshotText,
    missingCount,
  };
}

export function rankDistrictsByCategory(districts = [], categoryKey = 'all') {
  const category = CATEGORIES[categoryKey] || CATEGORIES.all;

  return districts
    .map((district) => {
      const scoreInfo = calculateCategoryScore(district.scores, category.metrics, 2, categoryKey);
      return {
        ...district,
        categoryTotalScore: scoreInfo.total,
        categoryNormalizedScore: scoreInfo.normalizedScore,
        categoryRank: scoreInfo.rank,
        categoryRankMeta: scoreInfo.rankMeta,
        snapshotText: scoreInfo.snapshotText
      };
    })
    .sort((a, b) => b.categoryTotalScore - a.categoryTotalScore);
}

// ----------------------------------------------------------------
// 5. 分析 ＆ 比較（VSモード）ユーティリティ
// ----------------------------------------------------------------

export function analyzeDistrict(selected, allDistricts = []) {
  if (!selected || !selected.scores) return null;

  // [パッチ] null（データ未取得）のpillarはbest/worstの対象から除外する
  const entries = Object.entries(selected.scores).filter(([, v]) => v !== null && v !== undefined);
  if (entries.length === 0) return null;

  const sorted = [...entries].sort((a, b) => b[1] - a[1]);
  const [bestKey, bestScore] = sorted[0];
  const [worstKey, worstScore] = sorted[sorted.length - 1];

  const complementDistrict = allDistricts
    .filter(d => d.code !== selected.code)
    .reduce((prev, curr) => {
      const prevScore = prev?.scores?.[worstKey] ?? -1;
      const currScore = curr?.scores?.[worstKey] ?? -1;
      return currScore > prevScore ? curr : prev;
    }, null);

  return {
    best: { key: bestKey, score: bestScore, meta: getMetricMeta(bestKey) },
    worst: { key: worstKey, score: worstScore, meta: getMetricMeta(worstKey) },
    complement: complementDistrict
  };
}

export function compareDistricts(districtA, districtB, categoryKey = 'all') {
  if (!districtA || !districtB) return null;

  const category = CATEGORIES[categoryKey] || CATEGORIES.all;
  const scoreA = calculateCategoryScore(districtA.scores, category.metrics, 2, categoryKey);
  const scoreB = calculateCategoryScore(districtB.scores, category.metrics, 2, categoryKey);

  return {
    districtA: { ...districtA, scoreInfo: scoreA },
    districtB: { ...districtB, scoreInfo: scoreB },
    winnerCode: scoreA.total >= scoreB.total ? districtA.code : districtB.code,
    scoreDiff: Math.abs(scoreA.total - scoreB.total)
  };
}

// ----------------------------------------------------------------
// 6. URL ＆ デザインヘルパー関数
// ----------------------------------------------------------------

export function getGoogleMapsUrl(districtName, metricKey) {
  const meta = getMetricMeta(metricKey);
  const query = meta.mapsQuery(districtName);
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`東京都${query}`)}`;
}

export function getGoogleSearchUrl(districtName, metricKey) {
  const meta = getMetricMeta(metricKey);
  return `https://www.google.com/search?q=${encodeURIComponent(`${districtName} ${meta.label}`)}`;
}

export function getCategoryGradient(categoryKey) {
  const category = CATEGORIES[categoryKey];
  if (!category || !category.metrics.length) {
    return 'linear-gradient(135deg, #2c3e50, #3498db)';
  }

  const colors = category.metrics.slice(0, 2).map(k => getMetricMeta(k).color);
  if (colors.length === 1) return colors[0];
  return `linear-gradient(135deg, ${colors[0]}, ${colors[1]})`;
}