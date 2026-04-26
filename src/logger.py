import logging
from pathlib import Path
from utils import get_log_path


def setup_logger():
    log_path = get_log_path()
    _logger = logging.getLogger("ScreenSaver")
    _logger.setLevel(logging.DEBUG)

    # 文件处理器（记录所有级别）
    file_handler = logging.FileHandler(log_path, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)
    _logger.addHandler(file_handler)

    # 可选：控制台处理器（仅在开发时启用，打包后可注释）
    # console_handler = logging.StreamHandler()
    # console_handler.setLevel(logging.INFO)
    # _logger.addHandler(console_handler)

    return _logger


# 全局日志实例
logger = setup_logger()