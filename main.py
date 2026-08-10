"""
AI Business Twin — Application Server
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.routes.auth import router as auth_router
from app.routes.business import router as business_router
from app.routes.data import router as data_router
from app.routes.analytics import router as analytics_router
from app.routes.ai import router as ai_router

# Create tables on startup
from app.database import engine, Base
from app.models import User, Business, DatasetJob, Sales, Inventory, Expenses
Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Business Twin")

# --- Static files & templates (landing page) ---
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# --- API routers ---
app.include_router(auth_router)
app.include_router(business_router)
app.include_router(data_router)
app.include_router(analytics_router)
app.include_router(ai_router)


@app.get("/", response_class=HTMLResponse)
async def landing_page(request: Request):
    """Serve the landing page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Serve the login page."""
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    """Serve the register page."""
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/setup", response_class=HTMLResponse)
async def setup_page(request: Request):
    """Serve the business setup page."""
    return templates.TemplateResponse("setup.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Serve the dashboard page (auth check is client-side via JWT)."""
    return templates.TemplateResponse("dashboard.html", {"request": request})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    """Serve the data upload page."""
    return templates.TemplateResponse("upload.html", {"request": request})


@app.get("/validate", response_class=HTMLResponse)
async def validate_page(request: Request):
    """Serve the data validation page."""
    return templates.TemplateResponse("validate.html", {"request": request})


@app.get("/assistant", response_class=HTMLResponse)
async def assistant_page(request: Request):
    """Serve the AI assistant page."""
    return templates.TemplateResponse("assistant.html", {"request": request})


@app.get("/whatif", response_class=HTMLResponse)
async def whatif_page(request: Request):
    """Serve the what-if scenario page."""
    return templates.TemplateResponse("whatif.html", {"request": request})
