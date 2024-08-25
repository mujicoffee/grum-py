from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app as app
from sqlalchemy import select
from flask_login import login_required, current_user
from .models import User, Classroom,Quiz,QuizQuestion, staff_classroom, Module, Labsheet, LabsheetQuestion
from .forms import AddStudentsForm, AddStudentsFileForm, LabsheetForm, QuestionForm
from .session import session_timeout
from .emails import send_student_account_setup_email
from .week import get_current_week_and_time
from . import db, bcrypt
import pandas as pd
import random
import string
import magic
import re

# Create a Blueprint for the authentication routes
staff = Blueprint('staff', __name__)



@staff.route('/classroom', methods=['GET'])
@login_required
@session_timeout
def classroom():
# Get the current week and time
    current_week, _ = get_current_week_and_time()

    # Step 1: Fetch all classrooms associated with the current user
    
    stmt = select(staff_classroom.c.classroom_id).where(staff_classroom.c.staff_id == current_user.id)
    result = db.session.execute(stmt)
    classroom_ids = [row[0] for row in result.fetchall()]

    # Step 2: Initialize an empty list to store classroom data
    classroom_data = []

    # Step 3: Fetch details for each classroom_id
    for classroom_id in classroom_ids:
        details = Classroom.query.filter_by(id=classroom_id).first()
        
        if details:
            student_count = len(details.students)  # Assuming Classroom has a 'students' relationship
            classroom_data.append({
                'code': details.code, 
                'student_count': student_count
            })

        # Now `classroom_data` contains the code and student count for each classroom


    return render_template("classroom.html", 
                           user=current_user, 
                           classroom_data=classroom_data,
                           current_week=current_week,)


