import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin, urlparse
import logging
import time
from typing import Set, Dict, List, Optional
import json
import os
from datetime import datetime
import re
import sys

class MOSDACScraper:
    def __init__(self, base_url: str = "https://mosdac.gov.in"):
        self.base_url = base_url
        self.visited_urls: Set[str] = set()
        self.content_data: List[Dict] = []
        self.setup_logging()
        self.setup_driver()
        self.categories = {
            'missions': [],
            'catalog': [],
            'galleries': [],
            'data_access': [],
            'reports': [],
            'services': []
        }

    def setup_logging(self):
        """Configure logging for the scraper"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('scraper.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def setup_driver(self):
        """Setup Selenium WebDriver for JavaScript-rendered content"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            
            # Use the default Chrome installation
            self.driver = webdriver.Chrome(options=chrome_options)
            self.logger.info("WebDriver setup successful")
        except Exception as e:
            self.logger.error(f"Error setting up WebDriver: {str(e)}")
            raise

    def is_valid_url(self, url: str) -> bool:
        """Check if URL belongs to MOSDAC domain"""
        parsed_url = urlparse(url)
        return parsed_url.netloc == urlparse(self.base_url).netloc

    def extract_announcements(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract announcements from the homepage"""
        announcements = []
        announcement_section = soup.find('div', class_='announcements')
        if announcement_section:
            for item in announcement_section.find_all('div', class_='announcement-item'):
                title = item.find('h3')
                date = item.find('span', class_='date')
                link = item.find('a')
                
                if title and link:
                    announcements.append({
                        'title': title.text.strip(),
                        'date': date.text.strip() if date else None,
                        'url': urljoin(self.base_url, link['href']) if link.get('href') else None
                    })
        return announcements

    def extract_services(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract services information"""
        services = []
        services_section = soup.find('div', class_='services')
        if services_section:
            for service in services_section.find_all('div', class_='service-item'):
                title = service.find('h3')
                description = service.find('p')
                icon = service.find('img')
                
                if title:
                    services.append({
                        'title': title.text.strip(),
                        'description': description.text.strip() if description else None,
                        'icon_url': urljoin(self.base_url, icon['src']) if icon and icon.get('src') else None
                    })
        return services

    def extract_satellite_data(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract satellite data information"""
        satellite_data = []
        data_section = soup.find('div', class_='satellite-data')
        if data_section:
            for item in data_section.find_all('div', class_='data-item'):
                title = item.find('h4')
                description = item.find('p')
                download_link = item.find('a', class_='download')
                
                if title:
                    satellite_data.append({
                        'title': title.text.strip(),
                        'description': description.text.strip() if description else None,
                        'download_url': urljoin(self.base_url, download_link['href']) if download_link and download_link.get('href') else None
                    })
        return satellite_data

    def extract_content(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract relevant content from a page"""
        content = {
            'url': url,
            'title': '',
            'text_content': '',
            'meta_description': '',
            'tables': [],
            'links': [],
            'aria_labels': [],
            'announcements': [],
            'services': [],
            'satellite_data': [],
            'crawl_timestamp': datetime.now().isoformat(),
            'category': self.determine_category(url)
        }

        # Extract title
        if soup.title:
            content['title'] = soup.title.string

        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc:
            content['meta_description'] = meta_desc.get('content', '')

        # Extract main text content
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content')
        if main_content:
            content['text_content'] = main_content.get_text(strip=True, separator=' ')

        # Extract tables
        tables = soup.find_all('table')
        for table in tables:
            table_data = []
            for row in table.find_all('tr'):
                row_data = [cell.get_text(strip=True) for cell in row.find_all(['td', 'th'])]
                if row_data:
                    table_data.append(row_data)
            if table_data:
                content['tables'].append(table_data)

        # Extract links
        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href:
                full_url = urljoin(url, href)
                if self.is_valid_url(full_url):
                    content['links'].append(full_url)

        # Extract aria-labels
        for element in soup.find_all(attrs={'aria-label': True}):
            content['aria_labels'].append({
                'element': element.name,
                'aria-label': element.get('aria-label')
            })

        # Extract announcements (if on homepage)
        if url == self.base_url:
            content['announcements'] = self.extract_announcements(soup)

        # Extract services
        content['services'] = self.extract_services(soup)

        # Extract satellite data
        content['satellite_data'] = self.extract_satellite_data(soup)

        return content

    def determine_category(self, url: str) -> str:
        """Determine the category of the page based on URL"""
        url_lower = url.lower()
        if '/missions/' in url_lower:
            return 'missions'
        elif '/catalog/' in url_lower:
            return 'catalog'
        elif '/galleries/' in url_lower:
            return 'galleries'
        elif '/data-access/' in url_lower:
            return 'data_access'
        elif '/reports/' in url_lower:
            return 'reports'
        elif '/services/' in url_lower:
            return 'services'
        return 'other'

    def crawl_page(self, url: str, depth: int = 0, max_depth: int = 3):
        """Crawl a single page and extract its content"""
        if url in self.visited_urls or depth > max_depth:
            return

        self.logger.info(f"Crawling: {url} (depth: {depth})")
        self.visited_urls.add(url)

        try:
            # Use Selenium for JavaScript-rendered content
            self.driver.get(url)
            time.sleep(2)  # Wait for JavaScript to load
            
            # Wait for main content to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'lxml')

            # Extract content
            content = self.extract_content(soup, url)
            self.content_data.append(content)

            # Save progress
            self.save_progress()

            # Get all links and crawl them
            for link in content['links']:
                if link not in self.visited_urls:
                    self.crawl_page(link, depth + 1, max_depth)

        except Exception as e:
            self.logger.error(f"Error crawling {url}: {str(e)}")

    def save_progress(self):
        """Save scraped data to a JSON file"""
        with open('scraped_data.json', 'w', encoding='utf-8') as f:
            json.dump(self.content_data, f, ensure_ascii=False, indent=2)

    def start_crawling(self):
        """Start the crawling process from the base URL"""
        try:
            self.crawl_page(self.base_url)
        finally:
            self.driver.quit()
            self.save_progress()

if __name__ == "__main__":
    scraper = MOSDACScraper()
    scraper.start_crawling() 