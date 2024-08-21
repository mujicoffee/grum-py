from flask import Blueprint, render_template, flash, redirect, url_for, request, current_app as app
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from .session import session_timeout
from .week import get_current_week_and_time
from .models import User, Classroom, Logs, Quiz, QuizQuestion, Module, Labsheet, LabsheetQuestion, AdminSettings
from .forms import AddStaffFileForm, AddStaffForm, UploadQuizForm, EditQuestionForm, DeleteQuestionForm, AddModuleForm, LabsheetForm, QuestionForm, UploadLabsheetForm, StartDateForm
from .emails import send_staff_account_setup_email, send_virus_liability_email, send_deactivation_warning_email, send_reactivation_warning_email
from .logs import log_user_activity
from . import db, bcrypt, scheduler
import pandas as pd
import random 
import string
import magic
import pytz

admin = Blueprint('admin', __name__)

# Create a timezone object for Singapore Time
sg_tz = pytz.timezone('Asia/Singapore')

@admin.route('/dashboard', methods=['GET', 'POST'])
@login_required
@session_timeout
def dashboard():
    form = StartDateForm()  # Create a form instance
    
    if form.validate_on_submit():
        start_date_str = form.start_date.data.strftime('%Y-%m-%d')
        start_date = sg_tz.localize(datetime.strptime(start_date_str, '%Y-%m-%d'))

        # Check if the start date is in the past
        current_date = datetime.now(sg_tz).date()
        if start_date.date() < current_date:
            flash("Start date cannot be in the past", category='error')
            return redirect(url_for('admin.dashboard'))

        # Fetch the first (and presumably only) record from AdminSettings
        setting = AdminSettings.query.first()
        if setting:
            # Make sure setting.start_date is aware before comparison
            if setting.start_date.tzinfo is None:
                setting.start_date = sg_tz.localize(setting.start_date)
            setting.start_date = start_date
        else:
            # Create a new setting with the provided start date
            setting = AdminSettings(start_date=start_date)
            db.session.add(setting)

        db.session.commit()
        flash("Start date updated successfully", category='success')
        return redirect(url_for('admin.dashboard'))

    # Fetch settings and calculate the current week
    setting = AdminSettings.query.first()
    if setting and setting.start_date:
        current_start_date = setting.start_date
        if current_start_date.tzinfo is None:
            current_start_date = sg_tz.localize(current_start_date)
    else:
        # Use a default start date if no settings are found
        default_start_date = sg_tz.localize(datetime(2024, 7, 20))
        current_start_date = default_start_date

    current_week, current_time = get_current_week_and_time()
    current_timezone = datetime.now(sg_tz)
    users_active = User.query.filter(User.session_token.isnot(None)).with_entities(User.name, User.email, User.role, User.last_login_time).all()
    users_inactive = User.query.filter(User.is_active == "No").with_entities(User.name, User.email, User.role, User.last_login_time).all()

    return render_template(
        "admin_dashboard.html",
        user=current_user,
        current_week=current_week,
        current_time=current_time,
        current_timezone=current_timezone,
        users_active=users_active,
        users_inactive=users_inactive,
        form=form,
        current_start_date=current_start_date
    )

# Clear Sessions and deactivate all Users that have student role.
@admin.route('/deactivate_students', methods=['POST'])
@login_required
def deactivate_students():
    if current_user.role != 'admin':
        flash("Unauthorized access", category='danger')
        return redirect(url_for('auth.login'))
    
    users = User.query.filter(User.role == 'student', User.is_active == 'Yes').all()
    if users:
        sg_tz = pytz.timezone('Asia/Singapore')
        deactivation_time = datetime.now(sg_tz) + timedelta(minutes=5)

        for user in users:
            # Update the user status to "pending_deactivation"
            user.is_active = 'Pend'
            user.deactivation_time = deactivation_time

            # Notify the user
            send_deactivation_warning_email(user.email, user.name, user.deactivation_time)
            
            # Schedule the deactivation job and pass the app instance
            schedule_deactivation(app._get_current_object(), user.id, deactivation_time)
        
        # Commit the changes after all students have been processed
        db.session.commit()

        flash("All students will be logged out and deactivated in 5 minutes", category='success')

    else:
        flash("No students found", category='danger')

    return redirect(url_for('admin.dashboard'))


