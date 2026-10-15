from config import Config
import time
import requests
from datetime import datetime
import json
import base64
import urllib.parse

config = Config()
today = datetime.now().day

base_url = config.AIRTABLE_BASE_URL
token = config.AIRTABLE_TOKEN
client_id = config.QUICKBOOKS_CLIENT_ID
client_secret = config.QUICKBOOKS_CLIENT_SECRET
redirect_uri = config.QUICKBOOKS_REDIRECT_URI
headers = {'Authorization': f'Bearer {token}'}


def get_transactions(client_id, month_name=None):
    """Fetch transactions for a specific client (optionally filtered by month)"""
    try:
        url = f"{base_url}/TransactionReport"

        if month_name:
            formula = f"AND({{ID}}='{client_id}', {{Month}}='{month_name}')"
        else:
            formula = f"{{ID}}='{client_id}'"

        params = {"filterByFormula": formula}

        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()

        data = response.json()
        transactions = []

        for record in data.get("records", []):
            fields = record.get("fields", {})

            # Parse the summary JSON string into a Python object
            raw_summary = fields.get("summary", "[]")
            try:
                summary = json.loads(raw_summary)
            except json.JSONDecodeError:
                summary = []

            transactions.append({
                "id": record.get("id"),
                "ID": fields.get("ID", ""),
                "Name": fields.get("Name", ""),
                "Month": fields.get("Month", ""),
                "transactioncount": fields.get("transactioncount", ""),
                "transactionamount": fields.get("transactionamount", ""),
                "transactiontype": fields.get("transactiontype", ""),
                "summary": summary,
                "timestamp": fields.get("timestamp", "")
            })

        return {"success": True, "transactions": transactions}

    except requests.RequestException as e:
        print(f"Error fetching transactions: {e}")
        return {"success": False, "error": str(e)}


def check_if_data_exists_for_current_month(client_id):
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

        transactions_result = get_transactions(client_id)
        if transactions_result['success']:
            for transaction in transactions_result['transactions']:
                if transaction.get('Month') == month_name:
                    return True
        return False

    except Exception as e:
        print(f"Error checking existing data for client {client_id}: {e}")
        return False


def fetch_scheduled_clients(day):
    """Fetch clients scheduled for the given day"""
    try:
        url = f"{base_url}/ClientDetails"
        params = {
            'filterByFormula': f"AND({{schedule_day}}='{day}',{{schedule_enabled}}='True')",
            'maxRecords': 100
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        clients = []
        
        for record in data.get('records', []):
            fields = record.get('fields', {})
            client_id = fields.get('ID')
            client_name = fields.get('Name', f'Client {client_id}')
            
            if client_id:
                # Check if data already exists for current month
                if not check_if_data_exists_for_current_month(client_id):
                    clients.append({
                        'id': client_id,
                        'name': client_name,
                        'record_id': record.get('id')
                    })
                else:
                    print(f"Data already exists for client {client_id}, skipping")
        
        return clients
        
    except requests.RequestException as e:
        print(f"Error fetching scheduled clients: {e}")
        return []


def get_client_tokens(realm_id):
    """Get client tokens by realm ID"""
    try:
        url = f'{base_url}/ClientDetails'
        params = {
            'filterByFormula': f"{{ID}}='{realm_id}'"
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        data = response.json()
        records = data.get('records', [])
        
        if records:
            fields = records[0].get('fields', {})
            return {
                'success': True, 
                'tokens': {
                    'access_token': fields.get('Atoken', ''),
                    'refresh_token': fields.get('Rtoken', ''),
                    'record_id': records[0].get('id')
                }
            }
        else:
            return {'success': False, 'error': 'Client not found'}
            
    except requests.RequestException as e:
        print(f"Error getting client tokens: {e}")
        return {'success': False, 'error': str(e)}


def refresh_access_token(refresh_token):
    """Generate new access token using refresh token"""
    try:
        token_url = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'

        # Create Basic Auth header
        credentials = f'{client_id}:{client_secret}'
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        token_headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_credentials}'
        }

        data = {
            'refresh_token': refresh_token,
            'redirect_uri': redirect_uri,
            'grant_type': 'refresh_token'
        }

        response = requests.post(token_url, headers=token_headers, data=data)
        response.raise_for_status()           

        return {'success': True, 'data': response.json()}

    except requests.RequestException as e:
        print(f"Token refresh error: {e}")
        return {'success': False, 'error': str(e)}


def get_transaction_list(access_token, company_id, start_date, end_date):
    """Fetch transaction list from QuickBooks API"""
    try:
        qb_base_url = f'https://quickbooks.api.intuit.com/v3/company/{company_id}/reports/TransactionList'
        params = {
            'start_date': start_date,
            'end_date': end_date,
            'minorversion': '75'
        }
        
        qb_headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {access_token}'
        }
        
        response = requests.get(qb_base_url, headers=qb_headers, params=params)
        response.raise_for_status()
        return {'success': True, 'data': response.json()}
        
    except requests.RequestException as e:
        print(f"Error fetching transactions: {e}")
        return {'success': False, 'error': str(e)}


