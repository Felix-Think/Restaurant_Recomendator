"""FastAPI app with login and chat pages."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional, Tuple

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from agent.chains.orchestrator import run_flow
from utils.logger import log_interaction
from utils.db import get_db

ROOT = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(ROOT / "templates"))


def load_users() -> Dict[str, Tuple[str, str]]:
    """Return mapping username -> (user_id, password)."""
    users: Dict[str, Tuple[str, str]] = {}
    db = get_db()
    for doc in db.users.find({}, {"username": 1, "password": 1, "user_id": 1}):
        users[doc["username"]] = (doc["user_id"], doc["password"])
    return users


def create_user(username: str, password: str) -> Tuple[str, str]:
    """Create a new user in Mongo, returns (user_id, username)."""
    users = load_users()
    if username in users:
        raise ValueError("Username already exists")
    next_id = f"u{len(users) + 1}"
    db = get_db()
    db.users.insert_one({"user_id": next_id, "username": username, "password": password})
    return next_id, username


app = FastAPI()

app.mount("/static", StaticFiles(directory=str(ROOT / "static")), name="static")


@app.get("/", response_class=HTMLResponse)
def home_page(request: Request):
    return TEMPLATES.TemplateResponse("home.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return TEMPLATES.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    users = load_users()
    if username in users and users[username][1] == password:
        resp = RedirectResponse(url="/chat", status_code=303)
        resp.set_cookie("user", username, httponly=True)
        resp.set_cookie("user_id", users[username][0], httponly=True)
        return resp
    return TEMPLATES.TemplateResponse(
        "login.html", {"request": request, "error": "Sai username hoặc password"}
    )


def _get_user(request: Request) -> Optional[str]:
    return request.cookies.get("user")


def _get_user_id(request: Request) -> Optional[str]:
    return request.cookies.get("user_id")


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return TEMPLATES.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register", response_class=HTMLResponse)
def register(request: Request, username: str = Form(...), password: str = Form(...), confirm: str = Form(...)):
    if password != confirm:
        return TEMPLATES.TemplateResponse("register.html", {"request": request, "error": "Mật khẩu không khớp"})
    try:
        uid, _ = create_user(username, password)
    except ValueError as e:
        return TEMPLATES.TemplateResponse("register.html", {"request": request, "error": str(e)})
    resp = RedirectResponse(url="/chat", status_code=303)
    resp.set_cookie("user", username, httponly=True)
    resp.set_cookie("user_id", uid, httponly=True)
    return resp


@app.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request):
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    user_id = _get_user_id(request)
    return TEMPLATES.TemplateResponse(
        "chat.html",
        {"request": request, "user": user, "user_id": user_id, "answer": None, "results": None, "message": ""},
    )


@app.post("/chat", response_class=HTMLResponse)
def chat_submit(
    request: Request,
    message: str = Form(...),
    lat: str = Form("16.065"),
    lng: str = Form("108.229"),
):
    user = _get_user(request)
    if not user:
        return RedirectResponse(url="/", status_code=303)
    user_id = _get_user_id(request) or f"user_{user}"

    try:
        lat_val = float(lat)
        lng_val = float(lng)
    except ValueError:
        lat_val, lng_val = None, None

    result = run_flow(message, lat=lat_val, lng=lng_val, top_k=5, user_id=user_id)
    restaurants = result.get("restaurants", [])

    # Log impressions
    for r in restaurants:
        ctx = {
            "lat": lat_val,
            "lng": lng_val,
            "intent": result["parsed"].get("intent"),
            "cuisine": result["parsed"].get("cuisine"),
            "price_range": result["parsed"].get("price_range"),
        }
        log_interaction(
            user_id=user_id,
            restaurant_id=r.get("restaurant_id") or r.get("url"),
            action="impression",
            reward=0,
            context=ctx,
        )

    return TEMPLATES.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "user": user,
            "user_id": user_id,
            "answer": result.get("answer"),
            "results": restaurants,
            "message": message,
            "user_lat": lat_val,
            "user_lng": lng_val,
            "parsed": result.get("parsed", {}),
        },
    )


@app.post("/track")
async def track(
    request: Request,
    restaurant_id: str = Form(...),
    action: str = Form("click"),
    reward: float = Form(0),
    lat: str = Form(""),
    lng: str = Form(""),
    intent: str = Form(""),
    cuisine: str = Form(""),
    price_min: str = Form(""),
    price_max: str = Form(""),
):
    user_id = _get_user_id(request) or "anonymous"
    def _to_float(val: str):
        if val in ("", None, "None"):
            return None
        try:
            return float(val)
        except ValueError:
            return None
    ctx = {
        "lat": _to_float(lat),
        "lng": _to_float(lng),
        "intent": intent or None,
        "cuisine": cuisine.split(",") if cuisine else None,
        "price_range": {
            "min": _to_float(price_min),
            "max": _to_float(price_max),
        },
    }
    log_interaction(
        user_id=user_id,
        restaurant_id=restaurant_id,
        action=action,
        reward=float(reward),
        context=ctx,
    )
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