# Clear Sessions and deactivate all Users that are not "admin" role
@admin.route('/deactivate_all', methods=['POST'])
@login_required
def deactivate_all():
    if current_user.role != 'admin':
        flash("Unauthorized access", category='danger')
        return redirect(url_for('auth.login'))

    users = User.query.filter(User.role.in_(['student', 'staff']), User.is_active == 'Yes').all()
    if users:
        sg_tz = pytz.timezone('Asia/Singapore')
        deactivation_time = datetime.now(sg_tz) + timedelta(minutes=5)

        for user in users:
            # Update the user status to "pending_deactivation"
            user.is_active = 'Pend'
            user.deactivation_time = deactivation_time

            # Notify the user
            send_deactivation_warning_email(user.email, user.name, user.deactivation_time)

            # Schedule the deactivation job and pass the app instance
            schedule_deactivation(app._get_current_object(), user.id, deactivation_time)

        # Commit the changes after all users have been processed
        db.session.commit()

        flash("All students and staff will be logged out and deactivated in 5 minutes", category='success')

    else:
        flash("No students or staff found", category='danger')

    return redirect(url_for('admin.dashboard'))

#Clear User From Session, and make account's "is_active" = No
@admin.route('/make_inactive/<string:email>', methods=['POST'])
@login_required
def make_inactive(email):
    user = User.query.filter_by(email=email).first()
    if user:
        # Calculate the deactivation time (e.g., 5 minutes from now)
        sg_tz = pytz.timezone('Asia/Singapore')
        deactivation_time = datetime.now(sg_tz) + timedelta(minutes=5)

        # Update the user status to "pending_deactivation"
        user.is_active = 'Pend'
        user.deactivation_time = deactivation_time

        # Notify the user
        send_deactivation_warning_email(user.email, user.name, user.deactivation_time)
        flash(f"User {user.name} will be logged out and deactivated in 5 minutes", category='success')

        db.session.commit()

        # Schedule the deactivation job and pass the app instance
        schedule_deactivation(app._get_current_object(), user.id, deactivation_time)

    else:
        flash("User not found", category='danger')

    return redirect(url_for('admin.dashboard'))

def schedule_deactivation(app, user_id, deactivation_time):
    scheduler.add_job(func=deactivate_user_account, 
                      trigger='date', 
                      run_date=deactivation_time, 
                      args=[app, user_id])

def deactivate_user_account(app, user_id):
    with app.app_context():
        user = User.query.get(user_id)
        if user and user.is_active == 'Pend':
            user.is_active = 'No'
            user.session_token = None
            db.session.commit()

#Make User Active from Inactive
@admin.route('/make_active/<string:email>', methods=['POST'])
@login_required
def make_active(email):
    user = User.query.filter_by(email=email).first()
    if user:
        send_reactivation_warning_email(user.email, user.name)
        user.is_active = 'Yes' #Set is_active to "Yes"
        db.session.commit()
        flash(f"{user.name} account has been actived", category='success')
    else:
        flash("User not found", category='danger')
    
    return redirect(url_for('admin.dashboard'))

#Activate all Users that have student role.
@admin.route('/activate_staff', methods=['POST'])
@login_required
def activate_staff():
    if current_user.role != 'admin':
        flash("Unauthorized access", category='danger')
        return redirect(url_for('auth.login'))
    
    students = User.query.filter_by(role='staff').all()
    if students:
        for student in students:
            student.is_active = 'Yes'
            db.session.commit()
        flash("All student accounts have been activated", category='success')
    else:
        flash("No students found", category='danger')

    return redirect(url_for('admin.dashboard'))

