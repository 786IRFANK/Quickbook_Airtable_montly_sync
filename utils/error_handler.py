# utils/error_handler.py
"""
Enhanced error handling and logging
"""

class ErrorHandler:
    def __init__(self, logger):
        self.logger = logger
        self.error_counts = defaultdict(int)
        self.last_errors = defaultdict(list)
    
    def handle_api_error(self, service, error, client_id=None):
        """Handle API errors with retry logic"""
        error_key = f"{service}_{client_id}" if client_id else service
        self.error_counts[error_key] += 1
        
        # Store recent errors (keep last 10)
        self.last_errors[error_key].append({
            'timestamp': datetime.now().isoformat(),
            'error': str(error),
            'count': self.error_counts[error_key]
        })
        
        if len(self.last_errors[error_key]) > 10:
            self.last_errors[error_key] = self.last_errors[error_key][-10:]
        
        # Log error with context
        self.logger.error(f"API Error - Service: {service}, Client: {client_id}, "
                         f"Error: {error}, Count: {self.error_counts[error_key]}")
        
        # Determine if we should retry or pause this client
        if self.error_counts[error_key] >= 5:
            self.logger.warning(f"Too many errors for {error_key}, consider pausing")
            return False  # Don't retry
        
        return True  # Can retry
    
    def get_error_summary(self):
        """Get summary of recent errors"""
        return {
            'error_counts': dict(self.error_counts),
            'recent_errors': dict(self.last_errors)
        }