#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engines/normalize_engine.py
────────────────────────────
文字列として混入した数値（単位付き、カンマ付きなど）を正規化し、
計算可能な float 型に変換する共通エンジン。

"1,200" のようなカンマ区切りや、"1.2ha" のような面積単位混在の表記を
適切にパースし、m² に換算してから合算できるようにする。
"""

from __future__ import annotations

import re
from typing import Any, Optional


def normalize_numeric_string(val: Any) -> Optional[float]:
    """
    オープンデータに含まれる様々な表記の数値をfloatに変換する。
    
    変換例:
      "1,200"      -> 1200.0
      "1.2ha"      -> 12000.0 (m2換算: 1ha = 10,000m2)
      "1.5ヘクタール" -> 15000.0 (m2換算)
      "500㎡"       -> 500.0
      150          -> 150.0
      "不明"       -> None
    
    Args:
        val: JSON等から抽出した生のデータ（文字列、数値、Noneなど）
        
    Returns:
        float: 正規化された数値。パース不可能な場合は None。
    """
    if val is None:
        return None
    
    # すでに数値型(int, float)の場合はそのままfloatにして返す
    if isinstance(val, (int, float)):
        return float(val)
    
    # 文字列として処理 (前後の空白除去、カンマ除去、小文字化)
    # 全角文字が含まれている場合も考慮
    text = str(val).strip().replace(',', '').lower()
    if not text:
        return None

    # ヘクタール(ha)が含まれているか判定
    is_hectare = 'ha' in text or 'ヘクタール' in text
    
    # 数字(0-9)と小数点(.)以外をすべて除去して抽出
    # 例: "1.2ha" -> "1.2"
    num_str = re.sub(r'[^\d.]', '', text)
    
    try:
        # 空文字になってしまった場合（例: "不明"などの文字だけだった場合）
        if not num_str:
            return None
        
        # 変換（"1.2.3"のような不正な文字列の場合はここでValueErrorになる）
        parsed = float(num_str)
        
        # ヘクタールの場合は m2 (平方メートル) に換算
        if is_hectare:
            parsed *= 10000.0
            
        return parsed
        
    except ValueError:
        # 変換に失敗した場合は None を返す
        return None