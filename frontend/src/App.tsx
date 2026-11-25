import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Login from './pages/Login.jsx';
import Dashboard from './pages/Dashboard.jsx';
import Builder from './pages/Builder.jsx';
import MemoryPage from './pages/MemoryPage.jsx';
import BackOfficePage from './pages/modules/BackOfficePage.jsx';
import FrontOfficePage from './pages/modules/FrontOfficePage.jsx';
import SupplyChainPage from './pages/modules/SupplyChainPage.jsx';
import OperationsPage from './pages/modules/OperationsPage.jsx';
import GovernancePage from './pages/modules/GovernancePage.jsx';
import ApiSettingsPage from './pages/modules/ApiSettingsPage.jsx';
import Layout from './components/Layout/Layout.jsx';
import TemplatesPage from './pages/TemplatesPage.jsx';
import RelocationMapPage from './pages/RelocationMapPage.jsx';
import DatabasePage from './components/DatabasePage';
import TopicAnalysisPage from './pages/TopicAnalysisPage';
import React from 'react';

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Layout />}>
          <Route index element={<Dashboard />} />
          <Route path="builder" element={<Builder />} />
          <Route path="builder/:pageId" element={<Builder />} />
          <Route path="memory" element={<MemoryPage />} />
          <Route path="analysis" element={<TopicAnalysisPage />} />
          <Route path="settings-api" element={<ApiSettingsPage />} />
          <Route path="backoffice" element={<BackOfficePage />} />
          <Route path="frontoffice" element={<FrontOfficePage />} />
          <Route path="supplychain" element={<SupplyChainPage />} />
          <Route path="operations" element={<OperationsPage />} />
          <Route path="governance" element={<GovernancePage />} />
          <Route path="templates" element={<TemplatesPage />} />
          <Route path="databases" element={<DatabasePage />} />
          <Route path="relocation-map" element={<RelocationMapPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
