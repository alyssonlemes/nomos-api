from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel

from app.api.deps import get_db, get_current_user
from app.schemas.meeting import (
    MeetingCreate,
    MeetingResponse,
    MeetingListResponse,
    MeetingPreviewRequest,
    MeetingConflictResponse,
    ConflictParticipant,
)
from app.models.meeting import MeetingParticipant, Meeting
from app.models.user import User
from app.schemas.meeting import MeetingParticipantBase

router = APIRouter()


def meetings_overlap(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return (start_a < end_b) and (end_a > start_b)


@router.post("/preview", response_model=list[MeetingConflictResponse])
def preview_conflicts(payload: MeetingPreviewRequest, db: Session = Depends(get_db)):
    """
    Retorna reuniões conflitantes para os participantes informados (preview).
    """
    start_at = payload.start_at
    end_at = payload.end_at

    # Buscar reuniões que se sobrepõem para os participantes
    conflicts = (
        db.query(Meeting)
        .join(Meeting.participants)
        .filter(
            User.id.in_(payload.participant_ids),
            Meeting.start_at < end_at,
            Meeting.end_at > start_at,
        )
        .all()
    )

    result: list[MeetingConflictResponse] = []
    for m in conflicts:
        conflict_participants = [
            ConflictParticipant(id=p.id, full_name=p.full_name, email=p.email)
            for p in m.participants
            if p.id in payload.participant_ids
        ]
        if conflict_participants and meetings_overlap(m.start_at, m.end_at, start_at, end_at):
            result.append(
                MeetingConflictResponse(
                    id=m.id,
                    title=m.title,
                    start_at=m.start_at,
                    end_at=m.end_at,
                    participants=conflict_participants,
                )
            )

    return result


@router.post("/", response_model=MeetingResponse, status_code=status.HTTP_201_CREATED)
def create_meeting(meeting_in: MeetingCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Validar intervalo
    if meeting_in.start_at >= meeting_in.end_at:
        raise HTTPException(status_code=400, detail="Intervalo inválido: start_at deve ser antes de end_at")

    # Verificar conflitos
    conflicts = (
        db.query(Meeting)
        .join(Meeting.participants)
        .filter(
            User.id.in_(meeting_in.participant_ids),
            Meeting.start_at < meeting_in.end_at,
            Meeting.end_at > meeting_in.start_at,
        )
        .all()
    )

    if conflicts:
        details = []
        for conflict in conflicts:
            participants = [
                ConflictParticipant(id=p.id, full_name=p.full_name, email=p.email)
                for p in conflict.participants
                if p.id in meeting_in.participant_ids
            ]
            details.append(
                MeetingConflictResponse(
                    id=conflict.id,
                    title=conflict.title,
                    start_at=conflict.start_at,
                    end_at=conflict.end_at,
                    participants=participants,
                ).model_dump(mode="json")
            )
        raise HTTPException(
            status_code=409,
            detail={
                "message": "Conflitos detectados",
                "conflicts": details,
            },
        )

    # Criar reunião
    meeting = Meeting(
        title=meeting_in.title,
        description=meeting_in.description,
        organization_id=meeting_in.organization_id,
        created_by_id=current_user.id,
        start_at=meeting_in.start_at,
        end_at=meeting_in.end_at,
        requires_acceptance=bool(meeting_in.requires_acceptance),
        status=("pending_confirmation" if meeting_in.requires_acceptance else "scheduled"),
    )

    db.add(meeting)
    db.flush()

    # Adicionar participantes como links (status pending), auto-accept organizer
    users = db.query(User).filter(User.id.in_(meeting_in.participant_ids)).all()
    for u in users:
        status_val = "accepted" if u.id == current_user.id or not meeting_in.requires_acceptance else "pending"
        mp = MeetingParticipant(meeting_id=meeting.id, user_id=u.id, status=status_val, accepted_at=(datetime.utcnow() if status_val == "accepted" else None))
        db.add(mp)

    db.commit()
    db.refresh(meeting)

    # If not requiring acceptance, mark meeting as confirmed
    if not meeting.requires_acceptance:
        meeting.status = "confirmed"
        db.add(meeting)
        db.commit()

    return meeting



@router.post("/{meeting_id}/accept")
def accept_meeting(meeting_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mp = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting_id,
        MeetingParticipant.user_id == current_user.id,
    ).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Participante não encontrado para esta reunião")
    mp.status = "accepted"
    mp.accepted_at = datetime.utcnow()
    mp.responded_by_id = current_user.id
    db.add(mp)

    # Re-evaluate meeting status
    remaining = db.query(MeetingParticipant).filter(MeetingParticipant.meeting_id == meeting_id).all()
    all_accepted = all((r.status == "accepted") for r in remaining)
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if all_accepted:
        meeting.status = "confirmed"
        db.add(meeting)

    db.commit()
    return {"message": "accepted"}


class DeclineRequest(BaseModel):
    reason: str


@router.post("/{meeting_id}/decline")
def decline_meeting(meeting_id: int, payload: DeclineRequest = Body(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    mp = db.query(MeetingParticipant).filter(
        MeetingParticipant.meeting_id == meeting_id,
        MeetingParticipant.user_id == current_user.id,
    ).first()
    if not mp:
        raise HTTPException(status_code=404, detail="Participante não encontrado para esta reunião")
    mp.status = "declined"
    mp.reason = payload.reason
    mp.responded_by_id = current_user.id
    db.add(mp)

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    meeting.status = "cancelled"
    db.add(meeting)
    db.commit()

    return {"message": "declined", "declined_by": current_user.id, "reason": payload.reason}


@router.get("/", response_model=MeetingListResponse)
def list_meetings(user_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Meeting)
    if user_id:
        q = q.join(Meeting.participants).filter(User.id == user_id)

    meetings = q.order_by(Meeting.start_at.desc()).all()
    return {"total": len(meetings), "meetings": meetings}
