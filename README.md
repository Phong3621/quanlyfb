🌍 Choose Language: [🇻🇳 Tiếng Việt](#-tiếng-việt) | [🇬🇧 English](#-english)

---

# 🇻🇳 Tiếng Việt

# 🚀 Facebook Account Manager Pro V4

Công cụ quản lý tài khoản Facebook chuyên nghiệp với hỗ trợ đa luồng (Multi-thread), Proxy, Telegram Bot và tự động hóa Playwright. Phù hợp cho việc quản lý số lượng lớn tài khoản, tự động đăng nhập, và theo dõi trạng thái sống/chết (Live/Die) qua giao diện Console hoặc Telegram.

---

## 🌟 Tính Năng Nổi Bật

1. **🤖 Tích hợp Telegram Bot**: Nhận thông báo và điều khiển qua Telegram (Hỗ trợ chạy ngầm trên Docker/VPS).
2. **⚡ Kiểm tra tài khoản đa luồng**: Tốc độ check trạng thái Live/Die cực nhanh (có hỗ trợ gắn Proxy).
3. **➕ Thêm tài khoản thông minh**: Hỗ trợ nhập định dạng `TK|MK|Cookie|2FA` hoặc `Cookie` thuần. Tự động nhận diện UID và Tên.
4. **🤖 Tự động Đăng nhập & Lấy Cookie**: Tự động vượt 2FA và lấy Cookie/Token bằng trình duyệt ảo Chromium (Playwright).
5. **🌐 Hỗ trợ Proxy**: Quản lý và gán Proxy (HTTP/HTTPS/SOCKS5) riêng biệt cho từng tài khoản.
6. **📊 Thống kê & Báo cáo**: Theo dõi tỷ lệ sống/chết, xuất dữ liệu ra file `.csv`.
7. **🧹 Dọn dẹp tài khoản**: Xóa các tài khoản trạng thái DIE hoặc xóa linh hoạt theo UID.
8. **🔑 Quản lý thông tin chi tiết**: Trích xuất Token từ Cookie, xem mật khẩu, mã 2FA dễ dàng.

---

## ⚙️ Yêu cầu hệ thống

- Python 3.8 trở lên
- Trình duyệt Chromium (để chạy Playwright)

### Thư viện cần thiết

Bạn cần cài đặt các thư viện Python sau:
```bash
pip install python-dotenv playwright pyotp
```

Sau đó cài đặt trình duyệt cho Playwright (dùng cho chức năng Auto Login):
```bash
playwright install chromium
```

---

## 🛠️ Cấu Hình Cài Đặt

Tạo một file `.env` ở thư mục gốc của dự án và điền các thông tin sau:

```env
# Cấu hình Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_chat_id_here

# Bật chế độ chạy ngầm Bot (Dành cho Docker / VPS Background)
HEADLESS_BOT=false
```

*Lưu ý: Nếu bạn muốn chạy Telegram Bot trực tiếp không cần mở menu Console (ví dụ trên Docker), hãy đổi `HEADLESS_BOT=true`.*

---

## 🚀 Hướng Dẫn Sử Dụng

Mở terminal và chạy file `main.py`:

```bash
python main.py
```

Một Menu chính sẽ hiện ra với các tùy chọn:
- **[1] Chạy Telegram Bot**: Khởi động bot để nhận lệnh từ Telegram.
- **[2] Kiểm tra tất cả tài khoản**: Bắt đầu check Live/Die toàn bộ tài khoản có trong Database (có hỏi dùng proxy hay không).
- **[3] Thêm tài khoản**: Nhập string chứa Cookie hoặc combo `UID|PASS|...`.
- **[11] Auto Đăng nhập & Lấy Cookie**: Nhập `UID|PASS|2FA`, hệ thống sẽ dùng trình duyệt ẩn danh để tự đăng nhập và cập nhật Cookie mới nhất.
- Các chức năng khác vui lòng làm theo hướng dẫn hiển thị trên màn hình.

---

## 📂 Cấu Trúc Cơ Sở Dữ Liệu

Dữ liệu được lưu trữ an toàn trong file `database.db` (SQLite) bao gồm các bảng về Tài khoản (`accounts`) lưu UID, Tên, Cookie, Email, Mật khẩu, Trạng thái, và Proxy kết nối.

---
*Phát triển bởi [Tên/Biệt danh của bạn]*

---

# 🇬🇧 English

## 🚀 Facebook Account Manager Pro V4

Professional Facebook account management tool with Multi-thread, Proxy, Telegram Bot, and Playwright automation support. Suitable for managing a large number of accounts, auto-login, and tracking Live/Die status via Console or Telegram interface.

---

## 🌟 Key Features

1. **🤖 Telegram Bot Integration**: Get notifications and control via Telegram (Supports background running on Docker/VPS).
2. **⚡ Multi-thread Account Checker**: Extremely fast Live/Die status checking (Proxy support).
3. **➕ Smart Account Addition**: Supports importing format `UID|PASS|Cookie|2FA` or raw `Cookie`. Auto-detects UID and Name.
4. **🤖 Auto Login & Get Cookie**: Automatically bypass 2FA and get Cookie/Token using Chromium virtual browser (Playwright).
5. **🌐 Proxy Support**: Manage and assign individual Proxies (HTTP/HTTPS/SOCKS5) for each account.
6. **📊 Statistics & Reporting**: Track Live/Die ratio, export data to `.csv` file.
7. **🧹 Account Cleanup**: Delete DIE accounts or delete flexibly by UID.
8. **🔑 Detail Management**: Extract Token from Cookie, view password, and 2FA codes easily.

---

## ⚙️ System Requirements

- Python 3.8 or higher
- Chromium browser (to run Playwright)

### Required Libraries

You need to install the following Python libraries:
```bash
pip install -r requirements.txt
pip install playwright pyotp
```

Then install the browser for Playwright (used for Auto Login):
```bash
playwright install chromium
```

---

## 🛠️ Configuration

Create a `.env` file in the root directory and fill in the following:

```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=your_bot_token_here
ADMIN_CHAT_ID=your_chat_id_here

# Enable background bot mode (For Docker / VPS Background)
HEADLESS_BOT=false
```

*Note: If you want to run the Telegram Bot directly without opening the Console menu (e.g., on Docker), change `HEADLESS_BOT=true`.*

---

## 🚀 Usage Guide

Open the terminal and run `main.py`:

```bash
python main.py
```

A Main Menu will appear with options:
- **[1] Run Telegram Bot**: Start the bot to receive commands from Telegram.
- **[2] Check all accounts**: Start checking Live/Die for all accounts in the Database (prompts for proxy usage).
- **[3] Add account**: Enter string containing Cookie or combo `UID|PASS|...`.
- **[11] Auto Login & Get Cookie**: Enter `UID|PASS|2FA`, the system will use an incognito browser to auto-login and update the latest Cookie.
- Follow the on-screen instructions for other functions.

---

## 📂 Database Structure

Data is safely stored in `database.db` (SQLite) including tables for Accounts (`accounts`) saving UID, Name, Cookie, Email, Password, Status, and assigned Proxy.

---
*Developed by TANPHONG AND AL*
