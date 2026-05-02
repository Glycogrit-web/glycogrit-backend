"""
Site Statistics Model
Stores real-time statistics for the home page
"""
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.core.database import Base


class SiteStatistics(Base):
    """
    Model to store site-wide statistics displayed on the home page
    This is a single-row table that gets updated periodically
    """
    __tablename__ = "site_statistics"

    id = Column(Integer, primary_key=True, index=True, default=1)

    # Statistics
    total_users = Column(Integer, nullable=False, default=0, comment="Total active users")
    total_events = Column(Integer, nullable=False, default=0, comment="Total challenges/events")
    total_registrations = Column(Integer, nullable=False, default=0, comment="Total registrations (activities logged)")
    total_medals_shipped = Column(Integer, nullable=False, default=0, comment="Total medals/rewards shipped")

    # Metadata
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by = Column(String, nullable=True, comment="System or admin user who updated")

    def __repr__(self):
        return f"<SiteStatistics(users={self.total_users}, events={self.total_events}, registrations={self.total_registrations}, medals={self.total_medals_shipped})>"
