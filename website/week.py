from datetime import datetime
import pytz
from .models import AdminSettings

# Define the Singapore timezone
sg_tz = pytz.timezone('Asia/Singapore')

def get_current_week_and_time():
    # Fetch the start date from the database
    setting = AdminSettings.query.first()
    
    if not setting or not setting.start_date:
        # Use a default start date if no setting is found
        default_start_date = sg_tz.localize(datetime(2024, 7, 20))
        current_date = datetime.now(sg_tz)
    else:
        # Use the start date from the setting if found
        start_date = setting.start_date
        if start_date.tzinfo is None:
            start_date = sg_tz.localize(start_date)
        current_date = datetime.now(sg_tz)
        
        # Calculate the difference in days between the current date and the start date
        delta = current_date - start_date
        # Calculate the current week number, ensuring it's within the valid range (1 to 8)
        current_week = (delta.days // 7) + 1
        current_week = max(1, min(8, current_week))
        return current_week, current_date.strftime('%A %d %B %H:%M:%S')
    
    # If no start date is set, use the default start date
    delta = current_date - default_start_date
    # Calculate the week number based on the default start date
    current_week = (delta.days // 7) + 1
    current_week = max(1, min(8, current_week))
    
    return current_week, current_date.strftime('%A %d %B %H:%M:%S')

def get_current_week_number():
    # Fetch the start date from the database
    setting = AdminSettings.query.first()
    
    if setting and setting.start_date:
        start_date = setting.start_date
        if start_date.tzinfo is None:
            start_date = sg_tz.localize(start_date)
    else:
        # Handle the case where no start date is set in the database
        # Use a default start date if no setting is found
        default_start_date = sg_tz.localize(datetime(2024, 7, 20))
        start_date = default_start_date
    
    # Get the current date in Singapore timezone
    current_date = datetime.now(sg_tz)
    
    # Calculate the difference in days between the current date and the start date
    delta = current_date - start_date
    
    # Calculate the current week number, ensuring it's within the valid range (1 to 8)
    current_week = max(1, min(8, (delta.days // 7) + 1))
    
    return current_week