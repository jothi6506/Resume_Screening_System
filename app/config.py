import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Uploads
    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER", "uploads/resumes")
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))
    ALLOWED_EXTENSIONS = {"pdf", "doc", "docx", "png", "jpg", "jpeg"}

    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    REMEMBER_COOKIE_DURATION = timedelta(days=14)

    # Future AI integration hooks
    AI_ENABLED = os.environ.get("AI_ENABLED", "true").lower() == "true"
    OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

    # Gmail SMTP Email
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 465))
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", "")


def _fix_db_url(url):
    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "instance"))
    os.makedirs(db_dir, exist_ok=True)
    sqlite_path = os.path.join(db_dir, "app.db").replace("\\", "/")
    fallback_uri = f"sqlite:///{sqlite_path}"

    if not url:
        return fallback_uri
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)

    if "mysql" in url and ("localhost" in url or "127.0.0.1" in url):
        try:
            import socket
            s = socket.create_connection(("127.0.0.1", 3306), timeout=1)
            s.close()
        except Exception:
            return fallback_uri

    return url






class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = _fix_db_url(
        os.environ.get(
            "DATABASE_URL",
            "mysql+pymysql://root:Root%40123@localhost:3306/resume_screening",
        )
    )


DEFAULT_CLOUD_DB = "mysql+pymysql://33AzvaX9rmmawum.root:7cbJrwDIjKnqXU7H@gateway01.ap-southeast-1.prod.aws.tidbcloud.com:4000/test?ssl=true&ssl_verify_cert=false"


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = _fix_db_url(os.environ.get("DATABASE_URL", DEFAULT_CLOUD_DB))

    @classmethod
    def init_app(cls, app):
        pass



class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}