#Activate all Users
@admin.route('/activate_all', methods=['POST'])
@login_required
def activate_all():
    if current_user.role != 'admin':
        flash("Unauthorized access", category='danger')
        return redirect(url_for('auth.login'))
    
    users = User.query.filter(User.role.in_(['student', 'staff'])).all()
    if users:
        for user in users:
            user.is_active = 'Yes'
        db.session.commit()
        flash("All student and staff accounts have been activated", category='success')
    else:
        flash("No students or staff found", category='danger')

    return redirect(url_for('admin.dashboard'))

@admin.route('/teaching_team', methods=['GET', 'POST'])
@login_required
@session_timeout
def teaching_team():
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))

    current_week, _ = get_current_week_and_time()
    search_query = request.args.get('query', '').strip()
    
    staff_members_query = User.query.filter_by(role='staff')

    if search_query:
        staff_members_query = staff_members_query.filter(
            (User.name.ilike(f'%{search_query}%')) |
            (User.email.ilike(f'%{search_query}%'))
        )

    staff_members = staff_members_query.all()
    classrooms = Classroom.query.all()

    staff_data = []
    for staff in staff_members:
        assigned_classrooms = [classroom.code for classroom in staff.staff_user]
        staff_data.append({
            'id': staff.id,
            'name': staff.name,
            'email': staff.email,
            'classrooms': assigned_classrooms
        })

    # Sort staff_data by name
    staff_data.sort(key=lambda x: x['name'])

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return render_template("staff_table.html", staff_data=staff_data, classrooms=classrooms)
    
    return render_template("teaching_team.html", staff_data=staff_data, classrooms=classrooms, current_week=current_week)


