import pytz
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, abort, jsonify
from flask_login import login_required, current_user
from .models import *
from datetime import datetime
from .session import session_timeout
from .forms import QuizForm, RestartQuizForm, CurrentModForm, RankingWeekForm, ChangepfpForm
from .week import get_current_week_number
import logging
import random
import json

student = Blueprint('student', __name__)

# Create a timezone object for Singapore Time
sg_tz = pytz.timezone('Asia/Singapore')

def unlock_next_module(user):
    # Ensure we have a current module and it is not the last module
    if user.current_module and user.current_module < 8:
        # Check if the user's weekly_score is 100
        weekly_scores = json.loads(user.weekly_score) if user.weekly_score else {}
        current_week_score = weekly_scores.get(str(get_current_week_number()), 0)

        # Get the current week number
        current_week = get_current_week_number()

        # Unlock the next module if the user has a score of 100 or is progressing to the next week
        if current_week_score >= 100 or current_week > user.current_module:
            next_module_id = user.current_module + 1
            next_module = Module.query.filter_by(id=next_module_id).first()

            if next_module:
                next_module.locked = False
                user.current_module = next_module_id
                db.session.commit()
                print(f"Unlocked module {next_module_id}")
            else:
                print(f"No module found with ID {next_module_id}")
        else:
            print("Weekly score is not enough to unlock the next module or it's not the right week to unlock")
    else:
        print("Current module is None or already at the last module")




def mark_quiz_complete(user, quiz_id):
    if user.completed_quizzes:
        completed_quizzes = user.completed_quizzes.split(',')
    else:
        completed_quizzes = []

    if str(quiz_id) not in completed_quizzes:
        completed_quizzes.append(str(quiz_id))
        user.completed_quizzes = ','.join(completed_quizzes)
        db.session.commit()



def get_start_of_week(date):
    if not isinstance(date, datetime):
        raise TypeError("The date must be a datetime object")
    
    # Ensure 'date' is timezone-aware
    if date.tzinfo is None:
        date = sg_tz.localize(date)
    
    start_of_week = date - timedelta(days=date.weekday())
    return start_of_week



def update_cumulative_score(user_id, week_number, total_marks):
    rankings = Ranking.query.filter_by(user_id=user_id, week_number=week_number).all()
    cumulative_score = total_marks

    for ranking in rankings:
        cumulative_score += ranking.score

    if rankings:
        for ranking in rankings:
            ranking.cumulative_score = cumulative_score
    else:
        ranking = Ranking(
            user_id=user_id,
            week_number=week_number,
            score=total_marks,
            cumulative_score=cumulative_score,
            ranking_time=datetime.now(sg_tz)  # Ensure this is timezone-aware
        )
        db.session.add(ranking)

    db.session.commit()




def update_ranking_and_scores(user, quiz_id, total_marks):
    current_week = get_current_week_number()

    # Initialize weekly_scores if not present
    if user.weekly_score:
        weekly_scores = json.loads(user.weekly_score)
    else:
        weekly_scores = {}

    # Update the highest weekly score
    highest_weekly_score = max(weekly_scores.get(str(current_week), 0), total_marks)
    weekly_scores[str(current_week)] = highest_weekly_score
    user.weekly_score = json.dumps(weekly_scores)

    # Calculate the new total score by summing the highest scores for all weeks
    new_total_score = sum(weekly_scores.get(str(week), 0) for week in range(1, 9))
    user.total_score = new_total_score

    # Update the ranking
    ranking = Ranking.query.filter_by(user_id=user.id, week_number=current_week).first()
    if ranking:
        ranking.score = highest_weekly_score
        ranking.cumulative_score = new_total_score
    else:
        ranking = Ranking(
            user_id=user.id,
            week_number=current_week,
            score=highest_weekly_score,
            cumulative_score=new_total_score,
            module_id=user.current_module,
            ranking_time=datetime.now(sg_tz)
        )
        db.session.add(ranking)

    db.session.commit()



