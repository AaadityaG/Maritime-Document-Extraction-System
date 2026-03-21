"""Job queue management"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from app.schemas import JobResponse, JobStatus


class JobQueue:
    """Simple in-memory job queue"""
    
    def __init__(self):
        self.queue: asyncio.Queue = asyncio.Queue()
        self.processing_jobs: Dict[str, JobResponse] = {}
    
    async def enqueue(self, job_id: str, session_id: str) -> JobResponse:
        """Add job to queue"""
        job = JobResponse(
            jobId=job_id,
            status=JobStatus.QUEUED,
            startedAt=None
        )
        await self.queue.put((job_id, session_id))
        self.processing_jobs[job_id] = job
        return job
    
    async def get_job_status(self, job_id: str) -> Optional[JobResponse]:
        """Get current job status"""
        return self.processing_jobs.get(job_id)
    
    async def update_job_status(self, job_id: str, **kwargs):
        """Update job status"""
        if job_id in self.processing_jobs:
            job = self.processing_jobs[job_id]
            for key, value in kwargs.items():
                if hasattr(job, key):
                    setattr(job, key, value)
    
    async def process_jobs(self, extraction_service):
        """Background job processor"""
        while True:
            try:
                job_id, session_id = await self.queue.get()
                
                # Update status to PROCESSING
                await self.update_job_status(
                    job_id,
                    status=JobStatus.PROCESSING,
                    startedAt=datetime.utcnow()
                )
                
                # TODO: Process the actual job here
                
                self.queue.task_done()
                
            except Exception as e:
                print(f"Job processing error: {e}")
                await asyncio.sleep(1)


# Global job queue instance
job_queue = JobQueue()
