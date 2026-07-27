// frontend/src/store/apiSettingsStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

// ① 箱のルールに「apiType」を追加
interface ApiSettingsStore {
  apiType: 'gemini' | 'custom'; // ★追加: 'gemini' か 'custom' しか入らないようにする
  endpoint: string;
  apiKey: string;
  method: string;
  timeout: number;
  savedAt: string;
  // ★ setSettingsが受け取る引数にも apiType を追加
  setSettings: (apiType: 'gemini' | 'custom', endpoint: string, apiKey: string, method: string, timeout: number, savedAt: string) => void;
  clearSettings: () => void;
}

export const useApiSettingsStore = create<ApiSettingsStore>()(
  persist(
    (set) => ({
      // ② 初期値を設定（最初はGeminiにしておく）
      apiType: 'gemini', // ★追加
      endpoint: '',
      apiKey: '',
      method: 'GET',
      timeout: 10,
      savedAt: '',
      
      // ③ 保存ボタンが押されたときの処理を更新
      setSettings: (apiType, endpoint, apiKey, method, timeout, savedAt) => 
        set({ apiType, endpoint, apiKey, method, timeout, savedAt }), // ★ apiTypeを追加
        
      // ④ 削除ボタンが押されたときの処理を更新
      clearSettings: () => 
        set({ apiType: 'gemini', endpoint: '', apiKey: '', method: 'GET', timeout: 10, savedAt: '' }), // ★ apiTypeを追加
    }),
    { name: 'jimdo_replica_api_settings' } 
  )
);