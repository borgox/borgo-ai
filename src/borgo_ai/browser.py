"""
Browser Module - Web search and content extraction for borgo-ai
SECURITY: Only GET requests allowed - no POST/PUT/DELETE
"""
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
from urllib.parse import quote_plus, urlparse
import re
import time
import pickle
from pathlib import Path

from .config import browser_config, DATA_DIR


# Cookies storage path
COOKIES_PATH = DATA_DIR / "browser_cookies.pkl"


@dataclass
class SearchResult:
    """Search result structure"""
    title: str
    url: str
    snippet: str


@dataclass
class PageContent:
    """Extracted page content"""
    url: str
    title: str
    content: str
    success: bool
    error: Optional[str] = None


class SafeSession(requests.Session):
    """
    A requests Session that ONLY allows GET requests.
    POST, PUT, DELETE, PATCH are all blocked for safety.
    """
    
    ALLOWED_METHODS = {'GET', 'HEAD', 'OPTIONS'}
    
    def request(self, method, url, **kwargs):
        """Override request to block non-GET methods"""
        method = method.upper()
        
        if method not in self.ALLOWED_METHODS:
            raise PermissionError(
                f"🚫 {method} requests are blocked for safety. "
                f"Only GET requests are allowed."
            )
        
        return super().request(method, url, **kwargs)
    
    def post(self, *args, **kwargs):
        raise PermissionError("🚫 POST requests are blocked for safety.")
    
    def put(self, *args, **kwargs):
        raise PermissionError("🚫 PUT requests are blocked for safety.")
    
    def delete(self, *args, **kwargs):
        raise PermissionError("🚫 DELETE requests are blocked for safety.")
    
    def patch(self, *args, **kwargs):
        raise PermissionError("🚫 PATCH requests are blocked for safety.")