@admin.route('/teaching-team/add-staff', methods=['GET', 'POST'])
@login_required
@session_timeout
def add_staff():
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))
    
    current_week,_ =get_current_week_and_time()
    form_staff_file = AddStaffFileForm()
    form_staff = AddStaffForm()

    # Load the pepper value from the config
    pepper = app.config.get('PEPPER', '')

    if form_staff_file.validate_on_submit() and form_staff_file.submit.data:
        staff_file = form_staff_file.staff_file.data
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(staff_file.read(2048))
        staff_file.seek(0)  # Reset file pointer to the beginning

        if file_type not in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            flash('Only .xlsx files are allowed.', category='danger')
            return redirect(url_for('admin.add_staff'))

        else:
            staff_data = pd.read_excel(staff_file)
            staff_data.columns = staff_data.columns.str.strip().str.lower()

            # Define required columns
            required_columns = ['name', 'email', 'classes']
            allowed_columns = set(required_columns)

            # Check if the uploaded file contains exactly the required columns
            uploaded_columns = set(staff_data.columns)
            if uploaded_columns != allowed_columns:
                flash(f'Invalid columns detected. Expected columns: {", ".join(required_columns)}', category='danger')
                return redirect(url_for('admin.add_staff'))

            # Check if the DataFrame is empty
            if staff_data.empty:
                flash('The file is empty. Please upload a file with staff data.', category='danger')
                return redirect(url_for('admin.add_staff'))

            # Check for missing values in required columns
            missing_column_values = [column for column in ['name', 'email'] if staff_data[column].isna().any()]
            if missing_column_values:
                flash(f'The following columns contain missing values: {", ".join(missing_column_values)}. Please ensure all rows have values for these columns.', category='danger')
                return redirect(url_for('admin.add_staff'))

            # Check for duplicate emails in the file
            duplicate_emails = staff_data[staff_data.duplicated(['email'], keep=False)]
            if not duplicate_emails.empty:
                flash(f'The following emails are duplicated: {", ".join(duplicate_emails["email"].unique())}. Please ensure all emails are unique and try again.', category='danger')
                return redirect(url_for('admin.add_staff'))

            all_emails = set(staff_data['email'])
            
            existing_emails = set(user.email for user in User.query.filter(User.email.in_(all_emails)).all())
            
            # Determine if there is any overlap between existing and new emails
            emails_exist = all_emails & existing_emails
            if emails_exist:
                flash(f'The following emails already exist in the system and cannot be processed: {", ".join(emails_exist)}', category='danger')
                return redirect(url_for('admin.add_staff'))

            # Validate assigned classes
            valid_classes = {'P01', 'P02', 'P03', 'P04', 'P05', 'P06', 'P07', 'P08'}
            invalid_classes_found = False

            for index, row in staff_data.iterrows():
                classes = row.get('classes')
                if pd.notna(classes):
                    classes = str(classes).strip()
                    assigned_classrooms = [cls.strip() for cls in classes.split(',')] if classes else []
                    invalid_classes = set(assigned_classrooms) - valid_classes
                    if invalid_classes:
                        invalid_classes_found = True
                        break

            if invalid_classes_found:
                flash('The file contains invalid class values. No staff members were added.', category='danger')
                return redirect(url_for('admin.add_staff'))

            # Process file if no invalid classes were found
            for index, row in staff_data.iterrows():
                name = row.get('name')
                email = row.get('email')
                classes = row.get('classes')

                # Handle NaN values
                if pd.isna(classes):
                    classes = ''  # Convert NaN to an empty string
                
                classes = str(classes).strip()
                assigned_classrooms = [cls.strip() for cls in classes.split(',')] if classes else []

                password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                hashed_password = bcrypt.generate_password_hash(password + pepper).decode('utf-8')

                new_staff = User(email=email, name=name, password=hashed_password, role='staff', first_login='Yes')
                db.session.add(new_staff)
                db.session.commit()

                # Assign staff to selected classrooms
                for classroom_code in assigned_classrooms:
                    classroom = Classroom.query.filter_by(code=classroom_code).first()
                    if classroom:
                        new_staff.staff_user.append(classroom)

                db.session.commit()
                send_staff_account_setup_email(email, name, password)
                send_virus_liability_email(email, name)

            flash("Staff added successfully.", category='success')
            return redirect(url_for('admin.teaching_team'))

    elif form_staff.validate_on_submit() and form_staff.submit.data:
        name = form_staff.staff_name.data
        email = form_staff.staff_email.data

        if not name or not email:
            flash('Both name and email are required.', category='danger')
            return redirect(url_for('admin.add_staff'))

        if User.query.filter_by(email=email).first():
            flash(f'Staff member with email {email} already exists', category='danger')
            return redirect(url_for('admin.add_staff'))

        password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
        hashed_password = bcrypt.generate_password_hash(password + pepper).decode('utf-8')

        new_staff = User(email=email, name=name, password=hashed_password, role='staff', first_login='Yes')
        db.session.add(new_staff)
        db.session.commit()

        # Assign staff to selected classrooms
        assigned_classrooms = [name for name, field in form_staff._fields.items() if field.data]
        for classroom_code in assigned_classrooms:
            classroom = Classroom.query.filter_by(code=classroom_code).first()
            if classroom:
                new_staff.staff_user.append(classroom)

        db.session.commit()
        send_staff_account_setup_email(email, name, password)
        send_virus_liability_email(email, name)

        flash(f'Staff member {name} ({email}) added successfully.', category='success')
        return redirect(url_for('admin.teaching_team'))

    return render_template("add_staff.html", user=current_user, form_staff_file=form_staff_file, form_staff=form_staff, current_week=current_week)

