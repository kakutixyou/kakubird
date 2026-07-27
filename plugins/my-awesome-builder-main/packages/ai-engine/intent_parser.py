"""
intent_parser.py
Detect mood and domain from user input
"""

MOOD_KEYWORDS = {
    "futuristic": ["未来", "AI", "テク", "最新", "モダン", "デジタル", "次世代"],
    "elegant": ["エレガント", "高級", "洗練", "上品", "優雅"],
    "academic": ["学習", "教育", "学問", "研究", "教材", "講義"],
    "historical": ["歴史", "古い", "伝統", "遺産", "過去", "年代"],
    "playful": ["楽しい", "遊び", "カラフル", "親しみやすい", "ポップ"],
    "corporate": ["ビジネス", "企業", "プロ", "オフィス", "会社"],
    "minimal": ["シンプル", "ミニマル", "スッキリ", "洗練", "シンプル"]
}

DOMAIN_KEYWORDS = {
    "engineering": ["工学", "電気", "機械", "制御", "回路", "建築"],
    "history": ["歴史", "過去", "時代", "遺跡", "年表", "古代"],
    "medical": ["医学", "医療", "健康", "解剖", "病気"],
    "business": ["ビジネス", "経営", "営業", "マーケティング", "商業"],
    "language": ["言語", "語学", "英語", "日本語", "翻訳"],
    "science": ["科学", "物理", "化学", "生物", "実験"],
    "general": ["一般", "基礎", "入門", "初心者"]
}


def detect_mood(text):
    """Detect mood from user input"""
    for mood, keywords in MOOD_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return mood

    return "academic"


def detect_domain(text):
    """Detect domain from user input"""
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return domain

    return "general"


def parse_user_intent(text):
    """
    Parse user input to extract mood and domain

    Args:
        text: str - User input text

    Returns:
        dict - {mood, domain, raw_input}
    """
    return {
        "mood": detect_mood(text),
        "domain": detect_domain(text),
        "raw_input": text
    }
