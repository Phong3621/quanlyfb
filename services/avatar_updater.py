from playwright.sync_api import sync_playwright
import time
import random
import logging
import os
from datetime import datetime
import json

# ====== LOGGING ======
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ====== UTILS ======
def human_delay(a=1, b=3):
    """Human-like random delay"""
    time.sleep(random.uniform(a, b))

def convert_cookie(raw):
    """Convert raw cookie string to Playwright format"""
    cookies = []
    for item in raw.split(";"):
        item = item.strip()
        if "=" in item:
            name, value = item.split("=", 1)
            cookies.append({
                "name": name.strip(),
                "value": value.strip(),
                "domain": ".facebook.com",
                "path": "/"
            })
    return cookies

def validate_cookies(cookies):
    """Check if cookies have required fields"""
    required_fields = ['c_user', 'xs', 'datr']
    cookie_names = [c['name'] for c in cookies]
    
    missing = [field for field in required_fields if field not in cookie_names]
    if missing:
        logger.warning(f"⚠️ Missing cookies: {missing}")
        return False
    
    logger.info("✅ Cookies are valid")
    return True

def check_avatar_file(path):
    """Check if avatar file exists and is valid"""
    if not os.path.exists(path):
        logger.error(f"❌ File not found: {path}")
        return False
    
    if not path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
        logger.error("❌ Invalid image format (must be jpg, jpeg, png, gif, or webp)")
        return False
    
    file_size = os.path.getsize(path) / (1024 * 1024)
    if file_size > 15:
        logger.error(f"❌ File too large: {file_size:.2f}MB (max 15MB)")
        return False
    
    if file_size > 10:
        logger.warning(f"⚠️ File size is {file_size:.2f}MB, Facebook may compress it")
    
    logger.info(f"✅ Avatar file is valid: {path} ({file_size:.2f}MB)")
    return True

def debug_screenshot(page, name):
    """Take screenshot for debugging"""
    try:
        timestamp = int(time.time())
        screenshot_path = f"debug_{name}_{timestamp}.png"
        page.screenshot(path=screenshot_path)
        logger.info(f"📸 Screenshot saved: {screenshot_path}")
    except Exception as e:
        logger.error(f"Failed to take screenshot: {e}")

def retry(func, func_name, tries=3):
    """Auto retry function if fails"""
    for i in range(tries):
        try:
            if func():
                if i > 0:
                    logger.info(f"✅ {func_name} succeeded on retry {i+1}")
                return True
        except Exception as e:
            logger.warning(f"⚠️ {func_name} attempt {i+1}/{tries} failed: {e}")
        
        if i < tries - 1:
            wait_time = random.uniform(3, 6)
            logger.info(f"🔄 Retrying {func_name} in {wait_time:.1f}s...")
            time.sleep(wait_time)
    
    logger.error(f"❌ {func_name} failed after {tries} attempts")
    return False

def simulate_human_behavior(page):
    """Simulate human mouse movements and scrolling"""
    try:
        # Random mouse movements
        for _ in range(random.randint(2, 5)):
            x = random.randint(100, 1100)
            y = random.randint(100, 600)
            page.mouse.move(x, y, steps=random.randint(3, 8))
            human_delay(0.2, 0.5)
        
        # Random scroll
        scroll_amount = random.randint(50, 300)
        page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        human_delay(0.3, 0.8)
        
        # Random scroll back sometimes
        if random.random() > 0.7:
            page.evaluate(f"window.scrollBy(0, -{scroll_amount // 2})")
            human_delay(0.2, 0.4)
            
    except Exception as e:
        logger.debug(f"Human behavior simulation error: {e}")

def wait_for_page_ready(page, url=None, timeout=30000):
    """Wait for page to be ready WITHOUT networkidle"""
    try:
        if url:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
        
        # Wait for body
        page.wait_for_selector("body", state="attached", timeout=10000)
        
        # Wait for any Facebook-specific element
        fb_selectors = [
            '[role="main"]', 
            '[data-pagelet]', 
            '#facebook', 
            'div[data-visualcompletion]',
            'div[class*="fb"]'
        ]
        
        for selector in fb_selectors:
            try:
                page.wait_for_selector(selector, timeout=3000)
                break
            except:
                continue
        
        human_delay(1, 2)
        logger.info(f"✅ Page loaded: {page.url}")
        return True
        
    except Exception as e:
        logger.error(f"Error waiting for page load: {e}")
        return False

def add_anti_detection_scripts(context):
    """Add scripts to avoid bot detection"""
    scripts = [
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
        "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});",
        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});",
        "window.chrome = {runtime: {}};",
        "const originalQuery = window.navigator.permissions.query; window.navigator.permissions.query = (parameters) => (parameters.name === 'notifications' ? Promise.resolve({ state: Notification.permission }) : originalQuery(parameters));",
        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});",
        "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});"
    ]
    
    for script in scripts:
        context.add_init_script(script)
    
    logger.info("🛡️ Anti-detection scripts added")

def click_avatar(page):
    """Click on avatar with multiple fallback methods"""
    logger.info("🖼 Trying to click avatar...")
    
    avatar_selectors = [
        '[aria-label*="profile picture" i]',
        '[aria-label*="ảnh đại diện" i]',
        '[data-testid="profile-picture"]',
        '[data-testid="profile-pic-link"]',
        'img[role="img"][alt*="profile" i]',
        'div[class*="profile_picture"]',
        'div[class*="avatar"]',
        '[data-pagelet="ProfileTabs"] img',
        'div[data-pagelet="ProfileTimeline"] [role="img"]',
        'img[aria-label*="profile" i]',
        '[role="img"][aria-label*="profile" i]'
    ]
    
    for selector in avatar_selectors:
        try:
            element = page.locator(selector).first
            if element.count() > 0 and element.is_visible(timeout=2000):
                element.click()
                logger.info(f"✅ Avatar clicked using: {selector}")
                return True
        except:
            continue
    
    # Try coordinates as last resort
    try:
        profile_header = page.locator('[data-pagelet="ProfileTabs"]')
        if profile_header.count() > 0:
            box = profile_header.first.bounding_box()
            if box:
                page.mouse.click(box['x'] + 50, box['y'] + 50)
                logger.info("✅ Avatar clicked using coordinates")
                return True
    except:
        pass
    
    logger.error("❌ Could not click avatar")
    return False

def click_update_button(page):
    """Click on update profile picture button"""
    logger.info("⚙️ Looking for update button...")
    
    update_selectors = [
        'text="Update profile picture"',
        'text="Cập nhật ảnh đại diện"',
        'text="Edit profile picture"',
        'text="Chỉnh sửa ảnh đại diện"',
        'button:has-text("Update")',
        'button:has-text("Edit")',
        'button:has-text("Chỉnh sửa")',
        '[aria-label*="update profile picture" i]',
        '[aria-label*="cập nhật ảnh đại diện" i]',
        'div[role="menuitem"]:has-text("Update")',
        'span:has-text("Update profile picture")'
    ]
    
    for selector in update_selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=2000):
                element.click()
                logger.info(f"✅ Update button clicked using: {selector}")
                return True
        except:
            continue
    
    logger.error("❌ Could not find update button")
    return False

def upload_by_direct_input(page, avatar_path):
    """Direct file input (fastest)"""
    try:
        file_input = page.locator('input[type="file"]')
        
        if file_input.count() > 0:
            file_input.first.set_input_files(avatar_path)
            human_delay(1, 2)
            return True
    except Exception as e:
        logger.debug(f"Direct input failed: {e}")
    return False

def upload_avatar(page, avatar_path):
    """Upload avatar with maximum coverage - PRO MAX"""
    logger.info("⬆️ Uploading avatar...")
    
    # List of upload methods
    upload_methods = [
        lambda: upload_by_direct_input(page, avatar_path),
    ]
    
    # Try each method
    for i, method in enumerate(upload_methods, 1):
        try:
            logger.info(f"📤 Trying upload method {i}...")
            if method():
                logger.info(f"✅ Upload successful with method {i}")
                return True
        except Exception as e:
            logger.debug(f"Method {i} failed: {e}")
            continue
    
    logger.error("❌ All upload methods failed")
    debug_screenshot(page, "upload_failed")
    return False

