from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# Association table entre meetings e users
meeting_participants = Table(
    "meeting_participants",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("meeting_id", Integer, ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("status", String(32), nullable=False, server_default="pending"),
    Column("accepted_at", DateTime(timezone=True), nullable=True),
    Column("reason", Text, nullable=True),
    Column("responded_by_id", Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
    Column("invite_token", String(128), nullable=True),
)


class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    start_at = Column(DateTime(timezone=True), nullable=False)
    end_at = Column(DateTime(timezone=True), nullable=False)

    organization = relationship("Organization", foreign_keys=[organization_id], backref="meetings")
    created_by = relationship("User", foreign_keys=[created_by_id])

    participants = relationship(
        "User",
        secondary=meeting_participants,
        primaryjoin="Meeting.id==meeting_participants.c.meeting_id",
        secondaryjoin="meeting_participants.c.user_id==User.id",
        foreign_keys=[meeting_participants.c.meeting_id, meeting_participants.c.user_id],
        backref="meetings_participating",
    )
    # association objects (with status/reason)
    participant_links = relationship("MeetingParticipant", back_populates="meeting", cascade="all, delete-orphan")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    requires_acceptance = Column(Boolean, default=False, nullable=False)
    status = Column(String(32), default="scheduled", nullable=False)

    def __repr__(self):
        return f"<Meeting(id={self.id}, title='{self.title}', start_at={self.start_at}, end_at={self.end_at})>"


class MeetingParticipant(Base):
    __table__ = meeting_participants

    # convenience relationships
    meeting = relationship("Meeting", back_populates="participant_links")
    user = relationship("User", foreign_keys=[meeting_participants.c.user_id])
    responded_by = relationship("User", foreign_keys=[meeting_participants.c.responded_by_id])
