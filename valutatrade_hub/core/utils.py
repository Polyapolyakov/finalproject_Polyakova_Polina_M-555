
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
        "USD_USD": 1.0,
        "RUB_RUB": 1.0,
        "EUR_EUR": 1.0,
        "BTC_BTC": 1.0,
        "ETH_ETH": 1.0,
        "USD_EUR": 0.92,
        "EUR_USD": 1.08,
        "USD_BTC": 0.00001685,
        "BTC_USD": 59337.21,
        "USD_ETH": 0.00027,
        "ETH_USD": 3720.00,
        "USD_RUB": 98.5,
        "RUB_USD": 0.01016,
        "EUR_RUB": 106.38,    # EUR→RUB через USD: 1.08 * 98.5
        "RUB_EUR": 0.0094,    # RUB→EUR через USD: 0.01016 * 0.92
        "BTC_EUR": 54590.23,  # BTC→EUR через USD
        "EUR_BTC": 0.0000183, # EUR→BTC через USD
        "BTC_RUB": 5844705.0, # BTC→RUB через USD
        "RUB_BTC": 0.000000171, # RUB→BTC через USD
        "ETH_EUR": 3422.4,    # ETH→EUR через USD
        "EUR_ETH": 0.000292,  # EUR→ETH через USD
        "ETH_RUB": 366420.0,  # ETH→RUB через USD
        "RUB_ETH": 0.00000273 # RUB→ETH через USD
    }
    
    key = f"{from_currency.upper()}_{to_currency.upper()}"
    
    if from_currency.upper() == to_currency.upper():
        return 1.0
    
    if key in rates:
        return rates[key]
    
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
