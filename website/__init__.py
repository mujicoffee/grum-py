from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, redirect, url_for, flash, request, session as flask_session, abort, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, current_user, logout_user
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config
from datetime import timedelta

# Initialise SQLAlchemy, CSRFProtect, Flask-Mail, and Bcrypt
db = SQLAlchemy()
csrf = CSRFProtect()
mail = Mail()
bcrypt = Bcrypt()
scheduler = BackgroundScheduler()

def create_app():
    # Create a Flask app instance
    app = Flask(__name__)
    # Load the configuration from Config class
    app.config.from_object(Config)

    app.config.update(
        SESSION_COOKIE_SAMESITE='Strict',  # Options: 'Lax', 'Strict', or 'None'
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,     # Ensure cookies are only sent over HTTPS (recommended)
    )

    # Initialise SQLAlchemy, CSRFProtect, Flask-Mail and Bcrypt with the app
    db.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)

    # Initialize and start the APScheduler here
    scheduler.start()

    #Initialize Flask-Limiter
    limiter = Limiter(
        key_func=get_remote_address,  # Use the IP address for rate limiting
        app=app,
        default_limits=["30 per minute"]  # Set a default limit for all routes for each user
        # default_limits=["100 per minute"]  # This was the deafult given
    )

    app.extensions['limiter'] = limiter  # Store limiter in app's extensions
    
    # Import the auth, admin, staff, and student blueprint
    from .auth import auth
    from .admin import admin
    from .staff import staff
    from .student import student

    # Register the auth, admin, staff, and student blueprint
    app.register_blueprint(auth, url_prefix='/')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(staff, url_prefix='/staff')
    app.register_blueprint(student, url_prefix='/student')

    # Create a login manager instance
    login_manager = LoginManager()
    # Set the default login view
    login_manager.login_view = 'auth.login'
    # Use strong session protection
    login_manager.session_protection = 'strong'
    # Initialise the login manager with the app
    login_manager.init_app(app)

    # Handle unauthorised access to authenticated pages
    @login_manager.unauthorized_handler
    def unauthorized_callback():
        flash('Please login to access this page.', category='danger')
        return redirect(url_for('auth.login'))
    
    # Import the User model
    from .models import User

    # Query the database for a user with the given id
    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    @app.before_request
    def check_ip():
        ip = request.remote_addr
        if ip in app.config['BLACKLISTED_IPS']:
            abort(403)  # Forbidden
        if app.config['WHITELISTED_IPS'] and ip not in app.config['WHITELISTED_IPS']:
            abort(403)  # Forbidden

    def check_session_token():
        if current_user.is_authenticated:
            session_token = flask_session.get('session_token')

            if request.path.startswith('/admin') and current_user.role == 'student':
                flash("Unauthorised access", category='danger')
                return redirect(url_for('student.dashboard'))
            if request.path.startswith('/admin') and current_user.role == 'staff':
                flash("Unauthorised access", category='danger')
                return redirect(url_for('staff.classroom'))
            if request.path.startswith('/staff') and current_user.role == 'student':
                flash("Unauthorised access", category='danger')
                return redirect(url_for('student.dashboard'))
            if request.path.startswith('/staff') and current_user.role == 'admin':
                flash("Unauthorised access", category='danger')
                return redirect(url_for('admin.dashboard'))
            if request.path.startswith('/student') and current_user.role == 'admin':
                flash("Unauthorised access", category='danger')
                return redirect(url_for('admin.dashboard'))
            if request.path.startswith('/student') and current_user.role == 'staff':
                flash("Unauthorised access", category='danger')
                return redirect(url_for('staff.classroom'))
            
            if not session_token or session_token != current_user.session_token:
                logout_user()
                flash('Your session has expired or is invalid.', category='danger')
                return redirect(url_for('auth.login'))
            
        if current_user.is_active == "No":
            logout_user()
            flash('Your session has been closed.', category='danger')
            return redirect(url_for('auth.login'))
            
    # Ensure responses are not cached
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        return response
    
    # Error handler for 404 Page Not Found
    @app.errorhandler(404)
    def page_not_found(e):
        if current_user.is_authenticated and current_user.session_token:
            if current_user.role == 'student':
                flash("Unknown Page", category='danger')
                return redirect(url_for('student.dashboard'))
            elif current_user.role == 'staff':
                flash("Unknown Page", category='danger')
                return redirect(url_for('staff.classroom'))
            elif current_user.role == 'admin':
                flash("Unknown Page", category='danger')
                return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('auth.login'))
        
    # Error handler for 405 Method Not Allowed
    @app.errorhandler(405)
    def method_not_allowed(error):
        if current_user.is_authenticated:
            # Redirect to the appropriate dashboard based on the user's role
            if current_user.role == 'staff':
                flash("Method not allowed.", category='danger')
                return redirect(url_for('staff.classroom'))
            elif current_user.role == 'student':
                flash("Method not allowed.", category='danger')
                return redirect(url_for('student.dashboard'))
            elif current_user.role == 'admin':
                flash("Method not allowed.", category='danger')
                return redirect(url_for('admin.dashboard'))
        else:
            # Redirect to the login page if the user is not authenticated
            email = flask_session.get('email')
            user = User.query.filter_by(email=email).first()
            user.session_token = None
            db.session.commit()
            flash("Method not allowed. Please login again", category='danger')
            return redirect(url_for('auth.login'))
        
    @app.errorhandler(429)
    def ratelimit_handler(e):
        logout_user()
        return render_template('errorpage.html'), 429
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(e):
        # Flash the CSRF error message with a category 'danger'
        flash(f'CSRF Error: {e.description}', category='danger')

    return app