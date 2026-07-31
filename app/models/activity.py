from datetime import datetime, timezone
from app.extensions import db

class ActivityLog(db.Model):
    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    action = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<ActivityLog {self.action} at {self.timestamp}>"

def log_activity(action, description=None):
    """Helper to log an activity event to the database."""
    try:
        log = ActivityLog(action=action, description=description)
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        import logging
        logging.getLogger(__name__).error(f"Failed to log activity: {e}")
