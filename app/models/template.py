"""
Certificate Template Model
Stores template configurations for each club
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class CertificateTemplate(Base):
    __tablename__ = "certificate_templates"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    
    # Template info
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    event_name = Column(String(200), nullable=True)
    template_image_url = Column(Text, nullable=False)
    
    # Text field coordinates (JSON)
    text_fields = Column(JSONB, nullable=False, default=[])
    
    # Version
    version = Column(Integer, default=1)
    
    # Metadata
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("club_administrators.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    club = relationship("Club", backref="templates")
    creator = relationship("ClubAdministrator", backref="created_templates")