@admin.route('/teaching-team/edit-staff/<int:staff_id>', methods=['POST'])
@login_required
@session_timeout
def edit_staff(staff_id):
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))
    
    current_week,_ = get_current_week_and_time()
    staff = User.query.get(staff_id)
    if not staff:
        flash('Staff not found.', category='danger')
        return redirect(url_for('admin.teaching_team'))

    name = request.form.get('name')
    email = request.form.get('email')
    selected_classrooms = request.form.getlist('classrooms')

    # Check if the new email is already taken by another user
    existing_staff = User.query.filter_by(email=email).first()
    if existing_staff and existing_staff.id != staff.id:
        flash(f'Staff member with email {email} already exists', category='danger')
        return redirect(url_for('admin.teaching_team'))

    staff.name = name
    staff.email = email  # Update the email address
    staff.staff_user = []

    for code in selected_classrooms:
        classroom = Classroom.query.filter_by(code=code).first()
        if classroom:
            staff.staff_user.append(classroom)

    db.session.commit()

    flash(f'Staff member {name} ({email}) updated successfully.', category='success')
    return redirect(url_for('admin.teaching_team'))

@admin.route('/teaching-team/remove-staff/<int:staff_id>', methods=['POST'])
@login_required
@session_timeout
def remove_staff(staff_id):
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))

    staff = User.query.get(staff_id)
    if not staff:
        flash('Staff not found.', category='danger')
        return redirect(url_for('admin.teaching_team'))

    # Check if the staff member is assigned to any classes
    if staff.staff_user:
        flash(f'Cannot remove staff member {staff.name} ({staff.email}) until they are unassigned from all classes.', category='danger')
        return redirect(url_for('admin.teaching_team'))

    # Proceed with deletion if not assigned to any classes
    db.session.delete(staff)
    db.session.commit()

    flash(f'Staff member {staff.name} ({staff.email}) removed successfully.', category='success')
    return redirect(url_for('admin.teaching_team'))

@admin.route('/logs', methods=['GET'])
@login_required
@session_timeout
def logs():
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))
    current_week,_ = get_current_week_and_time()
    logs = Logs.query.order_by(Logs.timestamp.desc()).all()
    return render_template('logs.html', user=current_user, logs=logs, current_week=current_week)



@admin.route('/quizzes', methods=['GET'])
@login_required
@session_timeout
def quizzes():
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))

    current_week,_=  get_current_week_and_time()
    quizzes = Quiz.query.all()
    quizzes_by_module = {}
    
    for quiz in quizzes:
        module_id = quiz.module_id
        if module_id not in quizzes_by_module:
            quizzes_by_module[module_id] = []
        quizzes_by_module[module_id].append(quiz)
    
    return render_template("admin_quiz_menu.html", user=current_user, quizzes_by_module=quizzes_by_module,current_week=current_week)