@student.route('/dashboard', defaults={'week_number': None})
@student.route('/dashboard/<int:week_number>')
@login_required
@session_timeout
def dashboard(week_number):
    if current_user.role == 'student':
        modules = Module.query.all()
        quiz = Quiz.query.all()
       
        if week_number is None:
            current_week = get_current_week_number()
        else:
            current_week = week_number

        if current_week < 1 or current_week > 8:
            current_week = get_current_week_number()

        rankings = Ranking.query.filter_by(week_number=current_week).order_by(Ranking.score.desc()).all()
        ranking_data = [
            {
                'name': User.query.get(rank.user_id).name, 
                'pfp': User.query.get(rank.user_id).image_file,
                'userid': User.query.get(rank.user_id).id,
                'score': rank.score, 
                'cumulative_score': rank.cumulative_score
            } 
                         
            for rank in rankings
        ]

        completed_quizzes = [int(quiz) for quiz in current_user.completed_quizzes.split(',')] if current_user.completed_quizzes else []
        completed_modules = [int(modules) for modules in current_user.completed_modules.split(',')] if current_user.completed_modules else []
        
        progBarQuiz = len(completed_quizzes)
        progBarModule = len(completed_modules)
        progbar = str ( int(progBarQuiz) + int(progBarModule))
        current_time = datetime.now(sg_tz).strftime('%A %d %B %H:%M:%S')
        
        return render_template('student_dashboard.html', 
                               current_user=current_user,
                               modules=modules, 
                               quiz=quiz,
                               rankings=ranking_data, 
                               completed_modules=completed_modules,
                               completed_quizzes=completed_quizzes, 
                               progBarQuiz = progBarQuiz,
                               progBarModule = progBarModule,
                               progbar=progbar,
                               current_week=current_week,
                               current_time=current_time,
                               int = int
                               )  # Pass current_time to the template
    else:
        flash("Unauthorized access.", category='danger')
        return redirect(url_for('auth.logout'))

@student.route('/changeProfilePic', methods=['GET', 'POST'])
@login_required
@session_timeout
def changePFP():
    current_profile = User.query.filter_by(email=current_user.email).first()
    form = ChangepfpForm()

    if current_profile:
        current_image_file = current_profile.image_file
    else:
        current_image_file = None

    if form.validate_on_submit():
        # Handle the form submission
        profile_picture = request.form.get('profilePic')
        current_user.image_file = profile_picture  # Update the user's profile picture

        try:
            db.session.commit()
            flash('Profile picture updated successfully!', 'success')
        except Exception as e:
            db.session.rollback()  # Rollback if something goes wrong
            flash('An error occurred. Please try again.', 'error')
        
        return redirect(url_for('student.dashboard'))

    # If GET request or form validation fails, render the form
    profile_pics = ['angry.png', 'crying.png', 'goofy.png', 'sadness.png', 'shocked.png', 'smile big.png', 'smile.png', 'meme1.png','meme2.png','meme3.png','meme4.png']
    return render_template('changeProfile.html', form=form, profile_pics=profile_pics, current_image_file=current_image_file)

@student.route('/display-quiz', methods=['GET'])
@login_required
@session_timeout
def displayQuiz():
       modules = Module.query.all()
       completed_quizzes = current_user.completed_quizzes.split(',') if current_user.completed_quizzes else []
       current_week = get_current_week_number()
       return render_template('display_quiz.html', completed_quizzes=completed_quizzes, modules=modules, current_week=current_week)

@student.route('/modules', defaults={'module_id': None})
@student.route('/modules/<int:module_id>')
@login_required
@session_timeout
def modules(module_id):
    
    current_week = get_current_week_number()
    if module_id:
        module = Module.query.get_or_404(module_id)
        labsheets = Labsheet.query.filter_by(module_id=module_id).all()
        return render_template('module_labsheets.html', module=module, labsheets=labsheets)
    else:
        all_modules = Module.query.all()
        modules_data = [{'module': module, 'labsheets': Labsheet.query.filter_by(module_id=module.id).all()} for module in all_modules]
        
        return render_template('modules.html', modules_data=modules_data, current_week=current_week)



