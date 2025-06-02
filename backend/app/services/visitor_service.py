from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from app.models.database import Visitor


class VisitorService:
    @staticmethod
    def get_or_create_visitor(
        db: Session,
        fingerprint_id: str,
        user_agent_raw: Optional[str] = None,
        ip_address_hash: Optional[str] = None,
    ) -> Tuple[Visitor, bool]:
        """Get or create a visitor record.

        Args:
            db (Session): Database session for executing queries
            fingerprint_id (str): Unique browser fingerprint ID
            user_agent_raw (Optional[str], optional): Raw user agent string. Defaults to None.
            ip_address_hash (Optional[str], optional): Hashed IP address. Defaults to None.

        Returns:
            Tuple[Visitor, bool]: The visitor record and a boolean indicating if it was created (True) or fetched (False).
        """

        visitor = (
            db.query(Visitor)
            .filter(Visitor.fingerprint_id == fingerprint_id)
            .first()
        )

        if visitor:
            # Update last seen
            visitor.last_seen_at = datetime.now(timezone.utc)
            db.commit()
            return visitor, False

        now = datetime.now(timezone.utc)
        visitor = Visitor(
            fingerprint_id=fingerprint_id,
            first_seen_at=now,
            last_seen_at=now,
            user_agent_raw=user_agent_raw,
            ip_address_hash=ip_address_hash,
        )
        try:
            db.add(visitor)
            db.commit()
            db.refresh(visitor)
            return visitor, True
        except IntegrityError:
            db.rollback()
            visitor = (
                db.query(Visitor)
                .filter(Visitor.fingerprint_id == fingerprint_id)
                .first()
            )
            if visitor:
                return visitor, False
            else:
                raise RuntimeError(
                    "Failed to create visitor and could not find existing one."
                )

    @staticmethod
    def update_visitor_data(
        visitor: Visitor, profile_data: dict, db: Session
    ) -> None:
        """Update visitor profile data extracted from chat messages.
        Args:
            visitor (Visitor): The visitor record to update
            profile_data (dict): Profile data to update
            db (Session): Database session for executing queries
        """
        if visitor.profile_data:
            visitor.profile_data.update(profile_data)
        else:
            visitor.profile_data = profile_data
        db.commit()

    @staticmethod
    def update_agent_notes(visitor: Visitor, notes: str, db: Session) -> None:
        """Update notes by agent for a visitor.

        Args:
            visitor (Visitor): The visitor record to update
            notes (str): Notes to update
            db (Session): Database session for executing queries
        """
        if visitor.notes_by_agent:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            visitor.notes_by_agent += f"\n\n[{timestamp}] {notes}"
        else:
            visitor.notes_by_agent = notes
        db.commit()