@admin.route('/quizzes/module/<int:module_id>/quiz/<int:quiz_id>', methods=['GET'])
@login_required
@session_timeout
def quizzes_by_module(module_id, quiz_id):
    if current_user.role != 'admin':
        flash("Unauthorized access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))

    current_week, _ = get_current_week_and_time()

    # Pagination for quizzes
    page = request.args.get('page', 1, type=int)
    per_page = 5
    quizzes_pagination = Quiz.query.filter_by(module_id=module_id).paginate(page=page, per_page=per_page, error_out=False)

    # Pagination for quiz questions
    questions_page = request.args.get('questions_page', 1, type=int)
    questions_per_page = 10

    # Get search query and determine if it is active
    search_query = request.args.get('search', '')
    search_active = bool(search_query)

    # Filter questions based on the search query
    quiz_questions_query = QuizQuestion.query.filter_by(quiz_id=quiz_id)
    if search_query:
        quiz_questions_query = quiz_questions_query.filter(QuizQuestion.question.ilike(f'%{search_query}%'))

    quiz_questions_pagination = quiz_questions_query.paginate(page=questions_page, per_page=questions_per_page, error_out=False)

    delete_forms = {}
    edit_forms = {}

    for question in quiz_questions_pagination.items:
        delete_form = DeleteQuestionForm()
        edit_form = EditQuestionForm(obj=question)
        delete_forms[question.id] = delete_form
        edit_forms[question.id] = edit_form

    return render_template(
        "admin_module_quizzes.html",
        user=current_user,
        current_week=current_week,
        module_id=module_id,
        quizzes_pagination=quizzes_pagination,
        quiz_id=quiz_id,
        quiz_questions_pagination=quiz_questions_pagination,
        delete_forms=delete_forms,
        edit_forms=edit_forms,
        search_query=search_query,  # Pass search query to the template
        search_active=search_active  # Pass search active status to the template
    )


@admin.route('/quizzes/module/<int:module_id>/quiz/<int:quiz_id>/add', methods=['GET', 'POST'])
@login_required
@session_timeout
def add_quiz(module_id, quiz_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('student.dashboard'))

    form = UploadQuizForm()

    current_week,_=  get_current_week_and_time()
    quizzes = Quiz.query.filter_by(module_id=module_id).all()
    titles = [quiz.title for quiz in quizzes]
    if form.validate_on_submit() and form.submit.data:
        quiz_file = form.labsheet_file.data

        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(quiz_file.read(2048))
        quiz_file.seek(0)  # Reset file pointer to the beginning

        if file_type not in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            flash('Only .xlsx files are allowed.', category='danger')
            return redirect(url_for('admin.add_quiz', module_id=module_id, quiz_id=quiz_id))
        
        else:
            # Read the Excel file
            quiz_data = pd.read_excel(quiz_file)

            # Clean column names to handle any discrepancies
            quiz_data.columns = quiz_data.columns.str.strip().str.lower()

            required_columns = ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option']
            allowed_columns = set(required_columns)

            uploaded_columns = set(quiz_data.columns)
            if uploaded_columns != allowed_columns:
                flash(f'Invalid columns detected. Expected columns: {", ".join(required_columns)}', category='danger')
                return redirect(url_for('admin.add_quiz', module_id=module_id, quiz_id=quiz_id))
            
            if quiz_data.empty:
                flash('The file is empty. Please upload a file with quiz data.', category='danger')
                return redirect(url_for('admin.add_quiz', module_id=module_id, quiz_id=quiz_id))
            
            missing_column_values = [column for column in ['question', 'option_a', 'option_b', 'option_c', 'option_d', 'correct_option'] if quiz_data[column].isna().any()]
            if missing_column_values:
                flash(f'The following columns contain missing values: {", ".join(missing_column_values)}. Please ensure all rows have values for these columns.', category='danger')
                return redirect(url_for('admin.add_quiz', module_id=module_id, quiz_id=quiz_id))
            
            # Validate that the correct_option column contains only A, B, C, or D
            allowed_options = {'A', 'B', 'C', 'D'}
            invalid_rows = []

            for index, row in quiz_data.iterrows():
                question_text = row.get('question')
                option_a = row.get('option_a')
                option_b = row.get('option_b')
                option_c = row.get('option_c')
                option_d = row.get('option_d')
                correct_option = row.get('correct_option')

                if not question_text or not option_a or not option_b or not option_c or not option_d or not correct_option:
                    flash(f'Invalid data: {row}', category='danger')
                    continue

                if correct_option not in allowed_options:
                    invalid_rows.append(index)
                    flash(f'Invalid correct answer option: {correct_option} in row {index + 2}', category='danger')
                    return redirect(url_for('admin.add_quiz', module_id=module_id, quiz_id=quiz_id))

                # Create a new quiz question
                new_quiz_question = QuizQuestion(
                    quiz_id=quiz_id,  # Ensure quiz_id is used here
                    question=question_text,
                    option_A=option_a,
                    option_B=option_b,
                    option_C=option_c,
                    option_D=option_d,
                    correct_option=correct_option
                )
                db.session.add(new_quiz_question)

        db.session.commit()
        flash('Questions added successfully!', category='success')
        return redirect(url_for('admin.quizzes_by_module', module_id=module_id, quiz_id=quiz_id))

    return render_template("add_quiz.html", user=current_user, form=form, module_id=module_id, quiz_id=quiz_id, titles=titles, current_week=current_week)



@admin.route('/questions/edit/<int:question_id>', methods=['GET', 'POST'])
@login_required
@session_timeout
def edit_question(question_id):
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))

    current_week,_=  get_current_week_and_time()
    question = QuizQuestion.query.get_or_404(question_id)
    form = EditQuestionForm(obj=question)

    if form.validate_on_submit():
        question.question = form.question.data
        question.option_A = form.option_A.data
        question.option_B = form.option_B.data
        question.option_C = form.option_C.data
        question.option_D = form.option_D.data
        question.correct_option = form.correct_option.data
        db.session.commit()

        flash('Question updated successfully!', category='success')
        return redirect(url_for('admin.quizzes_by_module', module_id=question.quiz.module_id, quiz_id=question.quiz_id))

    return render_template('edit_question.html', form=form, current_week=current_week)

