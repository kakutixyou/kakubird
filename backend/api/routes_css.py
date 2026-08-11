from fastapi import APIRouter
from pydantic import BaseModel

#main.pyではなくai_server.pyを探すこと!
router = APIRouter()

class CSSRequest(BaseModel):
    prompt: str
    plugin: str | None = None
    config: dict | None = None

@router.post("/generate")
async def generate_css(req: CSSRequest):
    print("🎨 CSS Generation Request")
    print("Prompt:", req.prompt)
    print("Plugin:", req.plugin)
    print("Config:", req.config)

    return {
        "status": "success",
        "summary": f"'{req.prompt}' を解析しました。",
        "css": ".generated-style { color: #4f46e5; }",
        "config": req.config
    }
    
