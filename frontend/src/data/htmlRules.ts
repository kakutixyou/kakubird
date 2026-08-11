// 型定義
export interface HtmlRuleInput {
  key: string;
  label: string;
  type: 'string' | 'number' | 'textarea' | 'select';
  options?: { value: string; label: string }[];
}

export interface HtmlRuleChild {
  tag: string;
  classes: string[];
  content?: string;
  attrs?: Record<string, string>;
}

export interface HtmlRule {
  id: string;
  display: string;
  tag: string;
  classes: string[];
  inputs: HtmlRuleInput[];
  children: HtmlRuleChild[];
}

// デフォルト定義
export const DEFAULT_HTML_RULES: HtmlRule[] = [
  {
    id: 'hero_basic',
    display: 'ヒーロー（基本）',
    tag: 'section',
    classes: ['hero', 'flex', 'items-center', 'justify-center', 'bg-gradient-to-r', 'from-blue-500', 'to-purple-600', 'text-white', 'py-20', 'px-4'],
    inputs: [
      { key: 'title', label: 'タイトル', type: 'string' },
      { key: 'subtitle', label: 'サブタイトル', type: 'textarea' },
      { key: 'button_text', label: 'ボタン文言', type: 'string' },
      { key: 'button_url', label: 'ボタンリンク', type: 'string' }
    ],
    children: [
      { tag: 'div', classes: ['text-center', 'max-w-2xl'], content: '' },
      { tag: 'h1', classes: ['text-5xl', 'font-bold', 'mb-4'], content: '{title}' },
      { tag: 'p', classes: ['text-xl', 'mb-8', 'opacity-90'], content: '{subtitle}' },
      { tag: 'a', classes: ['inline-block', 'bg-white', 'text-blue-600', 'px-8', 'py-3', 'rounded-lg', 'font-bold', 'hover:bg-gray-100', 'transition'], attrs: { href: '{button_url}' }, content: '{button_text}' }
    ]
  },
  {
    id: 'card_basic',
    display: 'カード（基本）',
    tag: 'div',
    classes: ['card', 'bg-white', 'rounded-lg', 'shadow-md', 'p-6', 'hover:shadow-lg', 'transition'],
    inputs: [
      { key: 'title', label: 'タイトル', type: 'string' },
      { key: 'description', label: '説明', type: 'textarea' },
      { key: 'link_text', label: 'リンク文言', type: 'string' },
      { key: 'link_url', label: 'リンク先', type: 'string' }
    ],
    children: [
      { tag: 'h3', classes: ['text-lg', 'font-bold', 'text-gray-800', 'mb-2'], content: '{title}' },
      { tag: 'p', classes: ['text-gray-600', 'mb-4', 'text-sm'], content: '{description}' },
      { tag: 'a', classes: ['text-blue-600', 'font-bold', 'hover:text-blue-800', 'transition'], attrs: { href: '{link_url}' }, content: '{link_text}' }
    ]
  },
  // 必要に応じて footer_simple, navbar_simple もここへ
];

/**
 * ルールと入力値からHTML文字列を生成するユーティリティ
 */
export function generateHtmlFromRule(rule: HtmlRule, values: Record<string, string>): string {
  let html = `<${rule.tag} class="${rule.classes.join(' ')}">\n`;

  for (const child of rule.children) {
    let content = child.content || '';
    for (const [key, val] of Object.entries(values)) {
      content = content.replace(`{${key}}`, val || '');
    }

    const childClasses = child.classes.length ? ` class="${child.classes.join(' ')}"` : '';
    const childAttrs = child.attrs
      ? Object.entries(child.attrs)
          .map(([k, v]) => {
            let attrVal = v;
            for (const [key, val] of Object.entries(values)) {
              attrVal = attrVal.replace(`{${key}}`, val || '');
            }
            return ` ${k}="${attrVal}"`;
          })
          .join('')
      : '';

    html += `  <${child.tag}${childClasses}${childAttrs}>${content}</${child.tag}>\n`;
  }

  html += `</${rule.tag}>\n`;
  return html;
}