import os
from utils import get_cache_dir


class VideoSaver:
    def __init__(self):
        self._cache_dir = get_cache_dir()

    def save_video(self, bvid, video):
        """保存视频"""
        video_path = self._cache_dir / f"{bvid}.m4s"
        if video_path.exists():
            return
        with open(video_path, "wb") as f:
            f.write(video)

    def get_video(self):
        """获取视频(只需获取视频路径)"""
        videos = sorted(self._cache_dir.glob("*.m4s"), key=os.path.getmtime)
        if videos:
            return videos[0]
        else:
            return None

    def clear(self):
        """清除旧视频"""
        videos = sorted(self._cache_dir.glob("*.m4s"), key=lambda p: p.stat().st_mtime)
        if videos:
            videos[0].unlink()