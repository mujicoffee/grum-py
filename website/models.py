from . import db
from flask_login import UserMixin
from datetime import datetime


# Association table for the many-to-many relationship between Staff and Classroom
staff_classroom = db.Table('staff_classroom',
    db.Column('staff_id', db.Integer, db.ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True),
    db.Column('classroom_id', db.Integer, db.ForeignKey('classroom.id', onupdate='CASCADE', ondelete='CASCADE'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    classroom_id = db.Column(db.Integer, db.ForeignKey('classroom.id'), nullable=True)  # Only for students
    role = db.Column(db.String(50), nullable=False)  # 'student' or 'staff'
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    last_password_change = db.Column(db.DateTime, nullable=True)
    is_active = db.Column(db.String(5), default='Yes', nullable=False)
    deactivation_time = db.Column(db.DateTime, nullable=True)
    first_login = db.Column(db.String(5), default='Yes', nullable=False)
    login_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_login_time = db.Column(db.DateTime)
    otp = db.Column(db.String(150))
    otp_attempts = db.Column(db.Integer, default=0, nullable=False)
    resend_otp_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_otp_time = db.Column(db.DateTime)
    forget_password_attempts = db.Column(db.Integer, default=0, nullable=False)
    last_forget_password_time = db.Column(db.DateTime)
    reset_password_token = db.Column(db.String(100), unique=True)
    last_reset_password_time = db.Column(db.DateTime)
    session_token = db.Column(db.String(255), unique=True, nullable=True)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    weekly_score = db.Column(db.Text)
    total_score = db.Column(db.Integer, default=0, nullable=False)   
    completed_modules = db.Column(db.Text)
    completed_quizzes = db.Column(db.Text)
    current_question_index = db.Column(db.Integer, nullable=False, default=0)
    lives = db.Column(db.Integer, nullable=False, default=3)
    current_module = db.Column(db.Integer, nullable=False, default=1)
    current_quiz = db.Column(db.Integer, nullable=False,default=1)

    password_history = db.Column(db.Text, nullable=True, default='[]')

    # Relationship to the Classroom table for students
    student_user = db.relationship('Classroom', back_populates='students', overlaps="classroom,student_user")

    # Relationship to the Classroom table for staff (many-to-many)
    staff_user = db.relationship('Classroom', secondary=staff_classroom, lazy='subquery',
                                 back_populates='staff', overlaps="classroom,staff_user")

class AdminSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    start_date = db.Column(db.DateTime, nullable=False)

class Classroom(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(5), unique=True, nullable=False)
    
    # Relationship to the User table (students)
    students = db.relationship('User', back_populates='student_user', overlaps="classroom,student_user", cascade="all, delete-orphan")
    
    # Relationship to the User table (staff, many-to-many)
    staff = db.relationship('User', secondary=staff_classroom, lazy='subquery',
                            back_populates='staff_user', overlaps="classroom,staff_user")
    
class Logs(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_role = db.Column(db.String(50), nullable=False)
    classroom_code = db.Column(db.String(5), nullable=True)  # Add this line
    status =  db.Column(db.String(10), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False)  # e.g., "Login", "Update", "Delete"
    description = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.now, nullable=False)
    
    user = db.relationship('User', backref=db.backref('logs', lazy=True))

class Module(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    week_number = db.Column(db.Integer, nullable=False)

class Labsheet(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    module = db.relationship('Module', backref=db.backref('labsheet', lazy=True, cascade='all, delete-orphan'))


class LabsheetQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    labsheet_id = db.Column(db.Integer, db.ForeignKey('labsheet.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    answer_text = db.Column(db.Text)
    labsheet = db.relationship('Labsheet', backref=db.backref('labsheet_question', lazy=True, cascade='all, delete-orphan'))


class Quiz(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    module_id = db.Column(db.Integer, db.ForeignKey('module.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    locked = db.Column(db.Boolean, default=True)  # Controls access
    boss_file = db.Column(db.String(255), nullable=True)  # Add this line
    boss_width = db.Column(db.Integer, nullable=True)  # Add this line
    module = db.relationship('Module', backref=db.backref('quizzes', lazy=True, cascade='all, delete-orphan'))
    
class QuizQuestion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    option_A = db.Column(db.String(255), nullable=False)
    option_B = db.Column(db.String(255), nullable=False)
    option_C = db.Column(db.String(255), nullable=False)
    option_D = db.Column(db.String(255), nullable=False)
    correct_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    marks = db.Column(db.Integer, nullable=False, default=5)
    quiz = db.relationship('Quiz', backref=db.backref('questions', lazy=True, cascade='all, delete-orphan'))

class TakeQuizAnswer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    quiz_id = db.Column(db.Integer, db.ForeignKey('quiz.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey('quiz_question.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    selected_option = db.Column(db.String(1), nullable=False)  # 'A', 'B', 'C', or 'D'
    attempt_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    score = db.Column(db.Integer)
    lives = db.Column(db.Integer, nullable=False, default=3)
    user = db.relationship('User', backref=db.backref('quiz_attempts', lazy=True, cascade='all, delete-orphan'))
    quiz = db.relationship('Quiz', backref=db.backref('attempts', lazy=True, cascade='all, delete-orphan'))
    question = db.relationship('QuizQuestion')

class Ranking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', onupdate='CASCADE', ondelete='CASCADE'), nullable=False)
    week_number = db.Column(db.Integer, nullable=False, default=1)  # Default to 1
    score = db.Column(db.Integer, nullable=False)
    cumulative_score = db.Column(db.Integer, nullable=False,default=0)  # Added cumulative_score field
    module_id = db.Column(db.Integer, nullable=False, default=1)  # Default to 1
    ranking_time = db.Column(db.DateTime)
    user = db.relationship('User', backref=db.backref('ranking', lazy=True, cascade='all, delete-orphan'))