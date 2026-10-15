# app.py
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
import requests
import base64
import os
import secrets
import urllib.parse
from datetime import datetime, timedelta
from functools import wraps
from config import Config
from datetime import datetime, timezone
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import atexit
from app.airtable_services import AirtableService
from app.quickbook_services import QuickBooksService
from app.scheduler_services import SchedulerService

# Add this configuration to your Config class
MAX_CONCURRENT_REQUESTS = 3  # Limit concurrent API requests
REQUEST_DELAY = 2  # Seconds between requests to respect rate limits


datetime.now(timezone.utc).isoformat()


app = Flask(__name__)
app.config.from_object(Config)

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def calculate_time_until_expire(timestamp, expire_seconds):
    """Calculate time until token expires"""
    try:
        created_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        expire_time = created_time + timedelta(seconds=int(expire_seconds))
        now = datetime.now(expire_time.tzinfo)
        
        if expire_time > now:
            remaining = expire_time - now
            days = remaining.days
            hours, remainder = divmod(remaining.seconds, 3600)
            minutes, _ = divmod(remainder, 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        else:
            return "Expired"
    except Exception as e:
        app.logger.error(f"Error calculating token expiry: {e}")
        return "Unknown"


############################################
# Initialize services
airtable_service = AirtableService(app.config['AIRTABLE_BASE_URL'], 
                                 app.config['AIRTABLE_TOKEN'],app)
quickbooks_service = QuickBooksService(app.config['QUICKBOOKS_CLIENT_ID'],
                                     app.config['QUICKBOOKS_CLIENT_SECRET'],
                                     app.config['QUICKBOOKS_REDIRECT_URI'],app)

# Initialize scheduler service at the end of your main.py, before the app.run()
scheduler_service = SchedulerService(airtable_service, quickbooks_service, app,app.config['AIRTABLE_TOKEN'])

# Routes
@app.route('/')
def index():
    """Home route - redirect based on authentication status"""
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username in app.config['USERS'] and app.config['USERS'][username] == password:
            session['user'] = username
            session.permanent = True
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    flash('You have been logged out successfully', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/transactions/<client_id>')
@login_required
def transactions_page(client_id):
    """Transactions page for a specific client"""
    result = airtable_service.get_transactions(client_id)
    
    # Get client name from clients list
    clients_result = airtable_service.get_clients(client_id)
    client_name = "Unknown Client"
    if clients_result['success']:
        for client in clients_result['clients']:
            if client['ID'] == client_id:
                client_name = client['Name']
                break

    return render_template('transactions.html', 
                         client_id=client_id, 
                         client_name=client_name,
                         transactions_result=result)

# Add this route for manual testing
@app.route('/api/test-scheduler')
@login_required  
def test_scheduler():
    """Manual trigger for testing scheduler functionality"""
    try:
        scheduler_service.daily_schedule_check()
        return jsonify({'success': True, 'message': 'Scheduler test completed'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/auth/quickbooks')
@login_required
def auth_quickbooks():
    """Initiate QuickBooks OAuth flow - Full redirect (no popup)"""
    # Generate secure state parameter
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state
    
    # Get authorization URL and redirect
    auth_url = quickbooks_service.get_auth_url(state)
    return redirect(auth_url)

@app.route('/oauth/callback')
@login_required
def oauth_callback():
    """Handle OAuth callback - Full page redirect"""
    try:
        code = request.args.get('code')
        realm_id = request.args.get('realmId')
        state = request.args.get('state')
        error = request.args.get('error')
        
        # Error handling
        if error:
            flash(f'Authorization failed: {error}', 'error')
            return redirect(url_for('dashboard'))
            
        if not code:
            flash('Authorization failed: No code received', 'error')
            return redirect(url_for('dashboard'))

        # State verification
        # if state != session.get('oauth_state'):
        #     flash('Authorization failed: Invalid state parameter', 'error')
        #     return redirect(url_for('dashboard'))

        # Exchange code for tokens
        token_result = quickbooks_service.exchange_code_for_tokens(code)
        if not token_result['success']:
            flash(f'Token exchange failed: {token_result["error"]}', 'error')
            return redirect(url_for('dashboard'))

        token_data = token_result['data']

        # Extract tokens
        access_token = token_data.get("access_token")
        refresh_token = token_data.get("refresh_token")
        expires_in = token_data.get("expires_in", 3600)
        refresh_expires_in = token_data.get("x_refresh_token_expires_in", 8726400)

        existing_client = airtable_service.find_client_by_realmid(realm_id)

        if existing_client:
            record_id = existing_client["id"]
            result = airtable_service.update_client(
                record_id=record_id,
                #name=f"QuickBooks Company {realm_id}",
                #client_id=realm_id,
                access_token=access_token,
                refresh_token=refresh_token,
                access_expire=expires_in,
                refresh_expire=refresh_expires_in
            )
        else:
            info = airtable_service.get_company_info(realm_id,access_token)

            result = airtable_service.create_client(
                name=info["company_name"],
                client_id=realm_id,
                access_token=access_token,
                refresh_token=refresh_token,
                access_expire=expires_in,
                refresh_expire=refresh_expires_in,
                address =  info["address"],
                city = info["city"],
                postal_code= info["postal_code"],
                qbo_industry_type= info["qbo_industry_type"],
                web_address= info["web_address"],
                email_communication= info["email_communication"],
                country_division_code= info["country_division_code"],
                country= info["country"],
                company_start_date= info["company_start_date"],
                employer_id=info["employer_id"],
                phone= info["phone"],
                email= info["email"]
            )

        # Save to Airtable
        result = airtable_service.create_client(
            name=f"QuickBooks Company {realm_id}",
            client_id=realm_id,
            access_token=access_token,
            refresh_token=refresh_token,
            access_expire=expires_in,
            refresh_expire=refresh_expires_in
        )

        # Clean up session
        session.pop('oauth_state', None)

        if result['success']:
            flash('QuickBooks connected successfully!', 'success')
        else:
            flash(f'Failed to save client data: {result["error"]}', 'error')
            
        return redirect(url_for('dashboard'))

    except Exception as e:
        app.logger.error(f"OAuth callback error: {e}")
        flash(f'OAuth process failed: {str(e)}', 'error')
        return redirect(url_for('dashboard'))

# API Routes
@app.route('/api/clients')
@login_required
def api_clients():
    """API endpoint to fetch clients"""
    result = airtable_service.get_clients()
    return jsonify(result)

@app.route('/api/transactions/<client_id>')
@login_required
def api_transactions(client_id):
    """API endpoint to fetch transactions for a specific client"""
    result = airtable_service.get_transactions(client_id)
    return jsonify(result)

@app.route('/api/fetch-transactions/<client_id>')
@login_required
def api_fetch_transactions(client_id):
    """API endpoint to fetch and process QuickBooks transaction data"""
    try:
        # Get current date for last month calculation
        today = datetime.now()
        if today.month == 1:
            last_month = 12
            year = today.year - 1
        else:
            last_month = today.month - 1
            year = today.year
        
        # Calculate last month's date range
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

        existing = airtable_service.get_transactions(client_id, month_name)
        if existing["success"] and existing["transactions"]:
            print(f" Skipping insert: {client_id} already has data for {month_name}")
            return {"success": True, "skipped": True, "message": f"Data already exists for {month_name}"}

        
        # Get client tokens
        tokens_result = airtable_service.get_client_tokens(client_id)
        print("fun 1 ============ sucess")
        if not tokens_result['success']:
            return jsonify({'success': False, 'error': tokens_result['error']})
        
        refresh_token = tokens_result['tokens']['refresh_token']
        print(refresh_token)
        
        # Refresh access token
        token_result = quickbooks_service.refresh_access_token(refresh_token)
        if not token_result['success']:
            return jsonify({'success': False, 'error': f'Failed to refresh token: {token_result["error"]}'})
        
        # Extract tokens from the nested 'data' dictionary
        data = token_result.get('data', {})

        access_token = data.get("access_token")
        refresh_token = data.get("refresh_token")
        expires_in = data.get("expires_in", 3600)
        refresh_expires_in = data.get("x_refresh_token_expires_in", 8726400)

        # Assuming you already have realm_id and record_id defined
        existing_client = airtable_service.find_client_by_realmid(client_id)

        if existing_client:
            record_id = existing_client.get('id')  # or however you retrieve it

            result = airtable_service.update_client(
                record_id=record_id,
                access_token=access_token,
                refresh_token=refresh_token,
                access_expire=expires_in,
                refresh_expire=refresh_expires_in
            )

            if result:
                print("Airtable updated successfully.")
            else:
                print("Failed to update Airtable.")
        else:
            print("Client not found.")
            
        new_access_token = token_result['data'].get('access_token')

        
        # Get client name
        clients_result = airtable_service.get_clients()
        client_name = "Unknown Client"
        if clients_result['success']:
            for client in clients_result['clients']:
                if client['ID'] == client_id:
                    client_name = client['Name']
                    break
        
        # Fetch Invoice data
        transaction_result = quickbooks_service.get_transaction_list(
            new_access_token, client_id, start_date, end_date
        )
        
        if not transaction_result['success']:
            return jsonify({'success': False, 'error': f'Failed to fetch invoice data: {invoice_result["error"]}'})
        
        # Parse Invoice data
        transaction_summary = quickbooks_service.parse_transaction_data(
            transaction_result['data']
        )
        
        # Save SalesReceipt report to Airtable
        transaction_save_result = airtable_service.save_transaction_report(
            client_name, client_id, month_name,
            start_date, end_date,transaction_summary['transactions']
        )
 
        return jsonify({
            'success': True,
            'data': {
                'month': month_name,
                'date_range': f"{start_date} to {end_date}",
                'transaction_summary':transaction_summary
                # 'invoice_summary': invoice_summary,
                # 'sales_summary': sales_summary,
                # 'saved_reports': {
                #     'invoice_saved': invoice_save_result['success'],
                #     'sales_saved': sales_save_result['success']
                # }
            }
        })
        
    except Exception as e:
        app.logger.error(f"Error fetching transactions: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

##
@app.route('/api/schedule', methods=['POST'])
@login_required
def api_schedule():
    """API endpoint to set up scheduling for a client"""
    global airtable_service
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'})

        # Required fields
        required_fields = ['client_id', 'schedule_enabled', 'schedule_day']
        for field in required_fields:
            if field not in data or data[field] is None:
                return jsonify({'success': False, 'error': f'Missing or invalid {field}'})

        client_id = data['client_id']
        schedule_enabled = str(data['schedule_enabled']).lower() == "true"
        schedule_day = data['schedule_day']


        try:
            schedule_day = int(schedule_day)

        except (ValueError, TypeError):
            return jsonify({'success': False, 'error': 'Invalid schedule_day, schedule_hour, or schedule_minute'})

        # Validate ranges
        if not (1 <= schedule_day <= 28):
            return jsonify({'success': False, 'error': 'schedule_day must be between 1 and 28'})


        # Get client record
        client_record = airtable_service.find_client_by_realmid(client_id)
        if not client_record:
            return jsonify({'success': False, 'error': 'Client not found'})

        # Update schedule in Airtable
        result = airtable_service.update_client_schedule(
            client_record['id'], schedule_enabled, schedule_day, "00:00"
        )
        
        print("RESULT - ",result)
        if result['success']:
            return jsonify({'success': True, 'data': result['data']})
        else:
            return jsonify({'success': False, 'error': result.get('error', 'Unknown error')})


        
    except Exception as e:
        app.logger.error(f"Schedule API error: {e}")
        return jsonify({'success': False, 'error': str(e)})




if __name__ == '__main__':
    print("=== CONFIGURATION REQUIRED ===")
    print("Please check config.py for required settings:")
    print("1. AIRTABLE_TOKEN")
    print("2. QUICKBOOKS_CLIENT_ID") 
    print("3. QUICKBOOKS_CLIENT_SECRET")
    print("4. SECRET_KEY")
    print("5. USERS dictionary")
    print("===============================")
    
    # Start the scheduler
    #scheduler_service.start_scheduler()

    app.run(debug=True, port=5000)