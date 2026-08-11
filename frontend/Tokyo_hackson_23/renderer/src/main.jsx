import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './app.jsx';
import './index.css';

// 🌟 一度だけ root を作成して定数に保持する
const container = document.getElementById('root');
const root = ReactDOM.createRoot(container);

// 🌟 レンダリング時は root.render() を使う
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);