// blocks/WeatherBlock.tsx (将来的な実装イメージ)
import React from 'react';

export function WeatherBlock({ data }) {
  if (!data || data.error) return <p className="text-red-500">天気情報の取得に失敗しました。</p>;

  return (
    <div className="bg-gradient-to-br from-blue-50 to-blue-100 dark:from-slate-800 dark:to-slate-900 rounded-xl p-5 shadow-sm">
      <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
        📍 {data.city} の天気
      </h3>
      
      {/* 現在の天気 or 週間予報でレイアウトを分岐 */}
      {data.forecast ? (
        <div className="flex gap-3 overflow-x-auto pb-2">
          {data.forecast.map((day, idx) => (
            <div key={idx} className="flex flex-col items-center bg-white/60 dark:bg-slate-800/60 p-3 rounded-lg min-w-[80px]">
              <span className="text-xs text-slate-500">{day.date}</span>
              <span className="text-2xl my-2">{/* weather_descからアイコンだけ抽出する関数などを挟むと綺麗 */} {day.weather}</span>
              <div className="text-xs font-bold flex gap-2">
                <span className="text-red-500">{day.temp_max}</span>
                <span className="text-blue-500">{day.temp_min}</span>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="text-center p-4">
          <div className="text-4xl mb-2">{data.weather}</div>
          <div className="text-2xl font-bold">{data.temperature}℃</div>
          <div className="text-sm text-slate-500 mt-2">風速: {data.windspeed} km/h</div>
        </div>
      )}
    </div>
  );
}