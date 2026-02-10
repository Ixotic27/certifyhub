"""
FastAPI Application Entry Point
Main application setup and route registration
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.config import settings
from app.database import connect_db, disconnect_db
import os


class NoCacheMiddleware(BaseHTTPMiddleware):
    """Prevent browser from caching HTML pages"""
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        ct = response.headers.get("content-type", "")
        if "text/html" in ct:
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-tenant certificate distribution platform",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# No-cache middleware for HTML pages
app.add_middleware(NoCacheMiddleware)

# Custom 404 error handler - show friendly page instead of raw JSON
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    # If client expects JSON (API call), return JSON
    accept = request.headers.get("accept", "")
    if "application/json" in accept or request.url.path.startswith(("/auth/", "/admin/", "/platform/")) and request.method != "GET":
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    # Otherwise show a friendly HTML page
    return HTMLResponse(
        status_code=404,
        content="""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Page Not Found - CertifyHub</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:radial-gradient(120% 120% at 50% 10%,#1f2347 0%,#12142b 45%,#0b0d1f 100%);min-height:100vh;display:flex;align-items:center;justify-content:center;color:#e6e9ff;font-family:'Segoe UI',sans-serif;}</style>
</head><body>
<div class="text-center">
<h1 style="font-size:5rem;font-weight:700;background:linear-gradient(135deg,#667eea,#764ba2);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">404</h1>
<h3 class="mb-3">Page Not Found</h3>
<p class="text-secondary mb-4">The page you're looking for doesn't exist or has been moved.</p>
<div class="d-flex gap-3 justify-content-center">
<a href="/login" class="btn btn-outline-light"><i class="fas fa-sign-in-alt"></i> Go to Login</a>
<a href="/" class="btn btn-outline-secondary"><i class="fas fa-home"></i> Home</a>
</div></div></body></html>"""
    )

# Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")
templates.env.auto_reload = True

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Startup event
@app.on_event("startup")
async def startup():
    """Run on application startup"""
    await connect_db()
    print(f"[START] {settings.APP_NAME} started in {settings.APP_ENV} mode")


# Shutdown event
@app.on_event("shutdown")
async def shutdown():
    """Run on application shutdown"""
    print("[DEBUG] Shutdown event triggered")
    await disconnect_db()
    print("[DEBUG] Shutdown complete")


# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": "1.0.0"
    }


# HTML Page Routes
@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    """Home page - student certificate retrieval"""
    return templates.TemplateResponse("home.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Login page"""
    return templates.TemplateResponse("login_new.html", {"request": request})


@app.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Force password reset page for first-time login"""
    return templates.TemplateResponse("reset_password.html", {"request": request})


@app.get("/certificate-generator", response_class=HTMLResponse)
async def certificate_generator_page(request: Request):
    """Certificate generator page for students"""
    return templates.TemplateResponse("certificate_generator.html", {"request": request})


@app.get("/platform/dashboard", response_class=HTMLResponse)
async def platform_dashboard_page(request: Request):
    """Platform admin dashboard page"""
    return templates.TemplateResponse("platform_dashboard.html", {"request": request})


@app.get("/platform/ui/clubs", response_class=HTMLResponse)
async def platform_clubs_page(request: Request):
    """Platform clubs management page"""
    return templates.TemplateResponse("platform_clubs.html", {"request": request})


@app.get("/platform/ui/admins", response_class=HTMLResponse)
async def platform_admins_page(request: Request):
    """Platform club admins page"""
    return templates.TemplateResponse("platform_admins.html", {"request": request})


@app.get("/platform/ui/analytics", response_class=HTMLResponse)
async def platform_analytics_page(request: Request):
    """Platform analytics page"""
    return templates.TemplateResponse("platform_analytics.html", {"request": request})


@app.get("/platform/ui/resources", response_class=HTMLResponse)
async def platform_resources_page(request: Request):
    """Platform resources management page"""
    return templates.TemplateResponse("platform_resources.html", {"request": request})


@app.get("/platform/ui/platform-admins", response_class=HTMLResponse)
async def platform_manage_admins_page(request: Request):
    """Platform admin management page"""
    return templates.TemplateResponse("platform_manage_admins.html", {"request": request})


@app.get("/admin/ui/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    """Dashboard page"""
    return templates.TemplateResponse("admin/dashboard.html", {"request": request})


@app.get("/admin/ui/templates", response_class=HTMLResponse)
async def templates_page(request: Request):
    """Templates list page"""
    return templates.TemplateResponse("admin/templates.html", {"request": request})


@app.get("/admin/ui/templates/create", response_class=HTMLResponse)
async def template_create_page(request: Request):
    """Template creator page"""
    return templates.TemplateResponse("admin/templates_create.html", {"request": request})


@app.get("/admin/ui/attendee-lists", response_class=HTMLResponse)
async def attendee_lists_page(request: Request):
    """Attendee lists (CSV imports) page"""
    return templates.TemplateResponse("admin/attendee_lists.html", {"request": request})


@app.get("/admin/ui/attendees", response_class=HTMLResponse)
async def attendees_page(request: Request):
    """Attendees list page"""
    return templates.TemplateResponse("admin/attendees.html", {"request": request})


@app.get("/admin/ui/attendees/upload", response_class=HTMLResponse)
async def attendees_upload_page(request: Request):
    """Attendees upload page"""
    return templates.TemplateResponse("admin/attendees_upload.html", {"request": request})


@app.get("/admin/ui/activity-logs", response_class=HTMLResponse)
async def activity_logs_page(request: Request):
    """Activity logs page"""
    return templates.TemplateResponse("admin/activity_logs.html", {"request": request})


@app.get("/admin/ui/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    """Settings page"""
    return templates.TemplateResponse("admin/settings.html", {"request": request})


# Import and include routers
from app.routes import auth, platform, admin, public

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(platform.router, prefix="/platform", tags=["Platform Admin"])
app.include_router(admin.router, prefix="/admin", tags=["Club Admin"])
app.include_router(public.router, tags=["Public"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )