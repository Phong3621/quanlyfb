from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import time
import os

# ===== Convert cookie =====
def convert_cookie(raw):
    cookies = []
    for item in raw.split(";"):
        item = item.strip()
        if not item or "=" not in item:
            continue

        name, value = item.split("=", 1)
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": ".facebook.com",
            "path": "/"
        })
    return cookies

# ===== Click avatar (Selenium) =====
def click_avatar(driver):
    selectors = [
        '[aria-label*="profile picture"]',
        '[aria-label*="ảnh đại diện"]',
        'img[alt*="profile"]',
        '[data-testid="profile-picture"]'
    ]

    for s in selectors:
        try:
            el = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, s))
            )
            el.click()
            print("✅ Click avatar")
            return True
        except:
            pass

    print("❌ Không thấy avatar")
    return False

# ===== Click Choose (Selenium) =====
def click_choose(driver):
    xpaths = [
        "//*[text()='Choose profile picture']",
        "//*[text()='Chọn ảnh đại diện']",
        "//*[text()='Update profile picture']",
        "//*[text()='Edit profile picture']"
    ]

    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            btn.click()
            print(f"✅ Click: Choose button")
            return True
        except:
            pass

    print("❌ Không thấy Choose")
    return False

# ===== Click Upload photo (Selenium) =====
def click_upload_photo(driver):
    xpaths = [
        "//*[text()='Upload photo']",
        "//*[text()='Tải ảnh lên']",
        "//*[text()='Upload from computer']",
        "//button[contains(., 'Upload')]"
    ]

    for xp in xpaths:
        try:
            btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            btn.click()
            print("✅ Click Upload photo")
            return True
        except:
            pass

    print("❌ Không thấy Upload photo")
    return False

# ===== Upload file (Selenium) =====
def upload_file(driver, path):
    try:
        print("🚀 Upload không mở popup...")
        abs_path = os.path.abspath(path)

        # tìm input file
        inputs = driver.find_elements(By.CSS_SELECTOR, 'input[type="file"]')
        count = len(inputs)

        print(f"📁 Tìm thấy {count} input")

        if count == 0:
            print("❌ Không có input file")
            return False

        # ưu tiên input cuối (avatar)
        try:
            inputs[-1].send_keys(abs_path)
            print("✅ Upload avatar (no popup)")
            return True
        except Exception as e:
            print(f"⚠️ Lỗi khi upload với input cuối: {e}")

        # fallback
        for i, input_el in enumerate(inputs):
            try:
                input_el.send_keys(abs_path)
                print(f"✅ Upload fallback #{i}")
                return True
            except:
                continue

        return False

    except Exception as e:
        print("❌ Upload lỗi:", e)
        return False

# ===== Click Save (Selenium) =====
def click_save(driver):
    xpaths = [
        "//*[text()='Save']",
        "//*[text()='Lưu']",
        "//*[text()='Done']",
        "//*[text()='Xong']",
        "//button[contains(., 'Save')]",
        "//button[contains(., 'Lưu')]"
    ]

    for _ in range(10):
        for s in xpaths:
            try:
                btn = WebDriverWait(driver, 2).until(
                    EC.element_to_be_clickable((By.XPATH, s))
                )
                btn.click()
                print(f"✅ Click: {s}")
                return True
            except:
                pass
        time.sleep(1)

    print("⚠️ Không thấy nút save")
    return False

# ===== MAIN EXPORT FOR BOT =====
def run_update_avatar(cookie_string, avatar_path, headless_mode=True, max_retries=3, proxy=None):
    if not os.path.exists(avatar_path):
        print(f"❌ Không tìm thấy ảnh: {avatar_path}")
        return False

    # Selenium setup
    from selenium.webdriver.chrome.service import Service as ChromeService
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        use_webdriver_manager = True
    except ImportError:
        use_webdriver_manager = False
        print("⚠️ 'webdriver-manager' not found. Please ensure 'chromedriver' is in your PATH.")
        print("   Suggestion: pip install webdriver-manager")

    options = webdriver.ChromeOptions()
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    if headless_mode:
        options.add_argument("--headless")
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')

    try:
        for attempt in range(max_retries):
            print(f"\n🔄 Thử nghiệm lần {attempt + 1}/{max_retries}")
            driver = None
            try:
                if use_webdriver_manager:
                    service = ChromeService(ChromeDriverManager().install())
                    driver = webdriver.Chrome(service=service, options=options)
                else:
                    driver = webdriver.Chrome(options=options)

                print("🌐 Đang vào Facebook...")
                driver.get("https://www.facebook.com/")

                cookies = convert_cookie(cookie_string)
                for cookie in cookies:
                    driver.add_cookie(cookie)

                driver.get("https://www.facebook.com/")
                time.sleep(5)

                # Kiểm tra login
                if "login" in driver.current_url:
                    print("❌ Cookie DIE!")
                    driver.quit()
                    return False

                print("✅ Cookie LIVE")
                driver.get("https://www.facebook.com/me")
                time.sleep(5)

                success = False
                if click_avatar(driver):
                    time.sleep(2)
                    if click_choose(driver):
                        time.sleep(2)
                        if click_upload_photo(driver):
                            time.sleep(2)
                            if upload_file(driver, avatar_path):
                                time.sleep(3)
                                if click_save(driver):
                                    time.sleep(3)
                                    print("✅ UP AVATAR DONE")
                                    success = True
                                else:
                                    print("❌ Save thất bại")
                            else:
                                print("❌ Upload thất bại")
                        else:
                            print("❌ Không click được Upload photo")
                    else:
                        print("❌ Không click được Choose")
                else:
                    print("❌ Không click được avatar")

                driver.quit()
                if success:
                    return True
            except Exception as e:
                print(f"❌ Lỗi: {e}")
                if driver:
                    driver.quit()
                
            time.sleep(2)

    finally:
        if os.path.exists(avatar_path):
            os.remove(avatar_path)
            print(f"🗑️ Đã xóa file ảnh tạm: {avatar_path}")

    return False