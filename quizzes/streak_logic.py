from datetime import date, timedelta
from django.utils import timezone
from .models import StudentStreak, StudentBadge, StudentAnswer

def update_daily_streak(student):
    """Updates the quiz streak for a student when they submit a quiz."""
    if not student.is_student:
        return
        
    streak_obj, created = StudentStreak.objects.get_or_create(student=student)
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    last_date = streak_obj.last_quiz_date
    
    if last_date == today:
        # Already updated today
        return
    
    if last_date == yesterday:
        # Continued streak
        streak_obj.current_streak += 1
    else:
        # Reset or start new streak
        streak_obj.current_streak = 1
        
    # Update longest streak
    if streak_obj.current_streak > streak_obj.longest_streak:
        streak_obj.longest_streak = streak_obj.current_streak
        
    streak_obj.last_quiz_date = today
    streak_obj.save()
    
    # Check for badges
    _check_badges(student, streak_obj.current_streak)

def _check_badges(student, streak_count):
    badges_to_award = []
    if streak_count == 3:
        badges_to_award.append("Bronze Badge (3 Day Streak)")
    elif streak_count == 7:
        badges_to_award.append("Silver Badge (7 Day Streak)")
    elif streak_count == 30:
        badges_to_award.append("Gold Badge (30 Day Streak)")
        
    for b_name in badges_to_award:
        if not StudentBadge.objects.filter(student=student, badge_name=b_name).exists():
            StudentBadge.objects.create(student=student, badge_name=b_name)

def get_streak_calendar(student):
    """Returns a list of dictionaries for the last 7 days status."""
    today = date.today()
    calendar = []
    
    # We check StudentAnswer history to see if any quiz was taken on each day
    # Or we can just calculate from last_quiz_date and streak, but checking DB is safer for individual days.
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        
        # Check if any quiz was submitted on this date
        completed = StudentAnswer.objects.filter(
            student=student,
            submitted_at__date=target_date
        ).exists()
        
        calendar.append({
            'date': target_date,
            'day_name': target_date.strftime('%a'),
            'completed': completed,
            'is_today': target_date == today
        })
        
    return calendar