@staff.route('/classroom/<string:code>', methods=['GET'])
@login_required
@session_timeout
def classroom_details(code):
    
    
    if current_user.role != 'staff':
        flash("Unauthorised access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))
    
    classroom = Classroom.query.filter_by(code=code).first_or_404()

    # Get the list of classroom IDs the current user has access to
    stmt = select(staff_classroom.c.classroom_id).where(staff_classroom.c.staff_id == current_user.id)
    result = db.session.execute(stmt)
    classroom_ids = {row[0] for row in result.fetchall()}  # Using a set for efficient membership checking

    # Check if the ID of the requested classroom is in the list of accessible classroom IDs
    if classroom.id not in classroom_ids:
        flash("You do not have access to this classroom.", category='danger')
        return redirect(url_for('staff.classroom'))
    # Retrieve the classroom details by code (e.g. P01)
    current_week, _ = get_current_week_and_time()

    classroom = Classroom.query.filter_by(code=code).first_or_404()
    students = classroom.students
    staff = classroom.staff

    # Create a list of student data
    
    students_data = []
    for student in students:
        # Retrieve the completed quizzes from each student
        completed_quizzes = student.completed_quizzes.split(',') if student.completed_quizzes else []
        completed_modules = student.completed_modules.split(',') if student.completed_modules else []
        completed_modules = [int(i) for i in completed_modules if i.isdigit()]
        completed_quizzes = [int(q) for q in completed_quizzes if q.isdigit()]

        
        students_data.append({
            'student': student,
            'completed_modules': completed_modules,
            'completed_quizzes': completed_quizzes
        })
    student_count = len(students_data)

    return render_template("classroom_details.html", user=current_user, classroom=classroom, students_data=students_data, staff=staff, student_count=student_count,current_week=current_week)


@staff.route('/classroom/<string:code>/search', methods=['GET'])
@login_required
@session_timeout
def search_students(code):
    if current_user.role != 'staff':
        flash("Unauthorised access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))

    classroom = Classroom.query.filter_by(code=code).first_or_404()
    stmt = select(staff_classroom.c.classroom_id).where(staff_classroom.c.staff_id == current_user.id)
    result = db.session.execute(stmt)
    classroom_ids = {row[0] for row in result.fetchall()}  # Using a set for efficient membership checking

    # Check if the ID of the requested classroom is in the list of accessible classroom IDs
    if classroom.id not in classroom_ids:
        flash("You do not have access to this classroom.", category='danger')
        return redirect(url_for('staff.classroom'))

    # Retrieve the classroom details by code (e.g. P01)
    current_week, _ = get_current_week_and_time()

    query = request.args.get('query', '').strip()

    if query:
        # Search in the User model based on classroom_id and name
        students = User.query.filter(
            User.classroom_id == classroom.id,
            User.name.ilike(f'%{query}%')
        ).all()
    else:
        # Get all users in the classroom if no search query is provided
        students = User.query.filter_by(classroom_id=classroom.id).all()
    
    # Process students data as you did previously
    students_data = []
    for student in students:
        completed_quizzes = student.completed_quizzes.split(',') if student.completed_quizzes else []
        completed_modules = student.completed_modules.split(',') if student.completed_modules else []
        students_data.append({
            'student': student,
            'completed_modules': [int(i) for i in completed_modules if i.isdigit()],
            'completed_quizzes': [int(q) for q in completed_quizzes if q.isdigit()]
        })

    # Sort staff data alphabetically by name
    staff = User.query.filter(User.classroom_id == classroom.id).all()
    staff = sorted(staff, key=lambda s: s.name.lower())

    students_data = sorted(students_data, key=lambda sd: sd['student'].name.lower())

    if not students_data:
        flash(f'No students found for "{query}".', 'warning')

    return render_template('classroom_details.html', classroom=classroom, students_data=students_data, student_count=len(students_data), current_week=current_week)


@staff.route('/classroom/<string:code>/add-students', methods=['GET', 'POST'])
@login_required
@session_timeout
def add_students(code):
    # Check if the current user is staff
    if current_user.role != 'staff':
        flash("Unauthorised access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))

    # Retrieve the classroom details by code (e.g. P01)
    classroom = Classroom.query.filter_by(code=code).first_or_404()
    stmt = select(staff_classroom.c.classroom_id).where(staff_classroom.c.staff_id == current_user.id)
    result = db.session.execute(stmt)
    classroom_ids = {row[0] for row in result.fetchall()}  # Using a set for efficient membership checking

    # Check if the ID of the requested classroom is in the list of accessible classroom IDs
    if classroom.id not in classroom_ids:
        flash("You do not have access to this classroom.", category='danger')
        return redirect(url_for('staff.classroom'))
    
    current_week, _ = get_current_week_and_time()
    # Initialise the add students Excel file form (multiple)
    form_students_file = AddStudentsFileForm()
    # Initialise the add student form (individual)
    form_students = AddStudentsForm()

    # Load the pepper value from the config
    pepper = app.config.get('PEPPER', '')

    # Handle form submissions for adding students using Excel
    if form_students_file.validate_on_submit() and form_students_file.submit.data:
        # Retrieve the uploaded file
        students_file = form_students_file.students_file.data

        # Check if the file is an Excel file using file headers
        mime = magic.Magic(mime=True)
        file_type = mime.from_buffer(students_file.read(2048))
        students_file.seek(0)  # Reset file pointer to the beginning

        if file_type not in ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']:
            flash('Only .xlsx files are allowed.', category='danger')
            return redirect(url_for('staff.add_students', code=code))

        else:
            # Read the Excel file
            students_data = pd.read_excel(students_file)

            # Clean column names to handle any discrepancies
            students_data.columns = students_data.columns.str.strip().str.lower()

            required_columns = ['name', 'email']
            allowed_columns = set(required_columns)

            uploaded_columns = set(students_data.columns)
            if uploaded_columns != allowed_columns:
                flash(f'Invalid columns detected. Expected columns: {", ".join(required_columns)}', category='danger')
                return redirect(url_for('staff.add_students', code=code))
            
            if students_data.empty:
                flash('The file is empty. Please upload a file with student data.', category='danger')
                return redirect(url_for('staff.add_students', code=code))
            
            missing_column_values = [column for column in ['name', 'email'] if students_data[column].isna().any()]
            if missing_column_values:
                flash(f'The following columns contain missing values: {", ".join(missing_column_values)}. Please ensure all rows have values for these columns.', category='danger')
                return redirect(url_for('staff.add_students', code=code))
            
            duplicate_emails = students_data[students_data.duplicated(['email'], keep=False)]
            if not duplicate_emails.empty:
                flash(f'The following emails are duplicated: {", ".join(duplicate_emails["email"].unique())}. Please ensure all emails are unique and try again.', category='danger')
                return redirect(url_for('staff.add_students', code=code))
            
            # Extract emails from the uploaded file
            all_emails = set(students_data['email'])
            # Get existing emails from the database
            existing_emails = set(user.email for user in User.query.filter(User.email.in_(all_emails)).all())
            
            # Determine if there are any existing emails from the uploaded file
            emails_exist = all_emails & existing_emails
            if emails_exist:
                flash(f'The following emails already exist in the system and cannot be processed: {", ".join(emails_exist)}', category='danger')
                return redirect(url_for('staff.add_students', code=code))
            
            # Check if the email column only contains emails with the domain @student.tp.edu.sg
            student_emails = students_data['email'].str.contains('@student\.tp\.edu\.sg$')
            if not student_emails.all():
                flash(f'Invalid email domains detected. Student emails must be from @student.tp.edu.sg.', category='danger')
                return redirect(url_for('staff.add_students', code=code))

            if all_emails.isdisjoint(existing_emails):
                # Iterate over the rows in the Excel file
                for index, row in students_data.iterrows():
                    # Retrieve the student's name and email
                    name = row.get('name')
                    email = row.get('email')

                    # Generate a random temporary password for each student 
                    password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=12))
                    # Apply pepper and hash the password
                    hashed_password = bcrypt.generate_password_hash(password + pepper).decode('utf-8')
                    
                    # Add the student to the database with the temporary password
                    new_user = User(email=email, name=name, password=hashed_password, role='student', classroom_id=classroom.id, first_login='Yes')
                    db.session.add(new_user)
                    db.session.commit()

                    # Send an email to the student with their temporary password
                    send_student_account_setup_email(email, name, password)

                flash("Students added successfully.", category='success')
                return redirect(url_for('staff.classroom_details', code=code))

    # Handle form submissions for adding students individually
    elif form_students.validate_on_submit() and form_students.submit.data:
        # Retrieve the student's name and email
        name = form_students.students_name.data
        email = form_students.students_email.data

        # Check if the email input only contains emails with the domain @student.tp.edu.sg
        if not re.match(r'.+@student\.tp\.edu\.sg$', email):
            flash('Invalid email domain. Student emails must be from @student.tp.edu.sg.', category='danger')
            return redirect(url_for('staff.add_students', code=code))

        # Validation check to ensure both fields are completed
        if not name or not email:
            flash('Both name and email are required.', category='danger')
            return redirect(url_for('staff.add_students', code=code))

        # Check if the student already exists
        if User.query.filter_by(email=email).first():
            flash(f"User with email {email} already exists.", category='danger')
            return redirect(url_for('staff.add_students', code=code))

        # Generate a random temporary password for each student
        password = ''.join(random.choices(string.ascii_letters + string.digits + string.punctuation, k=12))
        # Apply pepper and hash the password
        hashed_password = bcrypt.generate_password_hash(password + pepper).decode('utf-8')

        # Add the student to the database with the temporary password
        new_user = User(email=email, name=name, password=hashed_password, role='student', classroom_id=classroom.id, first_login='Yes')
        db.session.add(new_user)
        db.session.commit()

        # Send an email to the student with their temporary password
        send_student_account_setup_email(email, name, password)

        flash(f'Student {name} ({email}) added successfully.', category='success')
        return redirect(url_for('staff.classroom_details', code=code))


    return render_template("add_students.html", user=current_user, classroom=classroom, form_students_file=form_students_file, form_students=form_students, current_week=current_week)

@staff.route('/classroom/<string:code>/remove-student/<int:student_id>', methods=['POST'])
@login_required
@session_timeout
def remove_student(code, student_id):
    # Check if the current user is staff
    if current_user.role != 'staff':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))

    # Retrieve the classroom details by code (e.g. P01)
    classroom = Classroom.query.filter_by(code=code).first_or_404()
    stmt = select(staff_classroom.c.classroom_id).where(staff_classroom.c.staff_id == current_user.id)
    result = db.session.execute(stmt)
    classroom_ids = {row[0] for row in result.fetchall()}  # Using a set for efficient membership checking

    # Check if the ID of the requested classroom is in the list of accessible classroom IDs
    if classroom.id not in classroom_ids:
        flash("You do not have access to this classroom.", category='danger')
        return redirect(url_for('staff.classroom'))
    # Retrieve the student by their ID
    student = User.query.filter_by(id=student_id, role='student', classroom_id=classroom.id).first()

    # Check if the student exists and belong to the class
    if not student:
        flash("Student does not belong to this classroom.", category='danger')
        return redirect(url_for('staff.classroom_details', code=code))

    # Remove the student from the database
    db.session.delete(student)
    db.session.commit()

    flash(f'Student {student.name} ({student.email}) removed successfully.', category='success')
    return redirect(url_for('staff.classroom_details', code=code))


