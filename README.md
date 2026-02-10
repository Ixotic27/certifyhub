# CertifyHub

A full-featured **certificate generation and management platform** built with FastAPI. Designed for clubs, organizations, and institutions to create, distribute, and verify certificates for events, workshops, courses, and more.

## Features

- **Multi-Club Support** — Each club gets its own isolated workspace with admins, templates, attendees, and certificates
- **CSV Bulk Import** — Upload attendee lists via CSV with flexible column name mapping
- **Template Builder** — Upload certificate background images and configure text placement (name, event, date, etc.)
- **Certificate Generation** — Generate PDF certificates for individual attendees or entire batches
- **Public Verification** — Anyone can verify a certificate's authenticity via a public link
- **Public Certificate Pages** — Each club gets a branded `/club-slug` page to list and download certificates
- **Storage Management** — Supabase Storage integration with per-club usage tracking and 100 MB quota
- **Platform Admin Panel** — Super admin dashboard to manage all clubs, administrators, and analytics
- **Club Admin Panel** — Per-club dashboard with attendee management, template management, and certificate generation
- **Force Password Reset** — First-time club admins must change their temporary password on login
- **Activity Logging** — Track certificate generation and admin actions

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.10+, FastAPI |
| Database | PostgreSQL |
| ORM / Migrations | SQLAlchemy + Alembic |
| Async DB | `databases` + `asyncpg` |
| File Storage | Supabase Storage |
| Auth | JWT (python-jose) + bcrypt |
| Image Processing | Pillow |
| PDF Generation | img2pdf |
| Frontend | Bootstrap 5, Vanilla JS, Jinja2 templates |
| Email | aiosmtplib (optional) |

## Project Structure

```
certifyhub/
├── app/
│   ├── main.py              # FastAPI app, routes, startup/shutdown
│   ├── config.py             # Settings from .env
│   ├── database.py           # Async DB connection
│   ├── auth/                 # Auth utilities (JWT, hashing)
│   ├── models/               # SQLAlchemy models
│   ├── schemas/              # Pydantic schemas
│   ├── routes/
│   │   ├── auth.py           # Login, password change
│   │   ├── admin.py          # Club admin API endpoints
│   │   ├── platform.py       # Platform admin API endpoints
│   │   └── public.py         # Public certificate verification & download
│   ├── services/             # Business logic layer
│   │   ├── admin_service.py
│   │   ├── attendee_service.py
│   │   ├── certificate_service.py
│   │   ├── club_service.py
│   │   ├── csv_parser.py
│   │   ├── storage_service.py
│   │   └── template_service.py
│   └── utils/                # Helpers
├── templates/                # Jinja2 HTML templates
│   ├── admin/                # Club admin pages
│   ├── platform_admin/       # Platform admin pages
│   └── public/               # Public-facing pages
├── static/                   # CSS, JS, images
├── alembic/                  # Database migrations
├── scripts/                  # Setup & utility scripts
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Prerequisites

- **Python 3.10+**
- **PostgreSQL 14+**
- **Supabase account** (for file storage) — [supabase.com](https://supabase.com)

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ixotic27/certifyhub.git
cd certifyhub
```

### 2. Create a virtual environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your values:

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Supabase PostgreSQL connection string (get from Supabase Dashboard > Settings > Database > Connection string) |
| `SECRET_KEY` | Random string (min 32 chars) for app security |
| `JWT_SECRET_KEY` | Random string (min 32 chars) for JWT tokens |
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase **service_role** key (not anon key) |
| `STORAGE_BUCKET` | Supabase storage bucket name (default: `certifyhub`) |

### 5. Set up the database

Create the PostgreSQL database:

```bash
python scripts/create_database.py
```

Run migrations:

```bash
alembic upgrade head
```

### 6. Create a Platform Admin

```bash
python scripts/create_platform_admin.py
```

Follow the prompts to set up your super admin email and password.

### 7. Set up Supabase Storage

1. Go to your [Supabase Dashboard](https://supabase.com/dashboard) → Storage
2. Create a new **public** bucket named `certifyhub`
3. Add storage policies to allow read/write via service role key

## Running the Application

### Development

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

The app will be available at **http://127.0.0.1:8001**

### Key URLs

| URL | Description |
|-----|-------------|
| `/login` | Login page (club admins & platform admin) |
| `/platform/dashboard` | Platform admin dashboard |
| `/admin/dashboard` | Club admin dashboard |
| `/{club-slug}` | Public certificate page for a club |
| `/certificate/verify` | Public certificate verification |

## Usage

### Platform Admin Workflow

1. **Login** at `/login` with your platform admin credentials
2. **Create Clubs** from the Manage Clubs page
3. **Add Club Admins** — each club can have multiple administrators
4. Share the login credentials with club admins (they'll be forced to change the password on first login)

### Club Admin Workflow

1. **Login** at `/login` → change temporary password on first login
2. **Upload a certificate template** — background image with text field positioning
3. **Import attendees** — upload a CSV file with student details
4. **Generate certificates** — individual or bulk generation
5. **Share** — attendees can verify and download certificates from the public club page

## API Documentation

Once the server is running, visit:

- **Swagger UI**: http://127.0.0.1:8001/docs
- **ReDoc**: http://127.0.0.1:8001/redoc

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/create_database.py` | Create the PostgreSQL database |
| `scripts/create_platform_admin.py` | Create a platform super admin account |
| `scripts/seed_club_admin.py` | Seed a test club with an admin |
| `scripts/check_tables.py` | Verify database tables exist |
| `scripts/reset_alembic.py` | Reset Alembic migration state |

## License

This project is for educational and organizational use.
