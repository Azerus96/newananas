import logging
import sys
from typing import Optional
from pathlib import Path

def get_logger(name: str, 
               level: int = logging.INFO,
               log_file: Optional[str] = None) -> logging.Logger:
    """
    Создает и настраивает логгер
    
    Args:
        name: Имя логгера
        level: Уровень логирования
        log_file: Путь к файлу для записи логов
        
    Returns:
        Настроенный объект логгера
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Форматтер для логов
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Хендлер для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Хендлер для записи в файл
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    return logger
