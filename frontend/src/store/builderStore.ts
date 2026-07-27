// frontend/src/store/builderStore.ts
import { create } from 'zustand';
import { Page, PageComponent, ComponentType } from '../types';

function genId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

// =========================================================
// 🌟 デフォルトのプロパティと「縦横のサイズ」を定義
// =========================================================
const DEFAULT_PROPS: Record<string, Record<string, any>> = {
  header: { text: '見出しテキスト', level: 'h2', align: 'left' },
  text: { content: 'テキストを入力してください...', align: 'left' },
  image: { src: 'https://via.placeholder.com/800x400', alt: 'Image' },
  button: { label: 'クリック', href: '#', variant: 'primary', align: 'center' },
  card: { title: 'カードタイトル', content: 'ここにカードの説明が入ります。', imageUrl: '' },
  form: { fields: [{ label: 'お名前', type: 'text' }, { label: 'メール', type: 'email' }], submitLabel: '送信' },
  hero: { title: 'メインコピー', subtitle: 'サブコピーがここに入ります', ctaText: '詳しく見る', bgColor: '#1d4ed8' },
  divider: { style: 'solid', color: '#e5e7eb' },
  php_code: { code: '<?php echo "Hello World"; ?>', description: '動的出力' },
};

// 🌟 コンポーネントがキャンバスに配置されたときの「初期スタイル（縦横幅など）」
const DEFAULT_STYLES: Record<string, Record<string, string | number>> = {
  header: { width: '100%', height: 'auto', x: 0, y: 0, zIndex: 1, rotation: 0 },
  text: { width: '100%', height: 'auto', x: 0, y: 0, zIndex: 1, rotation: 0 },
  image: { width: '100%', height: 'auto', x: 0, y: 0, zIndex: 1, rotation: 0 },
  button: { width: 'auto', height: 'auto' },
  card: { width: '300px', height: 'auto' }, // カードは最初から300px幅にしておく
  hero: { width: '100%', height: '400px' }, // Heroは最初から縦幅を大きく
  form: { width: '100%', height: 'auto', maxWidth: '500px' },
  php_code: { width: '100%', height: 'auto' },
};


  
// 🌟 ページ情報に用紙サイズの概念を追加
interface Page {
  id: string;
  title: string;
  canvasWidth?: string;  // 例: '210mm' (A4)
  canvasHeight?: string; // 例: '297mm' (A4)
  layoutMode?: 'flow' | 'absolute'; // Webモードとポスターモードの切り替え
}
interface BuilderStore {
  pages: Page[];
  currentPage: Page | null;
  components: PageComponent[];
  selectedComponentId: string | null;
  isDirty: boolean;
  
  setPages: (pages: Page[]) => void;
  setCurrentPage: (page: Page | null) => void;
  setComponents: (components: PageComponent[]) => void;
  
  // 第3引数(insertIndex)で、ドロップした位置にパーツを割り込ませる
  addComponent: (type: ComponentType, defaultProps?: Record<string, any>, insertIndex?: number) => void;
  removeComponent: (id: string) => void;
  
  // props(テキスト等)とstyles(縦横幅等)を個別に更新できるようにする
  updateComponent: (id: string, props?: Record<string, any>, styles?: Record<string, any>) => void;
  reorderComponents: (startIndex: number, endIndex: number) => void;
  selectComponent: (id: string | null) => void;
  setDirty: (dirty: boolean) => void;
}

export const useBuilderStore = create<BuilderStore>((set) => ({
  pages: [],
  currentPage: null,
  components: [],
  selectedComponentId: null,
  isDirty: false,

  setPages: (pages) => set({ pages }),
  setCurrentPage: (page) => set({ currentPage: page }),
  setComponents: (components) => set({ components, isDirty: false }),

  // =========================================================
  // 🌟 新規コンポーネント追加（落とした位置に割り込み対応）
  // =========================================================
  addComponent: (type, customProps = {}, insertIndex) => {
    const newComponent: PageComponent = {
      id: genId(),
      page_id: '',
      type,
      order_index: 0,
      props: { ...(DEFAULT_PROPS[type] || {}), ...customProps },
      // 新規配置時に、縦横の初期値をセットする
      styles: { ...(DEFAULT_STYLES[type] || { width: '100%', height: 'auto' }) }, 
    };

    set((state) => {
      const newComponents = [...state.components];
      
      // insertIndex が指定されていればそこに挿入、なければ最後尾
      if (typeof insertIndex === 'number') {
        newComponents.splice(insertIndex, 0, newComponent);
      } else {
        newComponents.push(newComponent);
      }

      // 並び順（order_index）を再計算
      const updatedComponents = newComponents.map((c, i) => ({ ...c, order_index: i }));

      return {
        components: updatedComponents,
        selectedComponentId: newComponent.id, // 配置したら自動で選択状態にする
        isDirty: true,
      };
    });
  },

  removeComponent: (id) => {
    set((state) => ({
      components: state.components.filter((c) => c.id !== id),
      selectedComponentId: state.selectedComponentId === id ? null : state.selectedComponentId,
      isDirty: true,
    }));
  },

  // =========================================================
  // 🌟 プロパティ（テキスト）やスタイル（縦横幅）の更新処理
  // =========================================================
  updateComponent: (id, props = {}, styles = {}) => {
    set((state) => ({
      components: state.components.map((c) => {
        if (c.id === id) {
          return {
            ...c,
            props: { ...c.props, ...props },
            styles: { ...c.styles, ...styles } // 縦横サイズの更新をここで保存
          };
        }
        return c;
      }),
      isDirty: true,
    }));
  },

  reorderComponents: (startIndex, endIndex) => {
    set((state) => {
      const result = Array.from(state.components);
      const [removed] = result.splice(startIndex, 1);
      result.splice(endIndex, 0, removed);
      
      return { 
        components: result.map((c, i) => ({ ...c, order_index: i })), 
        isDirty: true 
      };
    });
  },

  selectComponent: (id) => set({ selectedComponentId: id }),
  setDirty: (dirty) => set({ isDirty: dirty }),
}));