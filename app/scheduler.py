"""Scheduler for automatic job scraping"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import logging

from .database import SessionLocal
from .scraper import scrape_all_jobs
from .database import Job

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_jobs():
    """Update jobs from all scrapers"""
    logger.info(f"Starting scheduled job update at {datetime.now()}")

    db = SessionLocal()
    try:
        jobs_data = scrape_all_jobs()

        # Get existing job URLs
        existing_urls = {job.url for job in db.query(Job.url).all()}

        # Mark all existing jobs as potentially inactive
        active_urls = set()

        new_count = 0
        updated_count = 0

        for job_data in jobs_data:
            url = job_data['url']
            active_urls.add(url)

            # Check if job exists
            existing_job = db.query(Job).filter(Job.url == url).first()

            if existing_job:
                # Update existing job
                existing_job.title = job_data['title']
                existing_job.description = job_data['description']
                existing_job.salary_min = job_data['salary_min']
                existing_job.salary_max = job_data['salary_max']
                existing_job.last_seen = datetime.now()
                existing_job.is_active = True
                updated_count += 1
            else:
                # Create new job
                new_job = Job(
                    company=job_data['company'],
                    title=job_data['title'],
                    url=url,
                    description=job_data['description'],
                    salary_min=job_data['salary_min'],
                    salary_max=job_data['salary_max'],
                    location=job_data.get('location'),
                    employment_type=job_data.get('employment_type'),
                    first_seen=datetime.now(),
                    last_seen=datetime.now(),
                    is_active=True
                )
                db.add(new_job)
                new_count += 1

        # Mark jobs not found in scrape as inactive
        inactive_count = 0
        for url in existing_urls - active_urls:
            job = db.query(Job).filter(Job.url == url, Job.is_active == True).first()
            if job:
                job.is_active = False
                job.last_seen = datetime.now()
                inactive_count += 1

        db.commit()

        logger.info(f"Job update completed: {new_count} new, {updated_count} updated, {inactive_count} closed")

    except Exception as e:
        logger.error(f"Error during scheduled job update: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler():
    """Start the job scheduler"""
    scheduler = BackgroundScheduler()

    # Schedule job to run daily at 12:00 PM
    scheduler.add_job(
        update_jobs,
        trigger=CronTrigger(hour=12, minute=0),
        id='daily_job_update',
        name='Daily job scraping at 12:00',
        replace_existing=True
    )

    # Optional: Run immediately on startup for testing
    # scheduler.add_job(
    #     update_jobs,
    #     id='startup_job_update',
    #     name='Initial job scraping on startup'
    # )

    scheduler.start()
    logger.info("Scheduler started - Jobs will be updated daily at 12:00")

    return scheduler
