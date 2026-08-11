import React, { useState } from "react";

export default function ConversionJsonBlock({ block }) {

    const jsonData = block.json || {};

    const [copied, setCopied] = useState(false);

    const copyJson = async () => {

        try {

            await navigator.clipboard.writeText(
                JSON.stringify(jsonData, null, 2)
            );

            setCopied(true);

            setTimeout(() => setCopied(false), 2000);

        } catch (e) {

            console.error(e);

        }

    };

    return (

        <div className="rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 p-4 mt-4">

            <div className="flex items-center justify-between mb-3">

                <h3 className="font-semibold text-slate-700 dark:text-slate-200">

                    📄 JSON変換結果

                </h3>

                <button
                    onClick={copyJson}
                    className="px-3 py-1 rounded bg-blue-500 text-white hover:bg-blue-600 text-sm"
                >
                    {copied ? "コピー済み" : "コピー"}
                </button>

            </div>

            <pre
                className="
                    overflow-x-auto
                    rounded-lg
                    bg-slate-100
                    dark:bg-slate-800
                    p-4
                    text-sm
                    whitespace-pre-wrap
                    break-all
                "
            >
                {JSON.stringify(jsonData, null, 2)}
            </pre>

        </div>

    );

}