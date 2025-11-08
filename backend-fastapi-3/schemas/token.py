from pydantic import BaseModel
from uuid import UUID

class Token(BaseModel):
    """
    Model respons yang DIKIRIM KE KLIEN.
    Kita tidak lagi mengirim token, jadi kita bisa ubah ini.
    """
    # Hapus 'access_token' dan 'token_type'
    # Ganti dengan pesan status sederhana:
    status: str = "success"
    message: str = "Logged in successfully"

# ... (TokenData tetap sama) ...
class TokenData(BaseModel):
    email: str | None = None
    farmer_id: UUID | None = None