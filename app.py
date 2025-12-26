from flask import Flask, redirect, url_for
import os
from werkzeug.security import generate_password_hash
from application.config import LocalDevelopmentConfig, DB_PATH
from application.models import db, User
from application.controllers import auth_bp, admin_bp, doctor_bp, patient_bp
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from sqlalchemy.exc import SQLAlchemyError
from application.api import api_bp

app=None
csrf= CSRFProtect()

def create_app():
    app = Flask(__name__, template_folder="Templates", static_folder="static")
    app.config.from_object(LocalDevelopmentConfig)
    app.config['SECRET_KEY']='dev-secret'
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    csrf.init_app(app)

    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir,exist_ok=True)
    
    db.init_app(app)

   
    with app.app_context():
        db.create_all()
        _ensure_default_admin()

    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    
    @login_manager.user_loader
    def load_user(user_id):
        try:
            return db.session.get(User, int(user_id))
        except SQLAlchemyError:
            return None
    
    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(doctor_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(api_bp) # Register API blueprint

    @app.context_processor
    def inject_csrf():
        return dict(csrf_token=generate_csrf)

    @app.route("/")
    def home():
        return redirect(url_for('auth.index'))

    return app


def _ensure_default_admin():
    admin_email = "admin@example.com"
    admin = User.query.filter_by(email=admin_email, role="admin").first()
    if not admin:
        admin = User(
            name="Admin",
            email=admin_email,
            password_hash=generate_password_hash("Admin@123"),
            role="admin",
            is_active=True,
        )
        db.session.add(admin)
        db.session.commit()


if __name__ == "__main__":
    app = create_app()
    app.run(debug=False)