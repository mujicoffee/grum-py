from .models import Logs, User, Classroom
from . import db

def log_user_activity(user_id, status, activity_type, description=None):
    user = User.query.get(user_id)
    role = user.role if user else None
    classroom_code = None
    
    if user and user.role == 'student' and user.classroom_id:
        classroom = Classroom.query.get(user.classroom_id)
        classroom_code = classroom.code if classroom else None
    
    activity = Logs(user_id=user_id, activity_type=activity_type, description=description, user_role=role, classroom_code=classroom_code, status=status)
    db.session.add(activity)
    db.session.commit()