@staff.route('/modules', methods=['GET'])
@login_required
@session_timeout
def view_modules():
    if current_user.role != 'staff':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))
    
    current_week,_=  get_current_week_and_time()
    modules = Module.query.all()

    return render_template('view_modules_staff.html', user=current_user, modules=modules,current_week=current_week)



@staff.route('/modules/<int:module_id>/labsheets', methods=['GET'])
@login_required
@session_timeout
def view_labsheets(module_id):
    if current_user.role != 'staff':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))
    
    current_week,_=  get_current_week_and_time()
    module = Module.query.get_or_404(module_id)
    labsheets = Labsheet.query.filter_by(module_id=module_id).all()
    labsheet_count = len(labsheets)
    return render_template(
        'view_labsheets_staff.html',
        current_week=current_week,
        user=current_user,
        module=module,
        labsheets=labsheets,
        labsheet_count=labsheet_count
    )
    
@staff.route('/labsheets/edit/<int:labsheet_id>', methods=['GET'])
@login_required
@session_timeout
def view_labsheet_questions(labsheet_id):
    if current_user.role != 'staff':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))

    current_week, _ = get_current_week_and_time()
    labsheet = Labsheet.query.get_or_404(labsheet_id)
    questions = LabsheetQuestion.query.filter_by(labsheet_id=labsheet_id).all()

    labsheet_form = LabsheetForm(obj=labsheet)
    question_forms = [QuestionForm(obj=question) for question in questions]

    return render_template(
        'view_labsheet_staff.html',  
        labsheet=labsheet,
        current_week=current_week,
        labsheet_form=labsheet_form,
        question_forms=question_forms,
        module_id=labsheet.module_id
    )


