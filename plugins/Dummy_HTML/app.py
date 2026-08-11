# TO(と)/plugins/Dummy_HTML\app.py
import os
from flask import Flask, jsonify

app = Flask(__name__)

BASE_DIR = os.path.dirname(__file__)
# TEMPLATE_DIR = os.path.join(BASE_DIR, "templates", "dummies")
# plugins/Dummy_HTML/app.py
TEMPLATE_DIR = os.path.join(
    BASE_DIR,
    "templates"
)

# ダミー資産が置かれているディレクトリ
# TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "templates", "dummies")

# @app.route("/api/load-dummy-ui", methods=["GET"])
# def load_dummy_ui():
#     """
#     ローカルのダミーHTMLやCSS、JSファイルを読み込んで
#     ReactのHtmlCssPreviewBlockが読める形式にして返却する
#     """
#     # 例として「dummy_button.html」などを読み込む想定
#     html_path = os.path.join(TEMPLATE_DIR, "dummy_layout.html")
#     css_path = os.path.join(TEMPLATE_DIR, "dummy_style.css")
    
#     # デフォルトのフォールバックデータ
#     html_content = "<button className='btn'>ダミーボタン</button>"
#     css_content = ".btn { padding: 10px; background: gray; color: white; }"
    
#     if os.path.exists(html_path):
#         with open(html_path, "r", encoding="utf-8") as f:
#             html_content = f.read()
            
#     if os.path.exists(css_path):
#         with open(css_path, "r", encoding="utf-8") as f:
#             css_content = f.read()
            
#     # React側の「block」の構造に合わせたJSONを返す
#     return jsonify({
#         "status": "success",
#         "block": {
#             "type": "HtmlCssPreviewBlock",
#             "component_name": "DummyLayoutComponent",
#             "html": html_content,
#             "css": css_content
#         }
#     })

def load_dummy_assets(template_name="dummy_layout"):
    """
    指定されたテンプレート名のHTML/CSSを読み込んで返す
    例: template_name="template_1" なら template_1.html を読み込む
    """
    html_path = os.path.join(TEMPLATE_DIR, f"{template_name}.html")
    css_path = os.path.join(TEMPLATE_DIR, f"{template_name}.css")

    html_content = ""
    css_content = ""

    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

    return {
        "html": html_content,
        "css": css_content
    }