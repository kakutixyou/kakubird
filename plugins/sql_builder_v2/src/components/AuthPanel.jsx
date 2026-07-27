// src/components/AuthPanel.jsx
import { Auth } from '@supabase/auth-ui-react';
import { ThemeSupa } from '@supabase/auth-ui-shared';
import { supabase } from '../utils/supabaseClient';

export function AuthPanel({ onSkip }) {
  return (
    <div className="auth-wrapper" style={{ maxWidth: '400px', margin: '50px auto', padding: '20px' }}>
      <h2 style={{ textAlign: 'center', marginBottom: '20px' }}>SQL Builder v2</h2>
      
      {/* Supabaseの公式UIコンポーネント */}
      <Auth
        supabaseClient={supabase}
        appearance={{ theme: ThemeSupa }}
        providers={[]} // 今回はGoogleログイン等を省き、メアド/パスワードのみ
      />
      
      <hr style={{ margin: '30px 0' }} />
      
      {/* オフラインスキップ用ボタン */}
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: '0.9em', color: '#666', marginBottom: '10px' }}>
          ネットワーク環境がない場合や、ローカルでのみ実行する場合はこちら
        </p>
        <button 
          onClick={onSkip}
          style={{ padding: '10px 20px', cursor: 'pointer', borderRadius: '4px' }}
        >
          オフラインモードで起動（スキップ）
        </button>
      </div>
    </div>
  );
}