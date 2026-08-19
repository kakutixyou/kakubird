# to/plugins/sql_builder_v2/backend_sql_v2/services/nlp_service.py
from pydantic import BaseModel

class AnalysisRequest(BaseModel):
    text: str

class TemplatePart(BaseModel):
    label: str
    value: str
    key: str

class AnalysisResponse(BaseModel):
    type: str
    title: str
    icon: str
    description: str
    sql: str
    parts: list[TemplatePart]
    input: str

class BuildRequest(BaseModel):
    type: str
    parts: dict[str, str] = {}

class BuildResponse(BaseModel):
    sql: str
    type: str

# services/nlp_service.py
import re

# ===
# 1. 日本語解析用の正規表現パターン定義
# ===

# 副問い合わせを示す日本語パターン
SUBQUERY_PATTERNS = [
    r'の中で.*より(高い|安い|大きい|小さい|多い|少ない)',
    r'の中で.*な.*は',
    r'(?:where|中で).*(?:select|選ぶ|取得)',
    r'([^\s]+)の中で.*([^\s]+)は(何|どんな|どれ)',
]

# JOIN種別ごとの日本語パターン
JOIN_PATTERNS = {
    'inner': [r'と.*を.*結合', r'両方に.*ある', r'一致する.*と'],
    'left':  [r'左.*結合', r'.*を基準に.*含む', r'全て.*と.*あれば', r'のすべてと'],
    'right': [r'右.*結合', r'.*右側', r'.*を基準に.*左'],
    'cross': [r'全組み合わせ', r'直積'],
}

# DML・集計系の日本語パターン
INSERT_PATTERNS = [r'追加', r'挿入', r'新しく.*登録', r'insert', r'入れる']
UPDATE_PATTERNS = [r'更新', r'変更', r'修正', r'update']
DELETE_PATTERNS = [r'削除', r'消す', r'除く', r'delete']
GROUPBY_PATTERNS = [r'グループ', r'集計', r'合計', r'平均', r'count', r'sum', r'avg', r'最大', r'最小']


# ===
# 2. ビジネスロジック実装
# ===

def detect_template_type(text: str) -> str:
    """
    日本語テキストを正規表現で走査し、最適なSQLテンプレート種別を返す。
    優先順位: subquery > left_join > right_join > inner_join >
              insert > update > delete > group_by > select (デフォルト)
    """
    text_lower = text.lower()

    for pat in SUBQUERY_PATTERNS:
        if re.search(pat, text):
            return 'subquery'

    for pat in JOIN_PATTERNS['left']:
        if re.search(pat, text):
            return 'left_join'

    for pat in JOIN_PATTERNS['right']:
        if re.search(pat, text):
            return 'right_join'

    for pat in JOIN_PATTERNS['inner']:
        if re.search(pat, text):
            return 'inner_join'

    for pat in INSERT_PATTERNS:
        if re.search(pat, text_lower):
            return 'insert'

    for pat in UPDATE_PATTERNS:
        if re.search(pat, text_lower):
            return 'update'

    for pat in DELETE_PATTERNS:
        if re.search(pat, text_lower):
            return 'delete'

    for pat in GROUPBY_PATTERNS:
        if re.search(pat, text_lower):
            return 'group_by'

    return 'select'


def extract_entities(text: str) -> dict:
    """
    日本語テキストからテーブル名・カラム名・WHERE条件を抽出して返す。

    Returns:
        {
            'tables':     list[str],  # 推定テーブル名
            'columns':    list[str],  # 推定カラム名
            'conditions': list[str],  # WHERE条件文字列
            'values':     list[str],  # INSERT用の値（現在は予約）
        }
    """
    entities: dict = {'tables': [], 'columns': [], 'conditions': [], 'values': []}

    # 価格・数値条件（例: "1000円より高い", "500円以上"）
    num_match = re.search(r'(\d+)円(より|以上|以下|未満)(高い|安い|大きい|小さい)?', text)
    if num_match:
        val      = num_match.group(1)
        op_word  = num_match.group(2) + (num_match.group(3) or '')
        # デフォルトは '>'。「より安い/小さい」や「未満」は '<'
        if '以上' in op_word:
            op = '>='
        elif '以下' in op_word:
            op = '<='
        elif '未満' in op_word or 'より安' in op_word or 'より小' in op_word:
            op = '<'
        else:
            op = '>'
        entities['conditions'].append(f'price {op} {val}')

    # 「〇〇の中で」「〇〇テーブル」「〇〇表」からテーブル名候補を抽出
    table_hints = re.findall(r'([ぁ-んァ-ン一-龥a-zA-Z]+)(?:の中で|テーブル|表)', text)
    entities['tables'] = list(dict.fromkeys(table_hints))  # 順序を保ちつつ重複除去

    # 意味的カラムのマッピング
    if '名前' in text or '名称' in text:
        entities['columns'].append('name')
    if '価格' in text or '値段' in text or '金額' in text:
        entities['columns'].append('price')

    return entities


