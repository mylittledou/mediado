import yt_dlp, time
def h(d):
    print('[HOOK]', d.get('status'), d.get('_percent_str'), d.get('_speed_str'))
ydl_opts={
    'external_downloader': 'aria2c',
    'external_downloader_args': ['-x', '16'],
    'progress_hooks': [h],
    'quiet': False
}
with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download(['https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8'])

