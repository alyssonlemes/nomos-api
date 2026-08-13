from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Table, Date, Time, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


# Association table: activity_participants (many-to-many)
activity_participants = Table(
    "activity_participants",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("activity_id", Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False),
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
    Column("role", String(32), nullable=True),
    UniqueConstraint("activity_id", "user_id", name="uq_activity_participants"),
)


class Activity(Base):
    """
    Atividades unificadas (tarefas + eventos).
    Type: 'task' ou 'event'
    Status padrão: 'todo', 'in_progress', 'done'
    Priority: 'low', 'medium', 'high', 'critical'
    """
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(32), nullable=False)  # 'task' or 'event'
    
    responsible_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    priority = Column(String(32), default="medium", nullable=False)
    status = Column(String(32), default="todo", nullable=False)
    
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    
    # Event-specific
    event_time = Column(Time, nullable=True)
    location_or_link = Column(String, nullable=True)
    
    # Task-specific
    estimated_hours = Column(Integer, nullable=True)
    
    # Common
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    observations = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    responsible = relationship("User", foreign_keys=[responsible_id], backref="activities_responsible")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    participants = relationship(
        "User",
        secondary=activity_participants,
        backref="activities_participating",
        primaryjoin="Activity.id==activity_participants.c.activity_id",
        secondaryjoin="activity_participants.c.user_id==User.id",
        foreign_keys=[activity_participants.c.activity_id, activity_participants.c.user_id],
    )
    
    comments = relationship("ActivityComment", back_populates="activity", cascade="all, delete-orphan")
    history = relationship("ActivityHistory", back_populates="activity", cascade="all, delete-orphan")
    attachments = relationship("ActivityAttachment", back_populates="activity", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Activity(id={self.id}, title='{self.title}', type='{self.type}', status='{self.status}')>"


class ActivityComment(Base):
    """Comentários em atividades"""
    __tablename__ = "activity_comments"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    content = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    activity = relationship("Activity", back_populates="comments")
    author = relationship("User", foreign_keys=[author_id])
    
    def __repr__(self):
        return f"<ActivityComment(id={self.id}, activity_id={self.activity_id})>"


class ActivityHistory(Base):
    """Histórico de movimentações/alterações"""
    __tablename__ = "activity_history"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    field_changed = Column(String, nullable=False)  # 'status', 'priority', 'responsible', etc
    old_value = Column(String, nullable=True)
    new_value = Column(String, nullable=True)
    
    changed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    activity = relationship("Activity", back_populates="history")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    
    def __repr__(self):
        return f"<ActivityHistory(id={self.id}, field='{self.field_changed}')>"


class ActivityAttachment(Base):
    """Arquivos/anexos de atividades"""
    __tablename__ = "activity_attachments"

    id = Column(Integer, primary_key=True, index=True)
    activity_id = Column(Integer, ForeignKey("activities.id", ondelete="CASCADE"), nullable=False)
    
    file_url = Column(String, nullable=False)
    file_name = Column(String, nullable=True)
    uploaded_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    activity = relationship("Activity", back_populates="attachments")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    
    def __repr__(self):
        return f"<ActivityAttachment(id={self.id}, file_name='{self.file_name}')>"


class ActivityColumn(Base):
    """Colunas customizáveis do Kanban (permite organizar por status ou custom)"""
    __tablename__ = "activity_columns"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    
    name = Column(String, nullable=False)
    status = Column(String(50), nullable=True, index=True)  # Status da atividade que essa coluna representa
    order_index = Column(Integer, nullable=False)
    color = Column(String, nullable=True)
    is_default = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    def __repr__(self):
        return f"<ActivityColumn(id={self.id}, name='{self.name}')>"


# ORM wrapper for activity_participants table
class ActivityParticipant(Base):
    __table__ = activity_participants
    
    # Relationships
    activity = relationship("Activity", foreign_keys=[activity_participants.c.activity_id], overlaps="activities_participating,participants")
    user = relationship("User", foreign_keys=[activity_participants.c.user_id], overlaps="activities_participating,participants")