def build_sql_template(template_type: str, text: str, entities: dict) -> dict:
    """
    テンプレート種別とエンティティ情報からSQLテンプレートとUIパーツを生成する。
    """
    tables = entities['tables'] or ['テーブルA', 'テーブルB']
    t1  = tables[0]
    t2  = tables[1] if len(tables) > 1 else tables[0] + '2'
    cols = ', '.join(entities['columns']) if entities['columns'] else '*'
    cond = entities['conditions'][0] if entities['conditions'] else 'カラム = 値'

    # サブクエリの結合キーに使うカラム名（条件の最初の単語、なければ "id"）
    cond_col = cond.split()[0] if entities['conditions'] else 'id'

    templates: dict[str, dict] = {
        'subquery': {
            'title': '副問い合わせ (Subquery)',
            'icon': '◎',
            'description': f'「{text}」→ 外側クエリの条件に内側クエリの結果を使います',
            'sql': (
                f"SELECT {cols}\n"
                f"FROM {t1}\n"
                f"WHERE {cond_col} IN (\n"
                f"    SELECT {cond_col}\n"
                f"    FROM {t1}\n"
                f"    WHERE {cond}\n"
                f");"
            ),
            'parts': [
                {'label': '外側テーブル',  'value': t1,       'key': 'outer_table'},
                {'label': '取得カラム',    'value': cols,      'key': 'select_cols'},
                {'label': '内側テーブル',  'value': t1,       'key': 'inner_table'},
                {'label': '条件',          'value': cond,      'key': 'condition'},
            ],
        },
        'left_join': {
            'title': 'LEFT JOIN',
            'icon': '⊂',
            'description': '左テーブルを基準に右テーブルを結合（右に一致がなくてもNULLで返す）',
            'sql': (
                f"SELECT a.*, b.*\n"
                f"FROM {t1} AS a\n"
                f"LEFT JOIN {t2} AS b\n"
                f"  ON a.id = b.{t1.lower()}_id\n"
                f"WHERE a.{cond};"
            ),
            'parts': [
                {'label': '左テーブル',  'value': t1,                        'key': 'left_table'},
                {'label': '右テーブル',  'value': t2,                        'key': 'right_table'},
                {'label': '結合条件',    'value': f'a.id = b.{t1.lower()}_id', 'key': 'on_clause'},
                {'label': 'WHERE条件',   'value': cond,                      'key': 'where_clause'},
            ],
        },
        'right_join': {
            'title': 'RIGHT JOIN',
            'icon': '⊃',
            'description': '右テーブルを基準に左テーブルを結合',
            'sql': (
                f"SELECT a.*, b.*\n"
                f"FROM {t1} AS a\n"
                f"RIGHT JOIN {t2} AS b\n"
                f"  ON a.id = b.{t1.lower()}_id;"
            ),
            'parts': [
                {'label': '左テーブル',  'value': t1,                        'key': 'left_table'},
                {'label': '右テーブル',  'value': t2,                        'key': 'right_table'},
                {'label': '結合条件',    'value': f'a.id = b.{t1.lower()}_id', 'key': 'on_clause'},
            ],
        },
        'inner_join': {
            'title': 'INNER JOIN',
            'icon': '∩',
            'description': '両テーブルで一致する行だけを返す',
            'sql': (
                f"SELECT a.*, b.*\n"
                f"FROM {t1} AS a\n"
                f"INNER JOIN {t2} AS b\n"
                f"  ON a.id = b.{t1.lower()}_id\n"
                f"WHERE {cond};"
            ),
            'parts': [
                {'label': '左テーブル',  'value': t1,                        'key': 'left_table'},
                {'label': '右テーブル',  'value': t2,                        'key': 'right_table'},
                {'label': '結合条件',    'value': f'a.id = b.{t1.lower()}_id', 'key': 'on_clause'},
                {'label': 'WHERE条件',   'value': cond,                      'key': 'where_clause'},
            ],
        },
        'insert': {
            'title': 'INSERT',
            'icon': '+',
            'description': 'テーブルに新しい行を追加する',
            'sql': (
                f"INSERT INTO {t1} (カラム1, カラム2, カラム3)\n"
                f"VALUES (値1, 値2, 値3);"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,               'key': 'table'},
                {'label': 'カラム',     'value': 'カラム1, カラム2', 'key': 'columns'},
                {'label': '値',         'value': '値1, 値2',        'key': 'values'},
            ],
        },
        'update': {
            'title': 'UPDATE',
            'icon': '↻',
            'description': '既存の行を更新する',
            'sql': (
                f"UPDATE {t1}\n"
                f"SET カラム1 = 新しい値\n"
                f"WHERE {cond};"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,             'key': 'table'},
                {'label': 'SET句',      'value': 'カラム1 = 新しい値', 'key': 'set_clause'},
                {'label': 'WHERE条件',  'value': cond,           'key': 'where_clause'},
            ],
        },
        'delete': {
            'title': 'DELETE',
            'icon': '✕',
            'description': '条件に一致する行を削除する',
            'sql': (
                f"DELETE FROM {t1}\n"
                f"WHERE {cond};"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,   'key': 'table'},
                {'label': 'WHERE条件',  'value': cond, 'key': 'where_clause'},
            ],
        },
        'group_by': {
            'title': 'GROUP BY / 集計',
            'icon': '≡',
            'description': 'グループ単位での集計クエリ',
            'sql': (
                f"SELECT カテゴリ, COUNT(*) AS 件数, AVG(price) AS 平均価格\n"
                f"FROM {t1}\n"
                f"GROUP BY カテゴリ\n"
                f"HAVING COUNT(*) > 1\n"
                f"ORDER BY 件数 DESC;"
            ),
            'parts': [
                {'label': 'テーブル名',   'value': t1,                   'key': 'table'},
                {'label': 'グループカラム', 'value': 'カテゴリ',          'key': 'group_col'},
                {'label': '集計関数',     'value': 'COUNT(*), AVG(price)', 'key': 'agg_funcs'},
                {'label': 'HAVING条件',   'value': 'COUNT(*) > 1',       'key': 'having'},
            ],
        },
        'select': {
            'title': 'SELECT',
            'icon': '▷',
            'description': '基本的なデータ取得クエリ',
            'sql': (
                f"SELECT {cols}\n"
                f"FROM {t1}\n"
                f"WHERE {cond}\n"
                f"ORDER BY id\n"
                f"LIMIT 100;"
            ),
            'parts': [
                {'label': 'テーブル名', 'value': t1,   'key': 'table'},
                {'label': '取得カラム', 'value': cols,  'key': 'select_cols'},
                {'label': 'WHERE条件',  'value': cond, 'key': 'where_clause'},
            ],
        },
    }

    return templates.get(template_type, templates['select'])


