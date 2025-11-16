"""Web scraper for startup job postings"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import logging
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobScraper:
    """Base class for job scraping"""

    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def extract_salary(self, text: str) -> tuple[Optional[float], Optional[float]]:
        """Extract salary range from text"""
        if not text:
            return None, None

        # Pattern: 500万円〜1000万円, 500-1000万円, etc.
        patterns = [
            r'(\d+)(?:万円?)?[〜～~\-](\d+)(?:万円?)?',
            r'(\d{3,4})万円[〜～~\-](\d{3,4})万円',
            r'年収\s*(\d+)万円?[〜～~\-](\d+)万円?',
            r'(\d+)万円以上',
            r'年収(\d+)万円',
            r'(\d{3,4})万',
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if len(match.groups()) == 2 and match.group(2):
                    return float(match.group(1)) * 10000, float(match.group(2)) * 10000
                elif len(match.groups()) == 1:
                    salary = float(match.group(1)) * 10000
                    return salary, None

        return None, None


class HERPCareersScraper(JobScraper):
    """Generic scraper for HERP Careers platform"""

    def __init__(self, company_name: str, company_slug: str):
        super().__init__()
        self.company_name = company_name
        self.company_slug = company_slug
        self.base_url = "https://herp.careers"
        self.careers_url = f"https://herp.careers/v1/{company_slug}"

    def scrape(self) -> List[Dict]:
        """Scrape job postings from HERP Careers"""
        jobs = []
        try:
            logger.info(f"Scraping {self.company_name}: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Find job cards - HERP Careers typically uses specific patterns
            # Try multiple selectors to find job listings
            job_containers = (
                soup.find_all('a', href=re.compile(r'/v1/' + self.company_slug + r'/[a-zA-Z0-9]+')) or
                soup.find_all('div', class_=re.compile(r'job|position|card', re.I))
            )

            for job_elem in job_containers[:30]:
                try:
                    # Extract URL
                    if job_elem.name == 'a':
                        url = job_elem.get('href', '')
                    else:
                        link = job_elem.find('a')
                        url = link.get('href', '') if link else ''

                    if not url:
                        continue

                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    # Extract title
                    title_elem = (
                        job_elem.find(['h2', 'h3', 'h4']) or
                        job_elem.find(class_=re.compile(r'title|heading', re.I)) or
                        job_elem
                    )
                    title = title_elem.get_text(strip=True) if title_elem else ''

                    # Skip if title is too short or looks like navigation
                    if not title or len(title) < 3 or title in ['Home', 'About', 'Contact']:
                        continue

                    # Extract description
                    description = job_elem.get_text(strip=True)[:500]

                    # Extract salary
                    salary_min, salary_max = self.extract_salary(description)

                    if title and url and '/v1/' in url:
                        jobs.append({
                            'company': self.company_name,
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.debug(f"Error parsing {self.company_name} job element: {e}")
                    continue

            # Remove duplicates based on URL
            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from {self.company_name}")
        except Exception as e:
            logger.error(f"Error scraping {self.company_name}: {e}")

        return jobs


class LayerXScraper(JobScraper):
    """Scraper for LayerX career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://jobs.layerx.co.jp"
        self.careers_url = "https://jobs.layerx.co.jp/"

    def scrape(self) -> List[Dict]:
        """Scrape LayerX job postings"""
        jobs = []
        try:
            logger.info(f"Scraping LayerX: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for job links
            job_links = soup.find_all('a', href=re.compile(r'/(position|job|career)', re.I))

            for link in job_links[:30]:
                try:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    parent = link.find_parent(['div', 'article', 'section'])
                    description = parent.get_text(strip=True)[:500] if parent else title

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
                    logger.debug(f"Error parsing LayerX job: {e}")
                    continue

            # Remove duplicates
            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from LayerX")
        except Exception as e:
            logger.error(f"Error scraping LayerX: {e}")

        return jobs


class SmartHRScraper(JobScraper):
    """Scraper for SmartHR career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://smarthr.co.jp"
        self.careers_url = "https://smarthr.co.jp/recruit/"

    def scrape(self) -> List[Dict]:
        """Scrape SmartHR job postings"""
        jobs = []
        try:
            logger.info(f"Scraping SmartHR: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Look for job-related links
            job_links = (
                soup.find_all('a', href=re.compile(r'/(recruit|career|job)', re.I)) or
                soup.find_all('a', class_=re.compile(r'job|position|career', re.I))
            )

            for link in job_links[:30]:
                try:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    parent = link.find_parent(['div', 'article', 'section', 'li'])
                    description = parent.get_text(strip=True)[:500] if parent else title

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
                    logger.debug(f"Error parsing SmartHR job: {e}")
                    continue

            # Remove duplicates
            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from SmartHR")
        except Exception as e:
            logger.error(f"Error scraping SmartHR: {e}")

        return jobs


class TenXScraper(JobScraper):
    """Scraper for 10X career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://10x.co.jp"
        self.careers_url = "https://10x.co.jp/recruit/"

    def scrape(self) -> List[Dict]:
        """Scrape 10X job postings"""
        jobs = []
        try:
            logger.info(f"Scraping 10X: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            job_links = soup.find_all('a', href=re.compile(r'/(recruit|position|job|career)', re.I))

            for link in job_links[:30]:
                try:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    parent = link.find_parent(['div', 'article', 'section'])
                    description = parent.get_text(strip=True)[:500] if parent else title

                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': '10X',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.debug(f"Error parsing 10X job: {e}")
                    continue

            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from 10X")
        except Exception as e:
            logger.error(f"Error scraping 10X: {e}")

        return jobs


class NealleScraper(JobScraper):
    """Scraper for Nealle (ニーリー) career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://jobs.nealle.com"
        self.careers_url = "https://jobs.nealle.com/"

    def scrape(self) -> List[Dict]:
        """Scrape Nealle job postings"""
        jobs = []
        try:
            logger.info(f"Scraping Nealle: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            job_links = soup.find_all('a', href=re.compile(r'/(job|position|career)', re.I))

            for link in job_links[:30]:
                try:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    parent = link.find_parent(['div', 'article', 'section'])
                    description = parent.get_text(strip=True)[:500] if parent else title

                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': 'Nealle',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.debug(f"Error parsing Nealle job: {e}")
                    continue

            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from Nealle")
        except Exception as e:
            logger.error(f"Error scraping Nealle: {e}")

        return jobs


class ShippioScraper(JobScraper):
    """Scraper for Shippio career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://recruit.shippio.io"
        self.careers_url = "https://recruit.shippio.io/"

    def scrape(self) -> List[Dict]:
        """Scrape Shippio job postings"""
        jobs = []
        try:
            logger.info(f"Scraping Shippio: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            job_links = soup.find_all('a', href=re.compile(r'/(job|position|career|recruit)', re.I))

            for link in job_links[:30]:
                try:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    parent = link.find_parent(['div', 'article', 'section'])
                    description = parent.get_text(strip=True)[:500] if parent else title

                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': 'Shippio',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.debug(f"Error parsing Shippio job: {e}")
                    continue

            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from Shippio")
        except Exception as e:
            logger.error(f"Error scraping Shippio: {e}")

        return jobs


class HacomonoScraper(JobScraper):
    """Scraper for hacomono career page"""

    def __init__(self):
        super().__init__()
        self.base_url = "https://www.hacomono.co.jp"
        self.careers_url = "https://www.hacomono.co.jp/recruit/"

    def scrape(self) -> List[Dict]:
        """Scrape hacomono job postings"""
        jobs = []
        try:
            logger.info(f"Scraping hacomono: {self.careers_url}")
            response = requests.get(self.careers_url, headers=self.headers, timeout=15)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            job_links = soup.find_all('a', href=re.compile(r'/(recruit|position|job|career)', re.I))

            for link in job_links[:30]:
                try:
                    url = link.get('href', '')
                    if url and not url.startswith('http'):
                        url = self.base_url + url

                    title = link.get_text(strip=True)

                    if not title or len(title) < 3:
                        continue

                    parent = link.find_parent(['div', 'article', 'section'])
                    description = parent.get_text(strip=True)[:500] if parent else title

                    salary_min, salary_max = self.extract_salary(description)

                    if title and url:
                        jobs.append({
                            'company': 'hacomono',
                            'title': title,
                            'url': url,
                            'description': description,
                            'salary_min': salary_min,
                            'salary_max': salary_max,
                            'location': None,
                            'employment_type': None
                        })
                except Exception as e:
                    logger.debug(f"Error parsing hacomono job: {e}")
                    continue

            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from hacomono")
        except Exception as e:
            logger.error(f"Error scraping hacomono: {e}")

        return jobs


def scrape_all_jobs() -> List[Dict]:
    """Scrape jobs from all companies"""
    all_jobs = []

    # Companies using HERP Careers platform
    herp_companies = [
        ('HERP', 'herpinc'),
        ('Nstock', 'nstock'),
        ('Stract', 'stract'),
        ('SecureNavi', 'securenavi'),
        ('IVRy', 'ivry'),
    ]

    # Custom scrapers
    custom_scrapers = [
        LayerXScraper(),
        SmartHRScraper(),
        TenXScraper(),
        NealleScraper(),
        ShippioScraper(),
        HacomonoScraper(),
    ]

    # Scrape from HERP Careers companies
    for company_name, company_slug in herp_companies:
        try:
            scraper = HERPCareersScraper(company_name, company_slug)
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            time.sleep(1)  # Be polite to the server
        except Exception as e:
            logger.error(f"Error with HERP Careers scraper for {company_name}: {e}")

    # Scrape from custom sites
    for scraper in custom_scrapers:
        try:
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            time.sleep(1)  # Be polite to the server
        except Exception as e:
            logger.error(f"Error with scraper {scraper.__class__.__name__}: {e}")

    logger.info(f"Total jobs scraped: {len(all_jobs)}")
    return all_jobs


if __name__ == "__main__":
    # Test scraping
    jobs = scrape_all_jobs()
    print(f"\n=== Summary ===")
    print(f"Total jobs found: {len(jobs)}")

    # Group by company
    by_company = {}
    for job in jobs:
        company = job['company']
        by_company[company] = by_company.get(company, 0) + 1

    print("\nJobs by company:")
    for company, count in sorted(by_company.items()):
        print(f"  {company}: {count}")

    # Show sample jobs
    print("\n=== Sample Jobs ===")
    for job in jobs[:5]:
        print(f"\n{job['company']}: {job['title']}")
        print(f"  URL: {job['url']}")
        if job['salary_min'] or job['salary_max']:
            print(f"  Salary: {job['salary_min']} - {job['salary_max']}")