@admin.route('/questions/delete/<int:question_id>', methods=['POST'])
@login_required
@session_timeout
def delete_question(question_id):
    if current_user.role != 'admin':
        flash("Unauthorised access", category='danger')
        return redirect(url_for('staff.dashboard') if current_user.role == 'staff' else url_for('student.dashboard'))


    form = DeleteQuestionForm()

    if form.validate_on_submit():
        # Retrieve the question to be deleted
        question = QuizQuestion.query.get_or_404(question_id)
        quiz_id = question.quiz_id
        module_id = question.quiz.module_id

        # Delete the question from the database
        db.session.delete(question)
        db.session.commit()

        flash('Question deleted successfully!', category='success')
        return redirect(url_for('admin.quizzes_by_module', module_id=module_id, quiz_id=quiz_id))

    flash('Error deleting question.', category='danger')
    return redirect(url_for('admin.quizzes_by_module', module_id=module_id, quiz_id=quiz_id))


@admin.route('/modules', methods=['GET'])
@login_required
@session_timeout
def view_modules():
    if current_user.role != 'admin':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('student.dashboard'))
    
    current_week,_=  get_current_week_and_time()
    modules = Module.query.all()

    return render_template('view_modules.html', user=current_user, modules=modules,current_week=current_week)

@admin.route('/modules/<int:module_id>/labsheets', methods=['GET'])
@login_required
@session_timeout
def view_labsheets(module_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('student.dashboard'))
    
    current_week,_=  get_current_week_and_time()
    module = Module.query.get_or_404(module_id)
    labsheets = Labsheet.query.filter_by(module_id=module_id).all()
    labsheet_count = len(labsheets)
    return render_template(
        'view_labsheets.html',
        current_week=current_week,
        user=current_user,
        module=module,
        labsheets=labsheets,
        labsheet_count=labsheet_count
    )




@admin.route('/labsheets/edit/<int:labsheet_id>', methods=['GET', 'POST'])
@login_required
@session_timeout
def edit_labsheet(labsheet_id):

    if current_user.role != 'admin':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('student.dashboard'))

    current_week,_=  get_current_week_and_time()
    labsheet = Labsheet.query.get_or_404(labsheet_id)
    questions = LabsheetQuestion.query.filter_by(labsheet_id=labsheet_id).all()
    
    labsheet_form = LabsheetForm(obj=labsheet)
    question_forms = [QuestionForm(obj=question) for question in questions]

    if request.method == 'POST':
        # Handle labsheet form submission
        if labsheet_form.validate_on_submit():
            labsheet.title = labsheet_form.title.data
            labsheet.description = labsheet_form.description.data

        # Handle question deletion
        delete_question_id = request.form.get('delete_question')
        if delete_question_id:
            question_to_delete = LabsheetQuestion.query.get(delete_question_id)
            if question_to_delete:
                db.session.delete(question_to_delete)

        # Handle question updates and additions
        for q_form in question_forms:
            if q_form.id.data:
                question = LabsheetQuestion.query.get(q_form.id.data)
                if question:
                    question.question_text = q_form.question_text.data
                    question.answer_text = q_form.answer_text.data
            else:
                new_question = LabsheetQuestion(
                    labsheet_id=labsheet_id,
                    question_text=q_form.question_text.data,
                    answer_text=q_form.answer_text.data
                )
                db.session.add(new_question)

        db.session.commit()
        flash('Labsheet and questions updated successfully!', category='success')
        return redirect(url_for('admin.view_labsheets', module_id=labsheet.module_id))

    return render_template(
        'edit_labsheet.html',
        labsheet=labsheet,
        current_week=current_week,
        labsheet_form=labsheet_form,
        question_forms=question_forms,
        module_id=labsheet.module_id
    )



