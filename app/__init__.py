import os
from flask import Flask
from config import Config
from app.models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure instance folder exists for SQLite
    instance_path = os.path.join(app.root_path, "..", "instance")
    os.makedirs(instance_path, exist_ok=True)

    db.init_app(app)

    from app.routes.main import main_bp
    from app.routes.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        db.create_all()

    return app