def parse_transaction_data(qb_response):
    """Parse QuickBooks transaction response and extract summary data for all transaction types"""
    try:
        # Extract header information
        header = qb_response.get('Header', {})
        rows = qb_response.get('Rows', {}).get('Row', [])

        start_date = header.get('StartPeriod', '')
        end_date = header.get('EndPeriod', '')

        # Dictionary to store summary by transaction type
        summary = {}

        # Process each row
        for row in rows:
            if row.get('type') == 'Data':
                col_data = row.get('ColData', [])

                # Ensure row has at least txn_type and amount
                if len(col_data) >= 2:
                    txn_type = col_data[1].get('value', '').strip()

                    # Initialize entry if not already present
                    if txn_type not in summary:
                        summary[txn_type] = {
                            "total_count": 0,
                            "total_amount": 0.0
                        }

                    summary[txn_type]["total_count"] += 1

                    # Amount is usually last column
                    amount_str = col_data[-1].get('value', '0')
                    try:
                        amount = float(amount_str.replace(',', '').strip())
                    except ValueError:
                        amount = 0.0

                    summary[txn_type]["total_amount"] += amount

        # Convert amounts to rounded values
        for txn_type in summary:
            summary[txn_type]["total_amount"] = round(summary[txn_type]["total_amount"], 2)

        # Prepare final output
        result = {
            "start_date": start_date,
            "end_date": end_date,
            "transactions": []
        }

        for txn_type, data in summary.items():
            result["transactions"].append({
                "transaction_type": txn_type,
                "total_count": data["total_count"],
                "total_amount": data["total_amount"]
            })

        return result

    except Exception as e:
        print(f"Error parsing transaction data: {e}")
        return {
            "start_date": "",
            "end_date": "",
            "transactions": []
        }


def save_transaction_report(name, client_id, month, start_date, end_date, transactions):
    """Save transaction report to Airtable with summary of all transaction types"""
    try:
        url = f'{base_url}/TransactionReport'

        # Calculate total count and total amount across all transaction types
        total_transaction_count = sum(item.get('total_count', 0) for item in transactions)
        total_transaction_amount = round(sum(item.get('total_amount', 0.0) for item in transactions), 2)

        data = {
            "records": [
                {
                    "fields": {
                        "Name": name,
                        "ID": client_id,
                        "Month": month,
                        "transactioncount": total_transaction_count,
                        "transactionamount": total_transaction_amount,
                        "startdate": start_date,
                        "enddate": end_date,
                        "summary": json.dumps(transactions, indent=2)
                    }
                }
            ]
        }
        
        # Fixed headers - should be a dict, not a set
        save_headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.post(url, headers=save_headers, json=data)
        response.raise_for_status()

        return {'success': True, 'data': response.json()}

    except requests.RequestException as e:
        print(f"Error saving transaction report: {e}")
        return {'success': False, 'error': str(e)}


def fetch_transaction_data_task(client):
    """Task function for fetching transaction data for a single client"""
    try:
        client_id = client['id']
        client_name = client['name']

        print(f"Starting transaction fetch for client {client_id} ({client_name})")

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
        tokens_result = get_client_tokens(client_id)
        if not tokens_result['success']:
            print(f"Failed to get tokens for client {client_id}: {tokens_result['error']}")
            return False

        refresh_token = tokens_result['tokens']['refresh_token']

        # Refresh access token
        token_result = refresh_access_token(refresh_token)
        if not token_result['success']:
            print(f"Failed to refresh token for client {client_id}: {token_result['error']}")
            return False

        new_access_token = token_result['data'].get('access_token')

        # Process transaction data
        success_count = 0

        # Fetch and save transaction data
        transaction_result = get_transaction_list(
            new_access_token, client_id, start_date, end_date
        )

        if transaction_result['success']:
            transaction_summary = parse_transaction_data(
                transaction_result['data']
            )

            transaction_save_result = save_transaction_report(
                client_name, client_id, month_name,
                start_date, end_date, transaction_summary['transactions']
            )

            if transaction_save_result['success']:
                success_count += 1
                print(f"Saved transaction data for client {client_id}")
            else:
                print(
                    f"Failed to save transaction data for client {client_id}: {transaction_save_result['error']}"
                )
        else:
            print(
                f"Failed to fetch transaction data for client {client_id}: {transaction_result['error']}"
            )
            return False

        return True

    except Exception as e:
        print(f"Task execution error for client {client_id}: {e}")
        return False


def process_scheduled_clients(client_id):
    """Process a specific client by ID"""
    client = {
        'id': str(client_id),
        'name': f'Client {client_id}'
    }
    return fetch_transaction_data_task(client)


# Main execution
if __name__ == "__main__":
    # Uncomment to fetch all scheduled clients for today
    # scheduled_clients = fetch_scheduled_clients(today)
    # if not scheduled_clients:
    #     print(f"No clients scheduled for day {today}")
    # else:
    #     for client in scheduled_clients:
    #         print(f"Processing client: {client['id']}")
    #         fetch_transaction_data_task(client)
    
    # Process specific client
    result = process_scheduled_clients(9341455XXXXX)
    print(f"Processing result: {result}")