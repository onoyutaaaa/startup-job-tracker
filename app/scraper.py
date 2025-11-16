"""Web scraper for startup job postings"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobScraper:
    """Base class for job scraping"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def extract_salary(self, text: str) -> tuple[Optional[float], Optional[float]]:
        """Extract salary range from text"""
        if not text:
            return None, None

        # Pattern: 500万円〜1000万円, 500-1000万円, etc.
        patterns = [
            r'(\d+)(?:万円?)?[〜～~\-](\d+)(?:万円?)?',
            r'(\d+)万円以上',
            r'年収(\d+)万円',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2:
                    return float(match.group(1)) * 10000, float(match.group(2)) * 10000
                elif len(match.groups()) == 1:
                    salary = float(match.group(1)) * 10000
                    return salary, None

        return None, None


class LayerXScraper(JobScraper):
    """Scraper for LayerX career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://layerx.co.jp"
        self.careers_url = "https://recruit.layerx.co.jp/"

    def scrape(self) -> List[Dict]:
        """Scrape LayerX job postings"""
        jobs = []
        try:
            logger.info(f"Scraping LayerX: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Note: This is a template - actual selectors need to be adjusted based on real website structure
            job_listings = soup.find_all(['article', 'div'], class_=re.compile(r'job|position|career', re.I))

            for job in job_listings[:20]:  # Limit to 20 jobs
                try:
                    title_elem = job.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|position', re.I))
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = job.find('a')
                    url = link['href'] if link and link.get('href') else ''

                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    description = job.get_text(strip=True)[:500]
                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': 'LayerX',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.error(f"Error parsing LayerX job: {e}")
                    continue

            logger.info(f"Found {len(jobs)} jobs from LayerX")
        except Exception as e:
            logger.error(f"Error scraping LayerX: {e}")

        return jobs


class SmartHRScraper(JobScraper):
    """Scraper for SmartHR career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://smarthr.co.jp"
        self.careers_url = "https://hello-world.smarthr.co.jp/"

    def scrape(self) -> List[Dict]:
        """Scrape SmartHR job postings"""
        jobs = []
        try:
            logger.info(f"Scraping SmartHR: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Note: This is a template - actual selectors need to be adjusted based on real website structure
            job_listings = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'job|position|career|recruit', re.I))

            for job in job_listings[:20]:
                try:
                    title_elem = job.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|position', re.I))
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = job.find('a')
                    url = link['href'] if link and link.get('href') else ''

                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    description = job.get_text(strip=True)[:500]
                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': 'SmartHR',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.error(f"Error parsing SmartHR job: {e}")
                    continue

            logger.info(f"Found {len(jobs)} jobs from SmartHR")
        except Exception as e:
            logger.error(f"Error scraping SmartHR: {e}")

        return jobs


class HERPScraper(JobScraper):
    """Scraper for HERP career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://herp.careers"
        self.careers_url = "https://herp.careers/v1/herpinc"

    def scrape(self) -> List[Dict]:
        """Scrape HERP job postings"""
        jobs = []
        try:
            logger.info(f"Scraping HERP: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Note: This is a template - actual selectors need to be adjusted based on real website structure
            job_listings = soup.find_all(['article', 'div', 'li'], class_=re.compile(r'job|position|career', re.I))

            for job in job_listings[:20]:
                try:
                    title_elem = job.find(['h2', 'h3', 'h4', 'a'], class_=re.compile(r'title|name|position', re.I))
                    if not title_elem:
                        continue

                    title = title_elem.get_text(strip=True)
                    link = job.find('a')
                    url = link['href'] if link and link.get('href') else ''

                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    description = job.get_text(strip=True)[:500]
                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': 'HERP',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.error(f"Error parsing HERP job: {e}")
                    continue

            logger.info(f"Found {len(jobs)} jobs from HERP")
        except Exception as e:
            logger.error(f"Error scraping HERP: {e}")

        return jobs


def scrape_all_jobs() -> List[Dict]:
    """Scrape jobs from all companies"""
    all_jobs = []

    scrapers = [
        LayerXScraper(),
        SmartHRScraper(),
        HERPScraper()
    ]

    for scraper in scrapers:
        try:
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
        except Exception as e:
            logger.error(f"Error with scraper {scraper.__class__.__name__}: {e}")

    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    # Test scraping
    jobs = scrape_all_jobs()
    for job in jobs:
        print(f"{job['company']}: {job['title']}")
