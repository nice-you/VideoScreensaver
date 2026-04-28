import logging
from utils import get_log_path
from datetime import datetime, timedelta


def setup_logger(keep_days=2):
    log_path = get_log_path()

    # 日志自动清理：删除超过 keep_days 天的旧日志
    if log_path.exists():
        mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        if datetime.now() - mtime > timedelta(days=keep_days):
            try:
                log_path.unlink()
                print(f"日志文件超过 {keep_days} 天，已自动清理")
            except OSError:
                pass

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