# utils/batch_processor.py
"""
Batch processing utilities for handling multiple clients efficiently
"""

class BatchProcessor:
    def __init__(self, airtable_service, quickbooks_service, task_queue, logger):
        self.airtable_service = airtable_service
        self.quickbooks_service = quickbooks_service
        self.task_queue = task_queue
        self.logger = logger
        
    def process_all_scheduled_clients(self):
        """Process all clients that have scheduling enabled (for manual trigger)"""
        try:
            clients_result = self.airtable_service.get_clients()
            if not clients_result['success']:
                self.logger.error("Failed to fetch clients for batch processing")
                return
            
            scheduled_clients = [
                client for client in clients_result['clients'] 
                if client.get('schedule_enabled', False)
            ]
            
            self.logger.info(f"Found {len(scheduled_clients)} clients with scheduling enabled")
            
            # Add delay between tasks to respect rate limits
            delay = 0
            for client in scheduled_clients:
                # Add task with delay
                threading.Timer(delay, lambda c=client: self.task_queue.add_task(
                    self._process_single_client, c['ID']
                )).start()
                delay += 2  # 2 second delay between clients
            
        except Exception as e:
            self.logger.error(f"Batch processing error: {e}")
    
    def _process_single_client(self, client_id):
        """Process a single client with error handling"""
        try:
            from main import fetch_transaction_data_task
            fetch_transaction_data_task(client_id)
            self.logger.info(f"Successfully processed client {client_id}")
        except Exception as e:
            self.logger.error(f"Error processing client {client_id}: {e}")
