
from typing import Tuple, Optional
from prettytable import PrettyTable

from .models import (
    User, Portfolio, get_currency,
    CurrencyNotFoundError, InsufficientFundsError
)
from .decorators import log_action
from .utils import (
    load_json, save_json, hash_password, get_next_user_id,
    get_exchange_rate, format_currency
)


class UserManager:
    def __init__(self):
        self.current_user: Optional[User] = None
    
    @log_action("REGISTER")
    def register(self, username: str, password: str) -> Tuple[bool, str]:
        """Регистрация пользователя."""
        users = load_json("data/users.json", [])
        
        if any(u["username"] == username for u in users):
            msg = f"Имя пользователя '{username}' уже занято"
            return False, msg
        
        if len(password) < 4:
            msg = "Пароль должен быть не короче 4 символов"
            return False, msg
        
        user_id = get_next_user_id()
        hashed_password, salt = hash_password(password)
        
        user = User(user_id, username, hashed_password, salt)
        users.append(user.to_dict())
        
        save_json("data/users.json", users)
        
        portfolio = Portfolio(user_id)
        portfolios = load_json("data/portfolios.json", [])
        portfolios.append(portfolio.to_dict())
        save_json("data/portfolios.json", portfolios)
        
        msg = f"Пользователь '{username}' зарегистрирован (id={user_id})"
        return True, msg
    
    @log_action("LOGIN")
    def login(self, username: str, password: str) -> Tuple[bool, str]:
        users = load_json("data/users.json", [])
        
        user_data = next((u for u in users if u["username"] == username), None)
        if not user_data:
            msg = f"Пользователь '{username}' не найден"
            return False, msg
        
        user = User.from_dict(user_data)
        if not user.verify_password(password):
            return False, "Неверный пароль"
        
        self.current_user = user
        return True, f"Вы вошли как '{username}'"
    
    def is_logged_in(self) -> bool:
        return self.current_user is not None


