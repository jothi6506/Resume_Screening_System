"""Application entry point."""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app import create_app

env_name = os.getenv("FLASK_ENV", "development")
app = create_app(env_name)

if __name__ == "__main__":
    if env_name == "production" or "--production" in sys.argv:
        try:
            from waitress import serve
            print(f"Starting Production WSGI Waitress Server on 0.0.0.0:5000 (Env: {env_name})...")
            serve(app, host="0.0.0.0", port=5000, threads=8)
        except ImportError:
            app.run(host="0.0.0.0", port=5000, debug=False)
    else:
        app.run(host="0.0.0.0", port=5000, debug=app.config.get("DEBUG", False))

