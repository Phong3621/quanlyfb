import requests
from urllib.parse import urlparse

class UIDChecker:
    @staticmethod
    def check_live(uid: str, proxy: str = None) -> bool:
        """
        Kiểm tra trạng thái LIVE/DIE của UID Facebook thông qua Graph API Picture,
        dựa trên logic kiểm tra URL redirect (giống Leaf.xNet).
        """
        if not uid:
            return False
            
        proxies = {"http": proxy, "https": proxy} if proxy else None
        url = f"https://graph.facebook.com/{uid}/picture?type=normal"
        response = None

        # Thử lặp lại tối đa 20 lần nếu có lỗi mạng
        for _ in range(20):
            try:
                # Bật allow_redirects=True để lấy URL cuối cùng sau khi chuyển hướng
                response = requests.get(url, proxies=proxies, allow_redirects=True, timeout=10)
                break
            except Exception:
                pass

        try:
            if response is None:
                return False
                
            parsed_url = urlparse(response.url)
            host = parsed_url.hostname or ""
            
            if "static.xx.fbcdn.net" in host:
                return False
            elif "scontent." in host:
                return True
            else:
                return True
        except Exception:
            return False