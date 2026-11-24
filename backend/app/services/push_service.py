"""
Web Push notifications (installed app / browser notifications).

- Devices register through /api/push (see app/api/push.py); rows live in the main DB (PushSubscription).
- A device is tied to the sign-in session that turned notifications on: logging out stops them,
  and token refresh carries them over to the new session.
- Sending never blocks or breaks the action that caused it: recipients are worked out quickly in the
  caller's tenant session, the actual sending runs in a background thread, and every failure is logged
  and swallowed.
- Messages appear on lock screens, so they never carry marks, fee amounts or other sensitive details.

Config (env): VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY (generate with backend/generate_vapid_keys.py), VAPID_SUBJECT.
Without the keys everything here is a no-op.
"""
import json
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime

from flask import current_app, has_app_context
from sqlalchemy import func

from app import db
from app.models.main.PushSubscription import PushSubscription
from app.models.main.User import User, UserRole
from app.models.main.UserSession import UserSession

_log = logging.getLogger(__name__)

DEFAULT_SUBJECT = "https://dev-sms.klopterz.in"
TTL_SECONDS = 24 * 60 * 60  # a phone that is off for longer than a day doesn't get stale alerts
MAX_TEXT = 140


def _clip(text, limit=MAX_TEXT):
    text = " ".join(str(text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


# ---------------------------------------------------------------- configuration

def public_key():
    return (os.environ.get("VAPID_PUBLIC_KEY") or "").strip()


def is_configured():
    return bool(public_key() and (os.environ.get("VAPID_PRIVATE_KEY") or "").strip())


# ---------------------------------------------------------------- device registration

def subscribe(user, session_token, subscription, user_agent=None):
    """Save (or move to this user) one device's subscription. `subscription` is the browser's PushSubscription JSON."""
    endpoint = str((subscription or {}).get("endpoint") or "").strip()
    keys = (subscription or {}).get("keys") or {}
    p256dh, auth = str(keys.get("p256dh") or "").strip(), str(keys.get("auth") or "").strip()
    if not endpoint.startswith("https://") or not p256dh or not auth:
        raise ValueError("This browser sent an incomplete notification subscription")

    row = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if row is None:
        row = PushSubscription(endpoint=endpoint)
        db.session.add(row)
    # a shared device: whoever turned notifications on last owns it
    row.user_id = user.id
    row.session_token = session_token
    row.p256dh = p256dh
    row.auth = auth
    row.user_agent = (user_agent or "")[:500]
    row.is_active = True
    db.session.commit()
    return row


def unsubscribe(user, endpoint):
    """Turn notifications off for one device of this user."""
    deleted = PushSubscription.query.filter_by(user_id=user.id, endpoint=str(endpoint or "").strip()).delete()
    db.session.commit()
    return deleted


def is_subscribed(user, endpoint):
    return PushSubscription.query.filter_by(
        user_id=user.id, endpoint=str(endpoint or "").strip(), is_active=True
    ).first() is not None


def forget_session(session_token=None, user_id=None):
    """Logout: drop the devices of that session (or, with only user_id, of all the user's sessions)."""
    try:
        query = PushSubscription.query
        if session_token:
            query = query.filter_by(session_token=session_token)
        elif user_id:
            query = query.filter_by(user_id=user_id)
        else:
            return
        query.delete(synchronize_session=False)
        db.session.commit()
    except Exception:  # logout must still succeed
        db.session.rollback()
        _log.exception("Couldn't remove push devices on logout")


def move_session(old_token, new_token):
    """Token refresh rotates the session token: keep the devices on the new one."""
    if not old_token or not new_token or old_token == new_token:
        return
    try:
        PushSubscription.query.filter_by(session_token=old_token).update(
            {"session_token": new_token}, synchronize_session=False
        )
        db.session.commit()
    except Exception:
        db.session.rollback()
        _log.exception("Couldn't move push devices to the refreshed session")


# ---------------------------------------------------------------- recipients (institution records -> login accounts)

def main_user_ids_for(skid, institution_user_ids=None, roles=None):
    """Active login accounts of this institution, by institution_users ids and/or login roles."""
    query = db.session.query(User.id).filter(User.skid == str(skid), User.is_active == True)  # noqa: E712
    if institution_user_ids is not None:
        ids = {int(i) for i in institution_user_ids if i is not None}
        if not ids:
            return set()
        query = query.filter(User.institution_user_id.in_(ids))
    if roles:
        query = query.filter(User.role.in_([UserRole(r) for r in roles]))
    return {row[0] for row in query.all()}


def students_in_sections(tenant_session, section_ids):
    """institution_users ids of students currently in these sections (active enrollment or their section)."""
    from app.models.tenant.Student import Student
    from app.models.tenant.StudentEnrollment import StudentEnrollment

    ids = [int(s) for s in (section_ids or []) if s is not None]
    if not ids:
        return set()
    found = {r[0] for r in tenant_session.query(Student.user_id).filter(Student.section_id.in_(ids)).all()}
    found |= {r[0] for r in tenant_session.query(StudentEnrollment.student_id).filter(
        StudentEnrollment.section_id.in_(ids), func.lower(StudentEnrollment.status) == "active"
    ).all() if r[0]}
    return found


def students_in_classes(tenant_session, class_ids):
    from app.models.tenant.Student import Student

    ids = [int(c) for c in (class_ids or []) if c is not None]
    if not ids:
        return set()
    return {r[0] for r in tenant_session.query(Student.user_id).filter(Student.class_id.in_(ids)).all()}


def all_students(tenant_session):
    from app.models.tenant.Student import Student

    return {r[0] for r in tenant_session.query(Student.user_id).all()}


def parents_of(tenant_session, student_ids):
    """institution_users ids of the parents linked to these students."""
    from app.models.tenant.StudentParent import StudentParent

    ids = [int(s) for s in (student_ids or []) if s is not None]
    if not ids:
        return set()
    return {r[0] for r in tenant_session.query(StudentParent.parent_user_id).filter(
        StudentParent.student_user_id.in_(ids)
    ).all()}


# ---------------------------------------------------------------- sending

def _send_one(sub, payload, urgency):
    """Returns 'gone' when the device no longer exists (uninstalled / permission removed)."""
    from pywebpush import webpush, WebPushException

    try:
        webpush(
            subscription_info={"endpoint": sub["endpoint"], "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]}},
            data=payload,
            vapid_private_key=os.environ.get("VAPID_PRIVATE_KEY", "").strip(),
            vapid_claims={"sub": (os.environ.get("VAPID_SUBJECT") or DEFAULT_SUBJECT).strip()},
            ttl=TTL_SECONDS,
            headers={"Urgency": urgency},
            timeout=10,
        )
        return "sent"
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            return "gone"
        _log.warning("Push to a device failed (%s): %s", status, str(exc)[:200])
        return "failed"
    except Exception as exc:  # network trouble etc.
        _log.warning("Push to a device failed: %s", str(exc)[:200])
        return "failed"


def _deliver(app, user_ids, message, urgency):
    with app.app_context():
        try:
            rows = db.session.query(PushSubscription).join(
                UserSession, UserSession.session_token == PushSubscription.session_token
            ).filter(
                PushSubscription.user_id.in_(list(user_ids)),
                PushSubscription.is_active == True,  # noqa: E712
                UserSession.is_logged_out == False,  # noqa: E712
                UserSession.is_active == True,  # noqa: E712
            ).all()
            subs = [{"id": r.id, "endpoint": r.endpoint, "p256dh": r.p256dh, "auth": r.auth} for r in rows]
            if not subs:
                return
            payload = json.dumps(message)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda s: (s["id"], _send_one(s, payload, urgency)), subs))
            gone = [sid for sid, result in results if result == "gone"]
            if gone:
                PushSubscription.query.filter(PushSubscription.id.in_(gone)).delete(synchronize_session=False)
                db.session.commit()
            _log.info("Push '%s': %d device(s), %d removed", message.get("tag"), len(subs), len(gone))
        except Exception:
            db.session.rollback()
            _log.exception("Sending push notifications failed")
        finally:
            db.session.remove()


def notify(user_ids, title, body, url="/dashboard", tag=None, urgency="normal", exclude_user_id=None):
    """
    Send one notification to these login accounts (main users.id), in the background.
    Safe to call from any request: does nothing without VAPID keys, never raises.
    """
    try:
        if not is_configured() or not has_app_context():
            return
        ids = {int(u) for u in (user_ids or []) if u is not None}
        if exclude_user_id is not None:
            ids.discard(int(exclude_user_id))
        if not ids:
            return
        message = {"title": _clip(title, 80), "body": _clip(body), "url": url or "/dashboard",
                   "tag": tag or f"eduspyre-{datetime.utcnow().timestamp():.0f}"}
        app = current_app._get_current_object()
        threading.Thread(target=_deliver, args=(app, ids, message, urgency), daemon=True).start()
    except Exception:
        _log.exception("Couldn't queue push notifications")


def today():
    return date.today()
