"""
Attendee Model
Students/participants who attended events
"""

from sqlalchemy import Column, String, Integer, DateTime, Date, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from app.database import Base


class Attendee(Base):
    __tablename__ = "attendees"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("certificate_templates.id"), nullable=True)
    
    # Student data
    name = Column(String(200), nullable=False, index=True)
    student_id = Column(String(50), nullable=False, index=True)
    email = Column(String(255), nullable=True)
    course = Column(String(100), nullable=True)
    
    # Event info
    event_name = Column(String(200), nullable=True)
    event_date = Column(Date, nullable=True)
    
    # Certificate generation tracking
    certificate_generated_count = Column(Integer, default=0)
    first_generated_at = Column(DateTime(timezone=True), nullable=True)
    last_generated_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("club_administrators.id"), nullable=True)
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    club = relationship("Club", backref="attendees")
    template = relationship("CertificateTemplate", backref="attendees")
    uploader = relationship("ClubAdministrator", backref="uploaded_attendees")


class CertificateGeneration(Base):
    __tablename__ = "certificate_generations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    club_id = Column(UUID(as_uuid=True), ForeignKey("clubs.id", ondelete="CASCADE"), nullable=False)
    attendee_id = Column(UUID(as_uuid=True), ForeignKey("attendees.id", ondelete="CASCADE"), nullable=False)
    template_id = Column(UUID(as_uuid=True), ForeignKey("certificate_templates.id"), nullable=False)
    
    # Generation info
    certificate_id = Column(String(100), nullable=False, index=True)
    generated_by_user = Column(String(10), default="public")  # 'public' or 'admin'
    ip_address = Column(String(45), nullable=True)
    
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    club = relationship("Club", backref="certificate_generations")
    attendee = relationship("Attendee", backref="generations")
    template = relationship("CertificateTemplate", backref="generations")