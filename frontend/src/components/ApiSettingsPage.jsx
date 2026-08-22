// src/components/ApiSettingsPage.jsx
import React, { useState, useEffect } from 'react';

const ApiSelector = ({ onSelectService }) => {
  const [services, setServices] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // コンポーネントがマウントされたら、バックエンドに「何ができる？」と聞きにいく
  useEffect(() => {
    const fetchServices = async () => {
      try {
        // 先ほど作ったカタログAPIを叩く
        const response = await fetch('https://kakubird.onrender.com/api/services');
        if (!response.ok) throw new Error('APIカタログの取得に失敗しました');
        
        const data = await response.json();
        setServices(data.services);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchServices();
  }, []);

  if (isLoading) return <div className="p-4">利用可能なAPIを探しています...</div>;
  if (error) return <div className="p-4 text-red-500">エラー: {error}</div>;

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">利用するAPIを選択してください</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {services.map((service) => (
          <div 
            key={service.id}
            onClick={() => onSelectService(service)}
            className="border border-gray-200 rounded-xl p-6 cursor-pointer hover:border-blue-500 hover:shadow-md transition-all bg-white group"
          >
            <div className="flex items-center gap-3 mb-3">
              {/* アイコンの出し分け (lucide-reactなどを使うと綺麗です) */}
              <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold">
                {service.icon === 'database' ? 'DB' : service.icon === 'palette' ? 'CSS' : 'API'}
              </div>
              <h3 className="text-lg font-semibold text-gray-800 group-hover:text-blue-600">
                {service.name}
              </h3>
            </div>
            
            <p className="text-sm text-gray-600 mb-4 h-10">
              {service.description}
            </p>

            {/* 「できること」のリスト表示 */}
            <div className="space-y-2">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider">できること (Capabilities)</p>
              <ul className="text-sm text-gray-700 list-disc list-inside">
                {service.capabilities.map((cap, idx) => (
                  <li key={idx}>{cap.description}</li>
                ))}
              </ul>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default ApiSelector;