import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { User, Tenant } from '../types';

interface AuthStore {
  token: string | null;
  user: User | null;
  tenant: Tenant | null;
  setAuth: (token: string, user: User, tenant: Tenant) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      tenant: null,
      setAuth: (token, user, tenant) => set({ token, user, tenant }),
      logout: () => set({ token: null, user: null, tenant: null }),
    }),
    { name: 'auth-storage' }
  )
);
