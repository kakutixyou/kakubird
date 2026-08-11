// src/utils/exportHtml.ts
// import { setTimeout } from 'timers';
import { PageComponent } from '../types'; // 型の場所は適宜合わせてください
// import { URL } from 'url';
// import { Blob } from 'buffer';

/**
 * 1. コンポーネント配列を純粋なHTML文字列に変換する関数
 */
export const generateHtmlString = (components: PageComponent[]): string => {
  // 各パーツをHTMLタグに変換
  const bodyContent = components.map((comp) => {
    const { props } = comp;
    const type = comp.type as string;

    switch (type) {
      case 'hero':
        return `
          <section style="background-color: ${props.bgColor || '#1d4ed8'}; color: white; padding: 4rem 2rem; text-align: center;">
            <h1 style="font-size: 2.5rem; font-weight: bold; margin-bottom: 1rem;">${props.title || ''}</h1>
            <p style="font-size: 1.25rem; margin-bottom: 2rem;">${props.subtitle || ''}</p>
            ${props.ctaText ? `<a href="#" style="background: white; color: black; padding: 0.75rem 1.5rem; border-radius: 9999px; text-decoration: none; font-weight: bold;">${props.ctaText}</a>` : ''}
          </section>
        `;
      
      case 'header':
        const Tag = props.level || 'h2';
        return `<${Tag} style="text-align: ${props.align || 'left'}; margin: 1rem 0;">${props.text}</${Tag}>`;
      
      case 'text':
        return `<p style="text-align: ${props.align || 'left'}; margin-bottom: 1rem;">${props.content}</p>`;
      
      case 'image':
        return `<img src="${props.src}" alt="${props.alt || ''}" style="width: ${props.width || '100%'}; max-width: 100%; height: auto;" />`;
      
      case 'html':
        // 先ほど話題に出た、生のHTMLをそのまま出力する機能！
        return props.content || '';
      case 'card':
  return `
    <div style="width: ${props.width || '100%'}; height: ${props.height || 'auto'}; border: 1px solid #e5e7eb; border-radius: 0.5rem; padding: 1rem; box-shadow: 0 1px 3px rgba(0,0,0,0.1); background: white;">
      ${props.imageUrl ? `<img src="${props.imageUrl}" style="width:100%; height:150px; object-fit:cover; border-radius:0.25rem;" />` : ''}
      <h3 style="font-weight:bold; margin-top:0.5rem;">${props.title}</h3>
      <p style="font-size:0.875rem; color:#6b7280; margin-top:0.25rem;">${props.content}</p>
    </div>
  `;

      case 'php_code':
  // HTMLとして書き出された時は、PHPサーバーで動くようにそのまま構文を吐き出す
  return `
    <div class="php-dynamic-block" style="border: 2px dashed #9333ea; padding: 1rem; border-radius: 0.375rem; margin: 1rem 0; background: #faf5ff;">
      <!-- PHP Execution Zone -->
      ${props.code}
    </div>
  `;
      // ...必要に応じて他のコンポーネントの変換ルールも追加...
      
      default:
        return `<!-- 未対応のコンポーネント: ${type} -->`;
    }
  }).join('\n');

  // Tailwind CSSのCDNを読み込んだ完全なHTML構造でラップする
  return `<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Exported Page</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-white text-gray-900">
  ${bodyContent}
</body>
</html>`;
};

/**
 * 2. HTML文字列をファイルとしてブラウザからダウンロードさせる関数
 */
export const downloadHtmlFile = (htmlContent: string, filename: string = 'website.html') => {
  // Blobオブジェクトを作成 (MIMEタイプを text/html に指定)
  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8;' });
  
  // ダウンロード用のURLを発行
  const url = URL.createObjectURL(blob);
  
  // 見えない <a> タグを作ってクリックイベントを発火させる
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  
  // 掃除
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * 3. 生成したHTMLを別タブで開いて印刷（PDF化）ダイアログを出す関数
 */
export const printAndPdfHtml = (components: any[]) => {
  // 1. 先ほど作った関数でHTML文字列を生成
  const htmlString = generateHtmlString(components);

  // 2. 新しい空のウィンドウ（タブ）を開く
  const printWindow = window.open('', '_blank');
  
  if (printWindow) {
    // 3. HTMLを書き込む
    printWindow.document.write(htmlString);
    printWindow.document.close();
    printWindow.focus();

    // 4. 画像やCSSが読み込まれるのを少し待ってから印刷ダイアログを出す
    setTimeout(() => {
      printWindow.print();
    }, 250); // 0.25秒待機
  } else {
    alert('ポップアップブロックが有効になっている可能性があります。解除して再度お試しください。');
  }
};

function alert(arg0: string) {
  throw new Error('Function not implemented.');
}
