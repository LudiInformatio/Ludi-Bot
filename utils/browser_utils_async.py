import asyncio
import random

async def simulate_human_interaction_async(page):
    """
    Asynchronous version: Performs random mouse movements, scrolling, and clicks.
    """
    try:
        # Random mouse movements
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1000)
            y = random.randint(100, 800)
            await page.mouse.move(x, y, steps=5)
            await asyncio.sleep(random.uniform(0.1, 0.3))

        # Random scroll
        await page.mouse.wheel(0, random.randint(300, 700))
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Scroll back up a bit sometimes
        if random.random() > 0.7:
            await page.mouse.wheel(0, -random.randint(100, 300))
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
    except Exception as e:
        print(f"[TAG] Context: {e}")
        pass

async def close_popups_async(page):
    """Asynchronous version: Checks for and closes common popups."""
    try:
        # 1. Cookie Banners
        onetrust_selectors = [
            "#onetrust-accept-btn-handler",
            "#onetrust-reject-all-handler",
            ".onetrust-close-btn-handler"
        ]
        for sel in onetrust_selectors:
            try:
                if await page.is_visible(sel, timeout=1000):
                    await page.click(sel, timeout=2000)
                    await asyncio.sleep(1)
                    break
            except Exception as e:
                print(f"[TAG] Context: {e}")
                continue

        # 2. General Overlays
        close_selectors = [
            ".close-button", "button.close", "div.close-modal",
            "[aria-label='Close']", ".newsletter-modal-close", ".modal-close"
        ]
        for sel in close_selectors:
            try:
                if await page.is_visible(sel, timeout=500):
                    await page.click(sel, timeout=1000)
                    await asyncio.sleep(0.5)
            except Exception as e:
                print(f"[TAG] Context: {e}")
                continue
    except Exception as e:
        print(f"[TAG] Context: {e}")
        pass 
