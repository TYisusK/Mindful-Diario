from dataclasses import dataclass
from typing import Optional

@dataclass
class User:
    uid: str
    email: str
    username: Optional[str] = None
    id_token: Optional[str] = None
