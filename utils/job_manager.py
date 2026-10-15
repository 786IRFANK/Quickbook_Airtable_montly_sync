# utils/job_manager.py
"""
Job management utilities for the scheduler
"""

class JobManager:
    def __init__(self, scheduler, airtable_service, logger):
        self.scheduler = scheduler
        self.airtable_service = airtable_service
        self.logger = logger
    
    def sync_jobs_with_database(self):
        """Synchronize scheduler jobs with Airtable database"""
        try:
            # Get all clients with scheduling enabled
            clients_result = self.airtable_service.get_clients()
            if not clients_result['success']:
                self.logger.error("Failed to fetch clients for job sync")
                return
            
            scheduled_clients = {}
            for client in clients_result['clients']:
                if client.get('schedule_enabled', False):
                    scheduled_clients[client['ID']] = {
                        'day': client.get('schedule_day', 1),
                        'time': client.get('schedule_time', '09:00')
                    }
            
            # Get current scheduler jobs
            current_jobs = {job.id: job for job in self.scheduler.get_jobs()}
            
            # Remove jobs for clients that no longer have scheduling enabled
            for job_id in current_jobs.keys():
                if job_id.startswith('fetch_data_'):
                    client_id = job_id.replace('fetch_data_', '')
                    if client_id not in scheduled_clients:
                        self.scheduler.remove_job(job_id)
                        self.logger.info(f"Removed job for client {client_id} (scheduling disabled)")
            
            # Add/update jobs for scheduled clients
            for client_id, schedule_info in scheduled_clients.items():
                job_id = f"fetch_data_{client_id}"
                hour, minute = map(int, schedule_info['time'].split(':'))
                
                try:
                    self.scheduler.add_job(
                        func='main:scheduled_fetch_transaction_data',
                        trigger='cron',
                        args=[client_id],
                        id=job_id,
                        day=schedule_info['day'],
                        hour=hour,
                        minute=minute,
                        replace_existing=True
                    )
                    self.logger.info(f"Synced job for client {client_id}")
                except Exception as e:
                    self.logger.error(f"Error syncing job for client {client_id}: {e}")
        
        except Exception as e:
            self.logger.error(f"Job sync error: {e}")
    
    def get_job_statistics(self):
        """Get statistics about scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        
        stats = {
            'total_jobs': len(jobs),
            'active_jobs': len([job for job in jobs if job.next_run_time]),
            'next_run': None,
            'jobs_by_day': defaultdict(int)
        }
        
        next_runs = [job.next_run_time for job in jobs if job.next_run_time]
        if next_runs:
            stats['next_run'] = min(next_runs).isoformat()
        
        for job in jobs:
            if job.trigger and hasattr(job.trigger, 'fields'):
                day_field = job.trigger.fields.get('day')
                if day_field:
                    stats['jobs_by_day'][str(day_field)] += 1
        
        return stats