import os
import asyncio
import requests
import re
from functools import wraps
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from services.account_manager import AccountManager

def get_token_from_cookie(cookie):
    try:
        headers = {
            "cookie": cookie,
            "user-agent": "Mozilla/5.0"
        }

        res = requests.get(
            "https://business.facebook.com/business_locations",
            headers=headers,
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
        if user_id != self.admin_chat_id:
            await message.reply_text("⛔ Cảnh báo: Bạn không có quyền sử dụng công cụ nội bộ này!")
            return
        return await func(self, update, context, *args, **kwargs)
    return wrapper

class TelegramBotHandler:
    def __init__(self, manager: AccountManager, token: str, admin_chat_id: int):
        self.manager = manager
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.application = None
        self.waiting_avatar = {}

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
            BotCommand("avatar", "Đổi avatar (nhập lệnh trước, gửi ảnh sau)")
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
            [InlineKeyboardButton("🔑 Lấy Token", callback_data="get_token_btn")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 *Facebook Account Manager PRO*\n\n"
            f"📊 Đang quản lý: `{len(self.manager.accounts)}` tài khoản\n\n"
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
        )
        await update.effective_message.reply_text(help_text, parse_mode='Markdown')
    
    @admin_only
    async def check_all(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        msg = await update.effective_message.reply_text("🔄 Đang kiểm tra... (có thể mất vài phút)")
        stats = await asyncio.to_thread(self.manager.check_all_accounts)
        await msg.edit_text(
            f"✅ *KẾT QUẢ KIỂM TRA*\n\n"
            f"📌 Tổng: `{stats['total']}`\n"
            f"✅ LIVE: `{stats['live']}`\n"
            f"❌ DIE: `{stats['die']}`",
            parse_mode='Markdown'
        )
    
    @admin_only
    async def list_accounts(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not self.manager.accounts:
            await update.effective_message.reply_text("📭 Chưa có tài khoản nào.")
            return
        
        text = "📋 *DANH SÁCH TÀI KHOẢN*\n\n"
        for i, acc in enumerate(self.manager.accounts[:15], 1):
            text += f"{i}. `{acc.uid}` - {acc.name[:20]}\n"
            text += f"   📊 {acc.status}\n\n"
        
        if len(self.manager.accounts) > 15:
            text += f"... và {len(self.manager.accounts) - 15} tài khoản khác"
        
        await update.effective_message.reply_text(text, parse_mode='Markdown')
    
    @admin_only
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = self.manager.get_statistics()
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
        removed = await asyncio.to_thread(self.manager.remove_dead_accounts)
        await update.effective_message.reply_text(f"🗑 Đã xóa `{removed}` tài khoản DIE", parse_mode='Markdown')
    
    @admin_only
    async def export_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.effective_message.reply_text("📁 Đang export...")
        filename = await asyncio.to_thread(self.manager.export_to_csv)
        with open(filename, 'rb') as f:
            await update.effective_message.reply_document(
                document=f, filename=os.path.basename(filename),
                caption=f"📊 {len(self.manager.accounts)} tài khoản"
            )
        os.remove(filename)

    @admin_only
    async def cookie_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/cookie <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        acc = await asyncio.to_thread(self.manager.get_account_by_uid, uid)
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
        acc = await asyncio.to_thread(self.manager.get_account_by_uid, uid)
        if acc:
            info_text = (
                f"✅ *THÔNG TIN TÀI KHOẢN*\n\n"
                f"📌 *UID:* `{acc.uid}`\n"
                f"👤 *Tên:* `{acc.name}`\n"
                f"📧 *TK:* `{acc.email}`\n"
                f"🔑 *MK:* `{acc.password}`\n"
                f"📝 *Note/2FA:* `{acc.note}`\n\n"
                f"🍪 *Cookie:*\n`{acc.cookie_string}`"
            )
            await update.effective_message.reply_text(info_text, parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')

    @admin_only
    async def add_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/add <cookie>`\nHoặc:\n`/add tk|mk|2fa` (để tự động đăng nhập)", parse_mode='Markdown')
            return
            
        input_str = " ".join(args)
        
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
                acc = await asyncio.to_thread(self.manager.add_account_from_cookie, cookie_str, email, password, note)
                
                success_text = f"✅ Đã thêm tài khoản thành công!\n\n📌 UID: `{acc.uid}`\n👤 Tên: `{acc.name}`"
                if email: success_text += f"\n📧 TK: `{email}`"
                if password: success_text += f"\n🔑 MK: `{password}`"
                if note: success_text += f"\n📝 Note: `{note}`"
                
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
                    cookies_list, uid, name = await asyncio.to_thread(run_auto_login, email, password, secret_2fa)
                    
                    if uid:
                        cookie_dict = {c['name']: c['value'] for c in cookies_list}
                        
                        acc = await asyncio.to_thread(self.manager.get_account_by_uid, uid)
                        if acc:
                            await asyncio.to_thread(self.manager.update_account, acc.id, cookie=cookie_dict, name=name, email=email, password=password, note=note)
                            success_text = f"✅ Đã CẬP NHẬT Cookie thành công!\n\n📌 UID: `{uid}`\n👤 Tên: `{name}`"
                        else:
                            acc = await asyncio.to_thread(self.manager.add_account, uid, cookie_dict, name, email, password, note)
                            success_text = f"✅ Đã THÊM tài khoản mới thành công!\n\n📌 UID: `{acc.uid}`\n👤 Tên: `{acc.name}`"
                            
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
    async def del_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/del <uid>`", parse_mode='Markdown')
            return
            
        uid = args[0]
        success = await asyncio.to_thread(self.manager.delete_account_by_uid, uid)
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
            file = await context.bot.get_file(document.file_id)
            file_content = await file.download_as_bytearray()
            lines = file_content.decode('utf-8', errors='ignore').splitlines()
            
            success_count = 0
            error_count = 0
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
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
                    await asyncio.to_thread(self.manager.add_account_from_cookie, cookie_str, email, password, note)
                    success_count += 1
                except Exception:
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
        acc = await asyncio.to_thread(self.manager.get_account_by_uid, uid)
        if acc:
            msg = await update.effective_message.reply_text(f"🔄 Đang lấy token cho UID `{uid}`...", parse_mode='Markdown')
            token = await asyncio.to_thread(get_token_from_cookie, acc.cookie_string)
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
        acc = await asyncio.to_thread(self.manager.get_account_by_uid, uid)
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
            # Không có caption /avatar và cũng không ở trạng thái chờ ảnh
            return
            
        acc = await asyncio.to_thread(self.manager.get_account_by_uid, uid)
        if not acc:
            await update.effective_message.reply_text(f"❌ Không tìm thấy tài khoản với UID: `{uid}`", parse_mode='Markdown')
            return

            photo = update.effective_message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            avatar_path = f"avatar_{uid}.jpg"
            await file.download_to_drive(avatar_path)

            msg = await update.effective_message.reply_text(f"🔄 Đang tự động cập nhật avatar cho UID `{uid}`...\n_Quá trình này chạy ngầm qua trình duyệt và có thể mất 1-2 phút..._", parse_mode='Markdown')
            
            try:
                from services.avatar_updater import run_update_avatar
                success = await asyncio.to_thread(run_update_avatar, acc.cookie_string, avatar_path, True, 3)
                
                if success:
                    await msg.edit_text(f"✅ Đã CẬP NHẬT AVATAR thành công cho UID: `{uid}`!", parse_mode='Markdown')
                else:
                    await msg.edit_text(f"❌ Cập nhật avatar thất bại cho UID: `{uid}`. Vui lòng thử lại sau.", parse_mode='Markdown')
            except Exception as e:
                await msg.edit_text(f"❌ Lỗi xử lý cập nhật avatar: {str(e)}")
            finally:
                if os.path.exists(avatar_path):
                    os.remove(avatar_path)

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
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.Document.FileExtension("txt"), self.handle_document))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        
        print("🤖 Telegram Bot PRO đang chạy...")
        self.application.run_polling()