def wait_for_upload_complete(page, timeout=30):
    """Wait for upload to complete"""
    logger.info("⏳ Waiting for upload to complete...")
    human_delay(2, 4)
    return True

def save_avatar(page):
    """Click save button after upload"""
    logger.info("💾 Saving avatar...")
    
    save_selectors = [
        'button:has-text("Save")',
        'button:has-text("Lưu")',
        'button:has-text("Save Changes")',
        'button:has-text("Lưu thay đổi")',
        'button:has-text("Done")',
        'button:has-text("Xong")',
        'div[aria-label*="Save" i]',
        '[data-testid="save-button"]',
        'button[type="submit"]:has-text("Save")'
    ]
    
    for selector in save_selectors:
        try:
            btn = page.locator(selector).first
            if btn.is_visible(timeout=2000):
                btn.click()
                logger.info(f"✅ Save button clicked")
                human_delay(1, 2)
                return True
        except:
            continue
    
    # Try keyboard shortcut
    try:
        page.keyboard.press("Enter")
        logger.info("✅ Used Enter key to save")
        return True
    except:
        pass
    
    logger.info("⚠️ No save button found, assuming auto-save")
    return True

def check_login_status(page):
    """Simple login check - most reliable"""
    current_url = page.url.lower()
    
    if "login" in current_url or "checkpoint" in current_url:
        logger.error("❌ Cookie expired or checkpoint detected!")
        debug_screenshot(page, "login_checkpoint")
        return False
    
    try:
        page.wait_for_selector('[role="main"], [data-pagelet]', timeout=5000)
        logger.info("✅ Cookie LIVE")
        return True
    except:
        logger.warning("⚠️ Could not verify login status, but continuing...")
        return True

def run_single_attempt(cookie_string, avatar_path, headless_mode):
    """Single attempt to update avatar"""
    cookies = convert_cookie(cookie_string)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=headless_mode,
            slow_mo=random.randint(80, 120),
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-web-security',
                '--disable-features=IsolateOrigins,site-per-process',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
                '--window-size=1280,720'
            ]
        )
        
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1280, 'height': 720},
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"],
            device_scale_factor=1
        )
        
        add_anti_detection_scripts(context)
        context.add_cookies(cookies)
        page = context.new_page()
        page.set_default_timeout(20000)
        
        try:
            logger.info("🌐 Loading Facebook...")
            if not wait_for_page_ready(page, "https://www.facebook.com/"): return False
            simulate_human_behavior(page)
            if not check_login_status(page): return False
            
            logger.info("👤 Going to profile...")
            if not wait_for_page_ready(page, "https://www.facebook.com/me"): return False
            simulate_human_behavior(page)
            
            if not retry(lambda: click_avatar(page), "click_avatar"): return False
            human_delay(1, 2)
            simulate_human_behavior(page)
            
            if not retry(lambda: click_update_button(page), "click_update_button"): return False
            human_delay(1, 2)
            
            if not retry(lambda: upload_avatar(page, avatar_path), "upload_avatar"): return False
            wait_for_upload_complete(page)
            human_delay(2, 3)
            
            save_avatar(page)
            human_delay(3, 5)
            
            logger.info("✅ Avatar update successful!")
            return True
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return False
        finally:
            human_delay(3, 5)
            browser.close()

def run_update_avatar(cookie_string, avatar_path, headless_mode=True, max_retries=3):
    """Main function to be called from Telegram bot"""
    if not check_avatar_file(avatar_path):
        return False
        
    for attempt in range(max_retries):
        if run_single_attempt(cookie_string, avatar_path, headless_mode):
            return True
        if attempt < max_retries - 1:
            time.sleep(random.uniform(5, 10))
    return False