class PortfolioManager:
    def __init__(self, user_manager: UserManager):
        self.user_manager = user_manager
    
    @log_action("SHOW_PORTFOLIO")
    def show_portfolio(self, base_currency: str = "USD") -> Tuple[bool, str]:
        if not self.user_manager.is_logged_in():
            return False, "Сначала выполните login"
        
        user = self.user_manager.current_user
        portfolios = load_json("data/portfolios.json", [])
        
        portfolio_data = next(
            (p for p in portfolios if p["user_id"] == user.user_id),
            None
        )
        if not portfolio_data:
            return True, "Ваш портфель пуст"
        
        portfolio = Portfolio.from_dict(portfolio_data)
        
        # Создание таблицы
        table = PrettyTable()
        columns = ["Валюта", "Баланс", f"Стоимость в {base_currency}"]
        table.field_names = columns
        table.align = "l"
        
        total = 0
        
        for currency_code, wallet in portfolio._wallets.items():
            balance = wallet.balance
            
            if currency_code == base_currency:
                value = balance
            else:
                try:
                    rate = get_exchange_rate(currency_code, base_currency)
                    value = balance * rate
                except Exception:
                    value = 0
            
            total += value
            
            table.add_row([
                currency_code,
                format_currency(balance, currency_code),
                format_currency(value, base_currency)
            ])
        
        result = f"Портфель пользователя '{user.username}':\n"
        result += str(table)
        result += f"\nИтого: {format_currency(total, base_currency)}"
        
        return True, result
    
    @log_action("BUY")
    def buy(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        """Купить валюту."""
        if not self.user_manager.is_logged_in():
            return False, "Сначала выполните login"
        
        try:
            currency = get_currency(currency_code)
        except CurrencyNotFoundError:
            msg = f"Неизвестная валюта '{currency_code}'"
            return False, msg
        
        if amount <= 0:
            msg = "Количество должно быть положительным"
            return False, msg
        
        user = self.user_manager.current_user
        
        portfolios = load_json("data/portfolios.json", [])
        portfolio_data = next(
            (p for p in portfolios if p["user_id"] == user.user_id),
            {}
        )
        portfolio = Portfolio.from_dict(portfolio_data) if portfolio_data \
            else Portfolio(user.user_id)
        
        try:
            rate = get_exchange_rate(currency_code, "USD")
            cost_usd = amount * rate
        except Exception:
            msg = f"Не удалось получить курс для {currency_code}"
            return False, msg
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet or usd_wallet.balance < cost_usd:
            required = format_currency(cost_usd, 'USD')
            msg = f"Недостаточно средств. Требуется: {required}"
            return False, msg
        
        target_wallet = portfolio.get_wallet(currency_code)
        if not target_wallet:
            target_wallet = portfolio.add_wallet(currency_code)
        
        try:
            usd_wallet.withdraw(cost_usd)
            target_wallet.deposit(amount)
        except InsufficientFundsError as e:
            return False, str(e)
        
        for i, p in enumerate(portfolios):
            if p["user_id"] == user.user_id:
                portfolios[i] = portfolio.to_dict()
                break
        else:
            portfolios.append(portfolio.to_dict())
        
        save_json("data/portfolios.json", portfolios)
        
        bought = format_currency(amount, currency_code)
        cost = format_currency(cost_usd, 'USD')
        msg = f"Куплено {bought} за {cost}"
        return True, msg
    
    @log_action("SELL")
    def sell(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        """Продать валюту."""
        if not self.user_manager.is_logged_in():
            return False, "Сначала выполните login"
        
        try:
            currency = get_currency(currency_code)
        except CurrencyNotFoundError:
            msg = f"Неизвестная валюта '{currency_code}'"
            return False, msg
        
        if amount <= 0:
            msg = "Количество должно быть положительным"
            return False, msg
        
        user = self.user_manager.current_user
        
        portfolios = load_json("data/portfolios.json", [])
        portfolio_data = next(
            (p for p in portfolios if p["user_id"] == user.user_id),
            {}
        )
        if not portfolio_data:
            return False, "Портфель не найден"
        
        portfolio = Portfolio.from_dict(portfolio_data)
        
        source_wallet = portfolio.get_wallet(currency_code)
        if not source_wallet:
            msg = f"У вас нет кошелька '{currency_code}'"
            return False, msg
        
        if source_wallet.balance < amount:
            available = format_currency(source_wallet.balance, currency_code)
            msg = f"Недостаточно {currency_code}. Доступно: {available}"
            return False, msg
        
        try:
            rate = get_exchange_rate(currency_code, "USD")
            revenue_usd = amount * rate
        except Exception:
            msg = f"Не удалось получить курс для {currency_code}"
            return False, msg
        
        usd_wallet = portfolio.get_wallet("USD")
        if not usd_wallet:
            usd_wallet = portfolio.add_wallet("USD")
        
        try:
            source_wallet.withdraw(amount)
            usd_wallet.deposit(revenue_usd)
        except Exception as e:
            return False, str(e)
        
        for i, p in enumerate(portfolios):
            if p["user_id"] == user.user_id:
                portfolios[i] = portfolio.to_dict()
                break
        
        save_json("data/portfolios.json", portfolios)
        
        sold = format_currency(amount, currency_code)
        revenue = format_currency(revenue_usd, 'USD')
        msg = f"Продано {sold} за {revenue}"
        return True, msg
    
    @log_action("GET_RATE")
    def get_rate(self, from_currency: str, to_currency: str) -> Tuple[bool, str]:
        """Получить курс валюты."""
        try:
            from_curr = get_currency(from_currency)
            to_curr = get_currency(to_currency)
        except CurrencyNotFoundError as e:
            return False, str(e)
        
        try:
            rate = get_exchange_rate(from_currency, to_currency)
            inverse_rate = 1 / rate if rate != 0 else 0
            
            result = f"Курс {from_currency}→{to_currency}: {rate:.8f}\n"
            result += f"Обратный курс {to_currency}→{from_currency}: {inverse_rate:.8f}"
            return True, result
        except Exception as e:
            msg = f"Не удалось получить курс: {e}"
            return False, msg
