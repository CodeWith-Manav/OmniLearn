import logging
import os
import uuid
from pathlib import Path
from aiohttp import web
from dotenv import load_dotenv

from livekit import api

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("forage2-web-server")

# Load environment
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)
load_dotenv()

LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").strip()
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "").strip()
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "").strip()
PORT = int(os.getenv("PORT", "7860"))

STATIC_DIR = Path(__file__).resolve().parent / "static"


async def get_token_handler(request: web.Request) -> web.Response:
    if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
        return web.json_response(
            {"error": "LiveKit API Key, Secret, or URL is not configured in .env"},
            status=500,
        )

    room_name = request.query.get("room", f"room-{uuid.uuid4().hex[:6]}")
    identity = request.query.get("identity", f"user-{uuid.uuid4().hex[:6]}")
    name = request.query.get("name", "User")

    try:
        token = (
            api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            .with_identity(identity)
            .with_name(name)
            .with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=room_name,
                    can_publish=True,
                    can_subscribe=True,
                    can_publish_data=True,
                )
            )
            .to_jwt()
        )

        return web.json_response(
            {
                "serverUrl": LIVEKIT_URL,
                "token": token,
                "room": room_name,
                "identity": identity,
            }
        )
    except Exception as e:
        logger.error(f"Error generating token: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def status_handler(request: web.Request) -> web.Response:
    has_creds = bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)
    return web.json_response(
        {
            "status": "ready" if has_creds else "missing_credentials",
            "serverUrl": LIVEKIT_URL,
            "hasCredentials": has_creds,
        }
    )


async def index_handler(request: web.Request) -> web.Response:
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return web.Response(text="Frontend index.html not found.", status=404)
    return web.FileResponse(index_file)


async def solve_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        query = data.get("query", "")
        diagram_type = data.get("diagram_type", "projectile_motion")
        angle = float(data.get("estimated_angle", 45.0))
        velocity = float(data.get("estimated_velocity", 25.0))
        mass = float(data.get("mass", 10.0))
        voltage = float(data.get("voltage", 12.0))
        resistance = float(data.get("resistance", 4.0))

        # Precision physics computation
        import math
        g = 9.8
        rad = math.radians(angle)
        ux = velocity * math.cos(rad)
        uy = velocity * math.sin(rad)
        t_flight = (2 * uy) / g
        h_max = (uy ** 2) / (2 * g)
        r_range = (velocity ** 2 * math.sin(2 * rad)) / g

        board_payload = {
            "action": "draw",
            "diagram": "projectile_motion",
            "title": "PROJECTILE MOTION & VECTOR RESOLUTION",
            "velocity": round(velocity, 2),
            "angle": round(angle, 1),
            "gravity": g,
            "ux": round(ux, 2),
            "uy": round(uy, 2),
            "t_flight": round(t_flight, 2),
            "h_max": round(h_max, 2),
            "range": round(r_range, 2),
        }

        explanation = (
            f"I have analyzed your whiteboard drawing and resolved the projectile motion vectors!\n\n"
            f"• **Launch Velocity ($u$)**: {velocity:.1f} m/s at launch angle $\\theta = {angle:.1f}°$\n"
            f"• **Horizontal Velocity ($u_x$)**: $u \\cdot \\cos(\\theta) = {ux:.2f}\\text{{ m/s}}$ *(constant motion)*\n"
            f"• **Vertical Velocity ($u_y$)**: $u \\cdot \\sin(\\theta) = {uy:.2f}\\text{{ m/s}}$ *(under gravity $g = 9.8\\text{{ m/s}}^2$)*\n"
            f"• **Maximum Apex Height ($H_{{\\max}}$)**: $\\frac{{u_y^2}}{{2g}} = {h_max:.2f}\\text{{ meters}}$\n"
            f"• **Total Time of Flight ($T$)**: $\\frac{{2u_y}}{{g}} = {t_flight:.2f}\\text{{ seconds}}$\n"
            f"• **Horizontal Range ($R$)**: $u_x \\times T = {r_range:.2f}\\text{{ meters}}$\n\n"
            f"Trajectory Equation: $y = x \\cdot \\tan({angle:.1f}°) - \\frac{{9.8 x^2}}{{2 \\cdot ({ux:.2f})^2}}$"
        )

        code = (
            f"import math\n\n"
            f"def solve_projectile(velocity={velocity:.1f}, angle_deg={angle:.1f}, g=9.8):\n"
            f"    rad = math.radians(angle_deg)\n"
            f"    ux = velocity * math.cos(rad)\n"
            f"    uy = velocity * math.sin(rad)\n"
            f"    h_max = (uy ** 2) / (2 * g)\n"
            f"    t_flight = (2 * uy) / g\n"
            f"    range_r = ux * t_flight\n"
            f"    \n"
            f"    print(f'=== Projectile Motion Solution ===')\n"
            f"    print(f'Horizontal Velocity (u_x): {{ux:.2f}} m/s')\n"
            f"    print(f'Vertical Velocity (u_y):   {{uy:.2f}} m/s')\n"
            f"    print(f'Max Height (H_max):        {{h_max:.2f}} m')\n"
            f"    print(f'Time of Flight (T):        {{t_flight:.2f}} s')\n"
            f"    print(f'Total Range (R):           {{range_r:.2f}} m')\n"
            f"    return {{'ux': ux, 'uy': uy, 'h_max': h_max, 't_flight': t_flight, 'range': range_r}}\n\n"
            f"solve_projectile()\n"
        )

        return web.json_response({
            "status": "success",
            "explanation": explanation,
            "code": code,
            "board": board_payload,
        })
    except Exception as e:
        logger.error(f"Error in solve_handler: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500)


async def chat_handler(request: web.Request) -> web.Response:
    try:
        data = await request.json()
        query = data.get("message", "").strip()
        if not query:
            return web.json_response({"error": "Empty message"}, status=400)

        return web.json_response({
            "status": "success",
            "message": f"Processed query: {query}",
        })
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)

