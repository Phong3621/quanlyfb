import json
from datetime import datetime
from typing import Optional, Dict
from utils.crypto import crypto
from utils.database import db

class Account:
    """Model tài khoản Facebook"""
    
    def __init__(self, uid: str = "", name: str = "", cookie: dict = None,
                 email: str = "", password: str = "", note: str = "", proxy: str = ""):
        self.id: Optional[int] = None
        self.uid = uid
        self.name = name
        self.cookie = cookie or {}
        self.email = email
        self._password = password
        self.note = note
        self.is_live = True
        self.last_checked = datetime.now().isoformat()
        self.created_at = datetime.now().isoformat()
        self.proxy_id: Optional[int] = None
        self.session_file: Optional[str] = None
        self.proxy = proxy
    
    @property
    def encrypted_password(self) -> str:
        if self._password:
            return crypto.encrypt(self._password)
        return ""
    
    @encrypted_password.setter
    def encrypted_password(self, value: str):
        if value:
            self._password = crypto.decrypt(value)
    
    @property
    def password(self) -> str:
        return self._password
    
    @password.setter
    def password(self, value: str):
        self._password = value
    
    @property
    def cookie_string(self) -> str:
        return '; '.join([f"{k}={v}" for k, v in self.cookie.items()])
    
    @property
    def status(self) -> str:
        return "✅ LIVE" if self.is_live else "❌ DIE"
    
    def to_dict(self) -> Dict:
        return {
            'uid': self.uid,
            'name': self.name,
            'cookie': json.dumps(self.cookie),
            'email': self.email,
            'encrypted_password': self.encrypted_password,
            'note': self.note,
            'is_live': 1 if self.is_live else 0,
            'last_checked': self.last_checked,
            'proxy_id': self.proxy_id,
            'session_file': self.session_file,
            'proxy': self.proxy
        }
    
    @staticmethod
    def from_row(row: Dict) -> 'Account':
        acc = Account(
            uid=row['uid'],
            name=row['name'],
            email=row['email'],
            note=row['note']
        )
        acc.id = row['id']
        acc.cookie = json.loads(row['cookie']) if row['cookie'] else {}
        acc.encrypted_password = row['encrypted_password'] or ""
        acc.is_live = bool(row['is_live'])
        acc.last_checked = row['last_checked']
        acc.created_at = row['created_at']
        acc.proxy_id = row['proxy_id']
        acc.session_file = row['session_file']
        acc.proxy = row['proxy'] if 'proxy' in row.keys() else ""
        return acc
    
    def save(self) -> int:
        data = self.to_dict()
        if self.id:
            query = '''
                UPDATE accounts SET
                    uid = ?, name = ?, cookie = ?, email = ?,
                    encrypted_password = ?, note = ?, is_live = ?,
                    last_checked = ?, proxy_id = ?, session_file = ?, proxy = ?
                WHERE id = ?
            '''
            params = (data['uid'], data['name'], data['cookie'], data['email'], data['encrypted_password'], data['note'], data['is_live'], data['last_checked'], data['proxy_id'], data['session_file'], data['proxy'], self.id)
            db.execute_update(query, params)
            return self.id
        else:
            query = '''
                INSERT INTO accounts 
                (uid, name, cookie, email, encrypted_password, note, 
                 is_live, last_checked, proxy_id, session_file, proxy)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            params = (data['uid'], data['name'], data['cookie'], data['email'], data['encrypted_password'], data['note'], data['is_live'], data['last_checked'], data['proxy_id'], data['session_file'], data['proxy'])
            self.id = db.execute_update(query, params)
            return self.id
    
    def delete(self):
        if self.id:
            db.execute_update("DELETE FROM accounts WHERE id = ?", (self.id,))
    
    def __str__(self) -> str:
        return f"{self.uid} - {self.name} - {self.status}"