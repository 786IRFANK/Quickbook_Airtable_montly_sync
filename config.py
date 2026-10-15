# config.py
import os
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    """Application configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY') or 'your-secret-key-change-in-production'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # Airtable Configuration
    AIRTABLE_BASE_URL = 'https://api.airtable.com/v0/appzGW5XXXXXXXX'
    AIRTABLE_TOKEN = os.getenv('AIRTABLE_TOKEN')  # Replace with your actual token
    
    # QuickBooks Configuration
    QUICKBOOKS_CLIENT_ID = os.getenv('QUICKBOOKS_CLIENT_ID')
    QUICKBOOKS_CLIENT_SECRET = os.getenv('QUICKBOOKS_CLIENT_SECRET')
    QUICKBOOKS_REDIRECT_URI = os.getenv('QUICKBOOKS_REDIRECT_URI')
    
    # User Authentication (in production, use a proper database)
    USERS = {
        'admin': 'password123'  # Change this password in production
    }
    
    # Logging Configuration
    LOG_LEVEL = os.getenv('LOG_LEVEL') or 'INFO'

    
    # Scheduler Configuration
    SCHEDULER_EXECUTORS = {
        'default': {'type': 'threadpool', 'max_workers': 5}
    }
    
    SCHEDULER_JOB_DEFAULTS = {
        'coalesce': False,
        'max_instances': 1
    }
    
    # Rate Limiting Configuration
    AIRTABLE_RATE_LIMIT = 5  # requests per second
    QUICKBOOKS_RATE_LIMIT = 450  # requests per minute (safe margin from 500)
    TASK_QUEUE_WORKERS = 3  # number of worker threads
    
    # Database Configuration (for job storage)
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL') or 'sqlite:///scheduler.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False