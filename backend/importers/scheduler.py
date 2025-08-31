"""
Import Scheduler for automatic thesis import from HAL and Greenstone
Runs scheduled imports and provides management interface
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List
import schedule
import threading
import time
import uuid
from motor.motor_asyncio import AsyncIOMotorDatabase

from .hal_connector import HALConnector
from .greenstone_connector import GreenstoneConnector

logger = logging.getLogger(__name__)

class ImportScheduler:
    """Scheduler for automatic thesis imports"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.hal_connector = HALConnector(db)
        self.greenstone_connector = GreenstoneConnector(db)
        self.running = False
        self.scheduler_thread = None
        
    def start(self):
        """Start the import scheduler"""
        if self.running:
            return
        
        self.running = True
        
        # Schedule imports
        schedule.every().sunday.at("02:00").do(self._run_weekly_import)
        schedule.every().day.at("03:00").do(self._run_daily_maintenance)
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=self._run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
        
        logger.info("Import scheduler started")
    
    def stop(self):
        """Stop the import scheduler"""
        self.running = False
        schedule.clear()
        logger.info("Import scheduler stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    
    def _run_weekly_import(self):
        """Run weekly import job"""
        logger.info("Starting weekly import job")
        asyncio.create_task(self.run_full_import())
    
    def _run_daily_maintenance(self):
        """Run daily maintenance tasks"""
        logger.info("Starting daily maintenance")
        asyncio.create_task(self.run_maintenance())
    
    async def run_full_import(self, max_records_per_source: int = 100) -> Dict[str, Any]:
        """Run full import from all sources"""
        logger.info("Starting full import process")
        
        import_stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "hal_stats": {"processed": 0, "imported": 0, "duplicates": 0, "errors": 0},
            "greenstone_stats": {"processed": 0, "imported": 0, "duplicates": 0, "errors": 0},
            "total_imported": 0,
            "completed_at": None,
            "status": "running"
        }
        
        try:
            # Save import job to database
            import_job = {
                "id": str(uuid.uuid4()),
                "type": "full_import",
                "status": "running",
                "started_at": import_stats["started_at"],
                "stats": import_stats
            }
            await self.db.import_jobs.insert_one(import_job)
            
            # Import from HAL
            logger.info("Starting HAL import...")
            try:
                import_stats["hal_stats"] = await self.hal_connector.import_from_hal(max_records_per_source)
            except Exception as e:
                logger.error(f"HAL import failed: {e}")
                import_stats["hal_stats"]["errors"] += 1
            
            # Import from Greenstone
            logger.info("Starting Greenstone import...")
            try:
                import_stats["greenstone_stats"] = await self.greenstone_connector.import_from_greenstone(max_records_per_source)
            except Exception as e:
                logger.error(f"Greenstone import failed: {e}")
                import_stats["greenstone_stats"]["errors"] += 1
            
            # Calculate totals
            import_stats["total_imported"] = (
                import_stats["hal_stats"]["imported"] + 
                import_stats["greenstone_stats"]["imported"]
            )
            
            import_stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            import_stats["status"] = "completed"
            
            # Update import job in database
            await self.db.import_jobs.update_one(
                {"id": import_job["id"]},
                {
                    "$set": {
                        "status": "completed",
                        "completed_at": import_stats["completed_at"],
                        "stats": import_stats
                    }
                }
            )
            
            logger.info(f"Full import completed: {import_stats['total_imported']} new theses imported")
            return import_stats
            
        except Exception as e:
            logger.error(f"Error during full import: {e}")
            import_stats["status"] = "failed"
            import_stats["error"] = str(e)
            import_stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            
            # Update import job as failed
            if 'import_job' in locals():
                await self.db.import_jobs.update_one(
                    {"id": import_job["id"]},
                    {
                        "$set": {
                            "status": "failed",
                            "completed_at": import_stats["completed_at"],
                            "error": str(e),
                            "stats": import_stats
                        }
                    }
                )
            
            return import_stats
    
    async def run_maintenance(self) -> Dict[str, Any]:
        """Run maintenance tasks"""
        logger.info("Starting maintenance tasks")
        
        maintenance_stats = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "tasks_completed": [],
            "errors": []
        }
        
        try:
            # Task 1: Clean up old import jobs (keep last 50)
            try:
                import_jobs = await self.db.import_jobs.find({}).sort("started_at", -1).to_list(length=None)
                if len(import_jobs) > 50:
                    jobs_to_delete = import_jobs[50:]
                    job_ids = [job["id"] for job in jobs_to_delete]
                    await self.db.import_jobs.delete_many({"id": {"$in": job_ids}})
                    maintenance_stats["tasks_completed"].append(f"Cleaned {len(job_ids)} old import jobs")
            except Exception as e:
                maintenance_stats["errors"].append(f"Import job cleanup failed: {e}")
            
            # Task 2: Update citation counts (recalculate cross-references)
            try:
                await self.update_citation_counts()
                maintenance_stats["tasks_completed"].append("Updated citation counts")
            except Exception as e:
                maintenance_stats["errors"].append(f"Citation count update failed: {e}")
            
            # Task 3: Update university and author rankings
            try:
                await self.update_rankings()
                maintenance_stats["tasks_completed"].append("Updated rankings")
            except Exception as e:
                maintenance_stats["errors"].append(f"Rankings update failed: {e}")
            
            maintenance_stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            logger.info(f"Maintenance completed: {len(maintenance_stats['tasks_completed'])} tasks, {len(maintenance_stats['errors'])} errors")
            
            return maintenance_stats
            
        except Exception as e:
            logger.error(f"Error during maintenance: {e}")
            maintenance_stats["errors"].append(str(e))
            maintenance_stats["completed_at"] = datetime.now(timezone.utc).isoformat()
            return maintenance_stats
    
    async def update_citation_counts(self):
        """Update citation counts based on internal references"""
        try:
            # Get all theses
            theses = await self.db.theses.find({}).to_list(length=None)
            
            # Simple citation counting based on title mentions in abstracts/titles
            for thesis in theses:
                citation_count = 0
                thesis_title_words = set(thesis.get("title", "").lower().split())
                
                if len(thesis_title_words) < 2:
                    continue
                
                # Count how many other theses reference this one
                for other_thesis in theses:
                    if other_thesis["id"] == thesis["id"]:
                        continue
                    
                    other_text = (
                        other_thesis.get("title", "") + " " + 
                        other_thesis.get("abstract", "")
                    ).lower()
                    
                    # Simple check for title word overlap
                    overlap = len(thesis_title_words.intersection(set(other_text.split())))
                    if overlap >= 2:  # At least 2 words match
                        citation_count += 1
                
                # Update thesis citation count
                await self.db.theses.update_one(
                    {"id": thesis["id"]},
                    {"$set": {"site_citations_count": citation_count}}
                )
                
        except Exception as e:
            logger.error(f"Error updating citation counts: {e}")
    
    async def update_rankings(self):
        """Update author and university rankings cache"""
        try:
            logger.info("Rankings updated (currently calculated on-demand)")
        except Exception as e:
            logger.error(f"Error updating rankings: {e}")
    
    async def get_import_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get import job history"""
        try:
            jobs = await self.db.import_jobs.find({}).sort("started_at", -1).limit(limit).to_list(length=limit)
            return jobs
        except Exception as e:
            logger.error(f"Error getting import history: {e}")
            return []
    
    async def close(self):
        """Close connectors and stop scheduler"""
        self.stop()
        await self.hal_connector.close()
        await self.greenstone_connector.close()