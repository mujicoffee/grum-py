from flask import Blueprint, render_template, flash, redirect, url_for, session, request, make_response, current_app as app, jsonify
from .models import User
from . import db
from flask_bcrypt import Bcrypt
from flask_login import login_user, login_required, logout_user, current_user
from .forms import LoginForm, SignUpForm, OTPForm, ChangePasswordForm, ForgetPasswordForm, ResetPasswordForm, SetupProfilePicForm
from .otp import generate_otp
from .emails import *
from .reset_password_token import generate_reset_password_token
from .recaptcha import verify_recaptcha
from .encryption import encrypt_token
from .session import check_session, regenerate_session_token
from .logs import log_user_activity
from datetime import datetime, timedelta
import logging
import time
import uuid
import hashlib
import re
import json

# Create a Blueprint for the authentication routes
auth = Blueprint('auth', __name__)

# Initialise Bcrypt for password hashing
bcrypt = Bcrypt()

@auth.route('/', methods=['GET', 'POST'])
def login():
    # Load the pepper value from the config
    pepper = app.config.get('PEPPER', '')

    if current_user.is_authenticated:
        # Check whether user is logged in
        redirect_response = check_session()
        if redirect_response:
            return redirect_response
        
    # Initialise the login form
    form = LoginForm()
    
    # Validate the form submission
    if form.validate_on_submit():
        # Retrieve the reCAPTCHA response
        recaptcha_response = request.form.get('g-recaptcha-response')
        # Verify the reCAPTCHA response
        if not verify_recaptcha(recaptcha_response):
            flash('Please complete the reCAPTCHA.', category='danger')
            return render_template('login.html', form=form)

        # Retrieve the email from the form
        email = form.email.data
        # Fetch the user associated with the provided email
        user = User.query.filter_by(email=email).first()
        
        # Check if the user exists
        if user:
            # Check if the account is active
            if user.is_active == 'No':
                flash('Your account has been deactivated. Please check your email for more details.', category='danger')
                log_user_activity(user.id, 'fail', 'Login', 'Attempted to access deactivated account.')
                return render_template('login.html', form=form)

            # Retrieve the login attempts and last login time from the user
            attempts = user.login_attempts
            last_attempt = user.last_login_time
            # Retrieve the failed login details from the session
            failed_attempts_details = session.get('failed_login_details', [])
            # Retrieve the current time
            current_time = datetime.now()
            # Calculate the 10 minute lockout time 
            ten_minutes_lockout = current_time - timedelta(minutes=10)

            # Filter failed login attempts within the last 10 minutes
            failed_attempts_details = [
                attempt for attempt in failed_attempts_details
                if datetime.strptime(attempt, '%d/%m/%Y %H:%M:%S') > ten_minutes_lockout
            ]
            
            # Update the session with the filtered failed login attempts
            session['failed_login_details'] = failed_attempts_details

            # Check if the user has exceeded the maximum login attempts within the lockout period
            if attempts == 5 and current_time - last_attempt < timedelta(minutes=10):
                # Calculate the remaining lockout time
                timeout = timedelta(minutes=10) - (current_time - last_attempt)
                minutes, seconds = divmod(timeout.total_seconds(), 60)
                # Display lockout message
                flash(f'Too many login attempts. Please try again in {int(minutes)} minutes {int(seconds)} seconds.', category='danger')
                log_user_activity(user.id, 'fail', 'Login', 'Attempted to access account when lockout in effect.')
                return render_template('login.html', form=form)

            # Retrieve the password from the form
            password = form.password.data

            # Combine the password with the pepper
            combined_password = password + pepper

            try:
                # Check if the user exists and the password is correct
                if bcrypt.check_password_hash(user.password, combined_password):
                    # Clear any existing session data
                    session.clear()
                    # Generate an OTP
                    otp = generate_otp()
                    # Hash the OTP 
                    hashed_otp = bcrypt.generate_password_hash(str(otp)).decode('utf-8')
                    # Store the user's OTP in the database
                    user.otp = hashed_otp
                    user.last_otp_time = current_time
                    # Reset the login attempts to 0 and update to the latest login time
                    user.login_attempts = 0
                    user.last_login_time = current_time
                    session['failed_login_details'] = []

                    # Generate a new session token
                    session_token = str(uuid.uuid4())
                    # Encrypt the session token
                    iv, encrypted_session_token, tag = encrypt_token(session_token)
                    # Store the encrypted token in the database
                    user.session_token = f"{iv}:{encrypted_session_token}:{tag}"
                    session['session_token'] = f"{iv}:{encrypted_session_token}:{tag}"

                    db.session.commit()
                    # Send the OTP to the user's email
                    send_otp_email(user.name, email, otp)
                    flash('An OTP has been sent to your email.', category='info')
                    # Store the email in the session
                    session['email'] = email

                    # Log successful login
                    log_user_activity(user.id, 'pass', 'Login', 'Login successful. OTP sent.')

                    return redirect(url_for('auth.verify_otp'))
                else:
                    # Increment the login attempts
                    user.login_attempts += 1
                    user.last_login_time = current_time
                    # Add the current time to the failed login attempts 
                    failed_attempts_details.append(current_time.strftime('%d/%m/%Y %H:%M:%S'))
                    
                    # Limit and retrieve the latest 5 failed login attempts
                    if len(failed_attempts_details) > 5:
                        failed_attempts_details = failed_attempts_details[-5:]

                    # Update the session with the failed login attempts
                    session['failed_login_details'] = failed_attempts_details
                    db.session.commit()

                    # Check if the user has 5 failed login attempts
                    if user.login_attempts == 5:
                        # Send a suspicious login email
                        send_suspicious_login_email(user.name, email, failed_attempts_details)
                        # Calculate the remaining lockout time
                        timeout = timedelta(minutes=10)
                        minutes, seconds = divmod(timeout.total_seconds(), 60)
                        flash(f'Too many login attempts. Please try again in {int(minutes)} minutes {int(seconds)} seconds.', category='danger')
                        log_user_activity(user.id, 'fail', 'Login', '5 failed login attempts. Lockout in effect.')
                        return render_template('login.html', form=form)

                    # Check if the user has 10 failed login attempts
                    if user.login_attempts >= 10:
                        # Deactivate the account
                        user.is_active = 'No'
                        db.session.commit()
                        # Send an account deactivation email
                        send_account_deactivation_email(user.name, email)
                        flash('Your account has been deactivated. Please check your email for more details.', category='danger')
                        log_user_activity(user.id, 'fail', 'Login', '10 failed login attempts. Account deactivated.')
                        return render_template('login.html', form=form)

                    # If the user has fewer than 10 failed login attempts, show the appropriate message
                    attempts = user.login_attempts
                    if attempts < 5:
                        # Calculate remaining attempts until account lockout
                        attempts_left = 5 - attempts
                        flash(f'The email or password you have provided is incorrect. Please try again. You have {attempts_left} tries left before your account gets locked.', category='danger')
                    else:
                        # Calculate remaining attempts until account deactivation
                        attempts_left = 10 - attempts
                        flash(f'The email or password you have provided is incorrect. Please try again. You have {attempts_left} tries left before your account gets deactivated.', category='danger')

                    # Log failed login attempt
                    log_user_activity(user.id, 'fail', 'Login', 'Incorrect email or password.')

            except ValueError as e:
                # Handle the ValueError that might occur due to invalid salt
                flash('There was an error processing your request. Please try again.', category='danger')
                log_user_activity(user.id if user else 'unknown', 'fail', 'Login', f'Error: {str(e)}')
                # Optionally, you can redirect to a generic error page or re-render the login page
                return render_template('login.html', form=form)

        else:
            flash('The email or password you have provided is incorrect. Please try again.', category='danger')

    # Create a response object
    response = make_response(render_template('login.html', form=form))

    # Set cache-control headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate" # HTTP 1.1
    response.headers["Pragma"] = "no-cache" # HTTP 1.0
    response.headers["Expires"] = "0" # Proxies

    return response

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    if current_user.is_authenticated:
        # Check whether user is logged in
        redirect_response = check_session()
        if redirect_response:
            return redirect_response

    # Initialize the OTP form
    form = OTPForm()
    # Retrieve the email from the session 
    email = session.get('email')

    # Check if the email exists
    if not email:
        return redirect(url_for('auth.login'))

    # Fetch the user associated with the provided email
    user = User.query.filter_by(email=email).first()

    # Retrieve the session token and start time from the session
    session_token = session.get('session_token')
    start_time = session.get('otp_start_time')
    
    if start_time:
        start_time = datetime.strptime(start_time, '%d/%m/%Y %H:%M:%S')
        if datetime.now() - start_time > timedelta(minutes=5):
            # If the session has expired, clear and log the user out
            user.otp = None
            user.last_otp_time = datetime.now()
            user.otp_attempts = 0
            user.resend_otp_attempts = 0
            user.session_token = None
            db.session.commit()
            session.clear()
            flash('Your session has expired. Please login again.', category='danger')
            log_user_activity(user.id, 'fail', 'Verify OTP', 'Session expired.')
            return redirect(url_for('auth.login'))
    else:
        session['otp_start_time'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    # Check if the session token is valid
    if not user or not session_token or user.session_token != session_token:
        # If the token is invalid or missing, clear and log the user out
        user.otp = None
        user.last_otp_time = datetime.now()
        user.otp_attempts = 0
        user.resend_otp_attempts = 0
        user.session_token = None
        db.session.commit()
        session.clear()
        flash('Your session has expired or is invalid.', category='danger')
        log_user_activity(user.id if user else None, 'fail', 'Verify OTP', 'Invalid session token.')
        return redirect(url_for('auth.login'))

    # Validate the form submission
    if form.validate_on_submit():
        # Retrieve the OTP from the form
        otp = form.otp.data

        # Retrieve the stored OTP and its timing from the database
        stored_otp = user.otp
        otp_time = user.last_otp_time

        # Check if the OTP has expired
        if datetime.now() - otp_time > timedelta(minutes=5):
            flash('OTP has expired, please login again to request a new OTP.', category='danger')
            user.otp = None
            user.last_otp_time = datetime.now()
            user.otp_attempts = 0
            user.session_token = None
            db.session.commit()
            session.clear()
            log_user_activity(user.id, 'fail', 'Verify OTP', 'OTP expired.')
            return redirect(url_for('auth.login'))

        # Check if the OTP is correct
        if bcrypt.check_password_hash(stored_otp, otp):
            # Log the user in
            login_user(user, remember=True)
            user.otp = None
            user.last_otp_time = datetime.now()
            user.otp_attempts = 0
            user.resend_otp_attempts = 0

            db.session.commit()

            # Regenerate the session token after successful OTP verification
            regenerate_session_token(user)

            # Check if the user has logged in for the first time
            if user.first_login == 'Yes':
                log_user_activity(user.id, 'pass', 'Verify OTP', 'First login - redirecting to setup profile picture.')
                return redirect(url_for('auth.setupProfilePic'))

            # Redirect to the appropriate dashboard based on the role
            if user.role == 'staff':
                flash('Login successful!', category='success')
                log_user_activity(user.id, 'pass', 'Verify OTP', 'Login successful - redirecting to staff dashboard.')
                return redirect(url_for('staff.classroom'))
            elif user.role == 'student':
                flash('Login successful!', category='success')
                log_user_activity(user.id, 'pass', 'Verify OTP', 'Login successful - redirecting to student dashboard.')
                return redirect(url_for('student.dashboard'))
            elif user.role == 'admin':
                flash('Login successful!', category='success')
                log_user_activity(user.id, 'pass', 'Verify OTP', 'Login successful - redirecting to admin dashboard.')
                return redirect(url_for('admin.dashboard'))
            else:
                log_user_activity(user.id, 'fail', 'Verify OTP', 'Unknown role after successful login.')
                return redirect(url_for('auth.login'))
        else:
            # Increment the OTP attempts
            user.otp_attempts += 1
            db.session.commit()
            if user.otp_attempts >= 3:
                flash('Too many incorrect OTP attempts, please login again.', category='danger')
                user.otp = None
                user.last_otp_time = datetime.now()
                user.otp_attempts = 0
                user.resend_otp_attempts = 0
                user.session_token = None
                db.session.commit()
                session.clear()
                log_user_activity(user.id, 'fail', 'Verify OTP', 'Too many incorrect OTP attempts.')
                return redirect(url_for('auth.login'))
            flash('Invalid OTP, please try again.', category='danger')
            form.otp.data = ''
            log_user_activity(user.id, 'fail', 'Verify OTP', 'Incorrect OTP.')

    # Split email into username and domain
    name = email.split('@')[0]
    # Construct obscured part
    censored_part = '*' * (len(name) - int(len(name)/2)) + name[-3:]
    # Combine with domain
    censored_email = censored_part + '@' + email.split('@')[1]

    # Create a response object
    response = make_response(render_template("verify_otp.html", user=current_user, form=form, email=email, censored_email=censored_email))

    # Set cache-control headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

@auth.route('/resend-otp', methods=['POST'])
def resend_otp():
    # Retrieve the email from the form submission
    email = request.form.get('email')
    # Fetch the user associated with the provided email
    user = User.query.filter_by(email=email).first()

    if user:
        # Retrieve the current time
        current_time = datetime.now()

        # Check if the time elapsed since the last OTP request is 5 minutes or more
        if current_time - user.last_otp_time >= timedelta(minutes=5):
            flash('Current OTP has expired, please login again to request a new OTP.', category='danger')
            # Clear the OTP and update the time, then reset the resend attempts
            user.otp = None
            user.last_otp_time = datetime.now()
            user.resend_otp_attempts = 0
            user.session_token = None
            db.session.commit()
            log_user_activity(user.id, 'fail', 'Resend OTP', 'OTP expired - request for new OTP failed.')
            return redirect(url_for('auth.login'))

        # Check if the maximum number of resend attempts has been reached
        if user.resend_otp_attempts >= 3:
            flash('Maximum resend attempts reached, please login again to request a new OTP.', category='danger')
            # Clear the OTP and update the time, then reset the resend attempts
            user.otp = None
            user.last_otp_time = datetime.now()
            user.resend_otp_attempts = 0
            user.session_token = None
            db.session.commit()
            log_user_activity(user.id, 'fail', 'Resend OTP', 'Maximum resend attempts reached.')
            return redirect(url_for('auth.login'))

        # Generate a new OTP
        otp = generate_otp()
        # Hash the OTP 
        hashed_otp = bcrypt.generate_password_hash(str(otp)).decode('utf-8')
        # Store the newly generated OTP in the database
        user.otp = hashed_otp
        user.last_otp_time = current_time
        user.resend_otp_attempts += 1
        db.session.commit()

        # Regenerate the session token and reset session start time
        regenerate_session_token(user)
        session['session_token'] = user.session_token
        session['otp_start_time'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

        # Send the new OTP via email
        send_otp_email(user.name, email, otp)
        flash('A new OTP has been sent to your email.', category='info')
        log_user_activity(user.id, 'pass', 'Resend OTP', 'New OTP generated and sent via email.')
    else:
        flash('Invalid email address.', category='danger')

    return redirect(url_for('auth.verify_otp'))

@auth.route('/setup-profilepicture', methods=['GET', 'POST'])
@login_required
def setupProfilePic():
    
    if current_user.role == 'admin' or current_user.role == 'staff': 

        session['pfp'] = 'default.png'
        return redirect(url_for('auth.change_password'))

    # Retrieve the email from the session 
    email = session.get('email')

    # Check if the email exists
    if not email:
        log_user_activity(current_user.id, 'fail', 'Setup Profile', 'Email not found in session - redirecting to login.')
        return redirect(url_for('auth.login'))

    # Fetch the user associated with the provided email
    user = User.query.filter_by(email=email).first()

    # Check if session tracking exists and whether it has expired
    start_time = session.get('setup_start_time')
    if start_time:
        start_time = datetime.strptime(start_time, '%d/%m/%Y %H:%M:%S')
        if datetime.now() - start_time > timedelta(minutes=5):
            user.session_token = None
            db.session.commit()
            session.clear()
            log_user_activity(user.id, 'fail', 'Setup Profile', 'Session expired - redirecting to login.')
            flash('Your session has expired. Please log in again to complete the setup.', category='danger')
            return redirect(url_for('auth.login'))
    else:
        # Set the start time when the route is accessed
        session['setup_start_time'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if current_user.first_login == "Yes":
        log_user_activity(user.id, 'pass', 'Setup Profile', 'Accessed setup profile picture page.')
        pass
    else:
        # Check whether the user is logged in
        redirect_response = check_session()
        if redirect_response:
            log_user_activity(user.id, 'fail', 'Setup Profile', 'Account already set up - redirecting to dashboard.')
            flash('Your account has already been setup!', category='danger')
            return redirect_response

    form = SetupProfilePicForm()
    profile_pics = ['angry.png', 'crying.png', 'goofy.png', 'sadness.png', 'shocked.png', 'smile big.png', 'smile.png', 'meme1.png','meme2.png','meme3.png','meme4.png']
    selected_pic = session.get('pfp')

    if form.validate_on_submit():
        profile_picture = request.form.get('profilePic')
        selected_pic = session.get('pfp')

        if profile_picture:
            # Process the selected image (e.g., save to user's profile)
            session['pfp'] = profile_picture
            log_user_activity(user.id, 'pass', 'Setup Profile', f'Selected profile picture: {profile_picture}')
            return redirect(url_for('auth.change_password'))

        elif selected_pic:
            session['pfp'] = selected_pic
            log_user_activity(user.id, 'pass', 'Setup Profile', f'Selected profile picture from session: {selected_pic}')
            return redirect(url_for('auth.change_password'))
        
            # Redirect to the next step

        else:
            flash('Please choose a profile picture.')
            log_user_activity(user.id, 'fail', 'Setup Profile', 'No profile picture selected.')

    # Create a response object
    response = make_response(render_template('ProfilePic.html', form=form, profile_pics=profile_pics, selected_pic=selected_pic))

    # Set cache-control headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


def extract_substrings(s):
    """Helper function to extract substrings from a string, excluding single characters."""
    substrings = set()
    s = s.lower()
    for i in range(len(s)):
        for j in range(i + 2, min(len(s) + 1, i + 7)):  # Start from length 2 up to 7 characters
            substrings.add(s[i:j])
    return substrings


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():

    
    # Load the pepper value from the config
    pepper = app.config.get('PEPPER', '')

    # Retrieve the email from the session 
    email = session.get('email')

    # Check if the email exists
    if not email:
        log_user_activity(current_user.id, 'fail', 'Change Password', 'Email not found in session - redirecting to login.')
        return redirect(url_for('auth.login'))

    # Fetch the user associated with the provided email
    user = User.query.filter_by(email=email).first()

    # Check if session tracking exists and whether it has expired
    start_time = session.get('change_password_start_time')
    if start_time:
        start_time = datetime.strptime(start_time, '%d/%m/%Y %H:%M:%S')
        if datetime.now() - start_time > timedelta(minutes=5):
            user.session_token = None
            db.session.commit()
            session.clear()
            log_user_activity(user.id, 'fail', 'Change Password', 'Session expired - redirecting to login.')
            flash('Your session has expired. Please log in again to change your password.', category='danger')
            return redirect(url_for('auth.login'))
    else:
        # Set the start time when the route is accessed
        session['change_password_start_time'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

    if current_user.first_login == "Yes":
        log_user_activity(user.id, 'pass', 'Change Password', 'Accessed change password page for the first login.')
        pass
    else:
        # Checker whether the user is logged in
        redirect_response = check_session()
        if redirect_response:
            log_user_activity(user.id, 'fail', 'Change Password', 'Account already set up - redirecting to dashboard.')
            flash('Your account has already been setup!', category='danger')
            return redirect_response

    # Initialise the change password form
    form = ChangePasswordForm()
    # Retrieve the email of the current user
    email = current_user.email

    # Validate the form submission
    if form.validate_on_submit():

        email_substrings = extract_substrings(email.split('@')[0])  # Username part only
        # Retrieve the new and confirm password from the form
        newPassword = form.newPassword.data
        confirmPassword = form.confirmPassword.data

        # Check if the password was changed within one day of the last password change
        if current_user.last_password_change and (datetime.now() - current_user.last_password_change < timedelta(days=1)):
            log_user_activity(user.id, 'fail', 'Change Password', 'Password change attempt within 24 hours - rejected.')
            flash('You can only change your password once every 24 hours.', category='danger')
        # Check if the password have 12 or more characters
        elif len(newPassword) < 12:
            log_user_activity(user.id, 'fail', 'Change Password', 'New password too short - must be at least 12 characters.')
            flash('New password must be at least 12 characters long.', category='danger')
        # Check if the password have at least 1 uppercase letter
        elif not re.search(r'[A-Z]', newPassword):
            log_user_activity(user.id, 'fail', 'Change Password', 'New password lacks uppercase letter.')
            flash('New password must contain at least one uppercase letter.', category='danger')
        # Check if the password have at least 1 lowercase letter
        elif not re.search(r'[a-z]', newPassword):
            log_user_activity(user.id, 'fail', 'Change Password', 'New password lacks lowercase letter.')
            flash('New password must contain at least one lowercase letter.', category='danger')
        # Check if the password have at least 1 number
        elif not re.search(r'[0-9]', newPassword):
            log_user_activity(user.id, 'fail', 'Change Password', 'New password lacks number.')
            flash('New password must contain at least one number.', category='danger')
        # Check if the password have at least 1 special character
        elif not re.search(r'[!@#$%^&*()]', newPassword):
            log_user_activity(user.id, 'fail', 'Change Password', 'New password lacks special character.')
            flash('New password must contain at least one special character.', category='danger')
        # Check if both passwords match
        elif newPassword != confirmPassword:
            log_user_activity(user.id, 'fail', 'Change Password', 'New passwords do not match.')
            flash('Passwords don\'t match.', category='danger')
        # Check if the new password is the same as the existing password
        elif bcrypt.check_password_hash(current_user.password, newPassword + pepper):
            log_user_activity(user.id, 'fail', 'Change Password', 'New password same as current password.')
            flash('New password cannot be the same as the current password.', category='danger')

        elif any(sub in newPassword.lower() for sub in email_substrings):
            flash('New password cannot contain any part of your email address.', category='danger')
        else:

            password_history = json.loads(current_user.password_history or '[]')
            if any(bcrypt.check_password_hash(pw, newPassword) for pw in password_history):
                flash('New password cannot be the same as any of the last used passwords.', category='danger')
            else:
                # Hash the new password
                hashed_password = bcrypt.generate_password_hash(newPassword).decode('utf-8')
                # Update the user's password and password history
                user = User.query.filter_by(email=email).first()
                password_history.append(hashed_password)
                if len(password_history) > 15:
                    password_history.pop(0)

 

                # Get the profile pic from the session
                profile_picture = session.get('pfp')
                # Combine new password with pepper
                combined_new_password = newPassword + pepper
                # Hash the new password
                hashed_password = bcrypt.generate_password_hash(combined_new_password).decode('utf-8')
                # Fetch the user associated with the provided email
                user = User.query.filter_by(email=email).first()
                # Update the user's password and first login status
                user.password_history = json.dumps(password_history)
                user.password = hashed_password
                user.first_login = 'No'
                user.image_file = profile_picture
                # Update the user's last password change date and time
                user.last_password_change = datetime.now()
                db.session.commit()
                
                # Regenerate session token after password change
                regenerate_session_token(user)
                
                # Send the first login email to the user
                send_first_login_email(current_user.name, email)
                # Send the virus liability email to the user
                send_virus_liability_email(email, current_user.name)
                # Delete session for the pfp
                del session['pfp']

                # Log the successful password change
                log_user_activity(user.id, 'pass', 'Change Password', 'Password changed successfully.')

            # Redirect to the appropriate dashboard based on the user's role
            if user.role == 'staff':
                flash('Password changed successfully!', category='success')
                return redirect(url_for('staff.classroom'))
            elif user.role == 'student':
                flash('Password changed successfully!', category='success')
                return redirect(url_for('student.dashboard'))
            elif user.role == 'admin':
                flash('Password changed successfully!', category='success')
                return redirect(url_for('admin.dashboard'))
            else:
                return redirect(url_for('auth.login'))

    # Create a response object
    response = make_response(render_template('change_password.html', user=current_user, form=form, email=email))

    # Set cache-control headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


@auth.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    # Initialise the forget password form
    form = ForgetPasswordForm()

    # Validate the form submission
    if form.validate_on_submit():
        # Retrieve the reCAPTCHA response
        recaptcha_response = request.form.get('g-recaptcha-response')
        # Verify the reCAPTCHA response
        if not verify_recaptcha(recaptcha_response):
            flash('Please complete the reCAPTCHA.', category='danger')
            return render_template('forget_password.html', form=form)
        
        # Retrieve the email from the form
        email = form.email.data
        # Fetch the user associated with the provided email
        user = User.query.filter_by(email=email).first()

        # Check if the user exists
        if user:
            # Retrieve the current time
            current_time = datetime.now()

            # Check if the user has exceeded the maximum password reset attempts
            if user.forget_password_attempts >= 3:
                if current_time - user.last_forget_password_time < timedelta(hours=1):
                    # Calculate the remaining time
                    remaining_time = timedelta(hours=1) - (current_time - user.last_forget_password_time)
                    minutes, seconds = divmod(remaining_time.total_seconds(), 60)
                    # Display an error message
                    flash(f'Too many password reset attempts. Please try again in {int(minutes)} minutes {int(seconds)} seconds.', category='danger')
                    log_user_activity(user.id, 'fail', 'Forget Password', 'Maximum password reset attempts exceeded.')
                    return render_template('forget_password.html', form=form)
                else:
                    user.forget_password_attempts = 0

            user.forget_password_attempts += 1

            if user.first_login == 'Yes':
                user.last_forget_password_time = current_time
                db.session.commit()
                # Send the unsuccessful password reset email
                send_forget_password_unsuccessful_email(user.name, email)
                log_user_activity(user.id, 'fail', 'Forget Password', 'Password reset email not sent (first login).')
                # Delay form processing by 2 seconds for consistent handling
                time.sleep(2)
                form.email.data = ''
                flash('A password reset link has been sent if the email is registered in our system.', category='success')
            else:
                # Generate a new password reset token
                token = generate_reset_password_token()
                # Hash the token using SHA-256
                hashed_token = hashlib.sha256(token.encode('utf-8')).hexdigest()
                # Store the hashed token in the database
                user.reset_password_token = hashed_token
                user.last_forget_password_time = current_time
                db.session.commit()

                # Send the password reset email to the user
                send_forget_password_email(user.name, email, token)
                log_user_activity(user.id, 'pass', 'Forget Password', 'Password reset email sent successfully.')

        # Delay form processing by 2 seconds for consistent handling
        time.sleep(2)
        form.email.data = ''
        flash('A password reset link has been sent if the email is registered in our system.', category='success')

    # Create a response object
    response = make_response(render_template('forget_password.html', form=form))

    # Set cache-control headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response

@auth.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    # Load the pepper value from the config
    pepper = app.config.get('PEPPER', '')

    # Initialise the reset password form
    form = ResetPasswordForm()
    hashed_token = hashlib.sha256(token.encode('utf-8')).hexdigest()

    # Query the database for a user with the given reset password token
    user = User.query.filter_by(reset_password_token=hashed_token).first()

    # Check if the user exists
    if user:
        # Check if the reset password token has expired
        if datetime.now() - user.last_forget_password_time > timedelta(minutes=20):
            user.reset_password_token = None
            db.session.commit()
            log_user_activity(user.id, 'fail', 'Reset Password', 'Reset password link expired.')
            flash('This reset link has expired, please request a new one.', category='danger')
            return redirect(url_for('auth.forget_password'))
        
        # Check if the password was changed within the last day
        if user.last_password_change and (datetime.now() - user.last_password_change < timedelta(days=1)):
            user.reset_password_token = None
            db.session.commit()
            # Calculate the timestamp for when the password reset will be available again
            available_reset_time = user.last_password_change + timedelta(days=1)
            send_reset_password_suspension_email(user.email, user.name, available_reset_time)
            log_user_activity(user.id, 'fail', 'Reset Password', 'Password change attempted too soon.')
            flash('You can only change your password once every 24 hours. Please try again later.', category='danger')
            return redirect(url_for('auth.login'))

        # Validate the form submission
        if form.validate_on_submit():
            # Retrieve the new and confirm password from the form
            newPassword = form.newPassword.data
            confirmPassword = form.confirmPassword.data
            
            # Extract substrings from the email for validation
            email_substrings = extract_substrings(user.email.split('@')[0])  # Username part only

            # Check if the password has 12 or more characters
            if len(newPassword) < 12:
                flash('New password must be at least 12 characters long.', category='danger')
                log_user_activity(user.id, 'fail', 'Reset Password', 'New password too short.')
            # Check if the password has at least 1 uppercase letter
            elif not re.search(r'[A-Z]', newPassword):
                flash('New password must contain at least one uppercase letter.', category='danger')
                log_user_activity(user.id, 'fail', 'Reset Password', 'New password missing uppercase letter.')
            # Check if the password has at least 1 lowercase letter
            elif not re.search(r'[a-z]', newPassword):
                log_user_activity(user.id, 'fail', 'Reset Password', 'New password missing lowercase letter.')
                flash('New password must contain at least one lowercase letter.', category='danger')
            # Check if the password has at least 1 number
            elif not re.search(r'[0-9]', newPassword):
                log_user_activity(user.id, 'fail', 'Reset Password', 'New password missing number.')
                flash('New password must contain at least one number.', category='danger')
            # Check if the password has at least 1 special character
            elif not re.search(r'[!@#$%^&*()]', newPassword):
                log_user_activity(user.id, 'fail', 'Reset Password', 'New password missing special character.') 
                flash('New password must contain at least one special character.', category='danger') 
            # Check if both passwords match
            elif newPassword != confirmPassword:
                log_user_activity(user.id, 'fail', 'Reset Password', 'Passwords do not match.')
                flash('Passwords don\'t match.', category='danger')
            # Check if the new password is the same as the existing password 
            elif bcrypt.check_password_hash(user.password, newPassword):
                log_user_activity(user.id, 'fail', 'Reset Password', 'New password same as current password.')
                flash('New password cannot be the same as the current password.', category='danger')
            elif any(sub in newPassword.lower() for sub in email_substrings):
                flash('New password cannot contain parts of your email address.', category='danger')
                
            else:
                password_history = json.loads(user.password_history or '[]')
                if any(bcrypt.check_password_hash(pw, newPassword) for pw in password_history):
                    flash('New password cannot be the same as any of the last used passwords.', category='danger')
                else:
                    password_history.append(user.password)  # Add the old password to history
                
                # Hash the new password                    
                    if len(password_history) > 15:
                        password_history.pop(0)  # Maintain a maximum of 15 passwords

                    user.password_history = json.dumps(password_history)   
                    hashed_password = bcrypt.generate_password_hash(newPassword + pepper).decode('utf-8')
                    # Update the user's password in the database
                    user.password = hashed_password
                    user.reset_password_token = None
                    # Update the last reset password time
                    user.last_reset_password_time = datetime.now()
                    # Update the last password  time
                    user.last_password_change = datetime.now()
                    # Reset the forget password attempts after successful password reset
                    user.forget_password_attempts = 0

                    # Deactivated accounts only
                    # Reset the login attempts and account status for reactivation
                    user.login_attempts = 0
                    user.is_active = 'Yes'
                    db.session.commit()

                # Send the reset password confirmation email to the user
                send_reset_password_email(user.name, user.email)
                log_user_activity(user.id, 'pass', 'Reset Password', 'Password reset successfully.')
                flash('Password reset successfully, you may login with the new password.', category='success')
                return redirect(url_for('auth.login'))

    else:
        flash('Invalid or expired reset link.', category='danger')
        return redirect(url_for('auth.forget_password'))

    # Create a response object
    response = make_response(render_template('reset_password.html', form=form, email=user.email, token=token))
    
    # Set cache-control headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
    response.headers['Pragma'] = 'no-cache'  # HTTP 1.0.
    response.headers['Expires'] = '0'  # Proxies.
    
    return response

@auth.route('/logout', methods=['POST', 'GET'])
@login_required
def logout():
    # Clear the user's session token
    user = User.query.filter_by(email=current_user.email).first()
    if user:
        user.session_token = None
        db.session.commit()
        log_user_activity(user.id, 'pass', 'Logout', 'Session token cleared.')

    # Clear all session data
    session.clear()

    # Logout the current user
    logout_user()

    # Log the successful logout event
    log_user_activity(user.id, 'pass', 'Logout', 'User logged out successfully.')

    # Check if the request is expecting a JSON response
    if request.method == 'POST' and request.is_json:
        response = {
            'message': 'Logout successful!',
            'status': 'success'
        }
        return jsonify(response)
    
    # Handle the redirect for GET requests or non-JSON POST requests
    flash('Logout successful!', category='success')
    
    response = make_response(redirect(url_for('auth.login')))
    
    # Set cache-control headers
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'  # HTTP 1.1.
    response.headers['Pragma'] = 'no-cache'  # HTTP 1.0.
    response.headers['Expires'] = '0'  # Proxies.
    
    return response

# To be removed / modified later
@auth.route('/sign-up', methods=['GET', 'POST'])
def sign_up():
    # Initialise the sign up form
    form = SignUpForm()

    # Validate the form submission
    if form.validate_on_submit():
        # Retrieve the form data
        email = form.email.data
        name = form.name.data
        passwordSet = form.passwordSet.data
        passwordConfirm = form.passwordConfirm.data
        role = form.role.data
        image_file = form.image_file.data

        # Check if the email is already in use
        user = User.query.filter_by(email=email).first()

        # Check if the user exists 
        if user:
            flash('Email is already in use.', category='danger')
        # Check if the email is at least 4 characters long
        elif len(email) < 4:
            flash('Email must be greater than 3 characters.', category='danger')
        # Check if the name is at least 2 characters long
        elif len(name) < 2:
            flash('Name must be greater than 1 character.', category='danger')
        # Check if both passwords match
        elif passwordSet != passwordConfirm:
            flash('Passwords don\'t match.', category='danger')
        # Check if the password is at least 8 characters long
        elif len(passwordSet) < 8:
            flash('Password must be at least 8 characters.', category='danger')
        # Check if the image file is valid
        elif image_file and not (image_file.filename.endswith(('jpg', 'png', 'jpeg', 'gif'))):
            flash('Unsupported file type. Only .jpg, .png, .jpeg, and .gif files are accepted.', category='danger')
        else:
            # Hash the password
            hashed_password = bcrypt.generate_password_hash(passwordSet).decode('utf-8')
            # Create a new user
            new_user = User(email=email, name=name, password=hashed_password, role=role, first_login='Yes')
            # Add the new user to the database
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            flash('Account created!', category='success')

            # Redirect to the appropriate dashboard based on the role
            if new_user.role == 'student':
                return redirect(url_for('student.dashboard'))
            elif new_user.role == 'staff':
                return redirect(url_for('staff.classroom'))

    return render_template("sign_up.html", user=current_user, form=form)

@auth.route('/reauthenticate', methods=['POST'])
def reauthenticate():
    try:
        data = request.form
        if 'email' not in data or 'password' not in data:
            return jsonify({'message': 'Email or password is missing. Please try again.'}), 400

        email = data['email'].strip().lower()
        password = data['password'].strip()
        pepper = app.config.get('PEPPER', '')

        # Ensure the user is logged in by checking the session
        if 'session_token' not in session:
            return jsonify({'status': 'error', 'message': 'User not logged in.'}), 401

        user = User.query.filter_by(email=email).first()

        if user:
            combined_password = password + pepper
            if bcrypt.check_password_hash(user.password, combined_password):
                session_token = str(uuid.uuid4())
                iv, encrypted_session_token, tag = encrypt_token(session_token)

                user.session_token = f"{iv}:{encrypted_session_token}:{tag}"
                db.session.commit()

                session['session_token'] = f"{iv}:{encrypted_session_token}:{tag}"
                session['last_activity'] = datetime.now().strftime('%d/%m/%Y %H:%M:%S')

                # Update session to indicate successful reauthentication
                session['reauthenticate'] = False

                return jsonify({'status': 'success', 'message': 'Session reauthenticated successfully.'})
            else:
                # Handle incorrect password
                flash('Incorrect password. Please try again.', 'danger')
                return jsonify({'status': 'error', 'message': 'Incorrect password. Please try again.'}), 401
        else:
            # Handle user not found
            flash('User not found. Please try again.', 'danger')
            return jsonify({'status': 'error', 'message': 'User not found. Please try again.'}), 401

    except Exception as e:
        logging.error(f'An unexpected error occurred: {str(e)}')
        return jsonify({'status': 'error', 'message': 'An unexpected error occurred. Please try again later.'}), 500


@auth.route('/check_reauthenticate', methods=['GET'])
def check_reauthenticate():
    # Check if the user is authenticated
    if not current_user.is_authenticated:
        # User is not authenticated; prompt reauthentication
        return jsonify({"status": "expired", "message": "Your session has expired, please log in again."}), 401
    
    # Check if reauthentication is required
    if session.get('reauthenticate', False):
        return jsonify({"reauthenticate": True})
    
    return jsonify({"reauthenticate": False})