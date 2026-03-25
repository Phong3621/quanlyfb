import requests
import re
import csv
import concurrent.futures
from datetime import datetime
from utils.database import db
from models.account import Account
from services.uid_checker import UIDChecker

# ==================== HELPER FUNCTIONS ====================

def get_name_html(uid: str, cookie_string: str = None) -> str:
    """
    Lấy tên từ UID qua HTML scraping
    Hỗ trợ cookie để tăng độ chính xác
    """
    try:
        url = f"https://www.facebook.com/{uid}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        
        if cookie_string:
            headers["Cookie"] = cookie_string
            
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        
        # Cách 1: Lấy từ <title>
        match = re.search(r"<title>(.*?)</title>", response.text, re.IGNORECASE)
        if match:
            name = match.group(1)
            # Xóa số thông báo ở đầu nếu có
            name = re.sub(r'^\([0-9+]+\)\s*', '', name)
            name = name.replace(" | Facebook", "").strip()
            
            # Kiểm tra không phải trang login/error
            if name and not any(x in name for x in ["Log in", "Đăng nhập", "Error", "Lỗi", "Not Found"]):
                return name
        
        # Cách 2: Lấy từ meta og:title
        match = re.search(r'<meta property="og:title" content="(.*?)"', response.text)
        if match:
            return match.group(1)
        
        # Cách 3: Lấy từ profile header
        match = re.search(r'<h1[^>]*class="[^"]*profile[^"]*"[^>]*>(.*?)</h1>', response.text, re.IGNORECASE)
        if match:
            name = re.sub(r'<[^>]+>', '', match.group(1))
            return name.strip()
            
    except requests.exceptions.Timeout:
        print(f"Timeout khi lấy tên UID {uid}")
    except requests.exceptions.ConnectionError:
        print(f"Lỗi kết nối khi lấy tên UID {uid}")
    except Exception as e:
        print(f"Lỗi lấy tên UID {uid}: {e}")
    
    return None

def extract_uid_from_cookie(cookie_string: str) -> str:
    """
    Trích xuất UID từ cookie string
    """
    cookie_dict = {}
    for item in cookie_string.split(';'):
        if '=' in item:
            k, v = item.strip().split('=', 1)
            cookie_dict[k] = v
    
    if 'c_user' in cookie_dict:
        return cookie_dict['c_user']
    
    match = re.search(r'c_user=(\d+)', cookie_string)
    if match:
        return match.group(1)
    
    return None

