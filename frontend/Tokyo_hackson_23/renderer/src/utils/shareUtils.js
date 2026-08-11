
// src/utils/shareUtils.js

/**
 * 共有用のテキスト文言を生成
 */
export function generateShareText(district, category) {
  if (!district) {
    return '【東京23区住みやすさマップ】自分にぴったりの街を見つけよう！';
  }

  const categoryName = category?.label ? `「${category.label}」` : '';
  const scoreText = district.categoryTotalScore 
    ? `（スコア: ${district.categoryTotalScore}点）` 
    : '';

  return `東京都${district.name}の住みやすさ情報${categoryName}${scoreText}をチェックしました！\n${district.bestEmoji || '✨'} ${district.description || ''}\n\n#東京23区住みやすさ #まちさがし`;
}

/**
 * X（旧Twitter）共有URLを取得
 */
export function getTwitterShareUrl(district, category, currentUrl = window.location.href) {
  const text = generateShareText(district, category);
  return `https://twitter.com/intent/tweet?text=${encodeURIComponent(text)}&url=${encodeURIComponent(currentUrl)}`;
}

/**
 * LINE共有URLを取得
 */
export function getLineShareUrl(district, category, currentUrl = window.location.href) {
  const text = generateShareText(district, category);
  return `https://social-plugins.line.me/lineit/share?url=${encodeURIComponent(currentUrl)}&text=${encodeURIComponent(text)}`;
}

/**
 * クリップボードにURLとテキストをコピー
 */
export async function copyToClipboard(district, category, currentUrl = window.location.href) {
  const text = `${generateShareText(district, category)}\n${currentUrl}`;
  try {
    await navigator.clipboard.writeText(text);
    return true; // 成功
  } catch (err) {
    console.error('コピーに失敗しました:', err);
    return false; // 失敗
  }
}

/**
 * モバイル端末の標準共有ダイアログ（Web Share API）を開く
 */
export async function shareNative(district, category, currentUrl = window.location.href) {
  const text = generateShareText(district, category);

  if (navigator.share) {
    try {
      await navigator.share({
        title: `${district?.name || '東京23区'}の住みやすさ診断`,
        text: text,
        url: currentUrl,
      });
      return true;
    } catch (err) {
      // ユーザーがキャンセルした場合などはエラーログを出さずに無視
      if (err.name !== 'AbortError') {
        console.error('共有エラー:', err);
      }
      return false;
    }
  }
  return false; // 未対応ブラウザ
}
