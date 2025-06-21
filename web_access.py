import asyncio
import aiohttp
import httpx
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import json
import re
from urllib.parse import urljoin, urlparse
from typing import Dict, List, Optional, Set
import logging
from datetime import datetime
import hashlib
import requests
from readability import Document
import time

logger = logging.getLogger(__name__)

class WebAccessManager:
    """Production-grade web access and content extraction"""

    def __init__(self):
        self.session_cache = {}
        self.visited_urls = set()
        self.rate_limits = {}
        self.blocked_domains = {
            'facebook.com', 'twitter.com', 'instagram.com',  # Social media
            'adult-site.com', 'gambling-site.com'           # Restricted content
        }
        self.allowed_domains = set()  # If set, only these domains allowed
        
    async def get_page_data(self, url: str, use_js: bool = False, extract_links: bool = True) -> Dict:
        """
        Main entry point for fetching web page data
        
        Args:
            url: Target URL
            use_js: Whether to use JavaScript rendering
            extract_links: Whether to extract links from the page
            
        Returns:
            Dict containing page data
        """
        if not self._is_url_allowed(url):
            logger.warning(f"URL blocked by policy: {url}")
            return {'error': 'URL blocked by access policy'}
        
        try:
            if use_js:
                return await self._get_dynamic_content(url, extract_links)
            else:
                return await self._get_static_content(url, extract_links)
                
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e ")
            return {'error': str(e), 'url': url}

    async def _get_static_content(self, url: str, extract_links: bool = True) -> Dict:
        """Fetch static HTML content using httpx"""
        
        # Check rate limiting
        if not self._check_rate_limit(url):
            await asyncio.sleep(1)  # Simple backoff
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        }
        
        try:
            async with httpx.AsyncClient(timeout=30, headers=headers) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # Parse content
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract main content using readability
                doc = Document(response.text)
                main_content = doc.summary()
                main_text = BeautifulSoup(main_content, 'html.parser').get_text()
                
                result = {
                    'url': str(response.url),
                    'title': self._extract_title(soup),
                    'content': main_text[:5000],  # Limit content length
                    'meta': self._extract_meta_data(soup),
                    'timestamp': datetime.now().isoformat(),
                    'content_type': response.headers.get('content-type', ''),
                    'status_code': response.status_code,
                    'word_count': len(main_text.split()),
                    'language': self._detect_language(soup)
                }
                
                if extract_links:
                    result['links'] = self._extract_links(soup, url)
                
                # Cache successful result
                self._cache_result(url, result)
                
                return result
                
        except httpx.HTTPStatusError as e:
            return {'error': f'HTTP {e.response.status_code}', 'url': url}
        except httpx.TimeoutException:
            return {'error': 'Request timeout', 'url': url}
        except Exception as e:
            return {'error': str(e), 'url': url}

    async def _get_dynamic_content(self, url: str, extract_links: bool = True) -> Dict:
        """Fetch content requiring JavaScript execution"""
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = None
        try:
            driver = webdriver.Chrome(options=options)
            driver.set_page_load_timeout(30)
            
            # Navigate to page
            driver.get(url)
            
            # Wait for content to load
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "body"))
                )
            except TimeoutException:
                logger.warning(f"Timeout waiting for page to load: {url}")
            
            # Additional wait for dynamic content
            await asyncio.sleep(3)
            
            # Get page source and parse
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Extract main content
            doc = Document(page_source)
            main_content = doc.summary()
            main_text = BeautifulSoup(main_content, 'html.parser').get_text()
            
            result = {
                'url': driver.current_url,
                'title': driver.title,
                'content': main_text[:5000],
                'meta': self._extract_meta_data(soup),
                'timestamp': datetime.now().isoformat(),
                'rendered_with_js': True,
                'word_count': len(main_text.split()),
                'language': self._detect_language(soup)
            }
            
            if extract_links:
                result['links'] = self._extract_links(soup, driver.current_url)
            
            return result
            
        except WebDriverException as e:
            return {'error': f'WebDriver error: {str(e)}', 'url': url}
        except Exception as e:
            return {'error': str(e), 'url': url}
        finally:
            if driver:
                driver.quit()

    async def search_web(self, query: str, num_results: int = 10) -> List[Dict]:
        """
        Perform web search using multiple search engines
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results
        """
        results = []
        
        # Use DuckDuckGo for privacy-friendly search
        try:
            search_url = f"https://duckduckgo.com/html/"
            params = {'q': query}
            
            async with httpx.AsyncClient(timeout=15) as client:
                response = await client.get(search_url, params=params)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract search results
                for result in soup.find_all('div', class_='result'):
                    title_elem = result.find('a', class_='result__a')
                    snippet_elem = result.find('div', class_='result__snippet')
                    
                    if title_elem and snippet_elem:
                        results.append({
                            'title': title_elem.get_text().strip(),
                            'url': title_elem.get('href'),
                            'snippet': snippet_elem.get_text().strip(),
                            'search_query': query
                        })
                    
                    if len(results) >= num_results:
                        break
                        
        except Exception as e:
            logger.error(f"Web search failed: {e}")
        
        return results

    async def monitor_webpage(self, url: str, check_interval: int = 300) -> Dict:
        """
        Monitor a webpage for changes
        
        Args:
            url: URL to monitor
            check_interval: Check interval in seconds
            
        Returns:
            Dict with change information
        """
        try:
            # Get current content
            current_data = await self.get_page_data(url)
            
            if 'error' in current_data:
                return current_data
            
            # Generate content hash
            content_hash = hashlib.md5(current_data['content'].encode()).hexdigest()
            
            # Check if we have previous hash
            cache_key = f"monitor_{url}"
            previous_hash = self.session_cache.get(cache_key)
            
            result = {
                'url': url,
                'current_hash': content_hash,
                'changed': previous_hash is not None and previous_hash != content_hash,
                'first_check': previous_hash is None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Store current hash
            self.session_cache[cache_key] = content_hash
            
            if result['changed']:
                result['current_content'] = current_data['content'][:1000]  # First 1000 chars
            
            return result
            
        except Exception as e:
            return {'error': str(e), 'url': url}

    async def extract_structured_data(self, url: str) -> Dict:
        """Extract structured data (JSON-LD, microdata, etc.) from webpage"""
        try:
            page_data = await self.get_page_data(url, extract_links=False)
            
            if 'error' in page_data:
                return page_data
            
            # Re-fetch to get full HTML for structured data
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(url)
                soup = BeautifulSoup(response.text, 'html.parser')
            
            structured_data = {}
            
            # Extract JSON-LD
            json_scripts = soup.find_all('script', type='application/ld+json')
            for script in json_scripts:
                try:
                    json_data = json.loads(script.string)
                    structured_data['json_ld'] = json_data
                except json.JSONDecodeError:
                    continue
            
            # Extract Open Graph data
            og_data = {}
            for tag in soup.find_all('meta', property=re.compile(r'^og:')):
                property_name = tag.get('property')
                content = tag.get('content')
                if property_name and content:
                    og_data[property_name] = content
            
            if og_data:
                structured_data['open_graph'] = og_data
            
            # Extract Twitter Card data
            twitter_data = {}
            for tag in soup.find_all('meta', attrs={'name': re.compile(r'^twitter:')}):
                name = tag.get('name')
                content = tag.get('content')
                if name and content:
                    twitter_data[name] = content
            
            if twitter_data:
                structured_data['twitter_card'] = twitter_data
            
            return {
                'url': url,
                'structured_data': structured_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {'error': str(e), 'url': url}

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title with fallbacks"""
        # Try title tag first
        if soup.title:
            return soup.title.string.strip()
        
        # Try h1 tag
        h1 = soup.find('h1')
        if h1:
            return h1.get_text().strip()
        
        # Try Open Graph title
        og_title = soup.find('meta', property='og:title')
        if og_title:
            return og_title.get('content', '').strip()
        
        return 'No Title Found'

    def _extract_meta_data(self, soup: BeautifulSoup) -> Dict:
        """Extract meta information from the page"""
        meta = {}
        
        # Standard meta tags
        for tag in soup.find_all('meta'):
            name = tag.get('name') or tag.get('property') or tag.get('http-equiv')
            content = tag.get('content')
            
            if name and content:
                meta[name] = content
        
        # Extract canonical URL
        canonical = soup.find('link', rel='canonical')
        if canonical:
            meta['canonical_url'] = canonical.get('href')
        
        return meta

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract and normalize links from the page"""
        links = []
        seen_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href'].strip()
            text = link.get_text().strip()
            
            # Skip empty links and anchors
            if not href or href.startswith('#') or not text:
                continue
            
            # Convert relative URLs to absolute
            full_url = urljoin(base_url, href)
            
            # Skip duplicates
            if full_url in seen_urls:
                continue
            
            seen_urls.add(full_url)
            
            # Skip non-HTTP(S) links
            if not full_url.startswith(('http://', 'https://')):
                continue
            
            links.append({
                'url': full_url,
                'text': text[:100],  # Limit text length
                'title': link.get('title', ''),
                'rel': link.get('rel', [])
            })
            
            # Limit number of links
            if len(links) >= 50:
                break
        
        return links

    def _detect_language(self, soup: BeautifulSoup) -> Optional[str]:
        """Detect page language"""
        # Check html lang attribute
        html_tag = soup.find('html')
        if html_tag and html_tag.get('lang'):
            return html_tag['lang']
        
        # Check meta tags
        lang_meta = soup.find('meta', attrs={'http-equiv': 'content-language'})
        if lang_meta:
            return lang_meta.get('content')
        
        return None

    def _is_url_allowed(self, url: str) -> bool:
        """Check if URL is allowed by access policy"""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix for comparison
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check blocked domains
            if any(blocked in domain for blocked in self.blocked_domains):
                return False
            
            # Check allowed domains (if set)
            if self.allowed_domains:
                return any(allowed in domain for allowed in self.allowed_domains)
            
            return True
            
        except Exception:
            return False

    def _check_rate_limit(self, url: str) -> bool:
        """Simple rate limiting check"""
        try:
            domain = urlparse(url).netloc
            now = time.time()
            
            if domain in self.rate_limits:
                last_request = self.rate_limits[domain]
                if now - last_request < 1:  # 1 second between requests
                    return False
            
            self.rate_limits[domain] = now
            return True
            
        except Exception:
            return True

    def _cache_result(self, url: str, result: Dict):
        """Cache successful results"""
        cache_key = f"web_cache_{hashlib.md5(url.encode()).hexdigest()}"
        self.session_cache[cache_key] = {
            'result': result,
            'timestamp': time.time()
        }
        
        # Keep cache size manageable
        if len(self.session_cache) > 1000:
            # Remove oldest entries
            oldest_key = min(self.session_cache.keys(), 
                           key=lambda k: self.session_cache[k].get('timestamp', 0))
            del self.session_cache[oldest_key]

# Global instance
web_manager = WebAccessManager()

async def get_page_data(url: str, use_js: bool = False) -> Dict:
    """Global function for backward compatibility"""
    return await web_manager.get_page_data(url, use_js)