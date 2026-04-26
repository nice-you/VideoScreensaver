import time, threading, requests
from pathlib import Path
from typing import List, Optional
from logger import logger
from utils import get_bg_dir


logger.info("程序启动")


class BackgroundManager:
    def __init__(self, max_images=20, min_trigger=5, check_interval=3600):
        """
        :param max_images: 最大保留图片数
        :param min_trigger: 低于此数时触发下载
        :param check_interval: 检查间隔（秒），默认1小时
        """
        self.bg_dir = get_bg_dir()
        self.bg_dir.mkdir(parents=True, exist_ok=True)
        self.max_images = max_images
        self.min_trigger = min_trigger
        self.check_interval = check_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._downloading = False
        self._image_list: List[Path] = []

        # 创建目录
        self.bg_dir.mkdir(parents=True, exist_ok=True)

        # 初始刷新列表
        self._refresh_list()

        # 启动后台监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _refresh_list(self):
        """刷新图片列表（按修改时间排序，旧→新）"""
        with self._lock:
            images = list(self.bg_dir.glob("*.jpg")) + list(self.bg_dir.glob("*.jpeg")) + list(self.bg_dir.glob("*.png"))
            images.sort(key=lambda p: p.stat().st_mtime)
            self._image_list = images

    def get_random_image(self) -> Optional[Path]:
        """随机返回一张背景图片路径"""
        with self._lock:
            if not self._image_list:
                return None
            import random
            return random.choice(self._image_list)

    def get_image_count(self) -> int:
        with self._lock:
            return len(self._image_list)

    def _need_more(self) -> bool:
        return self.get_image_count() < self.min_trigger

    def _cleanup_old(self):
        """删除旧图片，只保留最新的 max_images 张"""
        with self._lock:
            while len(self._image_list) > self.max_images:
                oldest = self._image_list.pop(0)
                try:
                    oldest.unlink()
                    print(f"清理旧背景图: {oldest.name}")
                except OSError:
                    pass

    def _monitor_loop(self):
        """后台监控循环"""
        while not self._stop_event.is_set():
            try:
                if self._need_more() and not self._downloading:
                    self._download_one_image()
                self._cleanup_old()
                # 等待检查间隔
                for _ in range(self.check_interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"BackgroundManager 异常: {e}")
                time.sleep(10)

    def _download_one_image(self):
        if self._downloading:
            return
        self._downloading = True
        try:
            img_url = "https://picsum.photos/1920/1080"
            # 设置超时，避免长时间阻塞
            resp = requests.get(img_url, timeout=15)
            if resp.status_code == 200:
                timestamp = int(time.time())
                filepath = self.bg_dir / f"bg_{timestamp}.jpg"
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                print(f"背景图下载成功: {filepath.name}")
                self._refresh_list()
            else:
                # 非 200 状态码（如 503）静默失败，不打印过多信息
                pass
        except requests.exceptions.RequestException as e:
            # 网络异常（无网、超时等）静默失败
            pass
        except Exception as e:
            print(f"背景图下载异常: {e}")
        finally:
            self._downloading = False

    def stop(self):
        """停止后台监控"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)