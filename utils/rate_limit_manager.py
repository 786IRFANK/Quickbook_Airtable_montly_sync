# utils/rate_limit_manager.py
"""
Advanced rate limiting with exponential backoff
"""
import time
import threading
from collections import defaultdict

class AdvancedRateLimiter:
    def __init__(self):
        self.limits = {
            'airtable_global': {'max_requests': 5, 'window': 1, 'requests': []},
            'quickbooks_global': {'max_requests': 450, 'window': 60, 'requests': []},
            'quickbooks_per_realm': defaultdict(lambda: {'max_requests': 450, 'window': 60, 'requests': []})
        }
        self.lock = threading.Lock()
    
    def can_proceed(self, service_type, realm_id=None):
        """Check if request can proceed based on rate limits"""
        with self.lock:
            now = time.time()
            
            # Clean old requests
            self._clean_old_requests(now)
            
            if service_type == 'airtable':
                limit_info = self.limits['airtable_global']
            elif service_type == 'quickbooks':
                # Check both global and per-realm limits
                global_limit = self.limits['quickbooks_global']
                realm_limit = self.limits['quickbooks_per_realm'][realm_id] if realm_id else None
                
                # Check global limit
                if len(global_limit['requests']) >= global_limit['max_requests']:
                    return False
                
                # Check per-realm limit if applicable
                if realm_limit and len(realm_limit['requests']) >= realm_limit['max_requests']:
                    return False
                
                # Record the request
                global_limit['requests'].append(now)
                if realm_limit:
                    realm_limit['requests'].append(now)
                return True
            
            else:
                limit_info = self.limits['airtable_global']
            
            if len(limit_info['requests']) < limit_info['max_requests']:
                limit_info['requests'].append(now)
                return True
            
            return False
    
    def _clean_old_requests(self, now):
        """Remove old requests outside the time window"""
        for service, limit_info in self.limits.items():
            if service != 'quickbooks_per_realm':
                window = limit_info['window']
                limit_info['requests'] = [
                    req_time for req_time in limit_info['requests'] 
                    if now - req_time < window
                ]
        
        # Clean per-realm limits
        for realm_id, limit_info in self.limits['quickbooks_per_realm'].items():
            window = limit_info['window']
            limit_info['requests'] = [
                req_time for req_time in limit_info['requests'] 
                if now - req_time < window
            ]