@student.route('/module_labsheets/<int:module_id>', methods=['GET'])
@login_required
@session_timeout
def module_labsheets(module_id):
    labsheets = Labsheet.query.filter_by(module_id=module_id).all()
    module = Module.query.get_or_404(module_id)
    return render_template('module_labsheets.html', labsheets=labsheets, module=module)



@student.route('/labsheet/<int:labsheet_id>', methods=['GET'])
@login_required
@session_timeout
def labsheet(labsheet_id):
    
    labsheet = Labsheet.query.get_or_404(labsheet_id)
    questions = LabsheetQuestion.query.filter_by(labsheet_id=labsheet_id).all()
    module_id = labsheet.module_id
    current_week = get_current_week_number()

    # Calculate the next labsheet ID
    nextlabsheetId = labsheet_id + 1
    # Get the next labsheet if it exists
    next_labsheet = Labsheet.query.filter_by(id=nextlabsheetId).first()
    form = CurrentModForm()

    if (module_id <= current_week and module_id <= current_user.current_module):
        

        return render_template('labsheet.html', labsheet=labsheet, questions=questions, module_id=module_id, current_week=current_week, form=form, next_labsheet=next_labsheet)
   
    else:

        if (module_id > current_week):
            flash(f"It is currently week {current_week}, and you do not have access to the content yet.", category='info')
            return redirect(url_for('student.modules'))  # Redirect to the 'modules' route
        
        elif ( module_id > current_user.current_module):
            flash(f"You have not completed week {current_user.current_module} yet. Please do so before you can access it.", category='info')
            return redirect(url_for('student.modules'))  # Redirect to the 'modules' route
        
        else:
            flash("Module is locked and you cannot access it", category='info')
            return redirect(url_for('student.modules'))  # Redirect to the 'modules' route
        

@student.route('/update_and_redirect', methods=['POST', 'GET'])
@login_required
@session_timeout
def update_and_redirect():
    form = CurrentModForm()
    if form.validate_on_submit():
        next_lab_module_id = form.next_lab_module_id.data
        lab_module_id = form.lab_module_id.data
        # Update the user's progress or database as needed
        if current_user.completed_modules:
             before_current_user_modules_completed = current_user.completed_modules.split(',')
             before_current_user_modules_completed.append(str(lab_module_id))
             current_user.current_module = next_lab_module_id
             current_user.completed_modules = ','.join(before_current_user_modules_completed)
        else:
            current_user.completed_modules = lab_module_id


        current_user.current_module = next_lab_module_id
        db.session.commit()

        flash('You have completed this module !', 'success')
        return redirect(url_for('student.modules'))
    
    else:
        flash('Failed to update module. Please try again.', 'error')
        return redirect(url_for('student.modules'))


       



@student.route('/labsheet/<int:module_id>', methods=['GET'])
@login_required
@session_timeout
def labsheets(module_id):
    labsheets = Labsheet.query.filter_by(module_id=module_id).all()
    return render_template('labsheet.html', labsheets=labsheets)



@student.route('/rankings', methods=['GET', 'POST'])
@login_required
@session_timeout
def rankings():

    form = RankingWeekForm()
    selected_week = form.ranking_week.data if form.validate_on_submit() else get_current_week_number()

    if form.validate_on_submit():
        return redirect(url_for('student.rankings', ranking_week=selected_week))

    selected_week = int(request.args.get('ranking_week', selected_week))
    if selected_week is None or not (1 <= selected_week <= 8):
         flash('Weeks must be between 1 to 8', 'error')
         return redirect(url_for('student.rankings', ranking_week=get_current_week_number()))

    rankings = Ranking.query.filter_by(week_number=selected_week).order_by(Ranking.score.desc()).all()

    if not rankings:
       pass

    ranking_data = [
        {
            'name': User.query.get(rank.user_id).name, 
            'pfp': User.query.get(rank.user_id).image_file,
            'userid': User.query.get(rank.user_id).id,
            'score': rank.score, 
            'cumulative_score': rank.cumulative_score
        } 
        for rank in rankings
    ]

    return render_template('rankings.html', form=form, rankings=ranking_data, selected_ranking_week=selected_week)



