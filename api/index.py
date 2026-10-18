import json
import math
import os
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler

try:
    from livekit import api
except ImportError:
    api = None

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class handler(BaseHTTPRequestHandler):
    def _send_json(self, data: dict, status: int = 200) -> None:
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
        self.wfile.write(payload)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        LIVEKIT_URL = os.getenv("LIVEKIT_URL", "").strip()
        LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY", "").strip()
        LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET", "").strip()

        # 1. Health check endpoint
        if path.endswith("/health") or path.endswith("/ping"):
            self._send_json({"status": "healthy", "service": "omnilearn-api"})
            return

        # 2. Status Check endpoint
        if path.endswith("/status") or "status" in path:
            has_creds = bool(LIVEKIT_URL and LIVEKIT_API_KEY and LIVEKIT_API_SECRET)
            self._send_json({
                "status": "ready" if has_creds else "missing_credentials",
                "serverUrl": LIVEKIT_URL,
                "hasCredentials": has_creds,
            })
            return

        # 3. Token generation endpoint
        if path.endswith("/token") or "token" in path:
            if not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET or not LIVEKIT_URL:
                self._send_json(
                    {"error": "LiveKit credentials (LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET) not configured in environment."},
                    status=500,
                )
                return

            if api is None:
                self._send_json({"error": "livekit-api module is not installed."}, status=500)
                return

            room_name = query.get("room", [f"omni-{uuid.uuid4().hex[:6]}"])[0]
            identity = query.get("identity", [f"user-{uuid.uuid4().hex[:6]}"])[0]
            name = query.get("name", ["Student"])[0]

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

                self._send_json({
                    "serverUrl": LIVEKIT_URL,
                    "token": token,
                    "room": room_name,
                    "identity": identity,
                })
                return
            except Exception as e:
                self._send_json({"error": f"Failed generating LiveKit token: {str(e)}"}, status=500)
                return

        self._send_json({"error": "Endpoint not found"}, status=404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        try:
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            data = json.loads(post_body.decode("utf-8")) if post_body else {}
        except Exception as e:
            self._send_json({"error": f"Invalid JSON payload: {str(e)}"}, status=400)
            return

        # 1. AI Physics Solver endpoint
        if path.endswith("/solve") or "solve" in path:
            try:
                angle = float(data.get("estimated_angle", 45.0))
                velocity = float(data.get("estimated_velocity", 25.0))
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

                self._send_json({
                    "status": "success",
                    "explanation": explanation,
                    "code": code,
                    "board": board_payload,
                })
                return
            except Exception as e:
                self._send_json({"error": f"Error solving diagram: {str(e)}"}, status=500)
                return

        # 2. AI Chat fallback endpoint
        if path.endswith("/chat") or "chat" in path:
            query = data.get("message", "").strip()
            if not query:
                self._send_json({"error": "Empty message"}, status=400)
                return
            self._send_json({
                "status": "success",
                "message": f"Processed query: {query}",
            })
            return

        self._send_json({"error": "Endpoint not found"}, status=404)
