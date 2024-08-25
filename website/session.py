from functools import wraps
from flask import session, redirect, url_for, flash
from flask_login import current_user
from datetime import datetime, timedelta
from .models import User
from .encryption import encrypt_token
from . import db
import uuid

def session_timeout(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        now = datetime.now()

        last_activity = session.get('last_activity')
        if last_activity:
            last_activity_time = datetime.strptime(last_activity, '%d/%m/%Y %H:%M:%S')

            # If idle time is more than 2 minutes, log out the user and show a message
            if now - last_activity_time > timedelta(minutes=2):
                # Clear session token and other session data
                if 'session_token' in session:
                    session.pop('session_token')
                User.query.filter_by(email=current_user.email).update({'session_token': None})
                db.session.commit()
                session.clear()
                
                # Flash a message and redirect to login
                flash("Your session has expired, please log in again.", 'warning')
                return redirect(url_for('auth.login'))
            
            # If idle time is more than 1 minute but less than 5 minutes, prompt reauthentication
            elif timedelta(minutes=1) < now - last_activity_time <= timedelta(minutes=60):
                session['reauthenticate'] = True

        # Reset last activity time
        session['last_activity'] = now.strftime('%d/%m/%Y %H:%M:%S')
        return f(*args, **kwargs)

    return decorated_function

def check_session():
#Check whether user has token in session
    if current_user.role == 'admin':
        flash("Unauthorized access", category='danger')
        # Render admin dashboard
        return redirect(url_for('admin.dashboard'))
    elif current_user.role == 'staff':
        flash("Unauthorized access", category='danger')
        # Redirect staff to staff dashboard
        return redirect(url_for('staff.classroom'))
    elif current_user.role == 'student':
        flash("Unauthorized access", category='danger')
        # Redirect students to student dashboard
        return redirect(url_for('student.dashboard')) 
    
def regenerate_session_token(user):
    # Generate a new session token
    new_token = str(uuid.uuid4())
    
    # Encrypt the new session token
    iv, encrypted_session_token, tag = encrypt_token(new_token)
    
    # Update the user's session token in the database
    user.session_token = f"{iv}:{encrypted_session_token}:{tag}"
    
    # Update session with the new token
    session['session_token'] = f"{iv}:{encrypted_session_token}:{tag}"
    
    # Commit the changes to the database
    db.session.commit()