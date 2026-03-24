import base64

class CryptoWrapper:
    def encrypt(self, plain_text: str) -> str:
        if not plain_text:
            return ""
        return base64.b64encode(plain_text.encode('utf-8')).decode('utf-8')
        
    def decrypt(self, encrypted_text: str) -> str:
        if not encrypted_text:
            return ""
        return base64.b64decode(encrypted_text.encode('utf-8')).decode('utf-8')

crypto = CryptoWrapper()