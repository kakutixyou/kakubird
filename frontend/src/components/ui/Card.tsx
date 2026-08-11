import React from "react";
// utils（sあり）に変更してエラーを解消！
import { cn } from "../../utils/cn";

interface CardProps extends React.ComponentProps<"div"> {
  children: React.ReactNode;
}

export function Card({ children, className = "", ...props }: CardProps) {
  return (
    <div
      {...props}
      // bg-editor や rounded-default は Tailwind の設定 (tailwind.config.js) に
      // 依存するカスタムクラス名です。もし色が反映されない場合は、
      // 'bg-white dark:bg-slate-800 rounded-xl shadow-sm' などに置き換えてください。
      className={cn("bg-editor rounded-default space-y-0 px-4 py-3", className)}
    >
      {children}
    </div>
  );
}