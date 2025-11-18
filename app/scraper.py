"""Web scraper for startup job postings"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
import re
import logging
from datetime import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class JobScraper:
    """Base class for job scraping"""

    def __init__(self):
        self.session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Enhanced headers to mimic real browser
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0',
        }

    def extract_salary(self, text: str) -> tuple[Optional[float], Optional[float]]:
        """Extract salary range from text"""
        if not text:
            return None, None

        # Pattern: 500万円〜1000万円, 500-1000万円, etc.
        patterns = [
            r'(\d{3,4})万円[〜～~\-](\d{3,4})万円',
            r'年収\s*(\d{3,4})万円?[〜～~\-](\d{3,4})万円?',
            r'(\d+)(?:万円?)?[〜～~\-](\d+)(?:万円?)?',
            r'(\d{3,4})万円以上',
            r'年収(\d{3,4})万円',
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

    def get_page(self, url: str, timeout: int = 15) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage"""
        try:
            response = self.session.get(url, headers=self.headers, timeout=timeout)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.warning(f"403 Forbidden for {url}. Trying with different headers...")
                # Try with minimal headers
                try:
                    simple_headers = {'User-Agent': 'Mozilla/5.0'}
                    response = self.session.get(url, headers=simple_headers, timeout=timeout)
                    response.raise_for_status()
                    return BeautifulSoup(response.content, 'html.parser')
                except:
                    pass
            logger.error(f"HTTP Error for {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None


class TalentioScraper(JobScraper):
    """Generic scraper for Talentio platform"""

    def __init__(self, company_name: str, company_slug: str):
        super().__init__()
        self.company_name = company_name
        self.company_slug = company_slug
        self.base_url = "https://open.talentio.com"
        self.api_url = f"https://open.talentio.com/api/v1/public/careers/{company_slug}/jobs"

    def scrape(self) -> List[Dict]:
        """Scrape job postings from Talentio"""
        jobs = []
        try:
            logger.info(f"Scraping {self.company_name} via Talentio API")

            # Try API first
            response = self.session.get(self.api_url, headers=self.headers, timeout=15)

            if response.status_code == 200:
                try:
                    data = response.json()
                    job_list = data.get('jobs', []) if isinstance(data, dict) else data

                    for job_data in job_list:
                        try:
                            job_id = job_data.get('id') or job_data.get('job_id')
                            title = job_data.get('title') or job_data.get('name', '')

                            url = f"{self.base_url}/r/1/c/{self.company_slug}/jobs/{job_id}"

                            description = job_data.get('description', '')[:500]
                            location = job_data.get('location') or job_data.get('workplace')

                            # Extract salary from description or dedicated field
                            salary_text = job_data.get('salary', '') or description
                            salary_min, salary_max = self.extract_salary(salary_text)

                            if title:
                                jobs.append({
                                    'company': self.company_name,
                                    'title': title,
                                    'url': url,
                                    'description': description,
                                    'salary_min': salary_min,
                                    'salary_max': salary_max,
                                    'location': location,
                                    'employment_type': job_data.get('employment_type')
                                })
                        except Exception as e:
                            logger.debug(f"Error parsing {self.company_name} job: {e}")
                            continue

                    logger.info(f"Found {len(jobs)} jobs from {self.company_name} (Talentio API)")
                    return jobs
                except Exception as e:
                    logger.warning(f"Failed to parse Talentio API response: {e}")

            # Fallback to HTML scraping
            careers_url = f"{self.base_url}/r/1/c/{self.company_slug}/homes/1"
            soup = self.get_page(careers_url)

            if soup:
                job_links = soup.find_all('a', href=re.compile(r'/jobs/\d+'))

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
                        logger.debug(f"Error parsing {self.company_name} job: {e}")
                        continue

                unique_jobs = {job['url']: job for job in jobs}.values()
                jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from {self.company_name}")
        except Exception as e:
            logger.error(f"Error scraping {self.company_name}: {e}")

        return jobs


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

            soup = self.get_page(self.careers_url)
            if not soup:
                return jobs

            # Find job cards
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


class LayerXScraper(TalentioScraper):
    """Scraper for LayerX career page (uses Talentio)"""

    def __init__(self):
        super().__init__('LayerX', 'layerx')


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

            soup = self.get_page(self.careers_url)
            if not soup:
                return jobs

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


class TenXScraper(TalentioScraper):
    """Scraper for 10X career page (uses Talentio)"""

    def __init__(self):
        super().__init__('10X', '10x')


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

            soup = self.get_page(self.careers_url)
            if not soup:
                return jobs

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

            soup = self.get_page(self.careers_url)
            if not soup:
                return jobs

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


class HacomonoScraper(TalentioScraper):
    """Scraper for hacomono career page (uses Talentio)"""

    def __init__(self):
        super().__init__('hacomono', 'hacomono')


class WantedlyScraper(JobScraper):
    """Generic scraper for Wantedly platform"""

    def __init__(self, company_name: str, company_slug: str):
        super().__init__()
        self.company_name = company_name
        self.company_slug = company_slug
        self.base_urls = [
            "https://sg.wantedly.com",      # Try Singapore version first (less restrictions)
            "https://www.wantedly.com",     # Then main site
            "https://en-jp.wantedly.com",   # English-Japanese version
        ]

    def scrape(self) -> List[Dict]:
        """Scrape job postings from Wantedly"""
        jobs = []

        # Try different Wantedly domains
        for base_url in self.base_urls:
            try:
                projects_url = f"{base_url}/companies/{self.company_slug}/projects"
                logger.info(f"Scraping {self.company_name} from Wantedly: {projects_url}")

                soup = self.get_page(projects_url)
                if not soup:
                    continue  # Try next domain

                # Find job cards/links on Wantedly
                # Wantedly uses project links like /projects/{id}
                job_links = soup.find_all('a', href=re.compile(r'/projects/\d+'))

                for link in job_links[:30]:
                    try:
                        url = link.get('href', '')
                        if url and not url.startswith('http'):
                            url = base_url + url

                        # Extract title from link or nearby heading
                        title = link.get_text(strip=True)

                        # Try to find better title from heading
                        heading = link.find(['h1', 'h2', 'h3', 'h4'])
                        if heading:
                            title = heading.get_text(strip=True)

                        if not title or len(title) < 3:
                            continue

                        # Get parent container for more context
                        parent = link.find_parent(['div', 'article', 'section', 'li'])
                        description = parent.get_text(strip=True)[:500] if parent else title

                        # Extract salary (Wantedly often doesn't show specific salary)
                        salary_min, salary_max = self.extract_salary(description)

                        # Extract location if available
                        location = None
                        if parent:
                            location_elem = parent.find(class_=re.compile(r'location|place|address', re.I))
                            if location_elem:
                                location = location_elem.get_text(strip=True)

                        if title and url and '/projects/' in url:
                            jobs.append({
                                'company': self.company_name,
                                'title': title,
                                'url': url,
                                'description': description,
                                'salary_min': salary_min,
                                'salary_max': salary_max,
                                'location': location,
                                'employment_type': None
                            })
                    except Exception as e:
                        logger.debug(f"Error parsing {self.company_name} Wantedly job: {e}")
                        continue

                # Remove duplicates
                unique_jobs = {job['url']: job for job in jobs}.values()
                jobs = list(unique_jobs)

                if jobs:
                    logger.info(f"Found {len(jobs)} jobs from {self.company_name} (Wantedly via {base_url})")
                    break  # Success, no need to try other domains

            except Exception as e:
                logger.debug(f"Error scraping {self.company_name} from {base_url}: {e}")
                continue  # Try next domain

        if not jobs:
            logger.warning(f"Could not scrape jobs from {self.company_name} on Wantedly (all domains failed)")

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

    # Companies on Wantedly platform
    wantedly_companies = [
        ('LayerX', 'layerx'),
        ('SmartHR', 'smarthr'),
        ('HERP', 'herp'),
        ('10X', '10x'),
        ('Stract', 'stract'),
        ('Shippio', 'shippioinc'),
        ('hacomono', 'hacomono'),
    ]

    # Custom scrapers (including Talentio-based ones)
    custom_scrapers = [
        LayerXScraper(),        # Uses Talentio
        SmartHRScraper(),       # Custom site
        TenXScraper(),          # Uses Talentio
        NealleScraper(),        # Custom site
        ShippioScraper(),       # Custom site
        HacomonoScraper(),      # Uses Talentio
    ]

    # Scrape from Wantedly (most reliable platform)
    for company_name, company_slug in wantedly_companies:
        try:
            scraper = WantedlyScraper(company_name, company_slug)
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            time.sleep(2)  # Be polite to the server
        except Exception as e:
            logger.error(f"Error with Wantedly scraper for {company_name}: {e}")

    # Scrape from HERP Careers companies
    for company_name, company_slug in herp_companies:
        try:
            scraper = HERPCareersScraper(company_name, company_slug)
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            time.sleep(2)  # Be polite to the server
        except Exception as e:
            logger.error(f"Error with HERP Careers scraper for {company_name}: {e}")

    # Scrape from custom sites
    for scraper in custom_scrapers:
        try:
            jobs = scraper.scrape()
            all_jobs.extend(jobs)
            time.sleep(2)  # Be polite to the server
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
