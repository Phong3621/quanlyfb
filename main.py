#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.account_manager import AccountManager
from services.proxy_manager import proxy_manager
from handlers.telegram_bot import TelegramBotHandler
import asyncio

def show_banner():
    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   ███████╗ █████╗  ██████╗███████╗██████╗  ██████╗  ██████╗ ██╗
║   ██╔════╝██╔══██╗██╔════╝██╔════╝██╔══██╗██╔═══██╗██╔═══██╗██║
║   █████╗  ███████║██║     █████╗  ██████╔╝██║   ██║██║   ██║██║
║   ██╔══╝  ██╔══██║██║     ██╔══╝  ██╔══██╗██║   ██║██║   ██║██║
║   ██║     ██║  ██║╚██████╗███████╗██║  ██║╚██████╔╝╚██████╔╝██║
║   ╚═╝     ╚═╝  ╚═╝ ╚═════╝╚══════╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚═╝
║                                                              ║
║               FACEBOOK ACCOUNT MANAGER PRO V4                ║
║                   Multi-thread + Proxy                       ║
╚══════════════════════════════════════════════════════════════╝
    """)

def main():
    show_banner()
    load_dotenv()
    
    manager = AccountManager()
    
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN', '')
    admin_chat_ids_str = os.getenv('ADMIN_CHAT_ID', '0')
    admin_chat_ids = [int(x.strip()) for x in admin_chat_ids_str.split(',') if x.strip().lstrip('-').isdigit()]
    
    # Kiểm tra chế độ chạy ngầm (Dành cho Docker / VPS Background)
    if os.getenv('HEADLESS_BOT', '').lower() == 'true':
        if bot_token and admin_chat_ids:
            print("🤖 Khởi động Telegram Bot ở chế độ ngầm (Docker mode)...")
            bot = TelegramBotHandler(bot_token, admin_chat_ids)
            bot.run()
        else:
            print("❌ Lỗi: Cần cấu hình TELEGRAM_BOT_TOKEN và ADMIN_CHAT_ID trong .env!")
        return

    print(f"📁 Database: database.db")
    print(f"📊 Số tài khoản: {len(manager.accounts)}")
    print(f"🌐 Số proxy: {len(proxy_manager.proxy_list)}")
    print()
    
    while True:
        print("\n" + "=" * 50)
        print("📌 MENU CHÍNH")
        print("=" * 50)
        print("1. 🚀 Chạy Telegram Bot")
        print("2. 🔍 Kiểm tra tất cả tài khoản (Multi-thread)")
        print("3. ➕ Thêm tài khoản")
        print("4. 📋 Xem danh sách")
        print("5. 🧹 Xóa tài khoản DIE")
        print("6. 🍪 Lấy Cookie theo UID")
        print("7. 📊 Thống kê")
        print("8. 📁 Export CSV")
        print("9. 🗑 Xóa tài khoản theo UID")
        print("10. ℹ️ Xem thông tin tài khoản (UID, Pass, Cookie...)")
        print("11. 🤖 Auto Đăng nhập & Lấy Cookie (UID|PASS|2FA)")
        print("12. 🔧 Gán/Đổi Proxy cho tài khoản")
        print("0. ❌ Thoát")
        print("=" * 50)
        
        choice = input("👉 Chọn: ").strip()
        
        if choice == "1":
            if not bot_token or not admin_chat_ids:
                print("❌ Cần cấu hình TELEGRAM_BOT_TOKEN và ADMIN_CHAT_ID trong .env!")
                input("⏎ Nhấn Enter...")
                continue
            
            bot = TelegramBotHandler(bot_token, admin_chat_ids)
            try:
                bot.run()
            except KeyboardInterrupt:
                print("\n⚠️ Đã dừng bot")
        
        elif choice == "2":
            use_proxy = input("Dùng proxy? (y/n): ").lower() == 'y'
            manager.check_all_accounts(use_proxy)
            input("⏎ Nhấn Enter...")
        
        elif choice == "3":
            print("\n--- ➕ THÊM TÀI KHOẢN TỪ COOKIE ---")
            input_str = input("Nhập Cookie FB (hoặc định dạng TK|MK|Cookie|2FA): ").strip()
            if not input_str:
                print("❌ Dữ liệu không được để trống!")
                input("⏎ Nhấn Enter...")
                continue
                
            email = ""
            password = ""
            note = ""
            cookie_str = input_str
            
            if "|" in input_str:
                parts = [p.strip() for p in input_str.split("|") if p.strip()]
                cookie_idx = -1
                for i, p in enumerate(parts):
                    if "c_user=" in p:
                        cookie_idx = i
                        break
                
                if cookie_idx != -1:
                    cookie_str = parts[cookie_idx]
                    parts.pop(cookie_idx)
                elif parts:
                    cookie_str = max(parts, key=len)
                    parts.remove(cookie_str)
                    
                if len(parts) > 0: email = parts[0]
                if len(parts) > 1: password = parts[1]
                if len(parts) > 2: note = "2FA: " + parts[2] if len(parts) == 3 else " | ".join(parts[2:])
                print(f"👉 Đã nhận diện: TK={email}, MK={password}")
            else:
                email = input("Email (Enter để bỏ qua): ").strip()
                password = input("Password (Enter để bỏ qua): ").strip()
                note = input("Ghi chú (Enter để bỏ qua): ").strip()
            
            proxy_str = ""
            use_proxy = input("\n🌐 Gắn proxy cho tài khoản này? (y/N): ").strip().lower()
            if use_proxy == 'y':
                print("Chọn loại Proxy:")
                print("1. HTTP/HTTPS")
                print("2. SOCKS5")
                p_type = input("👉 Chọn (1/2): ").strip()
                prefix = "socks5://" if p_type == "2" else "http://"
                p_val = input("Nhập proxy (định dạng ip:port hoặc ip:port:user:pass): ").strip()
                if p_val:
                    parts = p_val.split(':')
                    if len(parts) == 4:
                        proxy_str = f"{prefix}{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                    elif len(parts) == 2:
                        proxy_str = f"{prefix}{parts[0]}:{parts[1]}"
                    else:
                        print("⚠️ Định dạng proxy không chuẩn, lưu dạng raw.")
                        proxy_str = f"{prefix}{p_val}"

            print("🔄 Đang xử lý lấy UID & Tên từ Facebook...")
            try:
                acc = manager.add_account_from_cookie(cookie_str, email, password, note, proxy_str)
                print(f"✅ Thêm thành công: {acc.uid} - {acc.name}")
            except Exception as e:
                print(f"❌ Lỗi: {str(e)}")
                
            input("⏎ Nhấn Enter...")
        
        elif choice == "4":
            for i, acc in enumerate(manager.accounts[:20], 1):
                print(f"[{i}] {acc.uid} - {acc.name[:30]} - {acc.status}")
            input("⏎ Nhấn Enter...")
        
        elif choice == "5":
            manager.remove_dead_accounts()
            input("⏎ Nhấn Enter...")
            
        elif choice == "6":
            uid = input("Nhập UID cần lấy Cookie: ").strip()
            acc = manager.get_account_by_uid(uid)
            if acc:
                print(f"\n✅ Cookie của {acc.uid} ({acc.name}):\n{acc.cookie_string}")
            else:
                print(f"\n❌ Không tìm thấy tài khoản với UID: {uid}")
            input("\n⏎ Nhấn Enter...")
            
        elif choice == "7":
            stats = manager.get_statistics()
            print(f"\n📊 THỐNG KÊ\nTổng: {stats['total']}\nLIVE: {stats['live']}\nDIE: {stats['die']}")
            input("⏎ Nhấn Enter...")
            
        elif choice == "8":
            filename = manager.export_to_csv()
            input("⏎ Nhấn Enter...")
            
        elif choice == "9":
            uid_to_del = input("Nhập UID cần xóa: ").strip()
            if uid_to_del:
                success = manager.delete_account_by_uid(uid_to_del)
                if success:
                    print(f"✅ Đã xóa thành công tài khoản có UID: {uid_to_del}")
                else:
                    print(f"❌ Không tìm thấy tài khoản với UID: {uid_to_del}")
            input("⏎ Nhấn Enter...")
            
        elif choice == "10":
            uid = input("Nhập UID cần xem thông tin: ").strip()
            acc = manager.get_account_by_uid(uid)
            if acc:
                print("🔄 Đang lấy thông tin chi tiết và Token...")
                from handlers.telegram_bot import get_token_from_cookie
                token = get_token_from_cookie(acc.cookie_string, acc.proxy)
                token_str = token if token else "Không lấy được"
                print(f"\n✅ THÔNG TIN TÀI KHOẢN:")
                print(f"📌 UID: {acc.uid}")
                print(f"👤 Tên: {acc.name}")
                print(f"📧 TK: {acc.email}")
                print(f"🔑 MK: {acc.password}")
                print(f"📝 Note/2FA: {acc.note}")
                print(f"🔑 Token:\n{token_str}")
                if acc.proxy:
                    print(f"🌐 Proxy: {acc.proxy}")
                print(f"🍪 Cookie:\n{acc.cookie_string}")
            else:
                print(f"\n❌ Không tìm thấy tài khoản với UID: {uid}")
            input("\n⏎ Nhấn Enter...")
            
        elif choice == "11":
            print("\n--- 🤖 AUTO ĐĂNG NHẬP & LẤY COOKIE ---")
            input_data = input("👉 Nhập định dạng (UID|PASS|2FA): ").strip()
            parts = [p.strip() for p in input_data.split("|") if p.strip()]
            
            if len(parts) >= 2:
                email = parts[0]
                password = parts[1]
                secret_2fa = parts[2] if len(parts) >= 3 else ""
                note = f"2FA: {secret_2fa}" if secret_2fa else ""
                
                proxy_str = ""
                use_proxy = input("\n🌐 Gắn proxy cho tài khoản này? (y/N): ").strip().lower()
                if use_proxy == 'y':
                    print("Chọn loại Proxy:")
                    print("1. HTTP/HTTPS")
                    print("2. SOCKS5")
                    p_type = input("👉 Chọn (1/2): ").strip()
                    prefix = "socks5://" if p_type == "2" else "http://"
                    p_val = input("Nhập proxy (định dạng ip:port hoặc ip:port:user:pass): ").strip()
                    if p_val:
                        parts = p_val.split(':')
                        if len(parts) == 4:
                            proxy_str = f"{prefix}{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                        elif len(parts) == 2:
                            proxy_str = f"{prefix}{parts[0]}:{parts[1]}"
                        else:
                            print("⚠️ Định dạng proxy không chuẩn, lưu dạng raw.")
                            proxy_str = f"{prefix}{p_val}"

                try:
                    from services.auto_login import run_auto_login
                    cookies_list, uid, name = run_auto_login(email, password, secret_2fa)
                    if uid:
                        cookie_dict = {c['name']: c['value'] for c in cookies_list}
                        
                        acc = manager.get_account_by_uid(uid)
                        if acc:
                            print(f"\n⚠️ Tài khoản {uid} đã tồn tại trong hệ thống. Đang cập nhật cookie...")
                            update_kwargs = dict(cookie=cookie_dict, name=name, email=email, password=password, note=note)
                            if proxy_str:
                                update_kwargs['proxy'] = proxy_str
                            manager.update_account(acc.id, **update_kwargs)
                            print("✅ Đã cập nhật dữ liệu thành công!")
                        else:
                            acc = manager.add_account(uid, cookie_dict, name, email, password, note, proxy_str)
                            print(f"\n✅ Đã thêm tài khoản mới thành công: {acc.uid} - {acc.name}")
                    else:
                        print("\n❌ Đăng nhập thất bại hoặc tài khoản đã bị checkpoint nặng!")
                except ImportError:
                    print("\n❌ Lỗi: Bạn chưa cài đặt thư viện Selenium/Webdriver.")
                    print("👉 Vui lòng chạy lệnh: pip install selenium webdriver-manager pyotp")
                except Exception as e:
                    print(f"\n❌ Lỗi xử lý: {str(e)}")
            else:
                print("\n❌ Định dạng không hợp lệ! Yêu cầu: UID|PASS hoặc UID|PASS|2FA")
            input("\n⏎ Nhấn Enter...")
            
        elif choice == "12":
            print("\n--- 🔧 GÁN/ĐỔI PROXY CHO TÀI KHOẢN ---")
            uid = input("Nhập UID của tài khoản cần gán proxy: ").strip()
            acc = manager.get_account_by_uid(uid)
            
            if not acc:
                print(f"❌ Không tìm thấy tài khoản với UID: {uid}")
                input("\n⏎ Nhấn Enter...")
                continue

            print(f"✅ Tài khoản: {acc.uid} - {acc.name}")
            print(f"🌐 Proxy hiện tại: {acc.proxy if acc.proxy else 'Không có'}")

            proxy_str = ""
            print("\nChọn loại Proxy mới:")
            print("1. HTTP/HTTPS")
            print("2. SOCKS5")
            print("0. Xóa Proxy")
            p_type = input("👉 Chọn (1/2/0): ").strip()

            if p_type == '0':
                proxy_str = ""
                print("✅ Sẽ xóa proxy khỏi tài khoản.")
            elif p_type in ['1', '2']:
                prefix = "socks5://" if p_type == "2" else "http://"
                p_val = input("Nhập proxy mới (định dạng ip:port hoặc ip:port:user:pass): ").strip()
                if p_val:
                    parts = p_val.split(':')
                    if len(parts) == 4: # ip:port:user:pass
                        proxy_str = f"{prefix}{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
                    elif len(parts) == 2: # ip:port
                        proxy_str = f"{prefix}{parts[0]}:{parts[1]}"
                    else:
                        proxy_str = f"{prefix}{p_val}"
            
            manager.update_account(acc.id, proxy=proxy_str)
            print(f"\n✅ Đã cập nhật proxy thành công cho UID {uid}!")
            print(f"   Proxy mới: {proxy_str if proxy_str else 'Đã xóa'}")
            input("\n⏎ Nhấn Enter...")
            
        elif choice == "0":
            print("👋 Tạm biệt!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Tạm biệt!")
        sys.exit(0)