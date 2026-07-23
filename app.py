#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
M3U8视频下载器 - Web UI版本
基于Flask框架，提供网页界面用于下载m3u8视频
"""

import os
import sys
import time
import json
import threading
import requests
import ffmpeg
import tempfile
from urllib.parse import urljoin
from flask import Flask, render_template, request, jsonify, send_from_directory, session, redirect, url_for

# 添加当前目录到系统路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入原有的下载器功能
import subprocess

def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except:
        return False



app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'downloads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

# 会话配置
app.secret_key = os.environ.get('SECRET_KEY', 'default_secret_key')  # 会话密钥，生产环境建议通过环境变量设置

# 认证配置
app.config['AUTH_USERNAME'] = os.environ.get('AUTH_USERNAME', 'admin')  # 用户名，通过环境变量设置
app.config['AUTH_PASSWORD'] = os.environ.get('AUTH_PASSWORD', 'password')  # 密码，通过环境变量设置

# 确保下载目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# 确保temp目录存在
temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
os.makedirs(temp_dir, exist_ok=True)

# 任务持久化相关
TASKS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks.json')

# 下载任务管理
download_tasks = {}

# 从文件加载任务
def load_tasks():
    """从JSON文件加载任务"""
    global download_tasks
    if os.path.exists(TASKS_FILE):
        # 如果文件为空（0字节），直接返回，不要尝试解析
        if os.path.getsize(TASKS_FILE) == 0:
            print("tasks.json 文件为空，初始化为空列表。")
            return
            
        try:
            with open(TASKS_FILE, 'r', encoding='utf-8') as f:
                saved_tasks = json.load(f)
                # 只加载已完成的任务，因为正在下载的任务在重启后无法继续
                for task_data in saved_tasks:
                    if task_data['status'] == 'completed':
                        # 创建一个简化的任务对象，只包含必要的信息
                        task = type('Task', (), {})
                        for key, value in task_data.items():
                            setattr(task, key, value)
                        # 为每个任务创建独立的to_dict方法，避免闭包问题
                        task.to_dict = lambda data=task_data: data.copy()
                        download_tasks[task_data['task_id']] = task
                print(f"从文件加载了 {len(download_tasks)} 个已完成任务")
        except Exception as e:
            print(f"加载任务失败: {e}")

# 保存任务到文件
def save_tasks():
    """将任务保存到JSON文件"""
    global download_tasks
    try:
        # 只保存已完成的任务
        completed_tasks = [task.to_dict() for task in download_tasks.values() if task.status == 'completed']
        with open(TASKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(completed_tasks, f, ensure_ascii=False, indent=2)
        print(f"保存了 {len(completed_tasks)} 个已完成任务到文件")
    except Exception as e:
        print(f"保存任务失败: {e}")

class DownloadTask:
    """下载任务类"""
    def __init__(self, task_id, url, output_file, save_path=None, test_download=False):
        self.task_id = task_id
        self.url = url
        self.output_file = output_file if output_file.endswith('.mp4') else f"{output_file}.mp4"
        
        # 处理保存路径
        if save_path:
            # 修改：无论路径是否以/开头，都将其视为相对路径处理
            # 移除斜杠前缀（如果有），将其视为相对路径
            stripped_path = save_path.lstrip('/')
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self.save_path = os.path.join(base_dir, stripped_path)
            
            # 添加调试日志
            print(f"[DEBUG] 原始保存路径: {save_path}")
            print(f"[DEBUG] 操作系统: {os.name}")
            print(f"[DEBUG] 使用相对路径处理: 基础目录={base_dir}, 剥离斜杠后路径={stripped_path}, 最终路径={self.save_path}")
        else:
            # 默认使用应用程序的downloads文件夹
            self.save_path = app.config['UPLOAD_FOLDER']
            # 确保是基于应用程序所在目录的绝对路径
            self.save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.save_path)
        
        # 确保路径使用正确的分隔符
        self.save_path = os.path.normpath(self.save_path)
        

        self.test_download = test_download  # 测试下载模式
        self.status = 'pending'  # pending, downloading, completed, failed, paused
        self.progress = 0
        self.speed = 0
        self.total_segments = 0
        self.downloaded_segments = 0
        self.start_time = None
        self.end_time = None
        self.error_message = ""
        # 新增：体积进度相关
        self.size_progress = 0
        self.total_size = 0
        self.downloaded_size = 0
        
        # 控制标志
        self.pause_flag = False
        self.stop_flag = False
        
        # 临时文件信息
        self.temp_dir = None
        self.downloaded_files = []
        
        # 确保保存路径存在
        try:
            os.makedirs(self.save_path, exist_ok=True)
            print(f"保存路径: {self.save_path}")
        except Exception as e:
            print(f"创建保存路径失败: {e}")
            # 使用默认路径作为备选
            self.save_path = os.path.abspath(app.config['UPLOAD_FOLDER'])
            os.makedirs(self.save_path, exist_ok=True)
            print(f"使用默认保存路径: {self.save_path}")
        
        self.output_path = os.path.join(self.save_path, self.output_file)
        print(f"最终输出路径: {self.output_path}")
        
        # 启动下载线程
        self.thread = threading.Thread(target=self.download)
        self.thread.daemon = True
        self.thread.start()
    
    def download(self):
        """执行下载 (使用 yt-dlp)"""
        import yt_dlp
        try:
            self.status = 'downloading'
            self.start_time = time.time()
            
            def progress_hook(d):
                if self.stop_flag:
                    raise Exception("下载已停止")
                while self.pause_flag and not self.stop_flag:
                    self.status = 'paused'
                    time.sleep(0.5)
                self.status = 'downloading'
                
                if d['status'] == 'downloading':
                    # 恢复到最早版本的经典逻辑，完全信任 yt-dlp 的自带估算值
                    # 1. 进度百分比
                    if '_percent_str' in d:
                        import re
                        percent_str = re.sub(r'\x1b\[[0-9;]*m', '', d['_percent_str']).replace('%', '').strip()
                        try:
                            self.progress = float(percent_str)
                            self.size_progress = self.progress
                        except ValueError:
                            pass
                            
                    # 2. 速度
                    speed = d.get('speed')
                    if speed:
                        self.speed = speed / 1024  # KB/s
                    elif '_speed_str' in d:
                        import re
                        speed_str = re.sub(r'\x1b\[[0-9;]*m', '', d['_speed_str']).strip()
                        if 'KiB/s' in speed_str:
                            try:
                                self.speed = float(speed_str.replace('KiB/s', '').strip())
                            except ValueError:
                                pass
                        elif 'MiB/s' in speed_str:
                            try:
                                self.speed = float(speed_str.replace('MiB/s', '').strip()) * 1024
                            except ValueError:
                                pass

                    # 3. 核心：完全信赖 yt-dlp 后台计算的真实数据，让前端与终端输出保持 100% 一致
                    # 无论它怎么跳动，至少它是最准的！
                    downloaded = d.get('downloaded_bytes', 0)
                    total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                    
                    if downloaded > 0:
                        self.downloaded_size = downloaded
                        
                    if total > 0:
                        self.total_size = total
                        
                    # 如果 yt-dlp 没给字典，则尝试解析字符串作备用 (比如控制台输出的 ~ 522.94MiB)
                    if self.total_size == 0 and '_total_bytes_str' in d:
                        import re
                        m = re.search(r'([\d\.]+)(K|M|G)?i?B', d['_total_bytes_str'].replace('~', '').strip())
                        if m:
                            val, unit = float(m.group(1)), m.group(2)
                            if unit == 'K': val *= 1024
                            elif unit == 'M': val *= 1048576
                            elif unit == 'G': val *= 1073741824
                            self.total_size = val
                            
                    if self.downloaded_size == 0 and '_downloaded_bytes_str' in d:
                        import re
                        m = re.search(r'([\d\.]+)(K|M|G)?i?B', d['_downloaded_bytes_str'].replace('~', '').strip())
                        if m:
                            val, unit = float(m.group(1)), m.group(2)
                            if unit == 'K': val *= 1024
                            elif unit == 'M': val *= 1048576
                            elif unit == 'G': val *= 1073741824
                            self.downloaded_size = val

                    # 4. 片段
                    if 'fragment_count' in d:
                        self.total_segments = d.get('fragment_count', 0)
                    if 'fragment_index' in d:
                        self.downloaded_segments = d.get('fragment_index', 0)
                    
                    if self.total_segments == 0 and d.get('info_dict') and d['info_dict'].get('fragment_count'):
                        self.total_segments = d['info_dict']['fragment_count']
                        
                    if self.total_segments > 0 and self.downloaded_segments == 0 and self.progress > 0:
                        self.downloaded_segments = int(self.total_segments * (self.progress / 100.0))
                            
            ydl_opts = {
                'outtmpl': self.output_path,
                'format': 'bestvideo+bestaudio/best',
                'merge_output_format': 'mp4',
                'concurrent_fragment_downloads': 16,
                'progress_hooks': [progress_hook],
                'quiet': True,
                'no_warnings': True,
                'extractor_args': {'generic': {'impersonate': ['']}},
                'impersonate': 'chrome',
            }

            # 使用临时文件测试是否可写
            import os
            os.makedirs(os.path.dirname(self.output_path), exist_ok=True)
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([self.url])
                
            self.status = 'completed'
            self.progress = 100
            self.end_time = time.time()
            
            # 使用真实的本地文件大小覆盖之前的预估大小，因为 yt-dlp 下载多轨道（音视频分离）时，
            # 最后一次汇报的大小可能仅仅是最后下载的音频轨的大小，导致最终大小偏小。
            if os.path.exists(self.output_path):
                self.total_size = os.path.getsize(self.output_path)
            
            save_tasks()
            
        except Exception as e:
            if not self.stop_flag:
                self.status = 'failed'
                self.error_message = str(e)
                self.end_time = time.time()
                print(f"下载失败: {e}")
                import traceback
                traceback.print_exc()

    def pause(self):
        """暂停下载"""
        if self.status == 'downloading':
            self.pause_flag = True
            self.status = 'paused'
    
    def resume(self):
        """恢复下载"""
        if self.status == 'paused':
            self.pause_flag = False
            self.status = 'downloading'
    
    def stop(self):
        """停止下载"""
        self.stop_flag = True
        self.pause_flag = False  # 确保能退出暂停状态
        self.status = 'failed'
        self.error_message = "下载已停止"
        self.end_time = time.time()
    
    def delete(self):
        """删除任务"""
        # 停止下载
        self.stop()
        
        # 清理临时文件
        if self.temp_dir:
            import shutil
            try:
                shutil.rmtree(self.temp_dir)
            except:
                pass
        
        # 删除输出文件（如果存在）
        if os.path.exists(self.output_path):
            try:
                os.remove(self.output_path)
            except:
                pass
        
        # 从任务列表中移除
        if self.task_id in download_tasks:
            del download_tasks[self.task_id]
    
    def get_video_duration(self):
        """获取视频时长"""
        try:
            import subprocess
            import re
            
            # 使用ffmpeg获取视频时长
            cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', self.output_path]
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False)
            
            if result.returncode == 0:
                duration = float(result.stdout.strip())
                # 格式化时长为 HH:MM:SS 或 MM:SS
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                
                if hours > 0:
                    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                else:
                    return f"{minutes:02d}:{seconds:02d}"
        except Exception as e:
            print(f"获取视频时长失败: {e}")
        return None
    
    def to_dict(self):
        """转换为字典格式"""
        # 获取视频时长
        video_duration = self.get_video_duration() if self.status == 'completed' else None
        
        return {
            'task_id': self.task_id,
            'url': self.url,
            'output_file': self.output_file,
            'status': self.status,
            'progress': self.progress,
            'speed': self.speed,
            'total_segments': self.total_segments,
            'downloaded_segments': self.downloaded_segments,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'error_message': self.error_message,
            'output_path': self.output_path,
            'video_duration': video_duration,
            # 新增体积进度相关字段
            'size_progress': self.size_progress,
            'total_size': self.total_size,
            'downloaded_size': self.downloaded_size
        }

# 认证装饰器
def login_required(f):
    """保护需要认证的路由"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    """主页"""
    # 检查ffmpeg和aria2是否可用
    has_ffmpeg = check_ffmpeg()
    
    return render_template('index.html', has_ffmpeg=has_ffmpeg)

# 登录路由
@app.route('/login', methods=['GET', 'POST'])
def login():
    """登录页面"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # 验证用户名和密码
        if username == app.config['AUTH_USERNAME'] and password == app.config['AUTH_PASSWORD']:
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='用户名或密码错误')
    
    return render_template('login.html')

