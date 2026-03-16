@echo off
:: Daily Quiz Auto-Generator - runs every day via Windows Task Scheduler
cd /d "c:\Users\Naveen\OneDrive\Documents\collegeportal_314 - Copy"
python manage.py generate_daily_quizzes >> "c:\Users\Naveen\OneDrive\Documents\collegeportal_314 - Copy\logs\daily_quiz.log" 2>&1
