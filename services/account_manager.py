from utils.database import db
from models.account import Account
from datetime import datetime
import csv
import requests
import re
import concurrent.futures
from services.uid_checker import UIDChecker

class AccountManager:
    def __init__(self):
        self._accounts_cache = []
        self.refresh_cache()

    def refresh_cache(self):
        rows = db.execute_query("SELECT * FROM accounts ORDER BY id DESC")
        self._accounts_cache = [Account.from_row(row) for row in rows]

    @property
    def accounts(self):
        return self._accounts_cache

    def get_account_by_uid(self, uid):
        for acc in self._accounts_cache:
            if acc.uid == uid:
                return acc
        return None

    def add_account(self, uid, cookie, name, email, password, note):
        acc = Account(uid=uid, name=name, cookie=cookie, email=email, password=password, note=note)
        acc.save()
        self.refresh_cache()
        return acc

    def add_account_from_cookie(self, cookie_string, email="", password="", note=""):
        cookie_dict = {}
        for item in cookie_string.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookie_dict[k] = v
                
        uid = cookie_dict.get('c_user', '')
        if not uid:
            match = re.search(r'c_user=(\d+)', cookie_string)
            if match:
                uid = match.group(1)
                
        if not uid:
            raise ValueError("Không tìm thấy c_user (UID) trong cookie!")
            
        name = uid
        headers = {
            'cookie': cookie_string,
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        }
        
        try:
            resp = requests.get('https://mbasic.facebook.com/me', headers=headers, timeout=10)
            if resp.status_code == 200:
                match = re.search(r'<title>(.*?)</title>', resp.text, re.IGNORECASE)
                if match and "Đăng nhập" not in match.group(1) and "Log in" not in match.group(1) and match.group(1) != "Facebook":
                    name = match.group(1).replace(" | Facebook", "").strip()
        except Exception:
            pass
            
        return self.add_account(uid, cookie_dict, name, email, password, note)

    def remove_dead_accounts(self):
        dead = [acc for acc in self._accounts_cache if not acc.is_live]
        for acc in dead:
            acc.delete()
        self.refresh_cache()
        return len(dead)

    def get_statistics(self):
        total = len(self._accounts_cache)
        live = len([acc for acc in self._accounts_cache if acc.is_live])
        die = total - live
        live_percent = (live / total * 100) if total > 0 else 0
        return {'total': total, 'live': live, 'die': die, 'live_percent': live_percent}

    def check_all_accounts(self, use_proxy=False):
        def _check_acc(acc):
            proxy = None  # Logic thêm Proxy ở đây nếu use_proxy=True
            status = UIDChecker.check_live(acc.uid, proxy)
            if status is not None and acc.is_live != status:
                acc.is_live = status
                acc.last_checked = datetime.now().isoformat()
                acc.save()

        # Sử dụng 10 luồng cùng lúc để check nhanh hơn
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            executor.map(_check_acc, self._accounts_cache)
            
        self.refresh_cache()
        return self.get_statistics()

    def export_to_csv(self, filename=None):
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['UID', 'Name', 'Status', 'Email'])
            for acc in self._accounts_cache:
                writer.writerow([acc.uid, acc.name, acc.status, acc.email])
        return filename