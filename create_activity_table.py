from app import create_app
from app.extensions import db
from app.models.activity import ActivityLog

app = create_app()
with app.app_context():
    ActivityLog.__table__.create(db.engine, checkfirst=True)
    print("ActivityLog table created!")