@student.route('/quiz/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
@session_timeout
def quiz(quiz_id):

    current_week = get_current_week_number() 
    quiz = Quiz.query.get_or_404(quiz_id)
    modules = Module.query.all()
    completed_quiz = [int(quiz_id) for quiz_id in current_user.completed_quizzes.split(',')] if current_user.completed_quizzes else []
    completed_quizzes = current_user.completed_quizzes.split(',') if current_user.completed_quizzes else []

    if (quiz_id > current_week):
        flash(f"It is currently week {current_week}, and you do not have access to the content yet.", category='info')
        return redirect(url_for('student.displayQuiz'))  # Redirect to the 'modules' route
            
    elif ( quiz_id > current_user.current_module):
        flash(f"You have not completed week {current_user.current_module}'s quiz yet. Please do so before you can access it.", category='info')
        return redirect(url_for('student.displayQuiz'))  # Redirect to the 'modules' route
            

    
  

    # Check if the quiz is locked or already completed
   

    # Check if the quiz is already completed with 100 marks
    
    if quiz_id in completed_quiz:
        return redirect(url_for('student.revise', quiz_id=quiz_id))  # Pass quiz_id here

    form = QuizForm()

    # Clear session data to reset the quiz
    session.pop('selected_questions', None)
    session.pop('current_question_index', None)
    session.pop('total_score', None)
    session.pop('lives', None)
    session.pop('boss_health', None)

    if 'selected_questions' not in session or session.get('quiz_id') != quiz_id:
        session['selected_questions'] = []
        session['quiz_id'] = quiz_id

        all_questions = QuizQuestion.query.filter_by(quiz_id=quiz_id).all()
        selected_questions = []
        total_marks = 0

        while total_marks < 100 and all_questions:
            question = random.choice(all_questions)
            all_questions.remove(question)
            if total_marks + question.marks <= 100:
                selected_questions.append(question.id)
                total_marks += question.marks

        if total_marks < 100:
            return "Unable to fetch quiz questions totaling 100 marks", 400

        session['selected_questions'] = selected_questions
        session['current_question_index'] = 0
        session['total_score'] = 0
        session['lives'] = 3
        session['boss_health'] = 20 - session['current_question_index']

    current_question_index = session.get('current_question_index', 0)
    lives = session.get('lives', 3)
    selected_questions = session['selected_questions']
    boss_health = session.get('boss_health', 20 - current_question_index)

    if current_question_index >= len(selected_questions):
        return redirect(url_for('student.quiz_result', quiz_id=quiz_id))

    question_id = selected_questions[current_question_index]
    question = QuizQuestion.query.get(question_id)

    if form.validate_on_submit():
        selected_option = form.selected_option.data
        is_correct = selected_option == question.correct_option
        score = question.marks if is_correct else 0

        if is_correct:
            session['total_score'] += score
            session['current_question_index'] += 1
            session['lives'] = 3
            session['boss_health'] -= 1
        else:
            session['lives'] -= 1

            if session['lives'] <= 0:
                flash("You've run out of lives for this question. Please review your results.", category='danger')
                return redirect(url_for('student.quiz_result', quiz_id=quiz_id))

            flash("Incorrect answer. You have lost a life.", category='danger')

        take_quiz_answer = TakeQuizAnswer(
            user_id=current_user.id,
            quiz_id=quiz_id,
            question_id=question_id,
            selected_option=selected_option,
            score=score,
            lives=session['lives']
        )
        db.session.add(take_quiz_answer)
        db.session.commit()

        if session['current_question_index'] >= len(session['selected_questions']):
            total_score = session['total_score']
            update_ranking_and_scores(current_user, quiz_id, total_score)
            mark_quiz_complete(current_user, quiz_id)
            if total_score == 100:
                unlock_next_module(current_user)
            db.session.commit()
            return redirect(url_for('student.quiz_result', quiz_id=quiz_id))

        db.session.commit()
        return redirect(url_for('student.quiz', quiz_id=quiz_id))

    return render_template(
        'startQuiz.html',
        boss_health=boss_health,
        completed_quizzes=completed_quizzes,
        modules=modules,
        current_week=get_current_week_number(),
        quiz=quiz,
        question=question,
        lives=lives,
        current_question_index=current_question_index,
        form=form,
        quiz_id=quiz_id  # Ensure quiz_id is passed to the template
    )


def unlock_next_quiz(user):
    # Ensure we have a current quiz and it is not the last quiz
    if user.current_quiz and user.current_quiz < 8:
        # Check if the user's weekly_score is 100
        weekly_scores = json.loads(user.weekly_score) if user.weekly_score else {}
        current_week_score = weekly_scores.get(str(get_current_week_number()), 0)

        # Get the current week number
        current_week = get_current_week_number()

        # Unlock the next quiz if the user has a score of 100 or is progressing to the next week
        if current_week_score >= 100 or current_week > user.current_module:
            next_quiz_id = user.current_quiz + 1

            if next_quiz_id <= 8:
                user.current_quiz = next_quiz_id
                db.session.commit()
                print(f"Unlocked quiz {next_quiz_id}")
            else:
                print(f"No quiz found with ID {next_quiz_id}")
        else:
            print("Weekly score is not enough to unlock the next quiz or it's not the right week to unlock")
    else:
        print("Current quiz is None or already at the last quiz")

@student.route('/quiz/<int:quiz_id>/submit', methods=['POST'])
@login_required
@session_timeout
def submit_quiz(quiz_id):
    try:
        if 'selected_questions' not in session or session.get('quiz_id') != quiz_id:
            return jsonify({'error': 'Invalid quiz session'}), 400

        quiz = Quiz.query.get_or_404(quiz_id)
        current_question_index = session.get('current_question_index', 0)
        lives = session.get('lives', 3)
       
        selected_questions = session['selected_questions']

        if current_question_index >= len(selected_questions):
            return jsonify({'error': 'No more questions'}), 400

        question_id = selected_questions[current_question_index]
        question = QuizQuestion.query.get_or_404(question_id)

        selected_option = request.form.get('selected_option')
        is_correct = selected_option == question.correct_option
        score = question.marks if is_correct else 0

        if is_correct:
            
            session['total_score'] += score
            session['current_question_index'] += 1
            session['lives'] = 3  # Reset lives on correct answer
            session['boss_health'] -= 1
        else:
            
            session['lives'] -= 1
            if session['lives'] <= 0:
                return jsonify({
                    'redirect_url': url_for('student.quiz_result', quiz_id=quiz_id) ,
                     'lives':lives # Ensure quiz_result route exists
                })

        take_quiz_answer = TakeQuizAnswer(
            user_id=current_user.id,
            quiz_id=quiz_id,
            question_id=question_id,
            selected_option=selected_option,
            score=score,
            lives=session['lives']
        )
        db.session.add(take_quiz_answer)
        db.session.commit()

        if session['current_question_index'] >= len(selected_questions):
            total_score = session['total_score']
            update_ranking_and_scores(current_user, quiz_id, total_score)
            mark_quiz_complete(current_user, quiz_id)
            if total_score == 100:
                unlock_next_quiz(current_user)
            db.session.commit()
            return jsonify({
                'redirect_url': url_for('student.quiz_result', quiz_id=quiz_id)  # Ensure quiz_result route exists
            })

        db.session.commit()
        next_question_id = selected_questions[session['current_question_index']]
        next_question = QuizQuestion.query.get(next_question_id)

        return jsonify({
            'current_question_index': session['current_question_index'],
            'lives': session['lives'],
            'boss_health':session['boss_health'],
            'result': is_correct,
            'next_question': {

                'id': next_question.id,
                'question_text': next_question.question,
                'options': {
                    'A': next_question.option_A,
                    'B': next_question.option_B,
                    'C': next_question.option_C,
                    'D': next_question.option_D
                }
            }
        })
    except Exception as e:
        logging.error("An error occurred: %s", e)
        return jsonify({'error': 'Internal server error'}), 500
    
    

@student.route('/quiz_result/<int:quiz_id>', methods=['GET', 'POST'])
@login_required
@session_timeout
def quiz_result(quiz_id):
     

    completed_quizzes = [int(quiz_id) for quiz_id in current_user.completed_quizzes.split(',')] if current_user.completed_quizzes else []
    if quiz_id:
        pass
    
    
    elif quiz_id in completed_quizzes:
        flash("You have already completed the quiz. Redirecting to Revision page.", category='warning')
        return redirect(url_for('student.revise', quiz_id=quiz_id))

    elif quiz_id not in completed_quizzes:
        flash("Try the quiz before viewing your result", category='warning')
        return redirect(url_for('student.displayQuiz'))
    


    
   
    form = RestartQuizForm()
    total_score = session.get('total_score', 0)
    correct_answers = TakeQuizAnswer.query.filter_by(user_id=current_user.id, quiz_id=quiz_id).count()
    passed = total_score == 100

    if 'total_score' not in session or session.get('quiz_id') != quiz_id:
        flash("Invalid access to quiz result. Complete the quiz first.", category='warning')
        return redirect(url_for('student.displayQuiz'))
    
    # Clear quiz session but keep answers for result display
    session.pop('selected_questions', None)
    session.pop('quiz_id', None)
    session.pop('current_question_index', None)
    session.pop('total_score', None)
    session.pop('lives', None)
    db.session.commit()

   

    if request.method == 'POST':
        if 'restart_quiz' in request.form:
            if passed:
                flash("You cannot restart a quiz you have completed with 100 marks.", category='info')
                return redirect(url_for('student.revise', quiz_id=quiz_id))  # Ensure quiz_id is passed here
            else:
                return redirect(url_for('student.quiz', quiz_id=quiz_id))

    return render_template('quiz_result.html', form=form, total_score=total_score, passed=passed, quiz_id=quiz_id)


@student.route('/revise/<int:quiz_id>', methods=['GET'])
@login_required
@session_timeout
def revise(quiz_id):

    quiz = Quiz.query.get_or_404(quiz_id)
    completed_quizzes = [int(quiz_id) for quiz_id in current_user.completed_quizzes.split(',')] if current_user.completed_quizzes else []
    if quiz_id not in completed_quizzes:
        flash(f"You have not gotten 100 marks for the quiz. Please do so to be able to revise for week {quiz_id}'s quiz. ", category='warning')
        return redirect(url_for('student.displayQuiz'))
    
    # Fetch the unique question IDs with incorrect answers for the given quiz_id
    incorrect_question_ids = db.session.query(TakeQuizAnswer.question_id).filter_by(
        user_id=current_user.id,
        quiz_id=quiz_id,
        score=0  # Assuming score=0 for incorrect answers
    ).distinct().all()
    
    # Extract question IDs from the result
    question_ids = [qid[0] for qid in incorrect_question_ids]
    
    # Fetch the details of these questions
    questions = QuizQuestion.query.filter(QuizQuestion.id.in_(question_ids)).all()
    
    # Create a dictionary to easily access question details
    questions_dict = {q.id: q for q in questions}
    
    # Prepare data for the template
    revision_data = []
    for i, question_id in enumerate(question_ids, start=1):
        question = questions_dict.get(question_id)
        # Find the user's selected option for this question (there should be only one entry per question)
        user_answer = TakeQuizAnswer.query.filter_by(
            user_id=current_user.id,
            quiz_id=quiz_id,
            question_id=question_id,
            score=0  # Assuming score=0 for incorrect answers
        ).first()
        
        revision_data.append({
            'number': i,
            'question': question.question,
            'options': {
                'A': question.option_A,
                'B': question.option_B,
                'C': question.option_C,
                'D': question.option_D
            },
            'selected_option': user_answer.selected_option if user_answer else None,
            'correct_option': question.correct_option
        })
    
    return render_template('revise.html', revision_data=revision_data, quiz_id=quiz_id, quiz=quiz)