"""
Database Models
Import all models here for Alembic migrations
"""

from app.models.club import Club
from app.models.admin import PlatformAdmin, ClubAdministrator
from app.models.template import CertificateTemplate
from app.models.attendee import Attendee, CertificateGeneration

__all__ = [
    "Club",
    "PlatformAdmin",
    "ClubAdministrator",
    "CertificateTemplate",
    "Attendee",
    "CertificateGeneration",
]
# ```

# **Save the file**

# ---

## ✅ CHECKPOINT 4

# You've created all the database models!

# **File structure now:**
# ```
# app/models/
# ├── __init__.py        ✅
# ├── admin.py           ✅
# ├── attendee.py        ✅
# ├── club.py            ✅
# └── template.py        ✅