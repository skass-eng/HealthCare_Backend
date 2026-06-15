"""Helper de traçabilité — écrit dans la table audit_logs.

Best-effort : une erreur d'audit ne doit jamais interrompre l'action métier.
"""
import logging
from typing import Optional

from shared.models import AuditLog

logger = logging.getLogger(__name__)


def log_audit(
    db,
    action: str,
    ressource_type: str,
    ressource_id=None,
    *,
    user_id: Optional[int] = None,
    details: Optional[dict] = None,
    donnees_avant: Optional[dict] = None,
    donnees_apres: Optional[dict] = None,
) -> None:
    """Enregistre une entrée d'audit (flush immédiat, sans commit)."""
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            ressource_type=ressource_type,
            ressource_id=ressource_id,
            details=details or {},
            donnees_avant=donnees_avant,
            donnees_apres=donnees_apres,
        )
        db.add(entry)
        db.flush()
    except Exception as e:  # noqa: BLE001 - best-effort, ne jamais casser le métier
        logger.warning(
            f"⚠️ Audit non enregistré ({action} {ressource_type}#{ressource_id}): {e}"
        )


def get_historique(db, ressource_type: str, ressource_id) -> list:
    """Retourne l'historique d'audit d'une ressource, du plus récent au plus ancien."""
    try:
        rows = (
            db.query(AuditLog)
            .filter(
                AuditLog.ressource_type == ressource_type,
                AuditLog.ressource_id == ressource_id,
            )
            .order_by(AuditLog.date_creation.desc())
            .all()
        )
        return [
            {
                "id": r.id,
                "action": r.action,
                "user_id": r.user_id,
                "details": r.details,
                "donnees_avant": r.donnees_avant,
                "donnees_apres": r.donnees_apres,
                "date": r.date_creation.isoformat() if r.date_creation else None,
            }
            for r in rows
        ]
    except Exception as e:  # noqa: BLE001
        logger.warning(f"⚠️ Lecture historique impossible ({ressource_type}#{ressource_id}): {e}")
        return []
