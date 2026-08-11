import { createClient } from '@supabase/supabase-js';

// ★修正：「||」を使って、左側が空っぽなら右側のダミー文字列を使うようにします
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://dummy.supabase.co";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "dummy_key";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);