@staff.route('/quizzes', methods=['GET'])
@login_required
@session_timeout
def quizzes():
    if current_user.role != 'staff':
        flash("Unauthorised access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))
    current_week, _ = get_current_week_and_time()
    quizzes = Quiz.query.all()
    quizzes_by_module = {}
    
    for quiz in quizzes:
        module_id = quiz.module_id
        if module_id not in quizzes_by_module:
            quizzes_by_module[module_id] = []
        quizzes_by_module[module_id].append(quiz)
    
    return render_template("staff_quizzes.html", user=current_user, quizzes_by_module=quizzes_by_module, current_week=current_week)

@staff.route('/quizzes/module/<int:module_id>/quiz/<int:quiz_id>', methods=['GET'])
@login_required
@session_timeout
def quizzes_by_module(module_id, quiz_id):
    if current_user.role != 'staff':
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('admin.dashboard') if current_user.role == 'admin' else url_for('student.dashboard'))

    # Check if the module_id exists
    module_exists = Quiz.query.filter_by(module_id=module_id).first()
    if not module_exists:
        flash("Module not found.", category='danger')
        return redirect(url_for('staff.quizzes'))
    
    quizzes = Quiz.query.filter_by(module_id=module_id).all()
    titles = [quiz.title for quiz in quizzes]
    
    # Pagination for quizzes
    page = request.args.get('page', 1, type=int)
    per_page = 5
    quizzes_pagination = Quiz.query.filter_by(module_id=module_id).paginate(page=page, per_page=per_page, error_out=False)
    
    current_week, _ = get_current_week_and_time()
    
    # Handle quiz_id and search term
    search_term = request.args.get('search', '', type=str)
    questions_page = request.args.get('questions_page', 1, type=int)
    questions_per_page = 10

    quiz_questions_pagination = None

    if quiz_id:
        # Check if the quiz_id is valid for the given module_id
        quiz = Quiz.query.filter_by(id=quiz_id, module_id=module_id).first()
        if not quiz:
            flash("Invalid quiz ID.", category='danger')
            return redirect(url_for('staff.quizzes'))

        # Filter questions based on quiz_id and search term
        query = QuizQuestion.query.filter_by(quiz_id=quiz_id)
        if search_term:
            query = query.filter(QuizQuestion.question.ilike(f'%{search_term}%'))
        quiz_questions_pagination = query.paginate(page=questions_page, per_page=questions_per_page, error_out=False)
    
    else:
        # If no quiz_id is provided, redirect to quizzes list or handle accordingly
        flash("No quiz ID provided.", category='danger')
        return redirect(url_for('staff.quizzes'))

    return render_template(
        "questions_in_quizzes.html",
        user=current_user,
        titles=titles,
        current_week=current_week,
        module_id=module_id,
        quizzes_pagination=quizzes_pagination,
        quiz_id=quiz_id,
        quiz_questions_pagination=quiz_questions_pagination,
        search_query=search_term  # Correct variable name in the template
    )
