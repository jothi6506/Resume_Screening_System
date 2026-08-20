"""Application entry point."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app import create_app

env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    if env_name == "production" or "--production" in sys.argv:
        try:
            from waitress import serve
            print(f"Starting Production WSGI Server on 0.0.0.0:{port} (Env: {env_name})...")
            serve(app, host="0.0.0.0", port=port, threads=8)
        except ImportError:
            app.run(host="0.0.0.0", port=port, debug=False)
    else:
        app.run(host="0.0.0.0", port=port, debug=app.config.get("DEBUG", False))

