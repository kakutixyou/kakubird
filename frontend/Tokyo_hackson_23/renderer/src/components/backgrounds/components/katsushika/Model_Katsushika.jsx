import React, { useState, useEffect } from 'react';

export const key = 'katsushika';
export const label = '葛飾区：柴又帝釈天参道が組み上がる演出';

// 葛飾区：柴又帝釈天参道が組み上がる演出（component型のward effect）
const Model_Katsushika = () => {
  const [buildPhase, setBuildPhase] = useState(0);

  useEffect(() => {
    const phases = [
      setTimeout(() => setBuildPhase(1), 500),
      setTimeout(() => setBuildPhase(2), 1500),
      setTimeout(() => setBuildPhase(3), 2500),
      setTimeout(() => setBuildPhase(4), 3500),
    ];
    return () => phases.forEach(clearTimeout);
  }, []);

  const resetTown = () => {
    setBuildPhase(0);
    setTimeout(() => setBuildPhase(1), 500);
    setTimeout(() => setBuildPhase(2), 1500);
    setTimeout(() => setBuildPhase(3), 2500);
    setTimeout(() => setBuildPhase(4), 3500);
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-stone-200 p-8">
      <div
        className={`relative w-full max-w-4xl p-8 bg-stone-50 transition-all duration-1000 ease-in-out border-[12px] border-double border-amber-900
          ${buildPhase >= 1 ? 'opacity-100 scale-100' : 'opacity-0 scale-95'}`}
        style={{
          boxShadow: buildPhase >= 1 ? 'inset 0 0 20px rgba(120, 53, 15, 0.4), 0 10px 25px rgba(0,0,0,0.2)' : 'none'
        }}
      >
        <div className={`absolute top-0 left-0 w-full flex justify-between px-6 py-2 text-amber-900 transition-opacity duration-1000 ${buildPhase >= 1 ? 'opacity-100' : 'opacity-0'}`}>
           <span className="tracking-widest">❖ 〰〰〰 ❖ 〰〰〰 ❖</span>
           <span className="font-serif font-bold text-xl tracking-widest">柴又帝釈天参道</span>
           <span className="tracking-widest">❖ 〰〰〰 ❖ 〰〰〰 ❖</span>
        </div>

        <div className="mt-16 flex justify-around items-end h-72 gap-6 border-b-8 border-stone-400 pb-2 relative">
          <div className={`relative flex flex-col items-center justify-end w-40 h-52 bg-amber-100 border-x-4 border-t-4 border-amber-800 transition-all duration-1000 transform ${buildPhase >= 2 ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
            <div className="absolute -top-8 w-44 h-10 bg-stone-800 rounded-t-md shadow-lg"></div>
            <div className={`w-full h-16 bg-green-800 text-white flex items-center justify-center text-lg font-serif mb-auto transition-opacity duration-700 ${buildPhase >= 3 ? 'opacity-100' : 'opacity-0'}`}>
              草だんご
            </div>
            <div className={`absolute -left-6 bottom-0 bg-white border-4 border-amber-900 p-2 shadow-md transition-all duration-700 delay-300 ${buildPhase >= 3 ? 'rotate-0 opacity-100' : '-rotate-12 opacity-0'}`}>
              <div className="font-serif font-bold text-xl" style={{ writingMode: 'vertical-rl' }}>
                名物
              </div>
            </div>
          </div>

          <div className={`relative flex flex-col items-center justify-end w-40 h-48 bg-amber-50 border-x-4 border-t-4 border-amber-900 transition-all duration-1000 transform delay-100 ${buildPhase >= 2 ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
            <div className="absolute -top-6 w-44 h-8 bg-stone-700 rounded-t-sm shadow-md"></div>
            <div className={`w-full h-14 bg-red-800 text-white flex items-center justify-center text-md font-serif mb-auto transition-opacity duration-700 delay-200 ${buildPhase >= 3 ? 'opacity-100' : 'opacity-0'}`}>
              手焼き煎餅
            </div>
            <div className={`absolute -top-16 bg-white rounded-full w-16 h-16 border-4 border-black flex items-center justify-center shadow-lg transition-all duration-500 delay-500 ${buildPhase >= 3 ? 'scale-100 opacity-100' : 'scale-50 opacity-0'}`}>
               <span className="font-bold font-serif text-lg">米</span>
            </div>
          </div>

          <div className={`relative flex flex-col items-center justify-end w-36 h-40 bg-amber-100 border-x-4 border-t-4 border-amber-800 transition-all duration-1000 transform delay-200 ${buildPhase >= 2 ? 'translate-y-0 opacity-100' : 'translate-y-10 opacity-0'}`}>
            <div className="absolute -top-5 w-40 h-6 bg-stone-800 rounded-t-sm shadow-md"></div>
            <div className={`absolute -top-12 bg-blue-900 text-white px-3 py-1 border-2 border-white shadow-md transition-all duration-700 delay-400 ${buildPhase >= 3 ? 'opacity-100' : 'opacity-0'}`}>
              <span className="font-serif tracking-widest text-sm">おみやげ</span>
            </div>
          </div>

          <div className={`absolute top-4 left-0 w-full flex justify-around pointer-events-none transition-all duration-1000 ${buildPhase >= 4 ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0'}`}>
             {[1, 2, 3, 4, 5].map((i) => (
               <div key={i} className="w-8 h-10 bg-red-600 rounded-2xl border-2 border-black flex items-center justify-center shadow-red-900/50 shadow-lg">
                 <div className="w-full h-[2px] bg-black opacity-30 my-1"></div>
               </div>
             ))}
          </div>
        </div>
      </div>

      <button
        onClick={resetTown}
        className="mt-8 px-6 py-2 bg-stone-700 text-white rounded hover:bg-stone-600 transition-colors"
      >
        もう一度街を作る
      </button>
    </div>
  );
};

export default Model_Katsushika;