from utils.database import db
from models.account import Account
from datetime import datetime

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

    def add_account(self, uid, cookie, name, email, password, note):
        acc = Account(uid, name, cookie, email, password, note)
        acc.save()
        self.refresh_cache()
        return acc

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
        return self.get_statistics()

    def export_to_csv(self, filename="export.csv"):
        import csv
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['UID', 'Name', 'Status', 'Email'])
            for acc in self._accounts_cache:
                writer.writerow([acc.uid, acc.name, acc.status, acc.email])
        return filename