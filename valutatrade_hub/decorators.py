
import functools
import time
import logging


from typing import Callable, Any


def log_action(action_name: str):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger = logging.getLogger("valutatrade")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                logger.info(
                    f"{action_name}: успешно за {elapsed:.3f}с",
                    extra={
                        "action": action_name,
                        "elapsed": elapsed,
                        "status": "success"
                    }
                )
                return result
                
            except Exception as e:
                elapsed = time.time() - start_time
                error_msg = f"{action_name}: ошибка за {elapsed:.3f}с - {e}"
                logger.error(
                    error_msg,
                    extra={
                        "action": action_name,
                        "elapsed": elapsed,
                        "error": str(e),
                        "status": "error"
                    }
                )
                raise
        
        return wrapper
    return decorator


def confirm_action(action_name: str):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            table_name = args[1] if len(args) > 1 else None
            if table_name:
                prompt = (
                    f'Вы уверены, что хотите выполнить "{action_name}" '
                    f'таблицы "{table_name}"? [y/n]: '
                )
            else:
                prompt = (
                    f'Вы уверены, что хотите выполнить "{action_name}"? '
                    f'[y/n]: '
                )
            
            response = input(prompt).strip().lower()
            if response != 'y':
                print("Операция отменена.")
                return None, "Операция отменена пользователем."
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def create_cacher():
    cache = {}
    
    def cache_result(key: str, value_func: Callable, *args, **kwargs) -> Any:
        if key in cache:
            return cache[key]
        
        result = value_func(*args, **kwargs)
        cache[key] = result
        return result
    
    return cache_result


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("valutatrade.log"),
        logging.StreamHandler()
    ]
)
