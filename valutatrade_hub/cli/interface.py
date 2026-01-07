
import sys


from typing import Optional

from valutatrade_hub.core.usecases import UserManager, PortfolioManager
from valutatrade_hub.core.models import CurrencyNotFoundError, InsufficientFundsError


class SimpleCLI:
    def __init__(self):
        self.user_manager = UserManager()
        self.portfolio_manager = PortfolioManager(self.user_manager)
    
    def run(self, args: Optional[list] = None) -> int:
        """Запуск CLI."""
        if args is None:
            args = sys.argv[1:]
        
        if not args:
            self._print_welcome()
            self._print_help()
            return self._interactive_mode()
        
        command = args[0]
        
        if command == "register":
            return self._register(args[1:])
        elif command == "login":
            return self._login(args[1:])
        elif command == "portfolio":
            return self._portfolio(args[1:])
        elif command == "buy":
            return self._buy(args[1:])
        elif command == "sell":
            return self._sell(args[1:])
        elif command == "rate":
            return self._rate(args[1:])
        elif command == "help":
            self._print_help()
            return 0
        elif command == "exit":
            print("Выход из программы...")
            return 0
        else:
            print(f"Неизвестная команда: {command}")
            self._print_help()
            return 1
    
    def _interactive_mode(self) -> int:
        print("\n" + "="*50)
        print("Введите команду (или 'exit' для выхода):")
        
        while True:
            try:
                user_input = input("\n>>> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == 'exit':
                    print("Выход из программы...")
                    return 0
                elif user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                parts = user_input.split()
                command = parts[0]
                args = parts[1:] if len(parts) > 1 else []
                
                if command == "register":
                    self._register(args)
                elif command == "login":
                    self._login(args)
                elif command == "deposit":
                    self._deposit(args[1:])
                elif command == "portfolio":
                    self._portfolio(args)
                elif command == "buy":
                    self._buy(args)
                elif command == "sell":
                    self._sell(args)
                elif command == "rate":
                    self._rate(args)
                else:
                    print(f"Неизвестная команда: {command}")
                    print("Введите 'help' для просмотра доступных команд")
                
            except KeyboardInterrupt:
                print("\n\nПрограмма прервана пользователем.")
                return 0
            except EOFError:
                print("\n\nВыход из программы...")
                return 0
            except Exception as e:
                print(f"Ошибка: {e}")
    
    def _print_welcome(self):
        print("="*50)
        print("ВАШ ВАЛЮТНЫЙ КОШЕЛЕК")
        print("="*50)
    
    def _print_help(self):
        print("\nДОСТУПНЫЕ КОМАНДЫ:")
        print("="*30)
        print("Регистрация и авторизация:")
        print("  register <username> <password> - регистрация")
        print("  login <username> <password>    - вход в систему")
        
        print("\nРабота с портфелем:")
        print("  deposit <валюта> <количество>  - пополнение баланса")
        print("  portfolio [валюта]             - показать портфель")
        print("                                  (по умолчанию: USD)")
        print("  buy <валюта> <количество>      - купить валюту")
        print("  sell <валюта> <количество>     - продать валюту")
        
        print("\nКурсы валют:")
        print("  rate <из_валюты> <в_валюту>    - получить курс")
        
        print("\nСправка и управление:")
        print("  help                           - показать эту справку")
        print("  exit                           - выход из программы")
        print("="*30)
        print("\nПримеры использования:")
        print("  register alice 123456          # Регистрация")
        print("  login alice 123456             # Вход")
        print("  buy BTC 0.01                   # Купить 0.01 BTC")
        print("  rate USD EUR                   # Курс USD→EUR")
    
    def _register(self, args):
        """Обработка регистрации."""
        if len(args) < 2:
            print("Использование: register <username> <password>")
            print("Пример: register alice 123456")
            return 1
        
        success, message = self.user_manager.register(args[0], args[1])
        print("Успех" if success else "Ошибка", message)
        return 0 if success else 1
    
    def _login(self, args):
        """Обработка входа."""
        if len(args) < 2:
            print("Использование: login <username> <password>")
            print("Пример: login alice 123456")
            return 1
        
        success, message = self.user_manager.login(args[0], args[1])
        print("Успех" if success else "Ошибка", message)
        return 0 if success else 1

    def _deposit(self, args):
        if len(args) < 2:
            print("Использование: deposit <валюта> <количество>")
            print("Пример: deposit USD 100")
            return 1
        
        try:
            amount = float(args[1])
        except ValueError:
            print("Ошибка: количество должно быть числом")
            return 1
        
        portfolios = load_json("data/portfolios.json", [])
        user = self.user_manager.current_user
        
        if not user:
            print("Сначала выполните login")
            return 1
        
        # Находим портфель пользователя
        for portfolio in portfolios:
            if portfolio.get("user_id") == user.user_id:
                currency = args[0].upper()
                if "wallets" not in portfolio:
                    portfolio["wallets"] = {}
                if currency not in portfolio["wallets"]:
                    portfolio["wallets"][currency] = {
                        "currency_code": currency,
                        "balance": 0.0
                    }
                
                portfolio["wallets"][currency]["balance"] += amount
                save_json("data/portfolios.json", portfolios)
                print(f"Успешно пополнено: {format_currency(amount, currency)}")
                return 0
        
        print("Портфель не найден")
        return 1

    def _portfolio(self, args):
        base_currency = args[0] if args else "USD"
        success, message = self.portfolio_manager.show_portfolio(base_currency)
        print(message)
        return 0 if success else 1
    
    def _buy(self, args):
        """Обработка покупки."""
        if len(args) < 2:
            print("Использование: buy <валюта> <количество>")
            print("Пример: buy BTC 0.01")
            return 1
        
        try:
            amount = float(args[1])
        except ValueError:
            print("Ошибка: количество должно быть числом")
            print("Пример: buy BTC 0.01")
            return 1
        
        success, message = self.portfolio_manager.buy(args[0], amount)
        print("Успех" if success else "Ошибка", message)
        return 0 if success else 1
    
    def _sell(self, args):
        """Обработка продажи."""
        if len(args) < 2:
            print("Использование: sell <валюта> <количество>")
            print("Пример: sell BTC 0.01")
            return 1
        
        try:
            amount = float(args[1])
        except ValueError:
            print("Ошибка: количество должно быть числом")
            print("Пример: sell BTC 0.01")
            return 1
        
        success, message = self.portfolio_manager.sell(args[0], amount)
        print("Успех" if success else "Ошибка", message)
        return 0 if success else 1
    
    def _rate(self, args):
        """Обработка получения курса."""
        if len(args) < 2:
            print("Использование: rate <из_валюты> <в_валюту>")
            print("Пример: rate USD BTC")
            return 1
        
        success, message = self.portfolio_manager.get_rate(args[0], args[1])
        print("Успех" if success else "Ошибка", message)
        return 0 if success else 1


def main():
    cli = SimpleCLI()
    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
