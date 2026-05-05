import pygame, time, sys, cv2
from pynput import mouse, keyboard
from player import Player
from cache_manager import CacheManager
from bg_manager import BackgroundManager
from logger import logger


logger.info("程序启动")


WHITING_TIME = 5 * 60    # 空闲时间间隔，单位为秒
PROGRESS_BAR_HEIGHT = 5
PROGRESS_BAR_COLOR_BG = (60, 60, 60)
PROGRESS_BAR_COLOR_FG = (80, 150, 200)
RECOVER_INTERVAL = 2    # 恢复视频模式检测时间


cache_mgr = CacheManager(max_videos=20, min_trigger=10, check_interval=30)

# 初始化背景管理器（放在创建 Player 之前或之后都可以）
bg_manager = BackgroundManager(
    max_images=20,
    min_trigger=5,
    check_interval=3600     # 1小时检查一次
)

running = True
window_open = False
last_time = time.time()     #上次事件时间
last_recover_check = pygame.time.get_ticks()
now_time = time.localtime()
clock = pygame.time.Clock()
progress_rect = None

def draw_progress_bar(_screen, _player):
    """绘制，更新进度条"""
    video_rect = _player.video_rect
    v_bg_rect = _player.v_bg_rect
    bar_x = min(video_rect.x, v_bg_rect.x)
    bar_y = video_rect.bottom
    _bar_width = max(video_rect.width, v_bg_rect.width)
    # 背景
    pygame.draw.rect(_screen, PROGRESS_BAR_COLOR_BG, (bar_x, bar_y, _bar_width, PROGRESS_BAR_HEIGHT))
    # 前景
    if _player.total_frames > 0:
        _progress = _player.current_frame / _player.total_frames
        fill_width = int(_bar_width * _progress)
        pygame.draw.rect(_screen, PROGRESS_BAR_COLOR_FG, (bar_x, bar_y, fill_width, PROGRESS_BAR_HEIGHT))
    return pygame.Rect(bar_x, bar_y, _bar_width, PROGRESS_BAR_HEIGHT)

player = Player(bg_manager)   # 视频播放器
screen = None   # 屏保窗口


def get_wday_zh(wday: int):
    """星期数字到汉字的转换"""
    wday_zh = ["一", "二", "三", "四", "五", "六", "日"]
    return wday_zh[wday]

class EventChecker:
    """事件捕捉器"""
    def __init__(self):
        self.event_occurred = False
        self.running = True

        # 启动监听器
        self.keyboard_listener = keyboard.Listener(
            on_press=lambda k: self._set_event(),
            on_release=lambda k: self._set_event()
        )
        self.mouse_listener = mouse.Listener(
            on_click=lambda _x, _y, b, p: self._set_event(),
            on_move=lambda _x, _y: self._set_event(),
            on_scroll=lambda _x, _y, dx, dy: self._set_event()
        )

        self.keyboard_listener.start()
        self.mouse_listener.start()

    def _set_event(self):
        """标记有事件发生"""
        self.event_occurred = True

    def has_event(self):
        """检查是否有事件（会重置标志）"""
        if self.event_occurred:
            self.event_occurred = False
            return True
        return False

    def stop(self):
        """停止监听"""
        self.keyboard_listener.stop()
        self.mouse_listener.stop()

event_checker = EventChecker()


# 字体大小
button_font_size = int(min(player.screen_width, player.screen_height) * 0.04)
result_font_size = int(min(player.screen_width, player.screen_height) * 0.024)
time_font_size = int(min(player.screen_width, player.screen_height) * 0.28)
date_font_size = int(min(player.screen_width, player.screen_height) * 0.06)

# 字体
button_font = pygame.font.SysFont("microsoft yahei", button_font_size)
result_font = pygame.font.SysFont("microsoft yahei", result_font_size)
time_font = pygame.font.SysFont("microsoft yahei", time_font_size)
date_font = pygame.font.SysFont("microsoft yahei", date_font_size)

