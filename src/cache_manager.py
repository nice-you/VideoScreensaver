import asyncio, threading, time
from pathlib import Path
from typing import List
from fetcher import download_random_video
from logger import logger
from utils import get_cache_dir


class CacheManager:
    def __init__(self, max_videos=20, min_trigger=10, check_interval=30):
        """
        :param max_videos: 最大缓存数量，超过则删除最旧的
        :param min_trigger: 当缓存文件数低于此值时触发下载
        :param check_interval: 后台检查间隔（秒）
        """
        self.cache_dir = get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.max_videos = max_videos
        self.min_trigger = min_trigger
        self.check_interval = check_interval
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._downloading = False
        self._video_list: List[Path] = []   # 按修改时间排序（旧 → 新）

        # 创建文件夹
        self.cache_dir.mkdir(exist_ok=True)

        # 初始刷新列表
        self._refresh_list()

        # 启动后台监控线程
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _refresh_list(self):
        """扫描缓存目录，获取所有 .m4s 文件并按修改时间排序（旧→新）"""
        with self._lock:
            files = list(self.cache_dir.glob("*.m4s"))
            files.sort(key=lambda p: p.stat().st_mtime)
            logger.info(f"_refresh_list: 找到 {len(files)} 个文件: {[f.name for f in files]}")
            print(f"_refresh_list: 找到 {len(files)} 个文件: {[f.name for f in files]}")
            self._video_list = files

    def get_sorted_videos(self) -> List[Path]:
        """返回排序后的视频路径列表（旧→新）"""
        with self._lock:
            return self._video_list.copy()

    def get_video_count(self) -> int:
        with self._lock:
            return len(self._video_list)

    def remove_video(self, path: Path):
        """删除指定的视频文件，并从列表中移除"""
        with self._lock:
            if path in self._video_list:
                self._video_list.remove(path)
                try:
                    path.unlink()
                except OSError:
                    pass
                # 刷新列表（确保顺序）
                self._refresh_list()

    def _cleanup_old(self):
        with self._lock:
            while len(self._video_list) > self.max_videos:
                oldest = self._video_list.pop(0)
                if oldest.exists():
                    logger.warning(f"CacheManager 正在删除旧视频: {oldest}")
                    print(f"CacheManager 正在删除旧视频: {oldest}")
                    oldest.unlink()
                    logger.warning(f"CacheManager 已删除: {oldest}")
                    print(f"CacheManager 已删除: {oldest}")
                else:
                    logger.warning(f"CacheManager: 旧视频不存在: {oldest}")
                    print(f"CacheManager: 旧视频不存在: {oldest}")

    def _need_more(self) -> bool:
        return self.get_video_count() < self.min_trigger

    def _monitor_loop(self):
        """后台监控循环：定期检查缓存数量，不足则启动下载任务"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        while not self._stop_event.is_set():
            try:
                if self._need_more() and not self._downloading:
                    loop.run_until_complete(self._download_until_sufficient())
                # 清理旧文件
                self._cleanup_old()
                # 等待检查间隔
                for _ in range(self.check_interval):
                    if self._stop_event.is_set():
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"CacheManager 监控异常: {e}")
                logger.error(f"CacheManager 监控异常: {e}")
                time.sleep(10)
        loop.close()

    async def _download_until_sufficient(self):
        """下载视频直到缓存数量 ≥ min_trigger（或达到 max_videos）"""
        if self._downloading:
            return
        self._downloading = True
        try:
            # 需要下载的数量：至少让缓存达到 min_trigger，但不超过 max_videos
            current = self.get_video_count()
            target = min(self.max_videos, self.min_trigger + (self.max_videos - self.min_trigger))
            need = max(0, target - current)
            if need <= 0:
                return
            print(f"缓存不足，需下载 {need} 个视频 (当前 {current})")
            logger.info(f"缓存不足，需下载 {need} 个视频 (当前 {current})")

            # 记录已有的 bvid，避免重复下载
            with self._lock:
                existing_bvids = {p.stem for p in self._video_list}
            downloaded = 0
            attempts = 0
            max_attempts = need * 3

            while downloaded < need and attempts < max_attempts:
                attempts += 1
                bvid = await download_random_video()
                if bvid and bvid not in existing_bvids:
                    existing_bvids.add(bvid)
                    downloaded += 1
                    print(f"下载进度: {downloaded}/{need}")
                    logger.info(f"下载进度: {downloaded}/{need}")
                    # 每下载一个，刷新列表
                    self._refresh_list()
                await asyncio.sleep(1)  # 避免请求过快

            if downloaded < need:
                print(f"警告: 只下载了 {downloaded}/{need} 个视频")
                logger.warning(f"警告: 只下载了 {downloaded}/{need} 个视频")
            else:
                print("缓存补充完成")
                logger.info("缓存补充完成")
        finally:
            self._downloading = False

    def stop(self):
        """停止后台监控线程（程序退出时调用）"""
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2)