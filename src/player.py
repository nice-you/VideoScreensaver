import ctypes, cv2, numpy, pygame, asyncio, socket
from saver import VideoSaver
from fetcher import get_video_info
from pathlib import Path
from bg_manager import BackgroundManager
from logger import logger


logger.info("程序启动")


def is_online(host="8.8.8.8", port=53, timeout=3):
    """尝试连接公共 DNS 服务器判断网络状态"""
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except OSError:
        return False

def enable_dpi_awareness():
    try:
        # 对于Windows 8.1及以上版本
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except AttributeError:
        try:
            # 对于旧版Windows，尝试另一种方法
            ctypes.windll.user32.SetProcessDPIAware()
        except AttributeError:
            pass

enable_dpi_awareness()

saver = VideoSaver()

root = Path(__file__).parent
bg_dir = root / "backgrounds"
bg_dir.mkdir(exist_ok=True)


class Player:
    def __init__(self, bg_manager):
        self.bg_manager = bg_manager
        # 播放设置预处理
        pygame.init()
        info = pygame.display.Info()
        self.screen_size = self.screen_width, self.screen_height = info.current_w, info.current_h
        self.has_video = False
        self.video_list = []
        self.current_index = 0
        self.video_m4s_path = saver.get_video()
        if not self.video_m4s_path:
            # 无视频：进入纯背景模式
            print("无缓存视频，进入图片模式，后台下载中...")
            logger.info("无缓存视频，进入图片模式，后台下载中...")
            self.has_video = False
            self.video = None
            self.total_frames = 0
            self.current_frame = 0
            self.display_size = self.display_width, self.display_height = (1, 1)
            self.fps = 30  # 默认帧率，避免主循环 clock.tick(0)
            # 占位灰色背景
            self.title = "无标题"
            self.name = "未知"

            self.v_background = pygame.Surface((self.screen_height // 3 // 9 * 16, self.screen_height // 3))
            self.v_background.fill((50, 50, 50))
            self.v_bg_rect = self.v_background.get_rect()
            self.v_bg_rect.center = (self.screen_width / 2, self.screen_height * (7 / 12))

            self.video_rect = self.v_bg_rect.copy()
            self.frame = self.v_background.copy()
            # 屏保背景
            self.last_update_bg = pygame.time.get_ticks()
            self.background = pygame.Surface(self.screen_size)
            self.background.fill((230, 240, 240))
            self.bg_rect = self.background.get_rect()
            self.bg_rect.center = self.screen_width // 2, self.screen_height // 2
            return

        self.bvid = self.video_m4s_path.stem

        # 视频信息预处理
        self.title : str = "无标题"
        self.name : str = "未知"
        asyncio.run(self.get_info())

        # 视频预处理
        self.video = cv2.VideoCapture(self.video_m4s_path)
        self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0

        # 屏保背景加载
        self.last_update_bg = pygame.time.get_ticks()
        self.background = pygame.Surface(self.screen_size)
        self.background.fill((230, 240, 240))

        self.bg_rect =  self.background.get_rect()
        self.bg_rect.center = self.screen_width // 2, self.screen_height // 2

        # 视频灰色背景加载
        self.v_background = pygame.Surface((self.screen_height // 3 // 9 * 16, self.screen_height // 3))
        self.v_background.fill((50, 50 ,50))

        # 视频播放位置处理
        self.frame = self.v_background.copy()
        video_width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        zoom = self.screen_height * (1/3) / video_height
        self.display_size = self.display_width, self.display_height =\
            int(video_width * zoom), int(video_height * zoom)
        self.fps = self.video.get(cv2.CAP_PROP_FPS)

        self.v_bg_rect = self.v_background.get_rect()
        self.v_bg_rect.center = (self.screen_width / 2, self.screen_height * (7/12))
        self.video_rect = self.v_bg_rect.copy()

    def get_frame(self):
        """获取视频帧"""
        if self.has_video:
            rat, frame = self.video.read()
            if not rat:
                self.has_video = False
                self.frame = self.v_background.copy()
                return rat
            else:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_resized = cv2.resize(frame_rgb, self.display_size)
                self.frame = pygame.surfarray.make_surface(numpy.transpose(frame_resized, (1, 0, 2)))

                self.video_rect = self.frame.get_rect()
                self.video_rect.center = (self.screen_width / 2, self.screen_height * (7/12))

                self.current_frame += 1
                return rat
        return False

    async def get_info(self):
        try:
            info = await get_video_info(self.bvid)
            self.title = info.get('title', "无标题")
            self.name = info.get('name', "未知")
        except Exception as e:
            print(f"获取视频信息失败（可能无网络）: {e}")
            logger.error(f"获取视频信息失败（可能无网络）: {e}")
            self.title = "无标题"
            self.name = "未知"


    def create_window(self):
        """打开一个新的窗口"""
        # 判断display是否初始化
        try:
            pygame.display.get_init()
        except pygame.error:
            pygame.display.init()
        screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        screen.fill((230, 240, 240))
        pygame.display.set_caption("7981屏保")
        self.update_background(True)
        return screen

    @staticmethod
    def close_window():
        """关闭窗口"""
        print("窗口关闭")
        logger.info("窗口关闭")
        pygame.display.quit()

    def change_video(self):
        # 释放当前视频资源
        if hasattr(self, 'video') and self.video:
            self.video.release()
            cv2.destroyAllWindows()

        # 获取当前所有视频列表（按修改时间排序）
        all_videos = sorted(Path("cache").glob("*.m4s"), key=lambda p: p.stat().st_mtime)

        if not all_videos:
            self.has_video = False
            return

        # 根据网络状态决定删除还是循环
        if is_online():
            # 有网：删除当前视频文件（淘汰旧视频）
            if self.video_m4s_path and self.video_m4s_path.exists():
                self.video_m4s_path.unlink()
            # 重新获取列表，现在最旧的就是原来的第二个
            remaining = sorted(Path("cache").glob("*.m4s"), key=lambda p: p.stat().st_mtime)
            if not remaining:
                self.has_video = False
                return
            next_path = remaining[0]  # 取下一个最旧的
        else:
            # 无网：不删除，循环播放
            try:
                idx = all_videos.index(self.video_m4s_path)
            except ValueError:
                idx = -1
            next_idx = (idx + 1) % len(all_videos)
            next_path = all_videos[next_idx]

        # 加载新视频
        self._init_from_video_path(next_path)

    def try_recover_video(self):
        """尝试从无视频模式恢复到视频模式"""
        # 重新扫描缓存目录
        video_path = saver.get_video()
        if video_path:
            self.has_video = True
            self._init_from_video_path(video_path)
            print(f"检测到新视频，恢复播放: {video_path.name}")
            logger.info(f"检测到新视频，恢复播放: {video_path.name}")
        else:
            self.has_video = False
            print("cache中无视频")
            logger.warning("cache中无视频")

    def seek_to_progress(self, progress: float):
        """进度条跳转"""
        if not self.has_video:
            return
        last_target_frame = int(self.total_frames * progress)
        target_frame = max(0, min(last_target_frame, self.total_frames - 1))

        print(f"视频标题:{self.title}, bvid:{self.bvid}, 总时长{self.total_frames // self.fps}秒,"
              f" 进度条从{last_target_frame // self.fps}秒跳转至{target_frame // self.fps}")
        logger.info(f"视频标题:{self.title}, bvid:{self.bvid}, 总时长{self.total_frames // self.fps}秒,"
              f" 进度条从{last_target_frame // self.fps}秒跳转至{target_frame // self.fps}")

        self.video.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        self.current_frame = target_frame

    def update_background(self, is_now=False):
        now = pygame.time.get_ticks()
        if is_now or now - self.last_update_bg >= 30 * 1000:
            # 从 BackgroundManager 获取一张随机图片路径
            img_path = self.bg_manager.get_random_image()
            if img_path:
                try:
                    surf = pygame.image.load(str(img_path)).convert()
                    surf = pygame.transform.scale(surf, self.screen_size)
                    self.background = surf
                    print(f"更换背景: {img_path.name}")
                    logger.info(f"更换背景: {img_path.name}")
                except Exception as e:
                    print(f"加载背景失败: {e}")
                    logger.error(f"加载背景失败: {e}")
                    # 降级：纯色背景
                    self.background.fill((230, 240, 240))
            else:
                # 没有背景图，使用纯色
                self.background.fill((230, 240, 240))
            self.last_update_bg = now

    def _init_from_video_path(self, video_path):
        self.video_m4s_path = video_path
        self.bvid = self.video_m4s_path.stem
        asyncio.run(self.get_info())

        self.video = cv2.VideoCapture(str(self.video_m4s_path))
        self.total_frames = int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0

        video_width = int(self.video.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(self.video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        # 防止除零（理论上 video_height 不可能为 0，但安全起见）
        if video_height == 0:
            self.has_video = False
            return
        zoom = self.screen_height * (1 / 3) / video_height
        self.display_size = self.display_width, self.display_height = \
            int(video_width * zoom), int(video_height * zoom)
        self.has_video = True
        self.fps = self.video.get(cv2.CAP_PROP_FPS)
        self.video_rect = self.frame.get_rect()
        self.video_rect.center = self.v_bg_rect.center


if __name__ == '__main__':
    bg_m = BackgroundManager(bg_dir=Path(__file__).parent / "backgrounds",
    max_images=20,
    min_trigger=5,
    check_interval=3600     # 1小时检查一次
)
    player = Player(bg_m)
    _screen = player.create_window()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_b:
                    pygame.quit()

        if player.get_frame():
            x = (player.screen_width - player.display_width) // 2
            y = (player.screen_height - player.display_height) // 2
            _screen.blit(player.frame, (x, y))
            pygame.display.flip()
