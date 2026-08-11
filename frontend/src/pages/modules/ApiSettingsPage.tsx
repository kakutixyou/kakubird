// pages/modules/ApiSettingsPage.tsx

import React from "react";
import toast from "react-hot-toast";

import AiChatPanel from "../../components/AiChatPanel.jsx";

import { useThemeStore } from "../../store/themeStore";

const THEMES = [
  {
    id: "default",
    name: "Default",
    description: "標準テーマ"
  },
  {
    id: "future-purple",
    name: "Future Purple",
    description: "近未来UI"
  },
  {
    id: "alexandros",
    name: "Alexandros",
    description: "古代ギリシャ風UI"
  }
];

export default function ApiSettingsPage() {
  const {
    currentTheme,
    setTheme
  } = useThemeStore();

  const handleThemeChange = (
    themeId: string
  ) => {
    setTheme(themeId);

    toast.success(
      `${themeId} を適用しました`
    );
  };

  return (
    <div className="h-full p-6">
      <div className="flex gap-6 h-full">

        {/* =======================================
            左側
        ======================================= */}

        <div className="w-[420px] flex-shrink-0 space-y-6">

          {/* テーマ設定 */}
          <div className="bg-white rounded-xl shadow border p-5">

            <h1 className="text-xl font-bold mb-2">
              テーマ設定
            </h1>

            <p className="text-sm text-slate-500 mb-4">
              Sidebar や Chat UI の見た目を変更します
            </p>

            <div className="space-y-3">

              {THEMES.map(theme => (
                <div
                  key={theme.id}
                  className={`
                    border rounded-lg p-4 transition-all
                    ${
                      currentTheme === theme.id
                        ? "border-indigo-500 bg-indigo-50"
                        : "border-slate-200"
                    }
                  `}
                >
                  <div className="flex items-center justify-between">

                    <div>
                      <h3 className="font-semibold">
                        {theme.name}
                      </h3>

                      <p className="text-xs text-slate-500">
                        {theme.description}
                      </p>
                    </div>

                    <button
                      onClick={() =>
                        handleThemeChange(theme.id)
                      }
                      className="
                        px-3 py-2
                        rounded-lg
                        bg-indigo-600
                        text-white
                        text-sm
                        hover:bg-indigo-700
                      "
                    >
                      適用
                    </button>

                  </div>
                </div>
              ))}

            </div>

          </div>

          {/* 現在のテーマ */}
          <div className="bg-white rounded-xl shadow border p-5">

            <h2 className="font-semibold mb-3">
              現在のテーマ
            </h2>

            <div className="text-indigo-600 font-bold">
              {currentTheme}
            </div>

          </div>

        </div>

        {/* =======================================
            右側 AIチャット
        ======================================= */}

        <div className="flex-1 min-w-0">

          <div
            className="
              h-full
              bg-white
              rounded-xl
              shadow
              border
              overflow-hidden
            "
          >
            <AiChatPanel />
          </div>

        </div>

      </div>
    </div>
  );
}