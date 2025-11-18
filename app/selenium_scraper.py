"""Selenium-based scraper for sites with strong anti-bot protection"""
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from typing import List, Dict, Optional
import logging
import time
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SeleniumJobScraper:
    """Base class for Selenium-based job scraping"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None

    def init_driver(self):
        """Initialize Selenium WebDriver"""
        if self.driver:
            return

        chrome_options = Options()
        if self.headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.implicitly_wait(10)
        except Exception as e:
            logger.error(f"Failed to initialize Chrome driver: {e}")
            logger.info("Selenium requires ChromeDriver to be installed. Please install it or use requests-based scraping.")
            raise

    def close_driver(self):
        """Close Selenium WebDriver"""
        if self.driver:
            self.driver.quit()
            self.driver = None

    def extract_salary(self, text: str) -> tuple[Optional[float], Optional[float]]:
        """Extract salary range from text"""
        if not text:
            return None, None

        patterns = [
            r'(\d{3,4})万円[〜～~\-](\d{3,4})万円',
            r'年収\s*(\d{3,4})万円?[〜～~\-](\d{3,4})万円?',
            r'(\d+)(?:万円?)?[〜～~\-](\d+)(?:万円?)?',
            r'(\d{3,4})万円以上',
            r'年収(\d{3,4})万円',
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


class SeleniumLayerXScraper(SeleniumJobScraper):
    """Selenium-based scraper for LayerX"""

    def __init__(self, headless: bool = True):
        super().__init__(headless)
        self.company_name = 'LayerX'
        self.careers_url = 'https://open.talentio.com/r/1/c/layerx/homes/1'

    def scrape(self) -> List[Dict]:
        """Scrape LayerX job postings using Selenium"""
        jobs = []
        try:
            self.init_driver()
            logger.info(f"Scraping {self.company_name} with Selenium: {self.careers_url}")

            self.driver.get(self.careers_url)
            time.sleep(3)  # Wait for JavaScript to load

            # Find job links
            job_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="/jobs/"]')

            for elem in job_elements[:30]:
                try:
                    title = elem.text.strip()
                    url = elem.get_attribute('href')

                    if not title or len(title) < 3 or not url:
                        continue

                    # Get parent element for more context
                    try:
                        parent = elem.find_element(By.XPATH, '..')
                        description = parent.text[:500]
                    except:
                        description = title

                    salary_min, salary_max = self.extract_salary(description)

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
                    logger.debug(f"Error parsing job element: {e}")
                    continue

            # Remove duplicates
            unique_jobs = {job['url']: job for job in jobs}.values()
            jobs = list(unique_jobs)

            logger.info(f"Found {len(jobs)} jobs from {self.company_name}")

        except Exception as e:
            logger.error(f"Error scraping {self.company_name} with Selenium: {e}")
        finally:
            self.close_driver()

        return jobs


# Test function
if __name__ == "__main__":
    scraper = SeleniumLayerXScraper(headless=True)
    try:
        jobs = scraper.scrape()
        print(f"\n=== Results ===")
        print(f"Found {len(jobs)} jobs")
        for job in jobs[:3]:
            print(f"\n{job['title']}")
            print(f"URL: {job['url']}")
    except Exception as e:
        print(f"Error: {e}")
        print("\nNote: Selenium requires ChromeDriver to be installed.")
        print("Install with: apt-get install chromium-chromedriver or download from https://chromedriver.chromium.org/")