# 要绘制的文字
title = result_font.render(player.title, True, (0, 0, 0))
name = result_font.render("up:" + player.name, True, (0, 0, 0))
esc = button_font.render("退出", True, (50, 50, 50))

esc_rect = esc.get_rect(bottomright=(player.screen_width - 20, 40))
title_rect: pygame.rect.Rect | None = None


while running:
    now = time.time()
    if not player.has_video and now - last_recover_check >= RECOVER_INTERVAL:
        last_recover_check = now
        player.try_recover_video()
    # 计时器重置
    if not window_open and event_checker.has_event():
        last_time = time.time()

    # 超过阈值时打开窗口
    elif not window_open and (now - last_time >= WHITING_TIME):
        screen = player.create_window()
        window_open = True

    elif window_open:
        player.update_background()     # 更新屏保背景
        screen.fill((230, 240, 240))    # 屏保默认纯色背景
        screen.blit(player.background,player.bg_rect)   # 绘制屏保背景
        screen.blit(player.v_background, player.v_bg_rect)    # 绘制视频黑色背景

        # 视频播放
        if player.get_frame():
            screen.blit(player.frame, player.video_rect)

            # 视频信息更新
            title_rect = title.get_rect()
            title_rect.x, title_rect.y = (
                player.video_rect.x, player.video_rect.y - title_rect.height - 2)

            name_rect = name.get_rect()
            name_rect.x, name_rect.y = (
                player.video_rect.x, player.video_rect.y + player.video_rect.height + 8)

            screen.blit(name, name_rect)
            screen.blit(title, title_rect)
            progress_rect = draw_progress_bar(screen, player)
        else:
            player.change_video()
            title = result_font.render(player.title, True, (0, 0, 0))
            name = result_font.render("up:" + player.name, True, (0, 0, 0))
            screen.fill((230, 240, 240))
            screen.blit(player.background,player.bg_rect)

        now_time = time.localtime()

        date_img = (
            date_font.render(time.strftime("%Y年%m月%d日, 星期" + get_wday_zh(now_time.tm_wday), now_time),
                             True, (50, 50, 100)))
        date_rect = date_img.get_rect()
        date_rect.center = (player.video_rect.centerx, title_rect.y - date_rect.height // 2 - 2) if title_rect\
            else (player.video_rect.centerx, player.video_rect.y - date_rect.height // 2 - 2)

        time_img = (
            time_font.render(time.strftime("%H:%M", now_time),
                             True, (50, 50, 100)))
        time_rect = time_img.get_rect()
        time_rect.center = (date_rect.centerx, date_rect.y - time_rect.height // 3)

        screen.blit(time_img, time_rect)
        screen.blit(date_img, date_rect)
        screen.blit(esc, esc_rect)
        pygame.display.flip()
        clock.tick(player.fps)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                mods = pygame.key.get_mods()

                # 按下 esc 只关闭窗口
                if event.key == pygame.K_ESCAPE:
                    player.close_window()
                    window_open = False


                # 当屏保打开时按下组合键 ctrl + shift + e 关闭程序
                elif event.key == pygame.K_e and (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_SHIFT):
                    if player.video:
                        player.video.release()
                    cv2.destroyAllWindows()
                    player.close_window()
                    event_checker.stop()
                    cache_mgr.stop()
                    bg_manager.stop()
                    running = False
                    window_open = False
                    print("屏保程序退出")
                    logger.info("屏保程序退出")
                    pygame.quit()
                    sys.exit()

            elif event.type == pygame.QUIT:
                # 关闭窗口
                player.close_window()
                window_open = False

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # 关闭窗口
                if esc_rect.collidepoint(event.pos):
                    player.close_window()
                    window_open = False

                # 更新进度条位置
                elif progress_rect and progress_rect.collidepoint(event.pos):
                    bar_width = progress_rect.width
                    click_x = event.pos[0] - progress_rect.x
                    progress = max(0.0, min(1.0, click_x / bar_width))
                    player.seek_to_progress(progress)
