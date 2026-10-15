
import json
import requests
class AirtableService:
    """Service class for Airtable operations"""
    
    def __init__(self, base_url, token,app):
        self.base_url = base_url
        self.headers = {'Authorization': f'Bearer {token}'}
        self.app = app
    
    def get_clients(self, realm_id=None):
        """Fetch clients from Airtable (optionally filtered by realmID)"""
        try:
            url = f'{self.base_url}/ClientDetails'
            params = {
                'maxRecords': 100,
                'view': 'Grid view'
            }

            # If realm_id provided, add filterByFormula
            if realm_id:
                params['filterByFormula'] = f"{{ID}}='{realm_id}'"

            response = requests.get(url, headers=self.headers, params=params)
            print(response)
            response.raise_for_status()
            
            data = response.json()
            #print(data)  # Debugging
            clients = []
            
            for record in data.get('records', []):
                fields = record.get('fields', {})
                clients.append({
                    'id': record.get('id'),
                    'ID': fields.get('ID', ''),
                    'Name': fields.get('Name', ''),
                    'Rtoken_expire': fields.get('Rtoken_expire', '0'),
                    'timestamp': fields.get('timestamp', '')
                })
            
            return {'success': True, 'clients': clients}

        except requests.RequestException as e:
            print(f"Error fetching clients: {e}")
            return {'success': False, 'error': str(e)}


    
    def get_transactions(self, client_id, month_name=None):
        """Fetch transactions for a specific client (optionally filtered by month)"""
        try:
            url = f"{self.base_url}/TransactionReport"

            if month_name:
                formula = f"AND({{ID}}='{client_id}', {{Month}}='{month_name}')"
            else:
                formula = f"{{ID}}='{client_id}'"

            params = {"filterByFormula": formula}

            response = requests.get(url, headers=self.headers, params=params)
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
                    "summary": summary,  # now it's a list, not a string
                    "timestamp": fields.get("timestamp", "")
                })

            return {"success": True, "transactions": transactions}

        except requests.RequestException as e:
            print(f"Error fetching transactions: {e}")
            return {"success": False, "error": str(e)}

                
    def create_client(self, name, client_id, access_token, refresh_token, 
                     access_expire, refresh_expire,address,city,postal_code,qbo_industry_type,web_address,email_communication,country_division_code,country,company_start_date,employer_id,phone,email):
        """Create a new client record in Airtable"""
        try:
            url = f'{self.base_url}/ClientDetails'
            data = {
                "records": [
                    {
                        "fields": {
                            "Name": name,
                            "ID": client_id,
                            "Atoken": access_token,
                            "Rtoken": refresh_token,
                            "Atoken_expire": str(access_expire),
                            "Rtoken_expire": str(refresh_expire),
                            "address":address,
                            "city":city,
                            "postal_code":postal_code,
                            "qbo_industry_type":qbo_industry_type,
                            "web_address":web_address,
                            "email_communication":email_communication,
                            "country_division_code":country_division_code,
                            "country":country,
                            "company_start_date":company_start_date,
                            "employer_id":employer_id,
                            "phone":phone,
                            "email":email,
                        }
                    }
                ]
            }
            
            response = requests.post(url, headers={**self.headers, 'Content-Type': 'application/json'}, 
                                   json=data)
            response.raise_for_status()
            
            return {'success': True, 'data': response.json()}
            
        except requests.RequestException as e:
            print(f"Error creating client: {e}")
            return {'success': False, 'error': str(e)}

    def find_client_by_realmid(self, realm_id):
        """Check if client exists in Airtable by realmID"""
        try:
            url = f"{self.base_url}/ClientDetails"
            params = {
                "filterByFormula": f"{{ID}}='{realm_id}'"
            }
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            data = response.json()
            if data.get("records"):
                return data["records"][0]  # return first matching record
            return None
        except requests.RequestException as e:
            print(f"Error finding client: {e}")
            return None

    def update_client(self, record_id, access_token, refresh_token,
                      access_expire, refresh_expire):
        """Update an existing client record in Airtable"""
        try:
            url = f"{self.base_url}/ClientDetails"
            data = {
                "records": [
                    {
                        "id": record_id,
                        "fields": {


                            "Atoken": access_token,
                            "Rtoken": refresh_token,
                            "Atoken_expire": str(access_expire),
                            "Rtoken_expire": str(refresh_expire)
                        }
                    }
                ]
            }
            response = requests.patch(url, headers={**self.headers, "Content-Type": "application/json"}, json=data)
            response.raise_for_status()
            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            print(f"Error updating client: {e}")
            return {"success": False, "error": str(e)}


    def get_client_tokens(self, realm_id):
        """Get client tokens by realm ID"""
        try:
            url = f'{self.base_url}/ClientDetails'
            params = {
                'filterByFormula': f"{{ID}}='{realm_id}'"
            }
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            #print(data)
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


    def save_transaction_report(self, name, client_id, month, start_date, end_date, transactions):
        """Save transaction report to Airtable with summary of all transaction types"""
        try:
            url = f'{self.base_url}/TransactionReport'

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
                            "summary":  json.dumps(transactions, indent=2)  # Store the whole summary JSON
                        }
                    }
                ]
            }

            print("data = ",data)
            response = requests.post(
                url,
                headers={**self.headers, 'Content-Type': 'application/json'},
                json=data
            )
            response.raise_for_status()

            return {'success': True, 'data': response.json()}

        except requests.RequestException as e:
            print(f"Error saving transaction report: {e}")
            return {'success': False, 'error': str(e)}

    # def save_transaction_report(self, name, client_id, month, transaction_type, 
    #                           transaction_count, transaction_amount, start_date, end_date):
    #     """Save transaction report to Airtable"""
    #     try:
    #         url = f'{self.base_url}/TransactionReport'
    #         data = {
    #             "records": [
    #                 {
    #                     "fields": {
    #                         "Name": name,
    #                         "ID": client_id,
    #                         "Month": month,
    #                         "transactiontype": transaction_type,
    #                         "transactioncount": transaction_count,
    #                         "transactionamount": transaction_amount,
    #                         "startdate": start_date,
    #                         "enddate": end_date
    #                     }
    #                 }
    #             ]
    #         }
    #         # print("==========================================")
    #         # print("==========================================")
    #         # print(data)
    #         # print("==========================================")
    #         # print("==========================================")

    #         response = requests.post(
    #             url,
    #             headers={**self.headers, 'Content-Type': 'application/json'}, 
    #             json=data
    #         )
    #         response.raise_for_status()
            
    #         return {'success': True, 'data': response.json()}
            
    #     except requests.RequestException as e:
    #         app.logger.error(f"Error saving transaction report: {e}")
    #         return {'success': False, 'error': str(e)}


    def update_client_schedule(self, record_id, schedule_enabled, schedule_day, schedule_time):
        """Update client schedule settings"""
        try:
            url = f"{self.base_url}/ClientDetails"
            data = {
                "records": [
                    {
                        "id": record_id,
                        "fields": {
                            "schedule_enabled": str(schedule_enabled),
                            "schedule_day": str(schedule_day),
                            "schedule_time": str(schedule_time)
                        }
                    }
                ]
            }

            response = requests.patch(url, headers={**self.headers, "Content-Type": "application/json"}, json=data)
            response.raise_for_status()
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
            # print(data)
            # print(response)
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")

            return {"success": True, "data": response.json()}
        except requests.RequestException as e:
            print(f"Error updating client schedule: {e}")
            return {"success": False, "error": str(e)}


    def fetch_airtable_schedules(self,scheduler_day):
        try:
            base_urls = f"{self.base_url}/ClientDetails"
            headers = {
                'Accept': 'application/json',
                'Authorization': f'Bearer {self.access_token}'
            }
            params = {
                'filterByFormula': f"AND({{schedule_day}}='{scheduler_day}',{{schedule_enabled}}='True')"
            }

            response = requests.get(base_urls, headers=headers, params=params)
            response.raise_for_status()

            return {'success': True, 'data': response.json()}

        except requests.exceptions.HTTPError as http_err:
            print(f"HTTP error occurred: {http_err}")
            return {'success': False, 'error': f"HTTP error: {http_err}"}

        except requests.exceptions.RequestException as req_err:
            print(f"Request error occurred: {req_err}")
            return {'success': False, 'error': f"Request error: {req_err}"}

        except Exception as e:
            print(f"Unexpected error occurred: {e}")
            return {'success': False, 'error': f"Unexpected error: {e}"}


    def get_company_info(self,company_id, access_token):
        """
        Fetch company info from QuickBooks Online and return it in simplified JSON format.
        """
        url = f"https://quickbooks.api.intuit.com/v3/company/{company_id}/query"
        params = {
            "query": "select * from CompanyInfo",
            "minorversion": 75
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            # Debug print
            print("#########################################")
            print(data)
            print("#########################################")

            # If QueryResponse is missing → return error
            if "QueryResponse" not in data or "CompanyInfo" not in data["QueryResponse"]:
                return {"error": "CompanyInfo not found in response", "raw": data}

            company_info = data["QueryResponse"]["CompanyInfo"][0]

            result = {
                "company_name": company_info.get("CompanyName"),
                "address": company_info.get("CompanyAddr", {}).get("Line1"),
                "city": company_info.get("CompanyAddr", {}).get("City"),
                "postal_code": company_info.get("CompanyAddr", {}).get("PostalCode"),
                "qbo_industry_type": next(
                    (item.get("Value") for item in company_info.get("NameValue", [])
                     if item.get("Name") == "QBOIndustryType"), None
                ),
                "web_address": company_info.get("WebAddr", {}).get("URI"),
                "email_communication": company_info.get("CustomerCommunicationEmailAddr", {}).get("Address"),
                "country_division_code": company_info.get("CompanyAddr", {}).get("CountrySubDivisionCode"),
                "country": company_info.get("Country"),
                "company_start_date": company_info.get("CompanyStartDate"),
                "employer_id": company_info.get("EmployerId"),
                "phone": company_info.get("PrimaryPhone", {}).get("FreeFormNumber"),
                "email": company_info.get("Email", {}).get("Address"),
            }

            return result

        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
