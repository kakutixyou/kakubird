import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * 複数のクラス名を結合し、Tailwind CSS のクラスの競合を賢く解決します。
 * 例: cn('bg-blue-500', 'bg-red-500') -> 'bg-red-500' に自動解決
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
// cd front end →　npm install clsx tailwind-merge