import time
import random

def simulate_human_interaction(page):
    """
    Performs random mouse movements, scrolling, and clicks to simulate human behavior.
    Crucial for triggering lazy-loaded elements and bypassing bot detection.
    """
    try:
        # Random mouse movements
        for _ in range(random.randint(2, 4)):
            x = random.randint(100, 1000)
            y = random.randint(100, 800)
            page.mouse.move(x, y, steps=5)
            time.sleep(random.uniform(0.1, 0.3))

        # Random scroll
        page.mouse.wheel(0, random.randint(300, 700))
        time.sleep(random.uniform(0.5, 1.0))
        
        # Scroll back up a bit sometimes
        if random.random() > 0.7:
            page.mouse.wheel(0, -random.randint(100, 300))
            time.sleep(random.uniform(0.2, 0.5))
            
    except Exception as e:
        # Silently fail for interaction errors to prevent workflow breaks
        pass

def close_popups(page):
    """Checks for and closes common NBA.com, Covers, and OddsShark popups."""
    try:
        # 1. OneTrust / Cookie Banners (Common on NBA.com and others)
        onetrust_selectors = [
            "#onetrust-accept-btn-handler",
            "#onetrust-reject-all-handler",
            ".onetrust-close-btn-handler"
        ]
        for sel in onetrust_selectors:
            try:
                if page.is_visible(sel, timeout=1000):
                    page.click(sel, timeout=2000)
                    time.sleep(1)
                    break # Usually only one cookie banner
            except Exception as e:
                print(f"[TAG] Context: {e}")
                continue

        # 2. General Ad Popups / Newsletters / Overlays
        close_selectors = [
            ".close-button",
            "button.close",
            "div.close-modal",
            "[aria-label='Close']",
            ".newsletter-modal-close",
            ".modal-close",
            "button[class*='close']",
            "div[class*='close']",
            ".p-close", # Common in some frameworks
            # OddsShark Specific
            ".os-react-modal-close",
            "div[class*='os-react-modal'] button",
            "[data-testid='close-modal']"
        ]
        for sel in close_selectors:
            try:
                # Use a very short timeout to check for visibility
                if page.is_visible(sel, timeout=500):
                    page.click(sel, timeout=1000)
                    time.sleep(0.5)
            except Exception as e:
                print(f"[TAG] Context: {e}")
                continue
    except Exception as e:
        print(f"[TAG] Context: {e}")
        pass 

def wait_for_selector_safe(page, selector, timeout=30000, message=None):
    """Wait for selector while handling potential popups that might appear."""
    try:
        # Initial wait
        page.wait_for_selector(selector, timeout=timeout)
        return True
    except Exception as e:
        print(f"[TAG] Context: {e}")
        # If timeout, try closing popups and wait again briefly
        if message:
            print(f"      [BROWSER] ⏳ Timeout waiting for {message}, checking for popups...")
        close_popups(page)
        try:
            page.wait_for_selector(selector, timeout=5000)
            return True
        except Exception as e:
            print(f"[TAG] Context: {e}")
            return False
