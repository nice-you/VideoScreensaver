import aiohttp, random
from bilibili_api import video, video_zone, sync
from bilibili_api.video import VideoQuality
from saver import VideoSaver


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Referer': 'https://www.bilibili.com',  # 防盗链，不加会403
}

v_saver = VideoSaver()

ZONES = {1: "动画",
         4: "游戏",
         17: "单机游戏",
         36: "知识",
         119: "鬼畜",
         155: "时尚",
         160: "生活",
         181: "影视",
         211: "音乐",
         217:"舞蹈"}

async def download_random_video():
    """随机下载视频"""
    tid = random.choice(list(ZONES.keys()))
    top10_list = await video_zone.get_zone_top10(tid=tid, day=7)
    lucky_video = random.choice(top10_list)
    bvid = lucky_video.get("bvid")

    vd = video.Video(bvid)
    download_url_data = await vd.get_download_url(page_index=0)
    detecter = video.VideoDownloadURLDataDetecter(download_url_data)
    best_streams = detecter.detect_best_streams(
        video_max_quality=VideoQuality._1080P,
        video_min_quality=VideoQuality._360P
    )
    best_video_steam = best_streams[0]
    video_url = best_video_steam.url

    async with aiohttp.ClientSession() as session:
        async with session.get(video_url, headers=headers) as resp:
            # resp.status == 200 表示成功
            if resp.status == 200:
                # 读取所有二进制数据
                video_data = await resp.read()

                # 写入本地文件
                v_saver.save_video(bvid, video_data)
                return bvid
            else:
                return None

async def get_video_info(_bvid):
    """获取视频信息"""
    if not _bvid:
        return None
    v = video.Video(_bvid)
    info = await v.get_info()
    result =dict(
        title = info.get('title', '无标题'),
        name = info.get('owner', {}).get('name', "未知"))
    return result


if __name__ == "__main__":
    sync(download_random_video())
    v_saver.clear()
