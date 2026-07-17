"""Firebase Cloud Messaging (FCM) and Local Notification dispatch helper."""

import os
from sqlalchemy.orm import Session
from app.models.notification import Notification

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None

# Initialize Firebase App if credential path exists
firebase_initialized = False
cred_path = os.getenv("FIREBASE_CREDENTIALS", "firebase.json")

if firebase_admin and cred_path and os.path.exists(cred_path):
    try:
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
        firebase_initialized = True
        print("Firebase Admin successfully initialized.")
    except Exception as e:
        print(f"Error initializing Firebase Admin: {e}")


def dispatch_notification(
    db: Session,
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    device_token: str = None,
    request_id: int = None
) -> dict:
    """
    Saves the notification to the local database, and attempts to send a push notification via Firebase.
    """
    # 1. Save to local database
    db_notif = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type=notification_type,
        is_read=False,
        request_id=request_id
    )
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)

    result = {
        "notification_id": db_notif.id,
        "database_status": "saved",
        "push_status": "skipped"
    }

    # 2. Try sending push notification
    if firebase_initialized and device_token and messaging:
        try:
            payload = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=message
                ),
                token=device_token
            )
            response = messaging.send(payload)
            result["push_status"] = f"sent:{response}"
        except Exception as ex:
            result["push_status"] = f"error:{str(ex)}"
            print(f"FCM Send Error: {ex}")
    else:
        if device_token:
            result["push_status"] = "firebase_not_configured"

    return result