def build_custom_sql(template_type: str, parts: dict[str, str]) -> str:
    """
    ユーザーが編集したパーツ（テーブル名・条件など）とテンプレート種別から、
    最終的な実行用SQL文字列を再構築して返す。
    （ルーターに直書きされていた /build のロジックを抽出）
    """
    if template_type == 'subquery':
        cols     = parts.get('select_cols', '*')
        key_col  = cols.split(',')[0].strip()
        return (
            f"SELECT {cols}\n"
            f"FROM {parts.get('outer_table', 'table_a')}\n"
            f"WHERE {key_col} IN (\n"
            f"    SELECT {key_col}\n"
            f"    FROM {parts.get('inner_table', 'table_a')}\n"
            f"    WHERE {parts.get('condition', '条件')}\n"
            f");"
        )
        
    elif template_type in ('left_join', 'right_join', 'inner_join'):
        join_kw = {
            'left_join':  'LEFT JOIN',
            'right_join': 'RIGHT JOIN',
            'inner_join': 'INNER JOIN',
        }[template_type]
        
        where_clause = parts.get('where_clause', '')
        where = f"\nWHERE {where_clause}" if where_clause else ''
        return (
            f"SELECT a.*, b.*\n"
            f"FROM {parts.get('left_table', 'table_a')} AS a\n"
            f"{join_kw} {parts.get('right_table', 'table_b')} AS b\n"
            f"  ON {parts.get('on_clause', 'a.id = b.table_a_id')}{where};"
        )
        
    elif template_type == 'insert':
        return (
            f"INSERT INTO {parts.get('table', 'table_a')} ({parts.get('columns', 'col1, col2')})\n"
            f"VALUES ({parts.get('values', 'val1, val2')});"
        )
        
    elif template_type == 'update':
        return (
            f"UPDATE {parts.get('table', 'table_a')}\n"
            f"SET {parts.get('set_clause', 'col = value')}\n"
            f"WHERE {parts.get('where_clause', '条件')};"
        )
        
    elif template_type == 'delete':
        return (
            f"DELETE FROM {parts.get('table', 'table_a')}\n"
            f"WHERE {parts.get('where_clause', '条件')};"
        )
        
    elif template_type == 'group_by':
        return (
            f"SELECT {parts.get('group_col', 'category')}, COUNT(*) AS 件数\n"
            f"FROM {parts.get('table', 'table_a')}\n"
            f"GROUP BY {parts.get('group_col', 'category')}\n"
            f"HAVING {parts.get('having', 'COUNT(*) > 0')};"
        )
        
    else:  # select (default)
        return (
            f"SELECT {parts.get('select_cols', '*')}\n"
            f"FROM {parts.get('table', 'table_a')}\n"
            f"WHERE {parts.get('where_clause', '条件')};"
        )