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
    admin_chat_id = int(os.getenv('ADMIN_CHAT_ID', '0'))
    
    # Kiểm tra chế độ chạy ngầm (Dành cho Docker / VPS Background)
    if os.getenv('HEADLESS_BOT', '').lower() == 'true':
        if bot_token and admin_chat_id != 0:
            print("🤖 Khởi động Telegram Bot ở chế độ ngầm (Docker mode)...")
            bot = TelegramBotHandler(manager, bot_token, admin_chat_id)
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
        print("0. ❌ Thoát")
        print("=" * 50)
        
        choice = input("👉 Chọn: ").strip()
        
        if choice == "1":
            if not bot_token or admin_chat_id == 0:
                print("❌ Cần cấu hình TELEGRAM_BOT_TOKEN và ADMIN_CHAT_ID trong .env!")
                input("⏎ Nhấn Enter...")
                continue
            
            bot = TelegramBotHandler(manager, bot_token, admin_chat_id)
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
            cookie_str = input("Nhập Cookie FB: ").strip()
            if not cookie_str:
                print("❌ Cookie không được để trống!")
                input("⏎ Nhấn Enter...")
                continue
                
            email = input("Email (Enter để bỏ qua): ").strip()
            password = input("Password (Enter để bỏ qua): ").strip()
            note = input("Ghi chú (Enter để bỏ qua): ").strip()
            
            print("🔄 Đang xử lý lấy UID & Tên từ Facebook...")
            try:
                acc = manager.add_account_from_cookie(cookie_str, email, password, note)
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
            
        elif choice == "0":
            print("👋 Tạm biệt!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Tạm biệt!")
        sys.exit(0)