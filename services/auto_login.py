from playwright.sync_api import sync_playwright
import time
import random
import re
import pyotp

# ================== CHECK LOGIN ==================
def has_login_cookie(cookies):
    return any(c['name'] == 'c_user' for c in cookies)

# ================== FORMAT COOKIE ==================
def format_cookie(cookies):
    return "; ".join([f"{c['name']}={c['value']}" for c in cookies])

# ================== HUMAN TYPE ==================
def human_type(page, selector, text):
    page.wait_for_selector(selector, timeout=10000)
    page.click(selector)
    time.sleep(random.uniform(0.5, 1.2))

    for char in text:
        page.keyboard.type(char)
        time.sleep(random.uniform(0.05, 0.15))
        
    time.sleep(random.uniform(1, 2.5))

# ================== CLICK CONTINUE ==================
def click_continue(page):
    selectors = [
        "button:has-text('Continue')",
        "button:has-text('Tiếp')",
        "div[role='button']:has-text('Continue')",
        "div[role='button']:has-text('Tiếp')",
        "button[type='submit']",
        "input[type='submit']"
    ]

    for i in range(3):
        for sel in selectors:
            try:
                btn = page.locator(sel)
                if btn.count():
                    btn.first.scroll_into_view_if_needed()
                    btn.first.click(force=True)
                    return True
            except:
                pass

        try:
            page.evaluate("""
                let btn = [...document.querySelectorAll('button, div[role=button]')]
                .find(e => e.innerText.includes('Continue') || e.innerText.includes('Tiếp'));
                if (btn) btn.click();
            """)
            return True
        except:
            pass

        time.sleep(1)
    return False

# ================== HANDLE 2FA ==================
def handle_2fa(page, secret):
    try:
        print("🔐 Phát hiện 2FA...")
        if page.locator("text=Try another way").count():
            page.click("text=Try another way")
            time.sleep(random.uniform(2, 3))

        if page.locator("text=Authentication app").count():
            page.click("text=Authentication app")
            time.sleep(random.uniform(2, 3))

        if not click_continue(page):
            print("⚠️ Không bấm được Continue (bước chọn phương thức)")

        time.sleep(random.uniform(3, 4))
        secret = secret.replace(" ", "")
        code = pyotp.TOTP(secret).now()
        print(f"🔑 2FA Code: {code}")

        input_box = page.locator("input[type='text']")
        if input_box.count():
            input_box.first.click()
            human_type(page, "input[type='text']", code)
            time.sleep(random.uniform(1.5, 3))
        else:
            print("❌ Không tìm thấy ô nhập code")

        if not click_continue(page):
            print("⚠️ Không bấm được Continue sau khi nhập code")

        print("✅ Đã nhập 2FA")
        time.sleep(random.uniform(4, 6))
    except Exception as e:
        print(f"❌ Lỗi 2FA: {e}")

# ================== WAIT LOGIN ==================
def wait_for_login_or_2fa(page, context, secret_2fa=None, timeout=60):
    start = time.time()
    while time.time() - start < timeout:
        cookies = context.cookies()
        if has_login_cookie(cookies):
            print("✅ Login thành công!")
            return cookies

        url = page.url.lower()
        if "checkpoint" in url or "two_factor" in url:
            print("🔐 Detect checkpoint / 2FA")
            if secret_2fa:
                handle_2fa(page, secret_2fa)
            else:
                print("⚠️ Thiếu secret 2FA")
        time.sleep(2)

    print("❌ Timeout login")
    return context.cookies()

# ================== GET INFO ==================
def get_account_info(page, cookies):
    uid = next((c['value'] for c in cookies if c['name'] == 'c_user'), None)
    name = "Unknown"
    if uid:
        try:
            print("🔄 Đang lấy thông tin tên tài khoản...")
            page.goto("https://mbasic.facebook.com/me", timeout=15000)
            time.sleep(random.uniform(2, 4))
            title = page.title()
            name_match = re.sub(r'^\([0-9+]+\)\s*', '', title).replace(" | Facebook", "").strip()
            if name_match and not any(x in name_match for x in ["Log in", "Đăng nhập", "Facebook", "Error", "Lỗi"]):
                name = name_match
            else:
                h1 = page.locator("h1, strong").first.inner_text()
                if h1: name = h1
        except Exception as e:
            print(f"⚠️ Lỗi lấy tên: {e}")
    return uid, name

# ================== RUN AUTO LOGIN ==================
def run_auto_login(email, password, secret_2fa=None):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context()
        page = context.new_page()
        print("🌐 Đang mở Facebook...")
        page.goto("https://www.facebook.com/login")
        time.sleep(random.uniform(2, 4))
        print("⌨️ Nhập tài khoản, mật khẩu...")
        human_type(page, "input[name='email']", email)
        human_type(page, "input[name='pass']", password)
        print("🚀 Đăng nhập...")
        page.get_by_role("button", name="Log in").click()
        time.sleep(random.uniform(2, 3))
        cookies = wait_for_login_or_2fa(page, context, secret_2fa)
        uid, name = None, None
        if has_login_cookie(cookies):
            uid, name = get_account_info(page, cookies)
            cookies = context.cookies()
        browser.close()
        return cookies, uid, name