# 登出路由
@app.route('/logout')
def logout():
    """登出"""
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# 应用启动时加载任务
load_tasks()

@app.route('/download', methods=['POST'])
@login_required
def start_download():
    """开始下载"""
    try:
        url = request.form.get('url')
        output_file = request.form.get('output_file', 'output')
        save_path = request.form.get('save_path')

        test_download = request.form.get('test_download', 'false') == 'true'
        
        if not url:
            return jsonify({'error': '请输入m3u8地址'}), 400
        
        # 生成任务ID
        task_id = f"task_{int(time.time() * 1000)}"
        
        # 验证URL格式
        import re
        if not re.match(r'^https?://', url):
            return jsonify({'error': '请输入有效的HTTP/HTTPS URL'}), 400
        
        # 创建下载任务
        task = DownloadTask(task_id, url, output_file, save_path, test_download)
        download_tasks[task_id] = task
        
        return jsonify({'task_id': task_id})
    except Exception as e:
        print(f"下载请求处理失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'请求处理失败: {str(e)}'}), 500

@app.route('/status/<task_id>')
@login_required
def get_status(task_id):
    """获取下载状态"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = download_tasks[task_id]
    return jsonify(task.to_dict())

@app.route('/downloads/<filename>')
@login_required
def download_file(filename):
    """下载文件"""
    import os
    
    # 查找任务对应的保存路径
    save_path = app.config['UPLOAD_FOLDER']
    found = False
    
    # 1. 首先在正在运行的任务中查找
    for task in download_tasks.values():
        if task.output_file == filename:
            save_path = task.save_path
            found = True
            break
    
    # 2. 如果没有找到，尝试搜索所有可能的下载路径
    if not found:
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 搜索路径列表，按照优先级排序
        search_paths = [
            # 默认下载目录
            os.path.join(script_dir, app.config['UPLOAD_FOLDER']),
            # 当前目录下的downloads文件夹
            os.path.join(script_dir, 'downloads'),
            # 上级目录下的downloads文件夹
            os.path.join(script_dir, '..', 'downloads'),
            # 脚本所在目录本身
            script_dir
        ]
        
        # 遍历搜索路径，查找文件
        for path in search_paths:
            # 确保路径是绝对路径
            abs_path = os.path.abspath(path)
            file_path = os.path.join(abs_path, filename)
            if os.path.exists(file_path):
                save_path = abs_path
                found = True
                break
        
        # 3. 如果仍未找到，尝试递归搜索当前目录下所有可能的文件
        if not found:
            print(f"[DEBUG] 开始递归搜索文件: {filename}")
            for root, dirs, files in os.walk(script_dir):
                # 跳过隐藏目录和node_modules等大型目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '.git']]
                if filename in files:
                    save_path = root
                    found = True
                    print(f"[DEBUG] 递归搜索找到文件: {os.path.join(root, filename)}")
                    break
    
    # 确保路径是绝对路径
    if not os.path.isabs(save_path):
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), save_path)
    
    print(f"[DEBUG] 下载文件: {filename}")
    print(f"[DEBUG] 保存路径: {save_path}")
    
    # 检查文件是否存在
    file_path = os.path.join(save_path, filename)
    if not os.path.exists(file_path):
        print(f"[ERROR] 文件不存在: {file_path}")
        # 返回更详细的错误信息，帮助调试
        return jsonify({'error': f'文件不存在: {file_path}', 'searched_paths': search_paths}), 404
    
    # 设置正确的MIME类型，确保浏览器能正确播放视频
    from mimetypes import guess_type
    mime_type, _ = guess_type(file_path)
    if not mime_type:
        mime_type = 'application/octet-stream'
    
    # 移除as_attachment=True，允许浏览器直接播放视频
    return send_from_directory(save_path, filename, mimetype=mime_type)

@app.route('/tasks')
@login_required
def get_tasks():
    """获取所有任务"""
    return jsonify([task.to_dict() for task in download_tasks.values()])

@app.route('/pause/<task_id>', methods=['POST'])
@login_required
def pause_task(task_id):
    """暂停下载任务"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = download_tasks[task_id]
    task.pause()
    return jsonify({'status': 'success', 'new_status': task.status})

@app.route('/resume/<task_id>', methods=['POST'])
@login_required
def resume_task(task_id):
    """恢复下载任务"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = download_tasks[task_id]
    task.resume()
    return jsonify({'status': 'success', 'new_status': task.status})

@app.route('/stop/<task_id>', methods=['POST'])
@login_required
def stop_task(task_id):
    """停止下载任务"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = download_tasks[task_id]
    task.stop()
    return jsonify({'status': 'success', 'new_status': task.status})

@app.route('/delete/<task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    """删除下载任务"""
    if task_id not in download_tasks:
        return jsonify({'error': '任务不存在'}), 404
    
    task = download_tasks[task_id]
    
    # 1. 执行对象特定的删除逻辑
    if hasattr(task, 'delete'):
        task.delete()
    else:
        # 如果是重启后从 tasks.json 加载的简易对象（没有 delete 方法）
        if hasattr(task, 'output_path') and os.path.exists(task.output_path):
            try:
                os.remove(task.output_path)
            except Exception as e:
                print(f"删除物理文件失败: {e}")
        if task_id in download_tasks:
            del download_tasks[task_id]
            
    # 2. 统一清理缩略图
    output_file = getattr(task, 'output_file', None)
    if output_file:
        thumbnails_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbnails')
        thumbnail_path = os.path.join(thumbnails_dir, f"{output_file}.jpg")
        if os.path.exists(thumbnail_path):
            try:
                os.remove(thumbnail_path)
            except:
                pass

    # 保存任务到文件
    save_tasks()
    return jsonify({'status': 'success'})

@app.route('/rename', methods=['POST'])
@login_required
def rename_file():
    """重命名文件"""
    try:
        task_id = request.form.get('task_id')
        old_filename = request.form.get('old_filename')
        new_filename = request.form.get('new_filename')
        
        if not task_id or not old_filename or not new_filename:
            return jsonify({'error': '缺少必要参数'}), 400
        
        # 查找任务
        if task_id not in download_tasks:
            return jsonify({'error': '任务不存在'}), 404
        
        task = download_tasks[task_id]
        
        # 验证文件名是否匹配
        if task.output_file != old_filename:
            return jsonify({'error': '文件名不匹配'}), 400
        
        # 获取文件路径
        old_path = task.output_path
        new_path = os.path.join(os.path.dirname(old_path), new_filename)
        
        # 检查新文件名是否已存在
        if os.path.exists(new_path):
            return jsonify({'error': '新文件名已存在'}), 400
        
        # 执行重命名操作
        os.rename(old_path, new_path)
        
        # 更新任务的output_file和output_path属性
        task.output_file = new_filename
        task.output_path = new_path
        
        # 删除旧的缩略图（如果存在）
        thumbnails_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbnails')
        old_thumbnail_path = os.path.join(thumbnails_dir, f"{old_filename}.jpg")
        if os.path.exists(old_thumbnail_path):
            os.remove(old_thumbnail_path)
        
        # 保存任务到文件
        save_tasks()
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"重命名文件失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'重命名失败: {str(e)}'}), 500

@app.route('/thumbnails/<filename>')
@login_required
def get_thumbnail(filename):
    """获取视频缩略图"""
    import os
    import subprocess
    import tempfile
    
    # 查找视频文件
    save_path = app.config['UPLOAD_FOLDER']
    found = False
    
    # 首先在正在运行的任务中查找
    for task in download_tasks.values():
        if task.output_file == filename:
            # 使用getattr获取save_path属性，如果不存在则使用默认值
            save_path = getattr(task, 'save_path', app.config['UPLOAD_FOLDER'])
            found = True
            break
    
    # 如果没有找到，尝试搜索所有可能的下载路径
    if not found:
        # 获取当前脚本所在目录
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 搜索路径列表，按照优先级排序
        search_paths = [
            # 默认下载目录
            os.path.join(script_dir, app.config['UPLOAD_FOLDER']),
            # 当前目录下的downloads文件夹
            os.path.join(script_dir, 'downloads'),
            # 上级目录下的downloads文件夹
            os.path.join(script_dir, '..', 'downloads'),
            # 脚本所在目录本身
            script_dir
        ]
        
        # 遍历搜索路径，查找文件
        for path in search_paths:
            # 确保路径是绝对路径
            abs_path = os.path.abspath(path)
            file_path = os.path.join(abs_path, filename)
            if os.path.exists(file_path):
                save_path = abs_path
                found = True
                break
        
        # 3. 如果仍未找到，尝试递归搜索当前目录下所有可能的文件
        if not found:
            print(f"[DEBUG] 开始递归搜索文件: {filename}")
            for root, dirs, files in os.walk(script_dir):
                # 跳过隐藏目录和node_modules等大型目录
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '.git']]
                if filename in files:
                    save_path = root
                    found = True
                    print(f"[DEBUG] 递归搜索找到文件: {os.path.join(root, filename)}")
                    break
    
    # 确保路径是绝对路径
    if not os.path.isabs(save_path):
        save_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), save_path)
    
    # 检查文件是否存在
    video_path = os.path.join(save_path, filename)
    if not os.path.exists(video_path):
        print(f"[ERROR] 文件不存在: {video_path}")
        return jsonify({'error': '文件不存在'}), 404
    
    # 确保thumbnails目录存在
    thumbnails_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'thumbnails')
    os.makedirs(thumbnails_dir, exist_ok=True)
    
    # 生成缩略图文件名
    thumbnail_path = os.path.join(thumbnails_dir, f"{filename}.jpg")
    
    # 如果缩略图已存在，直接返回
    if os.path.exists(thumbnail_path):
        return send_from_directory(thumbnails_dir, f"{filename}.jpg")
    
    try:
        # 1. 获取视频时长
        duration_cmd = ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', video_path]
        duration_result = subprocess.run(duration_cmd, capture_output=True, text=True, shell=False)
        
        if duration_result.returncode != 0:
            print(f"[ERROR] 获取视频时长失败: {duration_result.stderr}")
            # 使用默认的第一帧
            thumbnail_cmd = ['ffmpeg', '-i', video_path, '-ss', '00:00:01', '-vframes', '1', '-q:v', '2', thumbnail_path]
        else:
            duration = float(duration_result.stdout.strip())
            # 选择中间一帧
            middle_time = duration / 2
            # 转换为HH:MM:SS格式
            hours = int(middle_time // 3600)
            minutes = int((middle_time % 3600) // 60)
            seconds = middle_time % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
            
            # 2. 生成缩略图
            thumbnail_cmd = ['ffmpeg', '-i', video_path, '-ss', time_str, '-vframes', '1', '-q:v', '2', thumbnail_path]
        
        result = subprocess.run(thumbnail_cmd, capture_output=True, text=True, shell=False)
        
        if result.returncode != 0:
            print(f"[ERROR] 生成缩略图失败: {result.stderr}")
            # 返回默认图片
            return send_from_directory('static', 'default_thumbnail.jpg'), 200
        
        # 返回生成的缩略图
        return send_from_directory(thumbnails_dir, f"{filename}.jpg")
    except Exception as e:
        print(f"[ERROR] 生成缩略图时发生异常: {e}")
        # 返回默认图片
        return send_from_directory('static', 'default_thumbnail.jpg'), 200

@app.route('/static/<path:filename>')
def static_files(filename):
    """静态文件服务"""
    return send_from_directory('static', filename)

if __name__ == '__main__':
    # 生产环境建议使用gunicorn或uwsgi
    app.run(host='0.0.0.0', port=5000, debug=True)
