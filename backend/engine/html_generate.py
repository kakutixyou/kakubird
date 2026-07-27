# html_engine.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
import json

app = FastAPI()

# =============== HTMLコンポーネントルール ===============
class ComponentRule:
    """HTMLコンポーネントの標準化ルール"""
    RULES = {
        "hero": {
            "tag": "section",
            "classes": ["hero", "min-h-screen", "flex", "items-center"],
            "children": ["h1", "p", "button"]
        },
        "card": {
            "tag": "div",
            "classes": ["card", "rounded-lg", "shadow-md", "p-4"],
            "children": ["h3", "p", "a"]
        },
        "navbar": {
            "tag": "nav",
            "classes": ["navbar", "bg-gray-900", "sticky", "top-0"],
            "children": ["logo", "menu", "cta"]
        },
        "footer": {
            "tag": "footer",
            "classes": ["footer", "bg-gray-800", "text-white", "py-8"],
            "children": ["links", "social", "copyright"]
        }
    }

class ComponentSpec(BaseModel):
    type: str  # "hero", "card", etc.
    content: Dict[str, Any]
    styling: Dict[str, str] = {}

class PageSpec(BaseModel):
    title: str
    components: List[ComponentSpec]

# =============== HTML生成ロジック ===============
def generate_html_from_spec(page_spec: PageSpec) -> str:
    """ルール定義に基づいてHTMLを生成"""
    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_spec.title}</title>
    <link rel="stylesheet" href="/styles.css">
</head>
<body>
"""
    
    for component in page_spec.components:
        if component.type not in ComponentRule.RULES:
            raise ValueError(f"Unknown component type: {component.type}")
        
        rule = ComponentRule.RULES[component.type]
        tag = rule["tag"]
        classes = " ".join(rule["classes"])
        
        html += f'    <{tag} class="{classes}">\n'
        
        # コンテンツを挿入
        if component.type == "hero":
            html += f'''        <h1>{component.content.get("title", "")}</h1>
        <p>{component.content.get("subtitle", "")}</p>
        <button class="cta-btn">{component.content.get("button_text", "")}</button>
'''
        elif component.type == "card":
            html += f'''        <h3>{component.content.get("title", "")}</h3>
        <p>{component.content.get("description", "")}</p>
        <a href="{component.content.get("link", "#")}">{component.content.get("link_text", "")}</a>
'''
        # 他のコンポーネント...
        
        html += f'    </{tag}>\n'
    
    html += """</body>
</html>"""
    
    return html

# =============== API エンドポイント ===============
@app.post("/api/html/generate")
async def generate_html(page_spec: PageSpec):
    """HTMLを生成"""
    try:
        html = generate_html_from_spec(page_spec)
        return {
            "status": "ok",
            "html": html,
            "size": len(html)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/html/export")
async def export_html(page_spec: PageSpec, format: str = "html"):
    """HTMLをファイルとしてエクスポート"""
    html = generate_html_from_spec(page_spec)
    
    if format == "html":
        return {"content": html, "filename": f"{page_spec.title}.html"}
    elif format == "zip":
        # HTML + CSS を ZIP で返す
        return {"content": "...", "filename": f"{page_spec.title}.zip"}

@app.get("/api/html/rules")
async def get_component_rules():
    """使用可能なコンポーネントルールを返す"""
    return {"rules": ComponentRule.RULES}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)