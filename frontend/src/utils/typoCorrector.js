// frontend/src/utils/typoCorrector.js
import typoDictionary from '../data/typoDictionary.json';

/**
 * 入力テキストのタイポを補正する純粋関数
 */
export const correctTypo = (text) => {
  let correctedText = text.normalize("NFKC");
  let detectedTargets = [];

  for (const item of typoDictionary) {
    for (const typo of item.typos) {
      if (correctedText.includes(typo) && typo !== item.target) {
        correctedText = correctedText.replaceAll(typo, item.target);
        if (!detectedTargets.includes(item.target)) {
          detectedTargets.push(item.target);
        }
      }
    }
  }

  return {
    correctedText,
    wasCorrected: detectedTargets.length > 0,
    detectedTargets
  };
};