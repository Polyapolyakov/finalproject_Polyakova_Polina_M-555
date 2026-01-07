
from typing import Tuple, Optional
from prettytable import PrettyTable

from .models import (
    User, Portfolio, get_currency,
    CurrencyNotFoundError, InsufficientFundsError
)
from valutatrade_hub.decorators import log_action
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
    
        available_payment_currencies = []
        for wallet_currency in portfolio._wallets.keys():
            if wallet_currency.upper() != currency_code.upper():
                wallet = portfolio.get_wallet(wallet_currency)
                if wallet and wallet.balance > 0:
                    available_payment_currencies.append(wallet_currency)
    
        if not available_payment_currencies:
            msg = "Нет доступных средств для оплаты. Пополните баланс."
            return False, msg
    
        payment_currency = available_payment_currencies[0]
        payment_wallet = portfolio.get_wallet(payment_currency)
    
        try:
            rate = get_exchange_rate(currency_code, payment_currency)
            cost_in_payment = amount * rate
        except Exception as e:
            msg = f"Не удалось получить курс {currency_code}→{payment_currency}: {str(e)}"
            return False, msg
    
        if payment_wallet.balance < cost_in_payment:
            available = format_currency(payment_wallet.balance, payment_currency)
            required = format_currency(cost_in_payment, payment_currency)
            msg = f"Недостаточно {payment_currency}. Доступно: {available}, требуется: {required}"
            return False, msg
    
        target_wallet = portfolio.get_wallet(currency_code)
        if not target_wallet:
            target_wallet = portfolio.add_wallet(currency_code)
    
        try:
            payment_wallet.withdraw(cost_in_payment)
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
        cost = format_currency(cost_in_payment, payment_currency)
        msg = f"Куплено {bought} за {cost}"
        return True, msg
    
    @log_action("SELL")
    def sell(self, currency_code: str, amount: float) -> Tuple[bool, str]:
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
    
        target_currency = "USD"
        if "USD" not in portfolio._wallets and portfolio._wallets:
            for wallet_currency in portfolio._wallets.keys():
                if wallet_currency != currency_code:
                    target_currency = wallet_currency
                    break
    
        try:
            rate = get_exchange_rate(currency_code, target_currency)
            revenue = amount * rate
        except Exception as e:
            msg = f"Не удалось получить курс {currency_code}→{target_currency}: {str(e)}"
            return False, msg
    
        target_wallet = portfolio.get_wallet(target_currency)
        if not target_wallet:
            target_wallet = portfolio.add_wallet(target_currency)
    
        try:
            source_wallet.withdraw(amount)
            target_wallet.deposit(revenue)
        except Exception as e:
            return False, str(e)
    
        for i, p in enumerate(portfolios):
            if p["user_id"] == user.user_id:
                portfolios[i] = portfolio.to_dict()
                break
    
        save_json("data/portfolios.json", portfolios)
    
        sold = format_currency(amount, currency_code)
        received = format_currency(revenue, target_currency)
        msg = f"Продано {sold} за {received}"
        return True, msg
    
    @log_action("DEPOSIT")
    def deposit(self, currency_code: str, amount: float) -> Tuple[bool, str]:
        if not self.user_manager.is_logged_in():
            return False, "Сначала выполните login"
        
        if amount <= 0:
            msg = "Сумма пополнения должна быть положительной"
            return False, msg
        
        try:
            currency = get_currency(currency_code)
        except CurrencyNotFoundError:
            msg = f"Неизвестная валюта '{currency_code}'"
            return False, msg
        
        user = self.user_manager.current_user
        
        portfolios = load_json("data/portfolios.json", [])
        portfolio_data = next(
            (p for p in portfolios if p["user_id"] == user.user_id),
            {}
        )
        
        if not portfolio_data:
            portfolio = Portfolio(user.user_id)
        else:
            portfolio = Portfolio.from_dict(portfolio_data)
        
        wallet = portfolio.get_wallet(currency_code)
        if not wallet:
            wallet = portfolio.add_wallet(currency_code)
        
        wallet.deposit(amount)
        
        portfolio_dict = portfolio.to_dict()
        
        updated = False
        for i, p in enumerate(portfolios):
            if p.get("user_id") == user.user_id:
                portfolios[i] = portfolio_dict
                updated = True
                break
        
        if not updated:
            portfolios.append(portfolio_dict)
        
        save_json("data/portfolios.json", portfolios)
        
        deposited = format_currency(amount, currency_code)
        msg = f"Успешно пополнено: {deposited}"
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
