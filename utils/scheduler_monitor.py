# utils/scheduler_monitor.py
"""
Utility functions for monitoring and managing the scheduling system
"""
import logging
from datetime import datetime, timedelta
import requests
import time

class SchedulerMonitor:
    def __init__(self, airtable_service, quickbooks_service, app_logger):
        self.airtable_service = airtable_service
        self.quickbooks_service = quickbooks_service
        self.logger = app_logger
        
    def health_check(self):
        """Perform health check on all services"""
        health_status = {
            'airtable': False,
            'quickbooks': False,
            'timestamp': datetime.now().isoformat()
        }
        
        # Check Airtable connectivity
        try:
            result = self.airtable_service.get_clients()
            health_status['airtable'] = result['success']
        except Exception as e:
            self.logger.error(f"Airtable health check failed: {e}")
        
        # Check QuickBooks API (basic connectivity)
        try:
            # This is a simple connectivity test
            response = requests.get('https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer', timeout=5)
            health_status['quickbooks'] = response.status_code in [400, 401]  # Expected for invalid request
        except Exception as e:
            self.logger.error(f"QuickBooks health check failed: {e}")
        
        return health_status
    
    def get_queue_status(self, task_queue):
        """Get current task queue status"""
        return {
            'queue_size': task_queue.queue.qsize(),
            'workers_active': len([w for w in task_queue.workers if w.is_alive()]),
            'total_workers': len(task_queue.workers),
            'running': task_queue.running
        }
    
    def check_token_expiry(self):
        """Check for tokens that will expire soon"""
        try:
            clients_result = self.airtable_service.get_clients()
            if not clients_result['success']:
                return []
            
            expiring_soon = []
            now = datetime.now()
            
            for client in clients_result['clients']:
                if client.get('timestamp'):
                    try:
                        # Check refresh token expiry (more critical)
                        created_time = datetime.fromisoformat(client['timestamp'].replace('Z', '+00:00'))
                        expire_seconds = int(client.get('Rtoken_expire', 0))
                        expire_time = created_time + timedelta(seconds=expire_seconds)
                        
                        # Alert if expiring within 7 days
                        if expire_time - now < timedelta(days=7):
                            expiring_soon.append({
                                'client_id': client['ID'],
                                'client_name': client['Name'],
                                'expires_in': str(expire_time - now),
                                'expire_time': expire_time.isoformat()
                            })
                    except Exception as e:
                        self.logger.error(f"Error checking token expiry for client {client['ID']}: {e}")
            
            return expiring_soon
            
        except Exception as e:
            self.logger.error(f"Error checking token expiry: {e}")
            return []