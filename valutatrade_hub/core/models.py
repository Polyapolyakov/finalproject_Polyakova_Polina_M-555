
import hashlib
import secrets


from datetime import datetime
from typing import Dict, Optional, Any
from abc import ABC, abstractmethod


class ValutaTradeError(Exception):
    pass


class InsufficientFundsError(ValutaTradeError):
    def __init__(self, currency_code: str, available: float, required: float):
        message = (
            f"Недостаточно средств: доступно {available:.4f} {currency_code}, "
            f"требуется {required:.4f} {currency_code}"
        )
        super().__init__(message)


class CurrencyNotFoundError(ValutaTradeError):
    def __init__(self, currency_code: str):
        message = f"Неизвестная валюта '{currency_code}'"
        super().__init__(message)


class Currency(ABC):
    def __init__(self, name: str, code: str):
        self._name = name
        self._code = code.upper()
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def code(self) -> str:
        return self._code
    
    @abstractmethod
    def get_display_info(self) -> str:
        pass


class FiatCurrency(Currency):
    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)
        self._issuing_country = issuing_country
    
    def get_display_info(self) -> str:
        info = f"[FIAT] {self._code} — {self._name}"
        return f"{info} (Issuing: {self._issuing_country})"


class CryptoCurrency(Currency):
    def __init__(self, name: str, code: str, algorithm: str):
        super().__init__(name, code)
        self._algorithm = algorithm
    
    def get_display_info(self) -> str:
        info = f"[CRYPTO] {self._code} — {self._name}"
        return f"{info} (Algo: {self._algorithm})"


CURRENCY_REGISTRY: Dict[str, Currency] = {}


def init_currencies():
    CURRENCY_REGISTRY.update({
        "USD": FiatCurrency("US Dollar", "USD", "United States"),
        "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
        "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256"),
        "ETH": CryptoCurrency("Ethereum", "ETH", "Ethash"),
        "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    })


def get_currency(code: str) -> Currency:
    code = code.upper()
    if not CURRENCY_REGISTRY:
        init_currencies()
    
    if code not in CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code)
    
    return CURRENCY_REGISTRY[code]


class User:
    def __init__(self, user_id: int, username: str,
                 hashed_password: str, salt: str):
        self._user_id = user_id
        self._username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = datetime.now()
    
    @property
    def user_id(self) -> int:
        return self._user_id
    
    @property
    def username(self) -> str:
        return self._username
    
    def verify_password(self, password: str) -> bool:
        hash_input = f"{password}{self._salt}".encode()
        return self._hashed_password == hashlib.sha256(hash_input).hexdigest()
    
    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"]
        )


class Wallet:
    def __init__(self, currency_code: str, balance: float = 0.0):
        self._currency = get_currency(currency_code)
        self._balance = float(balance)
    
    @property
    def currency_code(self) -> str:
        return self._currency.code
    
    @property
    def balance(self) -> float:
        return self._balance
    
    @balance.setter
    def balance(self, value: float):
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value
    
    def deposit(self, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")
        self.balance += amount
    
    def withdraw(self, amount: float) -> None:
        if amount <= 0:
            msg = "Сумма снятия должна быть положительной"
            raise ValueError(msg)
        if amount > self._balance:
            raise InsufficientFundsError(
                currency_code=self.currency_code,
                available=self._balance,
                required=amount
            )
        self.balance -= amount
    
    def to_dict(self) -> dict:
        return {
            "currency_code": self.currency_code,
            "balance": self._balance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"]
        )


class Portfolio:
    def __init__(self, user_id: int):
        self._user_id = user_id
        self._wallets: Dict[str, Wallet] = {}
    
    def add_wallet(self, currency_code: str) -> Wallet:
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            msg = f"Кошелек '{currency_code}' уже существует"
            raise ValueError(msg)
        
        wallet = Wallet(currency_code)
        self._wallets[currency_code] = wallet
        return wallet
    
    def get_wallet(self, currency_code: str) -> Optional[Wallet]:
        return self._wallets.get(currency_code.upper())
    
    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "wallets": {
                code: wallet.to_dict()
                for code, wallet in self._wallets.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        portfolio = cls(data["user_id"])
        for code, wallet_data in data["wallets"].items():
            portfolio._wallets[code] = Wallet.from_dict(wallet_data)
        return portfolio
