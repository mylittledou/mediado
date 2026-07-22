import os
import sys
import argparse
import yt_dlp
import signal

is_paused = False
is_stopped = False

def handle_pause(signum, frame):
    global is_paused
    is_paused = not is_paused
    if is_paused:
        print("\n下载已暂停，按Ctrl+C继续")
    else:
        print("\n下载已恢复")

def handle_stop(signum, frame):
    global is_stopped
    is_stopped = True
    print("\n接收到停止信号，正在保存状态...")

class M3U8Downloader:
    def __init__(self, url, output_file="output.mp4", save_path="."):
        self.url = url
        self.output_file = output_file if output_file.endswith(".mp4") else f"{output_file}.mp4"
        self.save_path = save_path
        self.output_path = os.path.join(save_path, self.output_file)

        
        if not os.path.exists(save_path):
            os.makedirs(save_path)
            
    def download(self):
        print(f"开始下载: {self.url}")
        print(f"保存路径: {self.save_path}")
        print(f"输出文件名: {self.output_file}")

        
        def progress_hook(d):
            if d['status'] == 'downloading':
                percent = d.get('_percent_str', 'N/A')
                speed = d.get('_speed_str', 'N/A')
                eta = d.get('_eta_str', 'N/A')
                print(f"\r下载中: 进度 {percent} | 速度 {speed} | 剩余时间 {eta}", end="")
            elif d['status'] == 'finished':
                print("\n下载完成，正在处理/合并...")
        
        ydl_opts = {
            'outtmpl': self.output_path,
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'concurrent_fragment_downloads': 6,
            'source_address': '0.0.0.0', # 强制IPv4
            'progress_hooks': [progress_hook],
            'quiet': True,
            'no_warnings': True,
        }
            
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
            print(f"\n视频已成功下载并保存至: {self.output_path}")
        except KeyboardInterrupt:
            print("\n下载被用户取消。")
        except Exception as e:
            print(f"\n下载过程中发生错误: {e}")

def main():
    parser = argparse.ArgumentParser(description="视频下载器 (支持网页链接与M3U8)")
    parser.add_argument("-u", "--url", required=True, help="视频/网页地址")
    parser.add_argument("-o", "--output", default="output.mp4", help="输出文件名")
    parser.add_argument("-p", "--path", default=".", help="保存路径")

    
    args = parser.parse_args()
    
    downloader = M3U8Downloader(args.url, args.output, args.path)
    downloader.download()

if __name__ == "__main__":
    main()
