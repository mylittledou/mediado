import os
import sys
import time
import requests
import tempfile
import json
from urllib.parse import urljoin
from tqdm import tqdm
import ffmpeg
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess

# 检查ffmpeg是否安装
def check_ffmpeg():
    try:
        result = os.system("ffmpeg -version >nul 2>&1")
        return result == 0
    except:
        return False

# 检查aria2是否安装
def check_aria2():
    try:
        result = os.system("aria2c --version >nul 2>&1")
        return result == 0
    except:
        return False

class M3U8DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("M3U8视频下载器")
        self.root.geometry("700x500")
        
        # 检查ffmpeg
        if not check_ffmpeg():
            error_msg = """未检测到ffmpeg！\n\n"""
            error_msg += "ffmpeg是视频处理的必要组件，必须先安装ffmpeg才能使用本工具。\n\n"
            error_msg += "安装方法：\n"
            error_msg += "1. Windows系统：\n"
            error_msg += "   - 下载地址：https://www.gyan.dev/ffmpeg/builds/\n"
            error_msg += "   - 解压到C:/ffmpeg\n"
            error_msg += "   - 将C:/ffmpeg/bin添加到系统环境变量\n"
            error_msg += "   - 重启应用程序\n\n"
            error_msg += "2. macOS系统：\n"
            error_msg += "   - 安装Homebrew：/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"\n"
            error_msg += "   - 运行：brew install ffmpeg\n\n"
            error_msg += "3. Linux系统：\n"
            error_msg += "   - Ubuntu/Debian：sudo apt install ffmpeg\n"
            error_msg += "   - CentOS/RHEL：sudo yum install ffmpeg\n\n"
            error_msg += "详细安装说明请查看：INSTALL_FFMPEG.md"
            
            messagebox.showerror("错误 - 缺少ffmpeg", error_msg)
            self.root.destroy()
            return
        
        # 初始化变量
        self.is_paused = False
        self.is_downloading = False
        self.download_thread = None
        self.downloader = None
        
        # 创建UI组件
        self.create_widgets()
        
    def create_widgets(self):
        # URL输入
        tk.Label(self.root, text="视频/网页地址:").pack(pady=5)
        self.url_entry = tk.Entry(self.root, width=80)
        self.url_entry.pack(pady=5)
        
        # 输出文件名
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Label(frame, text="输出文件名:").pack(side=tk.LEFT, padx=5)
        self.filename_entry = tk.Entry(frame, width=50)
        self.filename_entry.pack(side=tk.LEFT, padx=5)
        self.filename_entry.insert(0, "output.mp4")
        
        # 保存路径
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        tk.Label(frame, text="保存路径:").pack(side=tk.LEFT, padx=5)
        self.path_entry = tk.Entry(frame, width=55)
        self.path_entry.pack(side=tk.LEFT, padx=5)
        self.path_entry.insert(0, os.getcwd())
        tk.Button(frame, text="浏览", command=self.browse_path).pack(side=tk.LEFT, padx=5)
        
        # aria2选项
        frame = tk.Frame(self.root)
        frame.pack(pady=5)
        self.use_aria2_var = tk.BooleanVar()
        self.use_aria2_var.set(False)
        tk.Checkbutton(frame, text="使用aria2下载引擎（需要已安装aria2）", variable=self.use_aria2_var).pack(side=tk.LEFT, padx=5)
        if not check_aria2():
            tk.Label(frame, text="（未检测到aria2）", fg="red").pack(side=tk.LEFT, padx=5)
        
        # 控制按钮
        frame = tk.Frame(self.root)
        frame.pack(pady=20)
        self.download_btn = tk.Button(frame, text="开始下载", command=self.start_download, width=15, height=2)
        self.download_btn.pack(side=tk.LEFT, padx=10)
        self.pause_btn = tk.Button(frame, text="暂停", command=self.toggle_pause, width=15, height=2, state=tk.DISABLED)
        self.pause_btn.pack(side=tk.LEFT, padx=10)
        self.stop_btn = tk.Button(frame, text="停止", command=self.stop_download, width=15, height=2, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=10)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.root, variable=self.progress_var, length=600, mode='determinate')
        self.progress_bar.pack(pady=10)
        
        # 状态信息
        self.status_var = tk.StringVar()
        self.status_var.set("就绪")
        self.status_label = tk.Label(self.root, textvariable=self.status_var)
        self.status_label.pack(pady=5)
        
        # 下载速度
        self.speed_var = tk.StringVar()
        self.speed_var.set("速度: 0 KB/s")
        self.speed_label = tk.Label(self.root, textvariable=self.speed_var)
        self.speed_label.pack(pady=5)
        
        # 已下载信息
        self.downloaded_var = tk.StringVar()
        self.downloaded_var.set("已下载: 0 个片段")
        self.downloaded_label = tk.Label(self.root, textvariable=self.downloaded_var)
        self.downloaded_label.pack(pady=5)
        
        # 日志文本框和滚动条
        tk.Label(self.root, text="日志:").pack(pady=5)
        log_frame = tk.Frame(self.root)
        log_frame.pack(pady=5, fill=tk.BOTH, expand=True)
        
        scrollbar = tk.Scrollbar(log_frame, orient="vertical")
        self.log_text = tk.Text(log_frame, height=12, width=85, yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
        
        # 使用grid布局确保滚动条正常工作
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        
        self.log_text.config(state=tk.DISABLED)
    
    def browse_path(self):
        """浏览保存路径"""
        path = filedialog.askdirectory()
        if path:
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
    
    def log(self, message):
        """添加日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.root.update_idletasks()
    
    def toggle_pause(self):
        """暂停/恢复下载"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.config(text="恢复")
            self.status_var.set("下载已暂停")
            self.log("下载已暂停")
        else:
            self.pause_btn.config(text="暂停")
            self.status_var.set("正在恢复下载")
            self.log("正在恢复下载")
    
    def stop_download(self):
        """停止下载"""
        self.is_downloading = False
        self.status_var.set("正在停止下载...")
        self.log("正在停止下载...")
    
    def start_download(self):
        """开始下载"""
        url = self.url_entry.get().strip()
        filename = self.filename_entry.get().strip()
        save_path = self.path_entry.get().strip()
        
        if not url:
            messagebox.showerror("错误", "请输入M3U8地址")
            return
        
        if not filename:
            messagebox.showerror("错误", "请输入输出文件名")
            return
        
        if not os.path.exists(save_path):
            messagebox.showerror("错误", "保存路径不存在")
            return
        
        # 更新UI状态
        self.download_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.NORMAL)
        self.is_downloading = True
        self.is_paused = False
        
        # 开始下载
        self.log("开始下载...")
        self.status_var.set("正在下载m3u8文件")
        
        # 在新线程中执行下载，避免阻塞UI
        import threading
        self.download_thread = threading.Thread(target=self.download, args=(url, filename, save_path))
        self.download_thread.daemon = True
        self.download_thread.start()
    
    def download(self, url, filename, save_path):
        """下载逻辑"""
        import yt_dlp
        output_path = os.path.join(save_path, filename)
        try:
            self.status_var.set("正在下载")
            self.log("开始使用 yt-dlp 下载...")
            
            def progress_hook(d):
                if not self.is_downloading:
                    raise Exception("下载已停止")
                while self.is_paused and self.is_downloading:
                    time.sleep(0.5)
                
                if d['status'] == 'downloading':
                    percent_str = d.get('_percent_str', 'N/A')
                    # strip ANSI escape sequences that yt-dlp might output
                    import re
                    percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                    
                    try:
                        p = float(percent_str.replace('%','').strip())
                        self.progress_var.set(p)
                    except:
                        pass
                        
                    speed = d.get('_speed_str', 'N/A')
                    speed = re.sub(r'\x1b\[[0-9;]*m', '', speed)
                    self.speed_var.set(f"速度: {speed}")
                    
                    self.status_var.set(f"下载中: {percent_str}")
                    
                elif d['status'] == 'finished':
                    self.status_var.set("下载完成，正在合并...")
                    self.log("下载完成，正在合并...")
            
            ydl_opts = {
                'outtmpl': output_path,
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
            }
            if self.use_aria2_var.get():
                ydl_opts['external_downloader'] = 'aria2c'
                ydl_opts['external_downloader_args'] = ['-x16', '-s16', '-k1M']
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
                
            if self.is_downloading:
                self.status_var.set("下载成功")
                self.log(f"视频已成功下载并保存至: {output_path}")
                self.progress_var.set(100)
            
        except Exception as e:
            if self.is_downloading:
                self.status_var.set("下载失败")
                self.log(f"下载发生错误: {e}")
        finally:
            self.is_downloading = False
            self.download_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.DISABLED)

if __name__ == "__main__":
    main()
