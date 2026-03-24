import os
import asyncio
from functools import wraps
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from services.account_manager import AccountManager

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
    
    @admin_only
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("✅ Check LIVE", callback_data="check_live")],
            [InlineKeyboardButton("📋 Danh sách", callback_data="list")],
            [InlineKeyboardButton("📊 Thống kê", callback_data="stats")],
            [InlineKeyboardButton("➕ Thêm acc", callback_data="add")],
            [InlineKeyboardButton("🗑 Xóa DIE", callback_data="clean")],
            [InlineKeyboardButton("📁 Export CSV", callback_data="export")],
            [InlineKeyboardButton("🍪 Lấy Cookie", callback_data="get_cookie")]
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
    async def add_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        args = context.args
        if not args:
            await update.effective_message.reply_text("❌ Vui lòng nhập:\n`/add <cookie>`", parse_mode='Markdown')
            return
            
        cookie_str = " ".join(args)
        msg = await update.effective_message.reply_text("🔄 Đang xử lý và lấy thông tin từ Facebook...")
        try:
            acc = await asyncio.to_thread(self.manager.add_account_from_cookie, cookie_str)
            await msg.edit_text(f"✅ Đã thêm tài khoản thành công!\n\n📌 UID: `{acc.uid}`\n👤 Tên: `{acc.name}`", parse_mode='Markdown')
        except Exception as e:
            await msg.edit_text(f"❌ Lỗi: {str(e)}")

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
                "📝 Thêm tài khoản bằng lệnh:\n`/add <cookie>`\n\nHệ thống sẽ tự động lấy UID và Tên.",
                parse_mode='Markdown'
            )
        elif query.data == "get_cookie":
            await update.effective_message.reply_text(
                "📝 Lấy Cookie bằng lệnh:\n`/cookie <uid>`",
                parse_mode='Markdown'
            )
    
    def run(self):
        self.application = Application.builder().token(self.token).build()
        
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("check", self.check_all))
        self.application.add_handler(CommandHandler("list", self.list_accounts))
        self.application.add_handler(CommandHandler("stats", self.stats))
        self.application.add_handler(CommandHandler("clean", self.clean_dead))
        self.application.add_handler(CommandHandler("export", self.export_csv))
        self.application.add_handler(CommandHandler("add", self.add_cmd))
        self.application.add_handler(CommandHandler("cookie", self.cookie_cmd))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        print("🤖 Telegram Bot PRO đang chạy...")
        self.application.run_polling()