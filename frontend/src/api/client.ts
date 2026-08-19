// frontend/src/api/client.ts
import axios from 'axios';
import { useAuthStore } from '../store/authStore';
import { useApiSettingsStore } from '../store/apiSettingsStore'; // ★追加: API設定用Store
import React from 'react';
const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
});

// 
// リクエスト送信前の処理（ここで通信先を切り替える）
// 
api.interceptors.request.use((config) => {
  // 外部APIの設定と、内部のログイントークンを両方取得
  const { endpoint, apiKey } = useApiSettingsStore.getState();
  const internalToken = useAuthStore.getState().token;

  // 1. 外部エンドポイントが設定されている場合、送信先URLを上書きする
  if (endpoint) {
    // 最後にスラッシュがあれば取り除く等の整形をしておくと安全です
    config.baseURL = endpoint.replace(/\/$/, '');
  }

  // 2. トークンの付与（外部APIキーがあれば最優先、なければ内部トークンを使用）
  if (apiKey) {
    config.headers.Authorization = `Bearer ${apiKey}`;
  } else if (internalToken) {
    config.headers.Authorization = `Bearer ${internalToken}`;
  }

  return config;
});

// 
// レスポンス受信時の処理（エラーハンドリング）
// 
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const { endpoint } = useApiSettingsStore.getState();

    if (error.response?.status === 401) {
      // 外部API通信中の401エラーなら、jimbo本体から勝手にログアウトさせない
      if (endpoint) {
        console.error('外部APIの認証に失敗しました。API設定画面のキーを確認してください。');
      } else {
        // 通常の内部通信なら、ログアウトしてログイン画面へ
        useAuthStore.getState().logout();
        
      }
    }
    return Promise.reject(error);
  }
);

export default api;

// 
// 以降のAPI定義は一切変更なしでOKです！
// 

// Auth
export const authApi = {
  login: (email: string, password: string) => api.post('/auth/login', { email, password }),
  register: (data: { email: string; password: string; name: string; tenantName: string }) =>
    api.post('/auth/register', data),
  me: () => api.get('/auth/me'),
};

// Pages
export const pagesApi = {
  list: () => api.get('/pages'),
  get: (id: string) => api.get(`/pages/${id}`),
  create: (data: any) => api.post('/pages', data),
  update: (id: string, data: any) => api.put(`/pages/${id}`, data),
  delete: (id: string) => api.delete(`/pages/${id}`),
  saveComponents: (pageId: string, components: any[]) =>
    api.put(`/pages/${pageId}/components`, { components }),
};

// Backoffice
export const backofficeApi = {
  getEmployees: () => api.get('/backoffice/hr/employees'),
  createEmployee: (data: any) => api.post('/backoffice/hr/employees', data),
  updateEmployee: (id: string, data: any) => api.put(`/backoffice/hr/employees/${id}`, data),
  deleteEmployee: (id: string) => api.delete(`/backoffice/hr/employees/${id}`),
  getBudgets: () => api.get('/backoffice/finance/budgets'),
  createBudget: (data: any) => api.post('/backoffice/finance/budgets', data),
  getExpenses: () => api.get('/backoffice/finance/expenses'),
  createExpense: (data: any) => api.post('/backoffice/finance/expenses', data),
  approveExpense: (id: string) => api.patch(`/backoffice/finance/expenses/${id}/approve`),
  getStats: () => api.get('/backoffice/stats'),
};

// Front office
export const frontofficeApi = {
  getCustomers: (params?: any) => api.get('/frontoffice/crm/customers', { params }),
  createCustomer: (data: any) => api.post('/frontoffice/crm/customers', data),
  updateCustomer: (id: string, data: any) => api.put(`/frontoffice/crm/customers/${id}`, data),
  deleteCustomer: (id: string) => api.delete(`/frontoffice/crm/customers/${id}`),
  getDeals: () => api.get('/frontoffice/crm/deals'),
  createDeal: (data: any) => api.post('/frontoffice/crm/deals', data),
  updateDeal: (id: string, data: any) => api.put(`/frontoffice/crm/deals/${id}`, data),
  getPipeline: () => api.get('/frontoffice/crm/pipeline'),
};

// Supply chain
export const supplyChainApi = {
  getInventory: (params?: any) => api.get('/supplychain/inventory', { params }),
  createItem: (data: any) => api.post('/supplychain/inventory', data),
  updateItem: (id: string, data: any) => api.put(`/supplychain/inventory/${id}`, data),
  deleteItem: (id: string) => api.delete(`/supplychain/inventory/${id}`),
  getStats: () => api.get('/supplychain/inventory/stats'),
  getLowStock: () => api.get('/supplychain/inventory/alerts/low-stock'),
};

// Operations
export const operationsApi = {
  getTasks: (params?: any) => api.get('/operations/tasks', { params }),
  createTask: (data: any) => api.post('/operations/tasks', data),
  updateTask: (id: string, data: any) => api.put(`/operations/tasks/${id}`, data),
  deleteTask: (id: string) => api.delete(`/operations/tasks/${id}`),
  getTaskStats: () => api.get('/operations/tasks/stats'),
};

// Governance
export const governanceApi = {
  getAuditLogs: (params?: any) => api.get('/governance/audit-logs', { params }),
  getUsers: () => api.get('/governance/users'),
  updateUserRole: (id: string, role: string) => api.patch(`/governance/users/${id}/role`, { role }),
  toggleUser: (id: string) => api.patch(`/governance/users/${id}/toggle`),
  getAnalyticsOverview: () => api.get('/governance/analytics/overview'),
  getEsgMetrics: () => api.get('/governance/esg/metrics'),
};

// Plugins
export const pluginsApi = {
  list: () => api.get('/plugins'),
  install: (data: any) => api.post('/plugins', data),
  toggle: (id: string) => api.patch(`/plugins/${id}/toggle`),
  remove: (id: string) => api.delete(`/plugins/${id}`),
};
// AI Chat（SQL Builderバックエンドに直接送る）
const CHAT_BASE = import.meta.env.VITE_CHAT_ENDPOINT ;

const chatAxios = axios.create({
  baseURL: CHAT_BASE,
  headers: { "Content-Type": "application/json" },
});

export const chatApi = {
  send: (params: {
    message:  string;
    mode?:    "custom" | "gemini" | "claude";
    db_type?: string;
    db_path?: string;
    history?: { role: string; content: string }[];
  }) =>
    chatAxios.post("/api/chat", {
      mode:    "custom",
      db_type: "sqlite",
      history: [],
      ...params,
    }),
};
export const systemApi = {
  getDatabases: () => api.get('/system/databases'),
  getHealth: () => api.get('/system/health'),
};
export const htmlApi = {
  // HTMLを生成
  generate: (pageSpec: any) => api.post('/html/generate', pageSpec),
  
  // HTMLをエクスポート
  export: (pageSpec: any, format: 'html' | 'zip' = 'html') => 
    api.post('/html/export', pageSpec, { params: { format } }),
  
  // 使用可能なコンポーネントルール取得
  getRules: () => api.get('/html/rules'),
};