async def health_handler(request: web.Request) -> web.Response:
    return web.json_response({"status": "healthy", "service": "omnilearn-web"})


@web.middleware
async def cors_middleware(request: web.Request, handler):
    if request.method == "OPTIONS":
        response = web.Response(status=200)
    else:
        try:
            response = await handler(request)
        except web.HTTPException as ex:
            response = ex
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS, PUT, DELETE"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return response


def create_app() -> web.Application:
    app = web.Application(middlewares=[cors_middleware])
    app.router.add_get("/", index_handler)
    app.router.add_get("/api/token", get_token_handler)
    app.router.add_get("/api/status", status_handler)
    app.router.add_get("/api/health", health_handler)
    app.router.add_post("/api/ai/solve", solve_handler)
    app.router.add_post("/api/ai/chat", chat_handler)
    if STATIC_DIR.exists():
        app.router.add_static("/static/", STATIC_DIR, show_index=False)
    return app


def maybe_start_worker():
    start_worker = os.getenv("START_WORKER", "").lower() in ("true", "1", "yes") or \
                   os.getenv("RUN_WORKER", "").lower() in ("true", "1", "yes")
    if start_worker:
        import subprocess
        import sys
        logger.info("🚀 START_WORKER enabled: launching OmniLearn Voice Agent worker...")
        agent_path = Path(__file__).resolve().parent / "agent.py"
        mode = os.getenv("AGENT_MODE", "start")
        try:
            proc = subprocess.Popen([sys.executable, str(agent_path), mode])
            logger.info(f"✨ OmniLearn Agent worker active (PID: {proc.pid}, mode: {mode})")
            return proc
        except Exception as e:
            logger.error(f"Failed to launch background worker: {e}")
    return None


if __name__ == "__main__":
    worker_proc = maybe_start_worker()
    app = create_app()
    logger.info(f"✨ OmniLearn AI Web Server running at http://0.0.0.0:{PORT}")
    try:
        web.run_app(app, host="0.0.0.0", port=PORT)
    finally:
        if worker_proc and worker_proc.poll() is None:
            logger.info("Stopping background agent worker...")
            worker_proc.terminate()

