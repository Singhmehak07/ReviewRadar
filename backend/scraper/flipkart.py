import re
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode

try:
    from playwright.async_api import async_playwright
    import asyncio
except ImportError:
    async_playwright = None

try:
    from scraper import selectors
except ImportError:
    from backend.scraper import selectors


def _to_reviews_url(url: str, page: int) -> str:
    """Convert a product URL to its reviews page and inject ?page=N."""
    if "/p/" in url:
        url = url.replace("/p/", "/product-reviews/", 1)
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    qs["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))


def _parse_rating(text: str):
    digits = "".join(c for c in text if c.isdigit())
    try:
        return int(digits) if digits else None
    except ValueError:
        return None


async def fetch_reviews(product_url: str, max_reviews: int = 50) -> list[dict]:
    """Scrape up to max_reviews reviews from a Flipkart URL using headless Chromium."""
    reviews = []
    page_num = 1
    ua = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context(user_agent=ua)
        pg = await ctx.new_page()

        while len(reviews) < max_reviews:
            page_url = _to_reviews_url(product_url, page_num)
            try:
                await pg.goto(page_url, timeout=20000, wait_until="domcontentloaded")
            except Exception:
                break

            # Wait for review containers to render
            try:
                await pg.wait_for_selector(selectors.REVIEW_CONTAINER, timeout=8000)
            except Exception:
                break

            containers = await pg.locator(selectors.REVIEW_CONTAINER).all()
            if not containers:
                break

            page_added = 0
            for c in containers:
                if len(reviews) >= max_reviews:
                    break

                # Rating
                rating = None
                rating_el = c.locator(selectors.RATING)
                if await rating_el.count() > 0:
                    rating = _parse_rating(await rating_el.first.inner_text())

                # Title + body
                title = ""
                title_el = c.locator(selectors.TITLE)
                if await title_el.count() > 0:
                    title = (await title_el.first.inner_text()).strip()

                body = ""
                body_el = c.locator(selectors.TEXT)
                if await body_el.count() > 0:
                    body = (await body_el.first.inner_text()).strip()
                    for suffix in ("READ MORE", "Read More"):
                        if body.endswith(suffix):
                            body = body[: -len(suffix)].strip()

                sep = ". " if title and not title[-1] in ".!?" else " "
                text = (f"{title}{sep}{body}" if title and body else title or body).strip()
                if not text:
                    continue

                reviews.append({"text": text, "rating": rating})
                page_added += 1

            if not page_added:
                break

            # Don't paginate local file URLs (used in tests)
            if urlparse(page_url).scheme == "file":
                break

            page_num += 1

        await browser.close()

    return reviews
