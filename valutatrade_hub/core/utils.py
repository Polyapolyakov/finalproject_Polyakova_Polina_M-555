
import json
import hashlib
import secrets


from pathlib import Path
from typing import Any, Dict, List, Tuple


def load_json(filepath: str, default: Any = None) -> Any:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else []


def save_json(filepath: str, data: Any) -> bool:
    try:
        Path(filepath).parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(8)
    
    hashed = hashlib.sha256(f"{password}{salt}".encode()).hexdigest()
    return hashed, salt


def get_next_user_id() -> int:
    users = load_json("data/users.json", [])
    if not users:
        return 1
    max_id = max(user.get("user_id", 0) for user in users)
    return max_id + 1


def get_exchange_rate(from_currency: str, to_currency: str) -> float:
    rates = {
        "USD_EUR": 0.92,
        "EUR_USD": 1.08,
        "USD_BTC": 0.00001685,
        "BTC_USD": 59337.21,
        "USD_ETH": 0.00027,
        "ETH_USD": 3720.00,
        "USD_RUB": 98.5,
        "RUB_USD": 0.01016,
    }
    
    key = f"{from_currency.upper()}_{to_currency.upper()}"
    if key in rates:
        return rates[key]
    
    if from_currency != "USD" and to_currency != "USD":
        try:
            rate_to_usd = get_exchange_rate(from_currency, "USD")
            rate_from_usd = get_exchange_rate("USD", to_currency)
            return rate_to_usd * rate_from_usd
        except Exception:
            pass
    
    error_msg = f"Курс {from_currency}→{to_currency} не найден"
    raise ValueError(error_msg)


def format_currency(amount: float, currency: str) -> str:
    if currency == "USD":
        return f"${amount:,.2f}"
    elif currency == "EUR":
        return f"€{amount:,.2f}"
    elif currency == "BTC":
        return f"₿{amount:.8f}"
    elif currency == "ETH":
        return f"Ξ{amount:.6f}"
    else:
        return f"{amount:.2f} {currency}"
