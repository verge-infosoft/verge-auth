from fastapi.responses import RedirectResponse, JSONResponse
import httpx
import os

def add_central_auth(app):
    AUTH_INTROSPECT_URL = os.getenv("AUTH_INTROSPECT_URL")
    AUTH_LOGIN_URL = os.getenv("AUTH_LOGIN_URL")
    CLIENT_ID = os.getenv("VERGE_CLIENT_ID")
    CLIENT_SECRET = os.getenv("VERGE_CLIENT_SECRET")

    @app.middleware("http")
    async def central_auth(request, call_next):

        # Allow public endpoints
        if request.url.path in {"/health", "/docs", "/openapi.json"}:
            return await call_next(request)

        # -----------------------------
        # Extract token
        # -----------------------------
        token = None
        if "authorization" in request.headers:
            auth = request.headers.get("authorization")
            if auth.lower().startswith("bearer"):
                token = auth.split(" ")[1]

        if not token:
            token = request.cookies.get("access_token")

        # -----------------------------
        # No token → Redirect or 401
        # -----------------------------
        if not token:
            if "text/html" in request.headers.get("accept", ""):
                return RedirectResponse(
                    f"{AUTH_LOGIN_URL}?redirect_url={request.url}"
                )
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)

        # -----------------------------
        # Call central auth
        # -----------------------------
        try:
            async with httpx.AsyncClient(timeout=3) as client:
                res = await client.post(
                    AUTH_INTROSPECT_URL,
                    headers={
                        "Authorization": f"Bearer {token}",
                        "X-Client-Id": CLIENT_ID,
                        "X-Client-Secret": CLIENT_SECRET
                    }
                )

                data = res.json()
        except Exception:
            return JSONResponse({"detail": "Auth service unreachable"}, status_code=503)

        if not data.get("active"):
            return JSONResponse({"detail": "Session expired"}, status_code=401)

        # -----------------------------
        # Attach context
        # -----------------------------
        request.state.user = data.get("user")
        request.state.roles = data.get("roles", [])
        plan = data.get("plan", "free")
        redirect_target = data.get("redirect", "microservice")

        # -----------------------------
        # Browser Redirection Logic
        # -----------------------------
        if "text/html" in request.headers.get("accept", ""):
            # Free tier → Always go to microservice UI
            if plan == "free":
                if redirect_target == "microservice":
                    return RedirectResponse(str(request.url))

            # Paid users
            if plan == "paid":
                if redirect_target == "admin":
                    return RedirectResponse(f"{AUTH_LOGIN_URL}/admin")

        # -----------------------------
        # Continue request
        # -----------------------------
        return await call_next(request)
