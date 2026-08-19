import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';

import { pagesApi } from '../api/client';
import { useBuilderStore } from '../store/builderStore';
import { Page } from '../types';

/**
 * ページの取得・作成・保存・公開・削除など、
 * 非同期のバックエンド通信と状態管理をすべて引き受けるカスタムフック
 */
export function usePageManager(pageId?: string) {
  const navigate = useNavigate();

  // Storeの操作関数群
  const {
    pages,
    currentPage,
    components,
    setPages,
    setCurrentPage,
    setComponents
  } = useBuilderStore();

  // フック内部で管理するステート
  const [loading, setLoading] = useState(false);
  const [showPageList, setShowPageList] = useState(!pageId);
  const [newPageTitle, setNewPageTitle] = useState('');
  const [saving, setSaving] = useState(false);

  // ===
  // ① 初期ページ一覧の取得
  // ===
  useEffect(() => {
    const fetchPages = async () => {
      try {
        const res = await pagesApi.list();
        setPages(res.data.pages || []);
      } catch (err) {
        console.error('Failed to load pages:', err);
        toast.error('ページ一覧の取得に失敗しました');
      }
    };

    fetchPages();
  }, [setPages]);

  // ===
  // ② 個別ページの読み込み (pageId が変わるたびに実行)
  // ===
  useEffect(() => {
    const loadPage = async () => {
      if (!pageId) {
        setShowPageList(true);
        setCurrentPage(null);
        return;
      }

      try {
        setLoading(true);
        const res = await pagesApi.get(pageId);
        const page = res.data.page;
        const rawComponents = res.data.components || [];

        // DBから文字列で届いたJSON(props, styles)をオブジェクトに復元
        const parsedComponents = rawComponents.map((c: any) => ({
          ...c,
          props: typeof c.props === 'string' ? JSON.parse(c.props) : c.props,
          styles: typeof c.styles === 'string' ? JSON.parse(c.styles) : c.styles
        }));

        setCurrentPage(page);
        setComponents(parsedComponents);
        setShowPageList(false);
      } catch (err) {
        console.error(err);
        toast.error('ページ読み込みに失敗しました');
      } finally {
        setLoading(false);
      }
    };

    loadPage();
  }, [pageId, setCurrentPage, setComponents]);

  // ===
  // ③ 新規ページ作成
  // ===
  const createPage = async () => {
    if (!newPageTitle.trim()) {
      toast.error('ページタイトルを入力してください');
      return;
    }

    try {
      const res = await pagesApi.create({ title: newPageTitle });
      const page = res.data.page;

      setPages([...pages, page]);
      setNewPageTitle('');
      toast.success('ページを作成しました');
      
      // 作成したページの編集画面へ自動遷移
      navigate(`/builder/${page.id}`);
    } catch (err) {
      console.error(err);
      toast.error('ページ作成に失敗しました');
    }
  };

  // ===
  // ④ コンポーネント構成の保存
  // ===
  const savePage = async () => {
    if (!currentPage) return;

    try {
      setSaving(true);
      await pagesApi.saveComponents(currentPage.id, components);
      toast.success('ページを保存しました');
    } catch (err) {
      console.error(err);
      toast.error('保存に失敗しました');
    } finally {
      setSaving(false);
    }
  };

  // ===
  // ⑤ ページの公開
  // ===
  const publishPage = async () => {
    if (!currentPage) return;

    try {
      await pagesApi.update(currentPage.id, { status: 'published' });
      setCurrentPage({ ...currentPage, status: 'published' });
      toast.success('ページを公開しました');
    } catch (err) {
      console.error(err);
      toast.error('公開に失敗しました');
    }
  };

  // ===
  // ⑥ ページの削除
  // ===
  const deletePage = async (page: Page) => {
    const ok = window.confirm(`"${page.title}" を削除しますか？`);
    if (!ok) return;

    try {
      await pagesApi.delete(page.id);
      setPages(pages.filter((p) => p.id !== page.id));

      // もし現在開いているページを削除した場合はダッシュボードへ戻す
      if (currentPage?.id === page.id) {
        setCurrentPage(null);
        navigate('/builder');
        setShowPageList(true);
      }
      toast.success('ページを削除しました');
    } catch (err) {
      console.error(err);
      toast.error('削除に失敗しました');
    }
  };

  // 外部(Builder.tsx)で使いたいステートと関数だけをエクスポート
  return {
    loading,
    saving,
    showPageList,
    setShowPageList,
    newPageTitle,
    setNewPageTitle,
    createPage,
    savePage,
    publishPage,
    deletePage
  };
}