"""Stealth browser utilities for anti-bot evasion"""
import asyncio
import random
import logging
from playwright.async_api import async_playwright, Browser, Page, BrowserContext

logger = logging.getLogger(__name__)


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
]


async def random_delay(min_ms: int = 500, max_ms: int = 2000):
    """Random human-like delay"""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def human_scroll(page: Page, distance: int = 300):
    """Scroll with human-like behavior"""
    steps = random.randint(3, 7)
    step_size = distance // steps

    for _ in range(steps):
        await page.mouse.wheel(0, step_size)
        await asyncio.sleep(random.uniform(0.05, 0.15))


class StealthBrowser:
    """Playwright browser with stealth configuration"""

    def __init__(self, headless: bool = True, proxy: str | None = None):
        self.headless = headless
        self.proxy = proxy
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()

        launch_options = {
            "headless": self.headless,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-web-security",
                "--disable-features=IsolateOrigins,site-per-process",
            ],
        }

        if self.proxy:
            launch_options["proxy"] = {"server": self.proxy}

        self.browser = await self.playwright.chromium.launch(**launch_options)

        # Random viewport and user agent
        viewport = random.choice(VIEWPORTS)
        user_agent = random.choice(USER_AGENTS)

        self.context = await self.browser.new_context(
            viewport=viewport,
            user_agent=user_agent,
            locale="vi-VN",
            timezone_id="Asia/Ho_Chi_Minh",
            permissions=["geolocation"],
            geolocation={"latitude": 10.7769, "longitude": 106.7009},  # HCM center
        )

        # Inject stealth scripts
        await self.context.add_init_script("""
            // Override navigator.webdriver
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });

            // Override plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });

            // Override languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['vi-VN', 'vi', 'en-US', 'en']
            });

            // Chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    async def new_page(self) -> Page:
        """Create new page with random characteristics"""
        if not self.context:
            raise RuntimeError("Browser context not initialized")

        page = await self.context.new_page()

        # Random mouse movements on page load
        await page.evaluate("""
            () => {
                window.addEventListener('load', () => {
                    const event = new MouseEvent('mousemove', {
                        clientX: Math.random() * window.innerWidth,
                        clientY: Math.random() * window.innerHeight
                    });
                    document.dispatchEvent(event);
                });
            }
        """)

        return page
