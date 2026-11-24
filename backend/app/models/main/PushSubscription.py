from app.models.base import BaseModel
from sqlalchemy import Column, String, Integer, ForeignKey, Text


class PushSubscription(BaseModel):
    """
    One browser/device that has turned on push notifications for a signed-in user (Web Push).

    Tied to the sign-in session that created it: when that session logs out (or is revoked),
    the device stops getting this user's notifications - important on shared institution computers.
    New table, so the startup create_all() builds it; no migration needed.
    """
    __tablename__ = 'push_subscriptions'

    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    session_token = Column(String(255), nullable=True, index=True)
    endpoint = Column(Text, nullable=False, unique=True)  # the push service URL for this device
    p256dh = Column(String(255), nullable=False)          # device public key (encrypts the message)
    auth = Column(String(255), nullable=False)            # device auth secret
    user_agent = Column(Text, nullable=True)