def get_name_with_cookie(uid: str, cookie_string: str) -> str:
    """
    Lấy tên bằng cookie (qua mbasic.facebook.com)
    Ổn định hơn phương pháp không cookie
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cookie': cookie_string,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }
        
        response = requests.get('https://mbasic.facebook.com/me', headers=headers, timeout=10)
        
        if response.status_code == 200:
            match = re.search(r'<title>(.*?)</title>', response.text, re.IGNORECASE)
            if match:
                title = match.group(1)
                if not any(x in title for x in ["Đăng nhập", "Log in", "Facebook", "Error", "Lỗi", "Not Found"]):
                    return re.sub(r'^\([0-9+]+\)\s*', '', title).replace(" | Facebook", "").strip()
        
        return get_name_html(uid, cookie_string)
        
    except Exception as e:
        print(f"Lỗi lấy tên với cookie: {e}")
        return get_name_html(uid, cookie_string)


# ==================== ACCOUNT MANAGER CLASS ====================

class AccountManager:
    """Quản lý tài khoản Facebook"""
    
    def __init__(self):
        self._accounts_cache = []
        self.refresh_cache()

    def refresh_cache(self):
        """Refresh cache từ database"""
        rows = db.execute_query("SELECT * FROM accounts ORDER BY id DESC")
        self._accounts_cache = [Account.from_row(row) for row in rows]

    @property
    def accounts(self):
        """Lấy danh sách tài khoản"""
        return self._accounts_cache

    def get_account_by_uid(self, uid: str):
        """Lấy account theo UID"""
        for acc in self._accounts_cache:
            if acc.uid == uid:
                return acc
        return None

    def add_account(self, uid: str, cookie: dict, name: str, 
                    email: str = "", password: str = "", note: str = "") -> Account:
        """Thêm tài khoản mới"""
        if self.get_account_by_uid(uid):
            raise ValueError(f"Tài khoản UID {uid} đã tồn tại trong hệ thống!")
        
        acc = Account(
            uid=uid, 
            name=name, 
            cookie=cookie, 
            email=email, 
            password=password, 
            note=note
        )
        acc.save()
        self.refresh_cache()
        return acc

    def add_account_from_cookie(self, cookie_string: str, email: str = "", 
                                 password: str = "", note: str = "") -> Account:
        """
        Thêm tài khoản từ cookie string
        Tự động lấy UID và tên từ cookie
        """
        uid = extract_uid_from_cookie(cookie_string)
        if not uid:
            raise ValueError("Không tìm thấy c_user (UID) trong cookie!")
        
        # Kiểm tra trạng thái LIVE trước khi thêm
        if not UIDChecker.check_live(uid):
            raise ValueError(f"Tài khoản UID {uid} đã DIE, từ chối thêm!")
            
        cookie_dict = {}
        for item in cookie_string.split(';'):
            if '=' in item:
                k, v = item.strip().split('=', 1)
                cookie_dict[k] = v
                
        name = uid  # fallback
        try:
            name_from_cookie = get_name_with_cookie(uid, cookie_string)
            if name_from_cookie:
                name = name_from_cookie
            else:
                fallback_name = get_name_html(uid)
                if fallback_name:
                    name = fallback_name
        except Exception as e:
            fallback_name = get_name_html(uid)
            if fallback_name:
                name = fallback_name
                
        return self.add_account(uid, cookie_dict, name, email, password, note)

    def update_account(self, acc_id: int, **kwargs) -> bool:
        """Cập nhật thông tin tài khoản"""
        acc = None
        for a in self._accounts_cache:
            if a.id == acc_id:
                acc = a
                break
        
        if not acc:
            return False
        
        for key, value in kwargs.items():
            if hasattr(acc, key):
                setattr(acc, key, value)
        
        acc.save()
        self.refresh_cache()
        return True

    def delete_account(self, acc_id: int) -> bool:
        """Xóa tài khoản theo ID"""
        acc = None
        for a in self._accounts_cache:
            if a.id == acc_id:
                acc = a
                break
        
        if acc:
            acc.delete()
            self.refresh_cache()
            return True
        return False

    def delete_account_by_uid(self, uid: str) -> bool:
        """Xóa tài khoản theo UID"""
        acc = self.get_account_by_uid(uid)
        if acc:
            acc.delete()
            self.refresh_cache()
            return True
        return False

    def remove_dead_accounts(self) -> int:
        """Xóa tất cả tài khoản DIE"""
        dead = [acc for acc in self._accounts_cache if not acc.is_live]
        for acc in dead:
            acc.delete()
            
        self.refresh_cache()
        return len(dead)

    def get_statistics(self) -> dict:
        """Lấy thống kê"""
        total = len(self._accounts_cache)
        live = len([acc for acc in self._accounts_cache if acc.is_live])
        die = total - live
        live_percent = (live / total * 100) if total > 0 else 0
        
        return {
            'total': total,
            'live': live,
            'die': die,
            'live_percent': round(live_percent, 2)
        }

    def check_all_accounts(self, use_proxy: bool = False, max_workers: int = 10) -> dict:
        """
        Kiểm tra tất cả tài khoản với multi-thread
        use_proxy: có dùng proxy hay không (cần cài proxy manager)
        """
        def _check_acc(acc):
            proxy = None
            status = UIDChecker.check_live(acc.uid, proxy)
            
            if status is not None and acc.is_live != status:
                acc.is_live = status
                acc.last_checked = datetime.now().isoformat()
                acc.save()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(_check_acc, self._accounts_cache)
            
        self.refresh_cache()
        return self.get_statistics()

    def check_single_account(self, uid: str, use_proxy: bool = False) -> bool:
        """Kiểm tra một tài khoản cụ thể"""
        acc = self.get_account_by_uid(uid)
        if not acc:
            return False
        
        is_live = UIDChecker.check_live(uid, None)
        acc.is_live = is_live
        acc.last_checked = datetime.now().isoformat()
        acc.save()
        self.refresh_cache()
        
        return is_live

    def export_to_csv(self, filename: str = None) -> str:
        """Export danh sách ra file CSV"""
        if filename is None:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerow(['UID', 'Name', 'Status', 'Email', 'Note', 'LastChecked', 'CreatedAt'])
            
            for acc in self._accounts_cache:
                writer.writerow([
                    acc.uid,
                    acc.name,
                    acc.status,
                    acc.email,
                    acc.note,
                    acc.last_checked[:19] if acc.last_checked else '',
                    acc.created_at[:19] if acc.created_at else ''
                ])
                
        return filename

    def import_from_csv(self, filename: str) -> int:
        """Import danh sách từ file CSV"""
        imported = 0
        try:
            with open(filename, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uid = row.get('UID', '').strip()
                    if not uid:
                        continue
                    
                    if self.get_account_by_uid(uid):
                        continue
                    
                    name = row.get('Name', uid)
                    email = row.get('Email', '')
                    note = row.get('Note', '')
                    
                    acc = Account(
                        uid=uid,
                        name=name,
                        cookie={},
                        email=email,
                        note=note
                    )
                    acc.save()
                    imported += 1
            
            self.refresh_cache()
            return imported
        except Exception as e:
            print(f"Lỗi import: {e}")
            return 0
            
    def search_accounts(self, keyword: str) -> list:
        """Tìm kiếm tài khoản theo keyword"""
        keyword_lower = keyword.lower()
        results = []
        
        for acc in self._accounts_cache:
            if (keyword_lower in acc.uid.lower() or
                keyword_lower in acc.name.lower() or
                (acc.email and keyword_lower in acc.email.lower()) or
                (acc.note and keyword_lower in acc.note.lower())):
                results.append(acc)
        
        return results
    
    def get_all_uids(self) -> list:
        """Lấy danh sách tất cả UID"""
        return [acc.uid for acc in self._accounts_cache]
    
    def get_live_accounts(self) -> list:
        """Lấy danh sách tài khoản LIVE"""
        return [acc for acc in self._accounts_cache if acc.is_live]
    
    def get_dead_accounts(self) -> list:
        """Lấy danh sách tài khoản DIE"""
        return [acc for acc in self._accounts_cache if not acc.is_live]