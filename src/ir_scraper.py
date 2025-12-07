"""
Investor Relations Website Scraper
Scrapes UMG's investor relations website to find and download annual/quarterly reports
"""

import requests
from bs4 import BeautifulSoup
import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import time
import sys

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config


class IRScraper:
    """Scrapes UMG's investor relations website for financial reports"""
    
    def __init__(self):
        """Initialize IR scraper"""
        self.base_url = config.INVESTOR_RELATIONS_URL
        self.alt_url = config.INVESTOR_RELATIONS_ALT_URL
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self.reports_found = []
        
    def scrape_ir_website(self) -> List[Dict]:
        """
        Scrape IR website to find all available reports
        
        Returns:
            List of dictionaries with report information (url, year, type, title)
        """
        print("  - Scraping investor relations website...")
        
        reports = []
        
        # Try main URL first
        try:
            reports.extend(self._scrape_url(self.base_url))
        except Exception as e:
            print(f"    Warning: Could not scrape {self.base_url}: {e}")
        
        # Try alternative URL
        if not reports:
            try:
                reports.extend(self._scrape_url(self.alt_url))
            except Exception as e:
                print(f"    Warning: Could not scrape {self.alt_url}: {e}")
        
        # Also try common report URL patterns
        if not reports:
            reports.extend(self._try_direct_report_urls())
        
        self.reports_found = reports
        return reports
    
    def _scrape_url(self, url: str) -> List[Dict]:
        """Scrape a specific URL for report links"""
        reports = []
        
        try:
            response = self.session.get(url, timeout=config.IR_SCRAPING_TIMEOUT)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all links that might be reports
            links = soup.find_all('a', href=True)
            
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                # Check if it's a PDF link
                if href.lower().endswith('.pdf'):
                    report_info = self._parse_report_link(href, text, url)
                    if report_info:
                        reports.append(report_info)
                
                # Check for report-related keywords in text
                if any(keyword in text.lower() for keyword in 
                      ['annual report', 'quarterly', 'earnings', 'financial', '10-k', '10-q']):
                    # Try to follow the link to find PDF
                    full_url = self._make_absolute_url(href, url)
                    if full_url:
                        report_info = self._parse_report_link(full_url, text, url)
                        if report_info:
                            reports.append(report_info)
        
        except requests.RequestException as e:
            print(f"    Error scraping {url}: {e}")
        
        return reports
    
    def _parse_report_link(self, href: str, text: str, base_url: str) -> Optional[Dict]:
        """Parse a link to extract report information"""
        # Make absolute URL
        url = self._make_absolute_url(href, base_url)
        if not url:
            return None
        
        # Determine report type
        report_type = None
        if 'annual' in text.lower() or 'annual' in url.lower():
            report_type = 'annual'
        elif 'quarterly' in text.lower() or 'quarterly' in url.lower() or 'q1' in text.lower() or 'q2' in text.lower() or 'q3' in text.lower() or 'q4' in text.lower():
            report_type = 'quarterly'
        
        # Extract year
        year = self._extract_year(text, url)
        
        # Only return if we can identify type and year
        if report_type and year:
            return {
                'url': url,
                'year': year,
                'type': report_type,
                'title': text,
                'filename': self._generate_filename(url, year, report_type)
            }
        
        return None
    
    def _extract_year(self, text: str, url: str) -> Optional[int]:
        """Extract year from text or URL"""
        # Look for 4-digit years (2020-2030)
        year_pattern = r'\b(20[2-3][0-9])\b'
        
        # Check text first
        matches = re.findall(year_pattern, text)
        if matches:
            return int(matches[-1])  # Take the most recent year found
        
        # Check URL
        matches = re.findall(year_pattern, url)
        if matches:
            return int(matches[-1])
        
        return None
    
    def _make_absolute_url(self, href: str, base_url: str) -> Optional[str]:
        """Convert relative URL to absolute URL"""
        if not href:
            return None
        
        if href.startswith('http://') or href.startswith('https://'):
            return href
        
        if href.startswith('//'):
            return 'https:' + href
        
        if href.startswith('/'):
            # Absolute path
            base = '/'.join(base_url.split('/')[:3])
            return base + href
        
        # Relative path
        base = '/'.join(base_url.split('/')[:-1])
        return base + '/' + href
    
    def _generate_filename(self, url: str, year: int, report_type: str) -> str:
        """Generate filename for downloaded report"""
        # Extract filename from URL
        filename = url.split('/')[-1]
        
        # Clean filename
        filename = re.sub(r'[^\w\.-]', '_', filename)
        
        # Ensure it has .pdf extension
        if not filename.lower().endswith('.pdf'):
            filename = f"UMG_{report_type.capitalize()}_Report_{year}.pdf"
        else:
            # Prepend with company and year for clarity
            base_name = filename.replace('.pdf', '')
            filename = f"UMG_{base_name}_{year}.pdf"
        
        return filename
    
    def _try_direct_report_urls(self) -> List[Dict]:
        """Try common direct URL patterns for UMG reports"""
        reports = []
        current_year = datetime.now().year
        
        # Common patterns for annual reports
        for year in range(current_year, current_year - config.IR_YEARS_TO_DOWNLOAD, -1):
            # Try various URL patterns
            patterns = [
                f"https://www.universalmusic.com/wp-content/uploads/{year}/**/annual-report-{year}.pdf",
                f"https://www.universalmusic.com/investors/annual-report-{year}.pdf",
                f"https://www.universalmusic.com/investor-relations/annual-report-{year}.pdf",
            ]
            
            for pattern in patterns:
                # Note: This is a simplified approach - in practice, you'd need to
                # actually check if these URLs exist
                pass
        
        return reports
    
    def find_annual_reports(self, years: Optional[List[int]] = None) -> List[Dict]:
        """
        Find annual reports for specified years
        
        Args:
            years: List of years to find reports for (defaults to last 5 years)
        
        Returns:
            List of annual report dictionaries
        """
        if not self.reports_found:
            self.scrape_ir_website()
        
        if years is None:
            current_year = datetime.now().year
            years = list(range(current_year, current_year - config.IR_YEARS_TO_DOWNLOAD, -1))
        
        annual_reports = [
            r for r in self.reports_found 
            if r['type'] == 'annual' and r['year'] in years
        ]
        
        return annual_reports
    
    def find_quarterly_reports(self, year: Optional[int] = None) -> List[Dict]:
        """
        Find quarterly reports
        
        Args:
            year: Specific year to find reports for (defaults to current year)
        
        Returns:
            List of quarterly report dictionaries
        """
        if not self.reports_found:
            self.scrape_ir_website()
        
        quarterly_reports = [
            r for r in self.reports_found 
            if r['type'] == 'quarterly'
        ]
        
        if year:
            quarterly_reports = [r for r in quarterly_reports if r['year'] == year]
        
        return quarterly_reports
    
    def download_report(self, report_info: Dict, retry: int = 0) -> Optional[str]:
        """
        Download a report PDF
        
        Args:
            report_info: Dictionary with report information (url, filename, etc.)
            retry: Current retry attempt number
        
        Returns:
            Path to downloaded file, or None if download failed
        """
        url = report_info['url']
        filename = report_info['filename']
        report_type = report_info['type']
        
        # Determine download directory
        if report_type == 'annual':
            download_dir = config.IR_ANNUAL_DIR
        else:
            download_dir = config.IR_QUARTERLY_DIR
        
        os.makedirs(download_dir, exist_ok=True)
        
        filepath = os.path.join(download_dir, filename)
        
        # Skip if already downloaded
        if os.path.exists(filepath):
            print(f"    Report already exists: {filename}")
            return filepath
        
        try:
            print(f"    Downloading: {filename} from {url}")
            response = self.session.get(url, timeout=config.IR_SCRAPING_TIMEOUT, stream=True)
            response.raise_for_status()
            
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '')
            if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
                print(f"      Warning: URL does not appear to be a PDF")
                return None
            
            # Download file
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"      Downloaded: {filepath}")
            return filepath
        
        except requests.RequestException as e:
            if retry < config.IR_RETRY_ATTEMPTS:
                print(f"      Retry {retry + 1}/{config.IR_RETRY_ATTEMPTS}...")
                time.sleep(2)
                return self.download_report(report_info, retry + 1)
            else:
                print(f"      Error downloading {url}: {e}")
                return None
    
    def download_all_reports(self, report_type: str = 'annual', 
                            years: Optional[List[int]] = None) -> List[str]:
        """
        Download all reports of a specific type
        
        Args:
            report_type: 'annual' or 'quarterly'
            years: List of years to download (for annual reports)
        
        Returns:
            List of downloaded file paths
        """
        if report_type == 'annual':
            reports = self.find_annual_reports(years)
        else:
            reports = self.find_quarterly_reports()
        
        downloaded_files = []
        
        for report in reports:
            filepath = self.download_report(report)
            if filepath:
                downloaded_files.append(filepath)
        
        return downloaded_files
    
    def get_report_links(self) -> Dict[str, List[Dict]]:
        """
        Get all available report links organized by type
        
        Returns:
            Dictionary with 'annual' and 'quarterly' keys containing lists of reports
        """
        if not self.reports_found:
            self.scrape_ir_website()
        
        return {
            'annual': [r for r in self.reports_found if r['type'] == 'annual'],
            'quarterly': [r for r in self.reports_found if r['type'] == 'quarterly']
        }


if __name__ == "__main__":
    scraper = IRScraper()
    reports = scraper.scrape_ir_website()
    print(f"\nFound {len(reports)} reports")
    for report in reports[:5]:
        print(f"  - {report['type'].capitalize()} {report['year']}: {report['title']}")