@admin.route('/labsheets/<int:labsheet_id>/save_questions', methods=['POST'])
@login_required
@session_timeout
def save_questions(labsheet_id):
    labsheet = Labsheet.query.get_or_404(labsheet_id)
    current_week,_=  get_current_week_and_time()

    if request.method == 'POST':
        # Handle question deletion
        delete_question_id = request.form.get('delete_question')
        if delete_question_id:
            question_to_delete = LabsheetQuestion.query.get(delete_question_id)
            if question_to_delete:
                db.session.delete(question_to_delete)

        # Handle question updates and additions
        questions = LabsheetQuestion.query.filter_by(labsheet_id=labsheet_id).all()
        question_forms = [QuestionForm(obj=question) for question in questions]

        for q_form in question_forms:
            if q_form.id.data:
                question = LabsheetQuestion.query.get(q_form.id.data)
                if question:
                    question.question_text = q_form.question_text.data
                    question.answer_text = q_form.answer_text.data
            else:
                new_question = LabsheetQuestion(
                    labsheet_id=labsheet_id,
                    question_text=q_form.question_text.data,
                    answer_text=q_form.answer_text.data
                )
                db.session.add(new_question)

        db.session.commit()
        flash('Labsheet and questions updated successfully!', category='success')
        return redirect(url_for('admin.view_labsheets', module_id=labsheet.module_id))


    return redirect(url_for('admin.edit_labsheet', labsheet_id=labsheet_id))


@admin.route('/labsheets/<int:labsheet_id>/add_question', methods=['GET', 'POST'])
@login_required
@session_timeout
def add_question(labsheet_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('student.dashboard'))
    
    current_week,_=  get_current_week_and_time()
    labsheet = Labsheet.query.get_or_404(labsheet_id)
    lab_mod = labsheet.module_id
    module = Module.query.get_or_404(lab_mod)
    module_id = module.id
    
    form = QuestionForm()

    if form.validate_on_submit():
        new_question = LabsheetQuestion(
            labsheet_id=labsheet_id,
            question_text=form.question_text.data,
            answer_text=form.answer_text.data
        )
        db.session.add(new_question)
        db.session.commit()

        flash('New question added successfully!', category='success')
        return redirect(url_for('admin.edit_labsheet', labsheet_id=labsheet_id))

    return render_template('add_question.html', form=form, labsheet_id=labsheet_id, module=module, lab_mod=lab_mod, module_id=module_id, labsheet=labsheet,current_week=current_week)


@admin.route('/labsheets/delete_question/<int:question_id>', methods=['POST'])
@login_required
@session_timeout
def delete_labquestion(question_id):
    if current_user.role != 'admin':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('student.dashboard'))

    question = LabsheetQuestion.query.get_or_404(question_id)
    labsheet_id = question.labsheet_id
    db.session.delete(question)
    db.session.commit()

 
    flash('Question deleted successfully!', category='success')
    return redirect(url_for('admin.view_labsheets', module_id=question.labsheet.module_id))