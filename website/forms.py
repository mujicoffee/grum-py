from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, EmailField, FileField, SelectField, SubmitField, HiddenField, RadioField, TextAreaField, IntegerField, BooleanField, FieldList, DateField
from wtforms.validators import DataRequired, InputRequired, NumberRange
from flask_wtf.file import FileRequired

# Define a form class for login
class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

# To be removed / modified later
class SignUpForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    name = StringField('Name', validators=[DataRequired()])
    passwordSet = PasswordField('Password', validators=[DataRequired()])
    passwordConfirm = PasswordField('Confirm Password', validators=[DataRequired()])
    role = SelectField('Role', choices=[('student', 'Student'), ('staff', 'Staff')], validators=[DataRequired()])
    image_file = FileField('Profile Picture', validators=[FileRequired()])

# Define a form class for OTP verification
class OTPForm(FlaskForm):
    otp = StringField('OTP', validators=[DataRequired()])

# Define a form class for change password
class ChangePasswordForm(FlaskForm):
    newPassword = PasswordField('New Password', validators=[DataRequired()])
    confirmPassword = PasswordField('Confirm Password', validators=[DataRequired()])

class SetupProfilePicForm(FlaskForm):
   profilePic = HiddenField('profilePic')

class ChangepfpForm(FlaskForm):
   profilePic = HiddenField('profilePic')
    
# Define a class for forget password
class ForgetPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])

# Define a class for reset password
class ResetPasswordForm(FlaskForm):
    newPassword = PasswordField('New Password', validators=[DataRequired()])
    confirmPassword = PasswordField('Confirm Password', validators=[DataRequired()])

class UploadLabsheetForm(FlaskForm):
    labsheet_file = FileField('Labsheet File', validators=[DataRequired()])
    submit = SubmitField('Upload Labsheets')

class AddStudentsFileForm(FlaskForm):
    students_file = FileField('Upload Students File', validators=[DataRequired()])
    submit = SubmitField('Add Students')

class AddStudentsForm(FlaskForm):
    students_name = StringField('Name of Student', validators=[DataRequired()])
    students_email = EmailField('Email of Student', validators=[DataRequired()])
    submit = SubmitField('Add Student')

class AddStaffFileForm(FlaskForm):
    staff_file = FileField('Upload Staff File', validators=[DataRequired()])
    submit = SubmitField('Add Staff')

class AddStaffForm(FlaskForm):
    staff_name = StringField('Name of Staff', validators=[DataRequired()])
    staff_email = EmailField('Email of Staff', validators=[DataRequired()])
    p01 = BooleanField('P01')
    p02 = BooleanField('P02')
    p03 = BooleanField('P03')
    p04 = BooleanField('P04')
    p05 = BooleanField('P05')
    p06 = BooleanField('P06')
    p07 = BooleanField('P07')
    p08 = BooleanField('P08')
    submit = SubmitField('Add Staff')

class QuizForm(FlaskForm):
    csrf_token = HiddenField()
    quiz_id = HiddenField()
    selected_option = RadioField('Option', choices=[
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ], validators=[InputRequired()])

class UploadQuizForm(FlaskForm):
    labsheet_file = FileField('Upload Quiz Excel File', validators=[FileRequired()])
    submit = SubmitField('Submit')
    
class RestartQuizForm(FlaskForm):
    restart_quiz = SubmitField('Restart Quiz')
    back_to_dashboard = SubmitField('Back to Dashboard')
    
class EditQuestionForm(FlaskForm):
    question = StringField('Question', validators=[DataRequired()])
    option_A = StringField('Option A', validators=[DataRequired()])
    option_B = StringField('Option B', validators=[DataRequired()])
    option_C = StringField('Option C', validators=[DataRequired()])
    option_D = StringField('Option D', validators=[DataRequired()])
    correct_option = SelectField('Correct Option', choices=[
        ('A', 'A'),
        ('B', 'B'),
        ('C', 'C'),
        ('D', 'D')
    ], validators=[DataRequired()])
    submit = SubmitField('Save changes')

class DeleteQuestionForm(FlaskForm):
    submit = SubmitField('Delete')

class CurrentModForm(FlaskForm):
    next_lab_module_id = IntegerField('Next Lab Module ID', validators=[DataRequired()])
    lab_module_id = IntegerField('Lab Module ID', validators=[DataRequired()])
    submit = SubmitField('Update')


class AddModuleForm(FlaskForm):
    title = StringField('Module Title', validators=[DataRequired()])
    description = TextAreaField('Module Description')
    week_number = IntegerField('Week Number', validators=[DataRequired()])
    labsheet_titles = FieldList(StringField('Labsheet Title'), min_entries=1)
    labsheet_descriptions = FieldList(TextAreaField('Labsheet Description'), min_entries=1)


class AddLabsheetForm(FlaskForm):
    title = StringField('Labsheet Title', validators=[DataRequired()])
    description = TextAreaField('Labsheet Description')

class RankingWeekForm(FlaskForm):
    ranking_week = SelectField('Ranking Week', choices=[(str(i), f'Ranking for week {i}') for i in range(1, 9)], validators=[DataRequired()])
    
class LabsheetForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    submit = SubmitField('Update Labsheet')

class QuestionForm(FlaskForm):
    id = HiddenField('ID')
    question_text = TextAreaField('Question', validators=[DataRequired()])
    answer_text = TextAreaField('Answer', validators=[DataRequired()])
    submit = SubmitField('Save Question')

class StartDateForm(FlaskForm):
    start_date = DateField('Start Date', format='%Y-%m-%d', validators=[DataRequired()])
    submit = SubmitField('Save')