class PersistentBrowser:
    """
    Persistent browser with cookie storage.
    
    Features:
    - Saves cookies between sessions
    - Only allows GET requests
    - Maintains browsing history
    """
    
    def __init__(self, cookies_path: Path = COOKIES_PATH):
        self.cookies_path = cookies_path
        self.session = SafeSession()  # Only GET allowed!
        self.session.headers.update({
            "User-Agent": browser_config.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self.history: List[str] = []
        self._load_cookies()
    
    def _load_cookies(self):
        """Load cookies from disk"""
        if self.cookies_path.exists():
            try:
                with open(self.cookies_path, 'rb') as f:
                    self.session.cookies.update(pickle.load(f))
            except Exception:
                pass
    
    def _save_cookies(self):
        """Save cookies to disk"""
        try:
            with open(self.cookies_path, 'wb') as f:
                pickle.dump(self.session.cookies, f)
        except Exception:
            pass
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """Make a GET request (the only allowed method)"""
        kwargs.setdefault('timeout', browser_config.request_timeout)
        kwargs.setdefault('allow_redirects', True)
        
        response = self.session.get(url, **kwargs)
        
        # Track history
        self.history.append(url)
        if len(self.history) > 100:
            self.history = self.history[-100:]
        
        # Save cookies after each request
        self._save_cookies()
        
        return response
    
    def clear_cookies(self):
        """Clear all cookies"""
        self.session.cookies.clear()
        if self.cookies_path.exists():
            self.cookies_path.unlink()
    
    def get_cookies_for_domain(self, domain: str) -> Dict:
        """Get cookies for a specific domain"""
        return {
            cookie.name: cookie.value
            for cookie in self.session.cookies
            if domain in cookie.domain
        }


class WebBrowser:
    """Web browser for searching and extracting content"""
    
    def __init__(self, config=None, persistent: bool = True):
        self.config = config or browser_config
        
        if persistent:
            self._browser = PersistentBrowser()
            self.session = self._browser.session
        else:
            self.session = SafeSession()  # Still only GET!
            self.session.headers.update({
                "User-Agent": self.config.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            })
            self._browser = None
    
    def search_google(self, query: str) -> List[SearchResult]:
        """Search Google and return results"""
        results = []
        
        try:
            # Use DuckDuckGo HTML as it's more scraper-friendly
            url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            response = self.session.get(
                url,
                timeout=self.config.request_timeout
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Parse DuckDuckGo results
            for result in soup.select(".result"):
                title_elem = result.select_one(".result__title")
                link_elem = result.select_one(".result__url")
                snippet_elem = result.select_one(".result__snippet")
                
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    
                    # Extract actual URL
                    url_text = link_elem.get_text(strip=True)
                    if not url_text.startswith("http"):
                        url_text = "https://" + url_text
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append(SearchResult(
                        title=title,
                        url=url_text,
                        snippet=snippet
                    ))
                
                if len(results) >= self.config.max_search_results:
                    break
        
        except Exception as e:
            # Fallback: try a simple approach
            pass
        
        return results
    
    def fetch_page(self, url: str) -> PageContent:
        """Fetch and extract content from a webpage"""
        try:
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                allow_redirects=True
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove script and style elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            
            # Get title
            title = soup.title.string if soup.title else urlparse(url).netloc
            
            # Extract main content
            content = self._extract_content(soup)
            
            # Truncate if too long
            if len(content) > self.config.max_page_content_length:
                content = content[:self.config.max_page_content_length] + "..."
            
            return PageContent(
                url=url,
                title=title,
                content=content,
                success=True
            )
        
        except Exception as e:
            return PageContent(
                url=url,
                title="",
                content="",
                success=False,
                error=str(e)
            )
    
    def _extract_content(self, soup: BeautifulSoup) -> str:
        """Extract main content from parsed HTML"""
        # Try to find main content areas
        main_selectors = [
            "main",
            "article",
            '[role="main"]',
            ".content",
            ".post-content",
            ".article-content",
            "#content",
            ".entry-content"
        ]
        
        for selector in main_selectors:
            main = soup.select_one(selector)
            if main:
                text = main.get_text(separator="\n", strip=True)
                if len(text) > 100:  # Meaningful content
                    return self._clean_text(text)
        
        # Fallback: get body text
        body = soup.body
        if body:
            text = body.get_text(separator="\n", strip=True)
            return self._clean_text(text)
        
        return ""
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        
        # Remove common noise
        noise_patterns = [
            r'Cookie.*?(?:accept|policy)',
            r'Subscribe.*?newsletter',
            r'Sign up.*?free',
        ]
        
        for pattern in noise_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def search_and_browse(
        self, 
        query: str, 
        max_pages: int = 3
    ) -> str:
        """Search and browse top results, returning combined content"""
        results = self.search_google(query)
        
        if not results:
            return f"No search results found for: {query}"
        
        combined_content = []
        combined_content.append(f"Search results for: {query}\n")
        combined_content.append("=" * 50 + "\n")
        
        pages_fetched = 0
        for result in results:
            if pages_fetched >= max_pages:
                break
            
            page = self.fetch_page(result.url)
            
            if page.success and page.content:
                combined_content.append(f"\n### Source: {page.title}")
                combined_content.append(f"URL: {page.url}\n")
                combined_content.append(page.content)
                combined_content.append("\n" + "-" * 40)
                pages_fetched += 1
            
            # Small delay to be respectful
            time.sleep(0.5)
        
        return "\n".join(combined_content)
    
    def clear_cookies(self):
        """Clear browser cookies"""
        if self._browser:
            self._browser.clear_cookies()
        else:
            self.session.cookies.clear()
    
    def get_history(self) -> List[str]:
        """Get browsing history"""
        if self._browser:
            return self._browser.history
        return []


# Convenience functions
_browser: Optional[WebBrowser] = None

def get_browser() -> WebBrowser:
    """Get or create browser instance (with persistent cookies)"""
    global _browser
    if _browser is None:
        _browser = WebBrowser(persistent=True)
    return _browser


def search_web(query: str) -> str:
    """Search the web and return combined content (GET only)"""
    browser = get_browser()
    return browser.search_and_browse(query)


def search_google(query: str) -> List[SearchResult]:
    """Just search, don't browse (GET only)"""
    browser = get_browser()
    return browser.search_google(query)


def fetch_url(url: str) -> PageContent:
    """Fetch content from a URL (GET only - safe)"""
    browser = get_browser()
    return browser.fetch_page(url)


def clear_browser_cookies():
    """Clear all stored cookies"""
    get_browser().clear_cookies()


def get_browser_history() -> List[str]:
    """Get browsing history"""
    return get_browser().get_history()
