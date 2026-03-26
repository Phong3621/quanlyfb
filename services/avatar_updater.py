from playwright.sync_api import sync_playwright
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

# ===== Click avatar =====
def click_avatar(page):
    selectors = [
        '[aria-label*="profile picture" i]',
        '[aria-label*="ảnh đại diện" i]',
        'img[alt*="profile" i]',
        '[data-testid="profile-picture"]'
    ]

    for s in selectors:
        try:
            el = page.locator(s).first
            if el.is_visible(timeout=5000):
                el.click()
                print("✅ Click avatar")
                return True
        except:
            pass

    print("❌ Không thấy avatar")
    return False

# ===== Click Choose =====
def click_choose(page):
    selectors = [
        'text=Choose profile picture',
        'text=Chọn ảnh đại diện',
        'text=Update profile picture',
        'text=Edit profile picture'
    ]

    for s in selectors:
        try:
            btn = page.locator(s).first
            if btn.is_visible(timeout=5000):
                btn.click()
                print(f"✅ Click: {s}")
                return True
        except:
            pass

    print("❌ Không thấy Choose")
    return False

# ===== Click Upload photo =====
def click_upload_photo(page):
    selectors = [
        'text=Upload photo',
        'text=Tải ảnh lên',
        'text=Upload from computer',
        'button:has-text("Upload")'
    ]

    for s in selectors:
        try:
            btn = page.locator(s).first
            if btn.is_visible(timeout=5000):
                btn.click()
                print("✅ Click Upload photo")
                return True
        except:
            pass

    print("❌ Không thấy Upload photo")
    return False

# ===== Upload file (FIXED) =====
def upload_file(page, path):
    try:
        print("🚀 Upload không mở popup...")

        # tìm input file
        inputs = page.locator('input[type="file"]')
        count = inputs.count()

        print(f"📁 Tìm thấy {count} input")

        if count == 0:
            print("❌ Không có input file")
            return False

        # ưu tiên input cuối (avatar)
        try:
            inputs.last.set_input_files(path)
            print("✅ Upload avatar (no popup)")
            return True
        except:
            pass

        # fallback
        for i in range(count):
            try:
                inputs.nth(i).set_input_files(path)
                print(f"✅ Upload fallback #{i}")
                return True
            except:
                continue

        return False

    except Exception as e:
        print("❌ Upload lỗi:", e)
        return False

# ===== Click Save =====
def click_save(page):
    selectors = [
        'text=Save',
        'text=Lưu',
        'text=Done',
        'text=Xong',
        'button:has-text("Save")',
        'button:has-text("Lưu")'
    ]

    for _ in range(10):
        for s in selectors:
            try:
                btn = page.locator(s).first
                if btn.is_visible(timeout=2000):
                    btn.click()
                    print(f"✅ Click: {s}")
                    return True
            except:
                pass
        time.sleep(1)

    print("⚠️ Không thấy nút save")
    return False

# ================== PLAYWRIGHT PROXY PARSER ==================
def parse_playwright_proxy(proxy_str):
    if not proxy_str: return None
    import urllib.parse
    try:
        if not proxy_str.startswith(('http://', 'https://', 'socks5://')):
            proxy_str = 'http://' + proxy_str
        parsed = urllib.parse.urlparse(proxy_str)
        res = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username: res["username"] = parsed.username
        if parsed.password: res["password"] = parsed.password
        return res
    except:
        return {"server": proxy_str}

# ===== MAIN EXPORT FOR BOT =====
def run_update_avatar(cookie_string, avatar_path, headless_mode=True, max_retries=3, proxy=None):
    if not os.path.exists(avatar_path):
        print(f"❌ Không tìm thấy ảnh: {avatar_path}")
        return False
    
    pw_proxy = parse_playwright_proxy(proxy)

    try:
        launch_args = []

        for attempt in range(max_retries):
            print(f"\n🔄 Thử nghiệm lần {attempt + 1}/{max_retries}")
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=headless_mode, slow_mo=100, args=launch_args, proxy=pw_proxy)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
                    )

                    context.add_cookies(convert_cookie(cookie_string))
                    page = context.new_page()

                    print("🌐 Đang vào Facebook...")
                    page.goto("https://www.facebook.com/", timeout=60000)
                    time.sleep(5)

                    # Kiểm tra login
                    if "login" in page.url:
                        print("❌ Cookie DIE!")
                        browser.close()
                        return False

                    print("✅ Cookie LIVE")
                    page.goto("https://www.facebook.com/me", timeout=60000)
                    time.sleep(5)

                    success = False
                    if click_avatar(page):
                        time.sleep(2)
                        if click_choose(page):
                            time.sleep(2)
                            if click_upload_photo(page):
                                time.sleep(2)
                                if upload_file(page, avatar_path):
                                    time.sleep(3)
                                    click_save(page)
                                    time.sleep(3)
                                    print("✅ UP AVATAR DONE")
                                    success = True
                                else:
                                    print("❌ Upload thất bại")
                            else:
                                print("❌ Không click được Upload photo")
                        else:
                            print("❌ Không click được Choose")
                    else:
                        print("❌ Không click được avatar")

                    browser.close()
                    if success:
                        return True
            except Exception as e:
                print(f"❌ Lỗi: {e}")
                
            time.sleep(2)

        return False
    finally:
        if os.path.exists(avatar_path):
            os.remove(avatar_path)
            print(f"🗑️ Đã xóa file ảnh tạm: {avatar_path}")