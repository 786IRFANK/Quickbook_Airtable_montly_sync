from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
import time
import threading
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import atexit

MAX_CONCURRENT_REQUESTS = 3  # Limit concurrent API requests
REQUEST_DELAY = 2  # Seconds between requests to respect rate limits


class SchedulerService:
    """Service class for handling scheduled tasks"""
    
    def __init__(self, airtable_service, quickbooks_service, app,token):
        self.airtable_service = airtable_service
        self.quickbooks_service = quickbooks_service
        self.app = app
        self.scheduler = BackgroundScheduler()
        self.executor = ThreadPoolExecutor(max_workers=MAX_CONCURRENT_REQUESTS)
        self.headers = {'Authorization': f'Bearer {token}'}
        
    def start_scheduler(self):
        """Start the background scheduler"""
        try:
            self.scheduler.start()
            # Schedule daily check at 12:01 AM
            self.scheduler.add_job(
                func=self.daily_schedule_check,
                trigger=CronTrigger(hour=13, minute=25),
                id='daily_schedule_check',
                replace_existing=True
            )
            self.app.logger.info("Scheduler started successfully")
            
            # Register shutdown handler
            atexit.register(self.shutdown_scheduler)
            
        except Exception as e:
            self.app.logger.error(f"Failed to start scheduler: {e}")
    
    def shutdown_scheduler(self):
        """Shutdown scheduler and executor"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown()
            self.executor.shutdown(wait=True)
            self.app.logger.info("Scheduler shut down successfully")
        except Exception as e:
            self.app.logger.error(f"Error shutting down scheduler: {e}")
    
    def daily_schedule_check(self):
        """Daily check for scheduled tasks - runs at 12:01 AM"""
        with self.app.app_context():
            try:
                today = datetime.now().day
                self.app.logger.info(f"Running daily schedule check for day: {today}")
                
                # Only process schedules for days 2-28 to avoid month-end issues
                if not (2 <= today <= 28):
                    self.app.logger.info(f"Day {today} outside valid range (2-28), skipping")
                    return
                
                # Fetch clients scheduled for today
                scheduled_clients = self.fetch_scheduled_clients(today)
                
                if not scheduled_clients:
                    self.app.logger.info(f"No clients scheduled for day {today}")
                    return
                
                self.app.logger.info(f"Found {len(scheduled_clients)} clients scheduled for day {today}")
                
                # Process clients with rate limiting
                self.process_scheduled_clients(scheduled_clients)
                
            except Exception as e:
                self.app.logger.error(f"Error in daily schedule check: {e}")
    
    def fetch_scheduled_clients(self, day):
        """Fetch clients scheduled for the given day"""
        try:
            url = f"{self.airtable_service.base_url}/ClientDetails"
            params = {
                'filterByFormula': f"AND({{schedule_day}}='{day}',{{schedule_enabled}}='True')",
                'maxRecords': 100
            }
            
            response = requests.get(url, headers=self.airtable_service.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            clients = []
            
            for record in data.get('records', []):
                fields = record.get('fields', {})
                client_id = fields.get('ID')
                client_name = fields.get('Name', f'Client {client_id}')
                
                if client_id:
                    # Check if data already exists for current month
                    if not self.check_if_data_exists_for_current_month(client_id):
                        clients.append({
                            'id': client_id,
                            'name': client_name,
                            'record_id': record.get('id')
                        })
                    else:
                        self.app.logger.info(f"Data already exists for client {client_id}, skipping")
            
            return clients
            
        except requests.RequestException as e:
            self.app.logger.error(f"Error fetching scheduled clients: {e}")
            return []
    
    def check_if_data_exists_for_current_month(self, client_id):
        """Check if transaction data already exists for current month"""
        try:
            today = datetime.now()
            # Check for last month's data (since we're fetching previous month)
            if today.month == 1:
                last_month = 12
                year = today.year - 1
            else:
                last_month = today.month - 1
                year = today.year
            
            month_name = datetime(year, last_month, 1).strftime("%B %Y")
            
            transactions_result = self.airtable_service.get_transactions(client_id)
            if transactions_result['success']:
                for transaction in transactions_result['transactions']:
                    if transaction.get('Month') == month_name:
                        return True
            return False
            
        except Exception as e:
            self.app.logger.error(f"Error checking existing data for client {client_id}: {e}")
            return False
    
    def process_scheduled_clients(self, clients):
        """Process scheduled clients with rate limiting and error handling"""
        try:
            futures = []
            
            for i, client in enumerate(clients):
                # Add delay between submissions to respect rate limits
                if i > 0:
                    time.sleep(REQUEST_DELAY)
                
                future = self.executor.submit(self.fetch_transaction_data_task, client)
                futures.append((future, client))
            
            # Process completed tasks
            for future, client in futures:
                try:
                    result = future.result(timeout=300)  # 5 minute timeout
                    if result:
                        self.app.logger.info(f"Successfully processed client {client['id']}")
                    else:
                        self.app.logger.error(f"Failed to process client {client['id']}")
                        
                except Exception as e:
                    self.app.logger.error(f"Error processing client {client['id']}: {e}")
            
        except Exception as e:
            self.app.logger.error(f"Error in process_scheduled_clients: {e}")
    
    def fetch_transaction_data_task(self, client):
        """Task function for fetching transaction data for a single client"""
        try:
            client_id = client['id']
            client_name = client['name']
            
            self.app.logger.info(f"Starting transaction fetch for client {client_id} ({client_name})")
            
            # Calculate last month's date range
            today = datetime.now()
            if today.month == 1:
                last_month = 12
                year = today.year - 1
            else:
                last_month = today.month - 1
                year = today.year
            
            start_date = f"{year}-{last_month:02d}-01"
            
            # Get last day of the month
            if last_month in [1, 3, 5, 7, 8, 10, 12]:
                last_day = 31
            elif last_month in [4, 6, 9, 11]:
                last_day = 30
            else:  # February
                if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0):
                    last_day = 29
                else:
                    last_day = 28
            
            end_date = f"{year}-{last_month:02d}-{last_day}"
            month_name = datetime(year, last_month, 1).strftime("%B %Y")
            
            # Get client tokens
            tokens_result = self.airtable_service.get_client_tokens(client_id)
            if not tokens_result['success']:
                self.app.logger.error(f"Failed to get tokens for client {client_id}: {tokens_result['error']}")
                return False
            
            refresh_token = tokens_result['tokens']['refresh_token']
            
            # Refresh access token
            token_result = self.quickbooks_service.refresh_access_token(refresh_token)
            if not token_result['success']:
                self.app.logger.error(f"Failed to refresh token for client {client_id}: {token_result['error']}")
                return False
            
            new_access_token = token_result['data'].get('access_token')
            print(new_access_token)
            # Process Invoice data
            success_count = 0
            
            # Fetch and save Invoice data
            transaction_result = self.quickbooks_service.get_transaction_list(
                new_access_token, client_id, start_date, end_date
            )
            
            if transaction_result['success']:
                transaction_summary = self.quickbooks_service.parse_transaction_data(
                    transaction_result['data']
                )
                
                print(transaction_summary)
                transaction_save_result = self.airtable_service.save_transaction_report(
                    client_name, client_id, month_name,
                    start_date, end_date,transaction_summary['transactions']
                )
                
                if transaction_save_result['success']:
                    success_count += 1
                    self.app.logger.info(f"Saved Invoice data for client {client_id}")
                else:
                    self.app.logger.error(f"Failed to save Invoice data for client {client_id}: {save_result['error']}")
            
            # Add small delay between API calls
            # time.sleep(1)
            else:
                self.app.logger.error(f"Failed to fetch transaction data for client {client_id}: {transaction_result['error']}")
                return False
            
        except Exception as e:
            self.app.logger.error(f"Task execution error for client {client_id}: {e}")
            return False