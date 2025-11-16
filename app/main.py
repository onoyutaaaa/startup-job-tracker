"""FastAPI main application"""
from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .database import init_db, get_db, Job
from .scraper import scrape_all_jobs
from .scheduler import start_scheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Startup Job Tracker")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
async def startup_event():
    """Initialize database and scheduler on startup"""
    init_db()
    logger.info("Database initialized")

    # Start scheduler for daily job updates
    start_scheduler()
    logger.info("Scheduler started")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Serve main page"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/api/jobs")
async def get_jobs(
    search: Optional[str] = Query(None, description="Search by company or job title"),
    salary_min: Optional[float] = Query(None, description="Minimum salary"),
    salary_max: Optional[float] = Query(None, description="Maximum salary"),
    company: Optional[str] = Query(None, description="Filter by company"),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Get all jobs with filters"""
    query = db.query(Job).filter(Job.is_active == True)

    # Search filter
    if search:
        search_filter = or_(
            Job.title.ilike(f"%{search}%"),
            Job.company.ilike(f"%{search}%"),
            Job.description.ilike(f"%{search}%")
        )
        query = query.filter(search_filter)

    # Company filter
    if company:
        query = query.filter(Job.company == company)

    # Salary range filter
    if salary_min is not None:
        query = query.filter(
            or_(
                Job.salary_min >= salary_min,
                Job.salary_max >= salary_min
            )
        )

    if salary_max is not None:
        query = query.filter(
            or_(
                Job.salary_min <= salary_max,
                Job.salary_max <= salary_max
            )
        )

    total = query.count()
    jobs = query.order_by(Job.updated_at.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "jobs": [job_to_dict(job) for job in jobs]
    }


@app.get("/api/jobs/new-today")
async def get_new_jobs_today(db: Session = Depends(get_db)):
    """Get jobs posted today"""
    today = datetime.now().date()
    jobs = db.query(Job).filter(
        Job.is_active == True,
        Job.first_seen >= datetime.combine(today, datetime.min.time())
    ).order_by(Job.first_seen.desc()).all()

    return {
        "total": len(jobs),
        "jobs": [job_to_dict(job) for job in jobs]
    }


@app.get("/api/jobs/closed-yesterday")
async def get_closed_jobs_yesterday(db: Session = Depends(get_db)):
    """Get jobs that were closed yesterday"""
    yesterday = (datetime.now() - timedelta(days=1)).date()
    today = datetime.now().date()

    jobs = db.query(Job).filter(
        Job.is_active == False,
        Job.last_seen >= datetime.combine(yesterday, datetime.min.time()),
        Job.last_seen < datetime.combine(today, datetime.min.time())
    ).order_by(Job.last_seen.desc()).all()

    return {
        "total": len(jobs),
        "jobs": [job_to_dict(job) for job in jobs]
    }


@app.get("/api/jobs/high-salary")
async def get_high_salary_jobs(
    min_salary: float = Query(10000000, description="Minimum salary (default: 10,000,000 yen)"),
    db: Session = Depends(get_db)
):
    """Get high salary jobs (over 10M yen by default)"""
    jobs = db.query(Job).filter(
        Job.is_active == True,
        or_(
            Job.salary_min >= min_salary,
            Job.salary_max >= min_salary
        )
    ).order_by(Job.salary_max.desc()).all()

    return {
        "total": len(jobs),
        "min_salary": min_salary,
        "jobs": [job_to_dict(job) for job in jobs]
    }


@app.post("/api/scrape")
async def trigger_scrape(db: Session = Depends(get_db)):
    """Manually trigger job scraping"""
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

        return {
            "success": True,
            "new_jobs": new_count,
            "updated_jobs": updated_count,
            "closed_jobs": inactive_count,
            "total_scraped": len(jobs_data)
        }

    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    """Get statistics"""
    total_active = db.query(Job).filter(Job.is_active == True).count()
    total_inactive = db.query(Job).filter(Job.is_active == False).count()

    companies = db.query(Job.company).filter(Job.is_active == True).distinct().all()
    company_counts = {}
    for (company,) in companies:
        count = db.query(Job).filter(Job.company == company, Job.is_active == True).count()
        company_counts[company] = count

    today = datetime.now().date()
    new_today = db.query(Job).filter(
        Job.first_seen >= datetime.combine(today, datetime.min.time())
    ).count()

    high_salary_count = db.query(Job).filter(
        Job.is_active == True,
        or_(Job.salary_min >= 10000000, Job.salary_max >= 10000000)
    ).count()

    return {
        "total_active_jobs": total_active,
        "total_inactive_jobs": total_inactive,
        "companies": company_counts,
        "new_today": new_today,
        "high_salary_jobs": high_salary_count
    }


def job_to_dict(job: Job) -> dict:
    """Convert Job model to dictionary"""
    return {
        "id": job.id,
        "company": job.company,
        "title": job.title,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "url": job.url,
        "description": job.description,
        "location": job.location,
        "employment_type": job.employment_type,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
        "first_seen": job.first_seen.isoformat() if job.first_seen else None,
        "last_seen": job.last_seen.isoformat() if job.last_seen else None,
        "is_active": job.is_active
    }
