import os
import asyncio
import requests
import re
from functools import wraps
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from services.account_manager import AccountManager

def get_token_from_cookie(cookie, proxy=None):
    try:
        headers = {
            "cookie": cookie,
            "user-agent": "Mozilla/5.0"
        }

        proxies = {"http": proxy, "https": proxy} if proxy else None
        res = requests.get(
            "https://business.facebook.com/business_locations",
            headers=headers,
            proxies=proxies,
            timeout=15
        )

        # tìm token dạng EAA...
        token = re.search(r"(EAAG\w+)", res.text)

        if token:
            return token.group(1)
        else:
            return None

    except Exception as e:
        print("Lỗi:", e)
        return None

def admin_only(func):
    """Decorator để bảo mật Bot, chỉ Admin mới dùng được"""
    @wraps(func)
    async def wrapper(self, update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        message = update.effective_message
        if user_id not in self.admin_chat_ids:
            await message.reply_text("⛔ Cảnh báo: Bạn không có quyền sử dụng công cụ nội bộ này!")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

class TelegramBotHandler:
    def __init__(self, token: str, admin_chat_ids: list):
        self.token = token
        self.admin_chat_ids = admin_chat_ids
        self.application = None
        self.waiting_avatar = {}
        self.adding_states = {}
        self.proxy_setting_states = {}
        self.managers = {}

    def get_manager(self, user_id: int) -> AccountManager:
        if user_id not in self.managers:
            self.managers[user_id] = AccountManager(f"database_{user_id}.db")
        return self.managers[user_id]

    async def post_init(self, application: Application):
        from telegram import BotCommand
        commands = [
            BotCommand("start", "Mở Menu chính"),
            BotCommand("help", "Xem danh sách lệnh"),
            BotCommand("add", "Thêm tài khoản mới"),
            BotCommand("check", "Kiểm tra toàn bộ tài khoản"),
            BotCommand("list", "Xem danh sách tài khoản"),
            BotCommand("stats", "Xem thống kê tài khoản"),
            BotCommand("clean", "Xóa toàn bộ tài khoản DIE"),
            BotCommand("del", "Xóa tài khoản theo UID"),
            BotCommand("info", "Xem thông tin chi tiết tài khoản"),
            BotCommand("cookie", "Lấy Cookie theo UID"),
            BotCommand("token", "Lấy Token theo UID"),
            BotCommand("export", "Xuất danh sách ra file CSV"),
            BotCommand("avatar", "Đổi avatar (nhập lệnh trước, gửi ảnh sau)"),
            BotCommand("setproxy", "Gán/Đổi proxy cho tài khoản")
        ]
        await application.bot.set_my_commands(commands)
    
    @admin_only
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("✅ Check LIVE", callback_data="check_live")],
            [InlineKeyboardButton("📋 Danh sách", callback_data="list")],
            [InlineKeyboardButton("📊 Thống kê", callback_data="stats")],
            [InlineKeyboardButton("➕ Thêm acc", callback_data="add")],
            [InlineKeyboardButton("🗑 Xóa DIE", callback_data="clean"), InlineKeyboardButton("🗑 Xóa UID", callback_data="del_uid")],
            [InlineKeyboardButton("📁 Export CSV", callback_data="export")],
            [InlineKeyboardButton("🍪 Lấy Cookie", callback_data="get_cookie"), InlineKeyboardButton("ℹ️ Lấy Info", callback_data="get_info")],
            [InlineKeyboardButton("🔑 Lấy Token", callback_data="get_token_btn"), InlineKeyboardButton("🖼 Đổi Avatar", callback_data="change_avatar")],
            [InlineKeyboardButton("🔧 Cấu hình Proxy", callback_data="set_proxy")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        manager = self.get_manager(update.effective_user.id)
        
        await update.message.reply_text(
            "🤖 *Facebook Account Manager PRO*\n\n"
            f"📊 Đang quản lý: `{len(manager.accounts)}` tài khoản\n\n"
            "📌 Sử dụng menu bên dưới 👇",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    @admin_only
    async def help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = (
            "🤖 *DANH SÁCH LỆNH CỦA BOT*\n\n"
            "🔹 `/start` - Mở Menu tương tác\n"
            "🔹 `/help` - Xem danh sách lệnh\n"
            "🔹 `/add <dữ_liệu>` - Thêm tài khoản mới\n"
            "   _(Hỗ trợ: Cookie hoặc tk|mk|cookie|2fa)_\n"
            "🔹 `Gửi file .txt` - Thêm nhiều tài khoản từ file\n"
            "🔹 `/check` - Kiểm tra LIVE/DIE tất cả\n"
            "🔹 `/list` - Xem danh sách tài khoản\n"
            "🔹 `/stats` - Xem thống kê\n"
            "🔹 `/clean` - Xóa tài khoản DIE\n"
            "🔹 `/del <uid>` - Xóa tài khoản theo UID\n"
            "🔹 `/info <uid>` - Lấy thông tin tài khoản\n"
            "🔹 `/cookie <uid>` - Lấy Cookie theo UID\n"
            "🔹 `/token <uid>` - Lấy Token theo UID\n"
            "🔹 `/export` - Xuất file CSV\n"
            "🔹 `/avatar <uid>` - Đổi Avatar FB (Bot sẽ yêu cầu gửi ảnh)\n"
            "   _(Hoặc: Gửi Ảnh kèm caption `/avatar <uid>`)_\n"
            "🔹 `/setproxy <uid>` - Gán/Đổi proxy cho tài khoản\n"
        )
        await update.effective_message.reply_text(help_text, parse_mode='Markdown')
    
    @admin_only
    async def check_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.effective_message.reply_text("🔄 Đang kiểm tra... (có thể mất vài phút)")
        manager = self.get_manager(update.effective_user.id)
        stats = await asyncio.to_thread(manager.check_all_accounts)
        await msg.edit_text(
            f"✅ *KẾT QUẢ KIỂM TRA*\n\n"
            f"📌 Tổng: `{stats['total']}`\n"
            f"✅ LIVE: `{stats['live']}`\n"
            f"❌ DIE: `{stats['die']}`",
            parse_mode='Markdown'
        )
    
    @admin_only
    async def list_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        manager = self.get_manager(update.effective_user.id)
        if not manager.accounts:
            await update.effective_message.reply_text("📭 Chưa có tài khoản nào.")
            return
        
        text = "📋 *DANH SÁCH TÀI KHOẢN*\n\n"
        for i, acc in enumerate(manager.accounts[:15], 1):
            text += f"{i}. `{acc.uid}` - {acc.name[:20]}\n"
            text += f"   📊 {acc.status}\n\n"
        
        if len(manager.accounts) > 15:
            text += f"... và {len(manager.accounts) - 15} tài khoản khác"
        
        await update.effective_message.reply_text(text, parse_mode='Markdown')
    
    @admin_only
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        manager = self.get_manager(update.effective_user.id)
        stats = manager.get_statistics()
        text = (
            f"📊 *THỐNG KÊ TÀI KHOẢN*\n\n"
            f"📌 Tổng: `{stats['total']}`\n"
            f"✅ LIVE: `{stats['live']}` ({stats['live_percent']:.1f}%)\n"
            f"❌ DIE: `{stats['die']}` ({100 - stats['live_percent']:.1f}%)\n\n"
            f"🕐 Cập nhật: `{datetime.now().strftime('%H:%M:%S %d/%m/%Y')}`"
        )
        await update.effective_message.reply_text(text, parse_mode='Markdown')
    
    @admin_only
    async def clean_dead(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        manager = self.get_manager(update.effective_user.id)
        removed = await asyncio.to_thread(manager.remove_dead_accounts)
        await update.effective_message.reply_text(f"🗑 Đã xóa `{removed}` tài khoản DIE", parse_mode='Markdown')
    
    @admin_only
    async def export_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.effective_message.reply_text("📁 Đang export...")
        manager = self.get_manager(update.effective_user.id)
        filename = await asyncio.to_thread(manager.export_to_csv)
        with open(filename, 'rb') as f:
            await update.effective_message.reply_document(
                document=f, filename=os.path.basename(filename),
                caption=f"📊 {len(manager.accounts)} tài khoản"
            )
        os.remove(filename)

    @admin_only
    async def cookie_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/cookie <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        manager = self.get_manager(update.effective_user.id)
        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
        if acc:
            await update.effective_message.reply_text(f"✅ *Cookie của {uid}*:\n`{acc.cookie_string}`", parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')
    
    @admin_only
    async def info_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/info <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        manager = self.get_manager(update.effective_user.id)
        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
        if acc:
            msg = await update.effective_message.reply_text(f"🔄 Đang lấy thông tin chi tiết và Token cho `{uid}`...", parse_mode='Markdown')
            token = await asyncio.to_thread(get_token_from_cookie, acc.cookie_string, acc.proxy)
            token_str = token if token else "Không lấy được"
            info_text = (
                f"✅ *THÔNG TIN TÀI KHOẢN*\n\n"
                f"📌 *UID:* `{acc.uid}`\n"
                f"👤 *Tên:* `{acc.name}`\n"
                f"📧 *TK:* `{acc.email}`\n"
                f"🔑 *MK:* `{acc.password}`\n"
                f"📝 *Note/2FA:* `{acc.note}`\n"
                f"🔑 *Token:*\n`{token_str}`\n"
            )
            
            if acc.proxy:
                info_text += f"🌐 *Proxy:* `{acc.proxy}`\n"
                
            info_text += f"\n🍪 *Cookie:*\n`{acc.cookie_string}`"
            await msg.edit_text(info_text, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')

    @admin_only
    async def _process_add_account(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, proxy_str: str):
        manager = self.get_manager(user_id)
        input_str = self.adding_states.get(user_id, {}).get('data', '')
        if user_id in self.adding_states:
            del self.adding_states[user_id]
            
        if not input_str:
            await update.effective_message.reply_text("❌ Có lỗi xảy ra, không tìm thấy dữ liệu. Vui lòng thử lại lệnh /add.")
            return

        if "c_user=" in input_str:
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

            msg = await update.effective_message.reply_text("🔄 Đang xử lý và lấy thông tin từ Facebook...")
            try:
                acc = await asyncio.to_thread(manager.add_account_from_cookie, cookie_str, email, password, note, proxy_str)
                
                success_text = f"✅ Đã thêm tài khoản thành công!\n\n📌 UID: `{acc.uid}`\n👤 Tên: `{acc.name}`"
                if email: success_text += f"\n📧 TK: `{email}`"
                if password: success_text += f"\n🔑 MK: `{password}`"
                if note: success_text += f"\n📝 Note: `{note}`"
                if proxy_str: success_text += f"\n🌐 Proxy: `{proxy_str}`"
                
                await msg.edit_text(success_text, parse_mode='Markdown')
            except Exception as e:
                await msg.edit_text(f"❌ Lỗi: {str(e)}")
        else:
            # Chế độ Auto Login (TK|MK|2FA)
            parts = [p.strip() for p in input_str.split("|") if p.strip()]
            if len(parts) >= 2:
                email = parts[0]
                password = parts[1]
                secret_2fa = parts[2] if len(parts) >= 3 else ""
                note = f"2FA: {secret_2fa}" if secret_2fa else ""
                
                msg = await update.effective_message.reply_text(f"🔄 Đang Auto Login qua trình duyệt cho `{email}`...\n_Quá trình này có thể mất vài chục giây..._", parse_mode='Markdown')
                try:
                    from services.auto_login import run_auto_login
                    cookies_list, uid, name = await asyncio.to_thread(run_auto_login, email, password, secret_2fa, proxy_str)
                    
                    if uid:
                        cookie_dict = {c['name']: c['value'] for c in cookies_list}
                        
                        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
                        if acc:
                            update_kwargs = dict(cookie=cookie_dict, name=name, email=email, password=password, note=note)
                            if proxy_str: update_kwargs['proxy'] = proxy_str
                            await asyncio.to_thread(manager.update_account, acc.id, **update_kwargs)
                            success_text = f"✅ Đã CẬP NHẬT Cookie thành công!\n\n📌 UID: `{uid}`\n👤 Tên: `{name}`"
                            if proxy_str: success_text += f"\n🌐 Proxy: `{proxy_str}`"
                        else:
                            acc = await asyncio.to_thread(manager.add_account, uid, cookie_dict, name, email, password, note, proxy_str)
                            success_text = f"✅ Đã THÊM tài khoản mới thành công!\n\n📌 UID: `{acc.uid}`\n👤 Tên: `{acc.name}`"
                            if proxy_str: success_text += f"\n🌐 Proxy: `{proxy_str}`"
                            
                        await msg.edit_text(success_text, parse_mode='Markdown')
                    else:
                        await msg.edit_text("❌ Auto login thất bại hoặc tài khoản đã bị checkpoint nặng!", parse_mode='Markdown')
                except ImportError:
                    await msg.edit_text("❌ Lỗi: Chưa cài đặt thư viện Playwright.\n👉 `pip install playwright pyotp && playwright install chromium`", parse_mode='Markdown')
                except Exception as e:
                    await msg.edit_text(f"❌ Lỗi xử lý Auto Login: {str(e)}")
            else:
                await update.effective_message.reply_text("❌ Định dạng không hợp lệ!\nVui lòng nhập:\n`/add <cookie>` hoặc `/add tk|mk|2fa`", parse_mode='Markdown')

    @admin_only
    async def add_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/add <cookie>`\nHoặc:\n`/add tk|mk|2fa` (để tự động đăng nhập)", parse_mode='Markdown')
            return
            
        input_str = " ".join(args)
        user_id = update.effective_user.id
        self.adding_states[user_id] = {'data': input_str, 'step': 'ask_proxy'}
        
        keyboard = [
            [InlineKeyboardButton("🚫 Không dùng Proxy", callback_data="addproxy_none")],
            [InlineKeyboardButton("🌐 HTTP Proxy", callback_data="addproxy_http"), 
             InlineKeyboardButton("🧦 SOCKS5 Proxy", callback_data="addproxy_socks5")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_message.reply_text(
            "🌐 *Bạn có muốn sử dụng proxy cho tài khoản này không?*",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    @admin_only
    async def del_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/del <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        manager = self.get_manager(update.effective_user.id)
        success = await asyncio.to_thread(manager.delete_account_by_uid, uid)
        if success:
            await update.effective_message.reply_text(f"✅ Đã xóa thành công tài khoản có UID: `{uid}`", parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')

    @admin_only
    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        document = update.effective_message.document
        if not document.file_name.endswith('.txt'):
            return
            
        msg = await update.effective_message.reply_text("🔄 Đang tải và xử lý file `.txt`, vui lòng chờ...", parse_mode='Markdown')
        
        try:
            user_id = update.effective_user.id
            manager = self.get_manager(user_id)
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            lines = file_content.decode('utf-8', errors='ignore').splitlines()
            
            success_count = 0
            error_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if "c_user=" in line:
                    email, password, note, cookie_str = "", "", "", line

                    if "|" in line:
                        parts = [p.strip() for p in line.split("|") if p.strip()]
                        cookie_idx = next((i for i, p in enumerate(parts) if "c_user=" in p), -1)
                                
                        if cookie_idx != -1:
                            cookie_str = parts.pop(cookie_idx)
                        elif parts:
                            cookie_str = max(parts, key=len)
                            parts.remove(cookie_str)
                            
                        if len(parts) > 0: email = parts[0]
                        if len(parts) > 1: password = parts[1]
                        if len(parts) > 2: note = "2FA: " + parts[2] if len(parts) == 3 else " | ".join(parts[2:])

                    try:
                        await asyncio.to_thread(manager.add_account_from_cookie, cookie_str, email, password, note)
                        success_count += 1
                    except Exception:
                        error_count += 1
                else:
                    parts = [p.strip() for p in line.split("|") if p.strip()]
                    if len(parts) >= 2:
                        email = parts[0]
                        password = parts[1]
                        secret_2fa = parts[2] if len(parts) >= 3 else ""
                        note = f"2FA: {secret_2fa}" if secret_2fa else ""
                        
                        try:
                            from services.auto_login import run_auto_login
                            cookies_list, uid, name = await asyncio.to_thread(run_auto_login, email, password, secret_2fa, "")
                            
                            if uid:
                                cookie_dict = {c['name']: c['value'] for c in cookies_list}
                                
                                acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
                                if acc:
                                    update_kwargs = dict(cookie=cookie_dict, name=name, email=email, password=password, note=note)
                                    await asyncio.to_thread(manager.update_account, acc.id, **update_kwargs)
                                else:
                                    await asyncio.to_thread(manager.add_account, uid, cookie_dict, name, email, password, note, "")
                                success_count += 1
                            else:
                                error_count += 1
                        except Exception:
                            error_count += 1
                    else:
                        error_count += 1
                    
            await msg.edit_text(f"✅ *Đã xử lý xong file txt!*\n\n✔️ Thành công: `{success_count}`\n❌ Thất bại/Trùng: `{error_count}`", parse_mode='Markdown')
        except Exception as e:
            await msg.edit_text(f"❌ Lỗi xử lý file: {str(e)}")

    @admin_only
    async def token_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/token <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        manager = self.get_manager(update.effective_user.id)
        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
        if acc:
            msg = await update.effective_message.reply_text(f"🔄 Đang lấy token cho UID `{uid}`...", parse_mode='Markdown')
            token = await asyncio.to_thread(get_token_from_cookie, acc.cookie_string, acc.proxy)
            if token:
                await msg.edit_text(f"✅ *Token của {uid}*:\n`{token}`", parse_mode='Markdown')
            else:
                await msg.edit_text(f"❌ Không thể lấy token cho UID: `{uid}` (Cookie có thể bị lỗi hoặc tài khoản không có quyền).", parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')

    @admin_only
    async def avatar_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/avatar <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        manager = self.get_manager(update.effective_user.id)
        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
        if not acc:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')
            return
            
        self.waiting_avatar[update.effective_user.id] = uid
        await update.effective_message.reply_text(f"📸 Vui lòng gửi một bức ảnh để làm avatar cho tài khoản `{uid}`.\n_(Gửi ảnh bình thường, không cần chọn 'gửi dưới dạng file')_", parse_mode='Markdown')

    @admin_only
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        caption = update.effective_message.caption or ""
        uid = None
        
        if caption.startswith("/avatar"):
            parts = caption.split()
            if len(parts) >= 2:
                uid = parts[1]
            else:
                await update.effective_message.reply_text("❌ Vui lòng nhập UID tài khoản trong caption.\n👉 VD: Gửi ảnh kèm caption: `/avatar <uid>`", parse_mode='Markdown')
                return
        elif user_id in self.waiting_avatar:
            uid = self.waiting_avatar[user_id]
            del self.waiting_avatar[user_id]
        else:
            await update.effective_message.reply_text("⚠️ Bot đã nhận được ảnh nhưng không biết bạn muốn đổi avatar cho UID nào.\n👉 Vui lòng dùng lệnh `/avatar <uid>` trước, hoặc gửi ảnh kèm caption `/avatar <uid>`.", parse_mode='Markdown')
            return
            
        manager = self.get_manager(user_id)
        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
        if not acc:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')
            return

        if update.effective_message.photo:
            file_id = update.effective_message.photo[-1].file_id
        elif update.effective_message.document:
            file_id = update.effective_message.document.file_id
        else:
            return
            
        file = await context.bot.get_file(file_id)
        # Tạo đường dẫn tuyệt đối để trình duyệt chắc chắn tìm thấy tệp
        avatar_path = os.path.abspath(f"avatar_{uid}.jpg")
        await file.download_to_drive(avatar_path)

        msg = await update.effective_message.reply_text(f"🔄 Đang tự động cập nhật avatar cho UID `{uid}`...\n_Quá trình này chạy ngầm qua trình duyệt và có thể mất 1-2 phút..._", parse_mode='Markdown')
        
        try:
            from services.avatar_updater import run_update_avatar
            success = await asyncio.to_thread(run_update_avatar, acc.cookie_string, avatar_path, False, 3, proxy=acc.proxy)
            
            if success:
                await msg.edit_text(f"✅ Đã CẬP NHẬT AVATAR thành công cho UID: `{uid}`!", parse_mode='Markdown')
            else:
                await msg.edit_text(f"❌ Cập nhật avatar thất bại cho UID: `{uid}`. Vui lòng thử lại sau.", parse_mode='Markdown')
        except Exception as e:
            await msg.edit_text(f"❌ Lỗi xử lý cập nhật avatar: {str(e)}")

    @admin_only
    async def setproxy_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/setproxy <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        manager = self.get_manager(update.effective_user.id)
        acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
        if not acc:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')
            return
        
        keyboard = [
            [InlineKeyboardButton("🌐 HTTP Proxy", callback_data=f"setproxy_http_{uid}"), 
             InlineKeyboardButton("🧦 SOCKS5 Proxy", callback_data=f"setproxy_socks5_{uid}")],
            [InlineKeyboardButton("🚫 Xóa Proxy", callback_data=f"setproxy_remove_{uid}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.effective_message.reply_text(
            f"🔧 *Cấu hình Proxy cho tài khoản*\n\n"
            f"📌 UID: `{acc.uid}`\n"
            f"👤 Tên: `{acc.name}`\n"
            f"🌐 Proxy hiện tại: `{acc.proxy if acc.proxy else 'Không có'}`\n\n"
            f"👇 Vui lòng chọn hành động:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )

    @admin_only
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        text = update.effective_message.text.strip()
        
        if user_id in self.adding_states and self.adding_states[user_id].get('step') == 'wait_proxy':
            proxy_type = self.adding_states[user_id].get('proxy_type', 'http')
            prefix = "socks5://" if proxy_type == "socks5" else "http://"
            
            parts = text.split(':')
            if len(parts) == 4:
                proxy_str = f"{prefix}{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
            elif len(parts) == 2:
                proxy_str = f"{prefix}{parts[0]}:{parts[1]}"
            else:
                proxy_str = f"{prefix}{text}"
                
            await update.effective_message.reply_text("🔄 Đang xử lý thêm tài khoản...")
            await self._process_add_account(update, context, user_id, proxy_str)
        
        if user_id in self.proxy_setting_states:
            state = self.proxy_setting_states[user_id]
            uid = state['uid']
            proxy_type = state['proxy_type']
            
            del self.proxy_setting_states[user_id]

            manager = self.get_manager(user_id)
            acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
            if not acc:
                await update.effective_message.reply_text(f"❌ Lỗi: Không tìm thấy tài khoản `{uid}` để cập nhật.", parse_mode='Markdown')
                return

            prefix = "socks5://" if proxy_type == "socks5" else "http://"
            
            proxy_parts = text.split(':')
            if len(proxy_parts) == 4:
                proxy_str = f"{prefix}{proxy_parts[2]}:{proxy_parts[3]}@{proxy_parts[0]}:{proxy_parts[1]}"
            elif len(proxy_parts) == 2:
                proxy_str = f"{prefix}{proxy_parts[0]}:{proxy_parts[1]}"
            else:
                proxy_str = f"{prefix}{text}"
            
            await asyncio.to_thread(manager.update_account, acc.id, proxy=proxy_str)
            await update.effective_message.reply_text(
                f"✅ Đã cập nhật proxy thành công cho UID `{uid}`!\n\n"
                f"🌐 Proxy mới: `{proxy_str}`",
                parse_mode='Markdown'
            )
            return



    @admin_only
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "check_live": await self.check_all(update, context)
        elif query.data == "list": await self.list_accounts(update, context)
        elif query.data == "stats": await self.stats(update, context)
        elif query.data == "clean": await self.clean_dead(update, context)
        elif query.data == "export": await self.export_csv(update, context)
        elif query.data == "add":
            await update.effective_message.reply_text(
                "📝 Thêm tài khoản bằng lệnh:\n`/add <cookie>`\nHoặc:\n`/add tk|mk|2fa` (sẽ tự động đăng nhập để lấy cookie)\n\n📁 Hoặc *gửi trực tiếp 1 file .txt* chứa danh sách vào bot.",
                parse_mode='Markdown'
            )
        elif query.data == "del_uid":
            await update.effective_message.reply_text(
                "📝 Xóa tài khoản bằng lệnh:\n`/del <uid>`",
                parse_mode='Markdown'
            )
        elif query.data == "get_cookie":
            await update.effective_message.reply_text(
                "📝 Lấy Cookie bằng lệnh:\n`/cookie <uid>`",
                parse_mode='Markdown'
            )
        elif query.data == "get_info":
            await update.effective_message.reply_text(
                "📝 Xem thông tin chi tiết bằng lệnh:\n`/info <uid>`",
                parse_mode='Markdown'
            )
        elif query.data == "get_token_btn":
            await update.effective_message.reply_text(
                "📝 Lấy Token bằng lệnh:\n`/token <uid>`",
                parse_mode='Markdown'
            )
        elif query.data == "change_avatar":
            await update.effective_message.reply_text(
                "🖼 Đổi Avatar bằng lệnh:\n`/avatar <uid>`\nSau đó bot sẽ yêu cầu bạn gửi ảnh để cập nhật.",
                parse_mode='Markdown'
            )
        elif query.data == "set_proxy":
            await update.effective_message.reply_text(
                "🔧 Cấu hình Proxy bằng lệnh:\n`/setproxy <uid>`",
                parse_mode='Markdown'
            )
        elif query.data.startswith("addproxy_"):
            proxy_choice = query.data.split("_")[1]
            user_id = update.effective_user.id
            
            if user_id not in self.adding_states:
                await update.effective_message.edit_text("❌ Lỗi: Không tìm thấy dữ liệu cấu hình. Vui lòng làm lại bằng lệnh `/add`.")
                return
                
            if proxy_choice == "none":
                await self._process_add_account(update, context, user_id, "")
            else:
                self.adding_states[user_id]['proxy_type'] = proxy_choice
                self.adding_states[user_id]['step'] = 'wait_proxy'
                await update.effective_message.edit_text(
                    f"🌐 Bạn đã chọn `{proxy_choice.upper()}`.\n\n"
                    f"✍️ Vui lòng gửi proxy theo định dạng:\n`ip:port:tk:mk`\nhoặc\n`ip:port`", 
                    parse_mode='Markdown'
                )
        elif query.data.startswith("setproxy_"):
            parts = query.data.split("_")
            action = parts[1]
            uid = parts[2]
            user_id = update.effective_user.id

            manager = self.get_manager(user_id)
            acc = await asyncio.to_thread(manager.get_account_by_uid, uid)
            if not acc:
                await query.edit_message_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')
                return

            if action == "remove":
                await asyncio.to_thread(manager.update_account, acc.id, proxy="")
                await query.edit_message_text(f"✅ Đã xóa proxy thành công cho UID `{uid}`.", parse_mode='Markdown')
            else:
                self.proxy_setting_states[user_id] = {'uid': uid, 'proxy_type': action}
                await query.edit_message_text(
                    f"🌐 Bạn đã chọn `{action.upper()}` cho UID `{uid}`.\n\n"
                    f"✍️ Vui lòng gửi proxy theo định dạng:\n`ip:port:tk:mk`\nhoặc\n`ip:port`", 
                    parse_mode='Markdown'
                )

    
    def run(self):
        self.application = Application.builder().token(self.token).post_init(self.post_init).build()
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help_cmd))
        self.application.add_handler(CommandHandler("check", self.check_all))
        self.application.add_handler(CommandHandler("list", self.list_accounts))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("clean", self.clean_dead))
        self.application.add_handler(CommandHandler("export", self.export_csv))
        self.application.add_handler(CommandHandler("add", self.add_cmd))
        self.application.add_handler(CommandHandler("del", self.del_cmd))
        self.application.add_handler(CommandHandler("info", self.info_cmd))
        self.application.add_handler(CommandHandler("cookie", self.cookie_cmd))
        self.application.add_handler(CommandHandler("token", self.token_cmd))
        self.application.add_handler(CommandHandler("avatar", self.avatar_cmd))
        self.application.add_handler(CommandHandler("setproxy", self.setproxy_cmd))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), self.handle_document))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        self.application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, self.handle_photo))
        
        print("🤖 Telegram Bot PRO đang chạy...")
        self.application.run_polling()