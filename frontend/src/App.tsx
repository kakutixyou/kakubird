// To/frontend/src/App.tsx

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
// import { useAuthStore } from './store/authStore'; // ⬅︎ 一旦使わないのでコメントアウト
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Builder from './pages/Builder.jsx';
import MemoryPage from './pages/MemoryPage.jsx'; // 👈 新しいメモリー画面をインポート
import BackOfficePage from './pages/modules/BackOfficePage.jsx';
import FrontOfficePage from './pages/modules/FrontOfficePage.jsx';
import SupplyChainPage from './pages/modules/SupplyChainPage.jsx';
import OperationsPage from './pages/modules/OperationsPage.jsx';
import GovernancePage from './pages/modules/GovernancePage.jsx';
import ApiSettingsPage from './pages/modules/ApiSettingsPage.jsx'; 
import Layout from './components/Layout/Layout.jsx';
import TemplatesPage from './pages/TemplatesPage.jsx';
// import DatabasePage from './components/DatabaseManager.jsx';//どちらか一方にすること
import DatabasePage from './components/DatabasePage';
import React from 'react';
function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        
        {/* 👇 PrivateRouteを外し、誰でもLayout（メイン画面）に入れるように変更 */}
        <Route path="/" element={<Layout />}>
          {/* Dashboardではなく、いきなりBuilder(編集画面)を開きたい場合はここを <Builder /> にします */}
          <Route index element={<Dashboard />} /> 
          <Route path="builder" element={<Builder />} />
          <Route path="builder/:pageId" element={<Builder />} />
          <Route path="memory" element={<MemoryPage />} /> {/* 新しいルートを追加 */}
          <Route path="settings-api" element={<ApiSettingsPage />} />
          <Route path="backoffice" element={<BackOfficePage />} />
          <Route path="frontoffice" element={<FrontOfficePage />} />
          <Route path="supplychain" element={<SupplyChainPage />} />
          <Route path="operations" element={<OperationsPage />} />
          <Route path="governance" element={<GovernancePage />} />
          <Route path="templates" element={<TemplatesPage />} />
          <Route path="databases" element={<DatabasePage />} />
        </Route>
        
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;