import sys
from pathlib import Path

def get_base_dir():
    """返回可执行文件所在的目录（开发环境返回项目根目录）"""
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 运行
        return Path(sys.executable).parent
    else:
        # 开发环境：返回 src 的父目录（即项目根目录）
        return Path(__file__).parent.parent

def get_cache_dir():
    return get_base_dir() / "cache"

def get_bg_dir():
    return get_base_dir() / "backgrounds"

def get_log_path():
    return get_base_dir() / "screen_saver.log"