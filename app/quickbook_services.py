
import base64
import requests
import urllib.parse

class QuickBooksService:
    """Service class for QuickBooks OAuth operations"""
    
    def __init__(self, client_id, client_secret, redirect_uri,app):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.app = app
    
    def get_auth_url(self, state):
        """Generate QuickBooks OAuth authorization URL"""
        base_url = 'https://appcenter.intuit.com/connect/oauth2'
        params = {
            'client_id': self.client_id,
            'scope': 'com.intuit.quickbooks.accounting',
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'state': state
        }
        return f"{base_url}?{urllib.parse.urlencode(params)}"
    
    def exchange_code_for_tokens(self, code):
        """Exchange authorization code for access and refresh tokens"""
        try:
            token_url = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'
            
            # Create Basic Auth header
            credentials = f'{self.client_id}:{self.client_secret}'
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_credentials}'
            }
            
            data = {
                'code': code,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            
            response = requests.post(token_url, headers=headers, data=data)
            response.raise_for_status()
            print("=============================")
            print(response.json())
            print("=============================")
            
            return {'success': True, 'data': response.json()}
            
        except requests.RequestException as e:
            print(f"Token exchange error: {e}")
            return {'success': False, 'error': str(e)}

    def refresh_access_token(self, refresh_token):
        """Generate new access token using refresh token"""
        try:
            token_url = 'https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer'

            # Create Basic Auth header
            credentials = f'{self.client_id}:{self.client_secret}'
            encoded_credentials = base64.b64encode(credentials.encode()).decode()

            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': f'Basic {encoded_credentials}'
            }

            data = {
                'refresh_token': refresh_token,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'refresh_token'
            }

            #print("====================================")
            #print(data)
            #print(headers)
            response = requests.post(token_url, headers=headers, data=data)
            #print(response)
            response.raise_for_status()            
            #print("====================================")

            return {'success': True, 'data': response.json()}

        except requests.RequestException as e:
            print(f"Token refresh error: {e}")
            return {'success': False, 'error': str(e)}

    def get_transaction_list(self, access_token, company_id, start_date, end_date):
        """Fetch transaction list from QuickBooks API"""
        try:
            base_url = f'https://quickbooks.api.intuit.com/v3/company/{company_id}/reports/TransactionList'
            params = {
                'start_date': start_date,
                'end_date': end_date,
                #'transaction_type': transaction_type,
                'minorversion': '75'
            }
            
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {access_token}'
            }
            
            response = requests.get(base_url, headers=headers, params=params)
            response.raise_for_status()
            ##print(response)
            return {'success': True, 'data': response.json()}
            
        except requests.RequestException as e:
            print(f"Error fetching transactions: {e}")
            return {'success': False, 'error': str(e)}


    def parse_transaction_data(self, qb_response):
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

    # def parse_transaction_data(self, qb_response, transaction_type):
    #     """Parse QuickBooks transaction response and extract summary data"""
    #     try:
    #         # QuickBooks report format
    #         header = qb_response.get('Header', {})
    #         rows = qb_response.get('Rows', {}).get('Row', [])

    #         start_date = header.get('StartPeriod', '')
    #         end_date = header.get('EndPeriod', '')

    #         total_count = 0
    #         total_amount = 0.00

    #         # Process each row
    #         for row in rows:
    #             if row.get('type') == 'Data':
    #                 col_data = row.get('ColData', [])

    #                 # Ensure row has at least txn_type and amount
    #                 if len(col_data) >= 2:
    #                     txn_type = col_data[1].get('value', '')

    #                     # Match only requested transaction type (e.g., Invoice)
    #                     if txn_type.lower().replace(" ", "") == transaction_type.lower():
    #                         total_count += 1

    #                         # Amount is usually last column
    #                         amount_str = col_data[-1].get('value', '0')
    #                         try:
    #                             amount = float(amount_str.replace(',', '').strip())
    #                         except ValueError:
    #                             amount = 0.0
    #                         total_amount += amount

    #         return {
    #             "transaction_type": transaction_type,
    #             "total_count": total_count,
    #             "total_amount": round(total_amount, 2),
    #             "start_date": start_date,
    #             "end_date": end_date
    #         }

    #     except Exception as e:
    #         app.logger.error(f"Error parsing transaction data: {e}")
    #         return {
    #             "transaction_type": transaction_type,
    #             "total_count": 0,
    #             "total_amount": 0.00,
    #             "start_date": "",
    #             "end_date": ""
    #         }