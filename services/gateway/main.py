"""Gateway Service - API Gateway and Web UI"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import httpx

from shared.config import load_config
from shared.logger import setup_logger
from shared.schemas import HealthCheck


# 設定とロガーの初期化
config = load_config("gateway")
logger = setup_logger(
    service_name=config.get("service.name", "gateway"),
    log_level=config.get("logging.level", "INFO"),
    log_dir=config.get("logging.directory")
)

# FastAPIアプリ
app = FastAPI(title="Gateway Service", version=config.get("service.version", "1.0.0"))

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# テンプレート設定
templates = Jinja2Templates(directory="templates")

# 静的ファイル（将来使用）
# app.mount("/static", StaticFiles(directory="static"), name="static")

# バックエンドサービスのURL
CAMERA_SERVICE_URL = config.get("services.camera.url", "http://localhost:8001")
GRIPPER_SERVICE_URL = config.get("services.gripper.url", "http://localhost:8002")

# HTTPクライアント
http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def startup_event():
    """起動時処理"""
    global http_client
    logger.info("Gateway Service起動")
    http_client = httpx.AsyncClient(timeout=30.0)


@app.on_event("shutdown")
async def shutdown_event():
    """終了時処理"""
    logger.info("Gateway Service終了")
    if http_client:
        await http_client.aclose()


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """統合Web UI"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """ゲートウェイのヘルスチェック"""
    # バックエンドサービスの状態も確認
    camera_healthy = False
    gripper_healthy = False

    try:
        resp = await http_client.get(f"{CAMERA_SERVICE_URL}/health")
        camera_healthy = resp.status_code == 200
    except:
        pass

    try:
        resp = await http_client.get(f"{GRIPPER_SERVICE_URL}/health")
        gripper_healthy = resp.status_code == 200
    except:
        pass

    status = "healthy" if (camera_healthy and gripper_healthy) else "degraded"

    return HealthCheck(
        service=config.get("service.name", "gateway"),
        status=status,
        version=config.get("service.version", "1.0.0"),
        timestamp=datetime.now()
    )


# ===== Camera Service Proxy =====
@app.api_route("/api/camera/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def camera_proxy(path: str, request: Request):
    """Camera Serviceへのプロキシ"""
    url = f"{CAMERA_SERVICE_URL}/{path}"

    # リクエストボディを取得
    body = None
    if request.method in ["POST", "PUT"]:
        body = await request.body()

    try:
        # バックエンドへリクエスト転送
        resp = await http_client.request(
            method=request.method,
            url=url,
            content=body,
            headers=dict(request.headers),
            params=dict(request.query_params)
        )

        # レスポンスを返す
        return JSONResponse(
            content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Camera proxy error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ===== Gripper Service Proxy =====
@app.api_route("/api/gripper/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def gripper_proxy(path: str, request: Request):
    """Gripper Serviceへのプロキシ"""
    url = f"{GRIPPER_SERVICE_URL}/{path}"

    # リクエストボディを取得
    body = None
    if request.method in ["POST", "PUT"]:
        body = await request.body()

    try:
        # バックエンドへリクエスト転送
        resp = await http_client.request(
            method=request.method,
            url=url,
            content=body,
            headers=dict(request.headers),
            params=dict(request.query_params)
        )

        # レスポンスを返す
        return JSONResponse(
            content=resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text,
            status_code=resp.status_code
        )
    except Exception as e:
        logger.error(f"Gripper proxy error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.get("service.host", "0.0.0.0"),
        port=config.get_int("service.port", 8000),
        log_level=config.get("logging.level", "info").lower()
    )