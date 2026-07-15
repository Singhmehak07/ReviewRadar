import os
import asyncio
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from playwright.async_api import async_playwright

class UnsupportedMarketplace(Exception):
    pass

class BlockedError(Exception):
    pass

# Selector registry for extension to Meesho/Ajio later
SELECTORS = {
    "flipkart": {
        "container": "div.col.EPCmLS, div.RcK1V_, div._2wzgFH",
        "text": "div.ZmyHe8, div.t-ZTKy, div.ZmyHeo",
        "rating": "div.XQDdHH, div._3LWZlK"
    }
}

def detect_marketplace(url: str) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        hostname = hostname.lower()
        if "flipkart.com" in hostname:
            return "flipkart"
        elif "meesho.com" in hostname:
            return "meesho"
        elif "ajio.com" in hostname:
            return "ajio"
    except Exception:
        pass
    return None

def build_reviews_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path
    if "/p/" in path:
        path = path.replace("/p/", "/product-reviews/", 1)
        
    qs = parse_qs(parsed.query)
    pid = qs.get("pid")
    new_qs = {}
    if pid:
        new_qs["pid"] = pid[0]
        
    return urlunparse(parsed._replace(path=path, query=urlencode(new_qs)))

async def fetch_reviews(url: str, max_results: int = 30) -> list[dict]:
    mp = detect_marketplace(url)
    if mp != "flipkart":
        raise UnsupportedMarketplace("Only Flipkart is currently supported.")
        
    base_reviews_url = build_reviews_url(url)
    results = []
    
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent=ua,
            viewport={"width": 1366, "height": 768}
        )
        page = await context.new_page()
        
        # Limit pages to a maximum of 10
        for n in range(1, 11):
            if len(results) >= max_results:
                break
                
            connector = "&" if "?" in base_reviews_url else "?"
            page_url = f"{base_reviews_url}{connector}page={n}"
            
            try:
                await page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                break
                
            # Check for block page
            content = await page.content()
            if "Something went wrong" in content or "E002" in content:
                raise BlockedError("Flipkart blocked the request (E002).")
                
            # Selectors
            sel = SELECTORS["flipkart"]
            
            # Wait briefly for containers or content
            try:
                await page.wait_for_selector(sel["container"], timeout=5000)
            except Exception:
                # If no container renders, assume no more reviews
                break
                
            containers = await page.locator(sel["container"]).all()
            if not containers:
                break
                
            page_added = 0
            for container in containers:
                if len(results) >= max_results:
                    break
                    
                # Extract rating
                rating = None
                rating_el = container.locator(sel["rating"])
                if await rating_el.count() > 0:
                    try:
                        digits = "".join(c for c in await rating_el.first.inner_text() if c.isdigit())
                        if digits:
                            rating = int(digits)
                    except Exception:
                        pass
                        
                # Extract text
                text = ""
                text_el = container.locator(sel["text"])
                if await text_el.count() > 0:
                    text = (await text_el.first.inner_text()).strip()
                    for suffix in ("READ MORE", "Read More"):
                        if text.endswith(suffix):
                            text = text[:-len(suffix)].strip()
                else:
                    # Log outer HTML for debugging if text is 0 matches
                    html = await container.inner_html()
                    print(f"[DEBUG] Text selector returned 0 matches. Container HTML: {html[:1000]}")
                    
                if text:
                    results.append({
                        "text": text,
                        "rating": rating
                    })
                    page_added += 1
                    
            if not page_added:
                break
                
            # Don't paginate local file URLs
            if urlparse(page_url).scheme == "file":
                break
                
            await asyncio.sleep(1.5)
            
        await browser.close()
        
    return results[:max_results]
