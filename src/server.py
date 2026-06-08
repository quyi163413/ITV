#!/usr/bin/env python3
# src/server.py
# HTTP 静态文件服务器模块

import os
import sys
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

# 将项目根目录添加到系统路径，以便导入 config 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import OUTPUT_DIR, WEB_SERVER_HOST, WEB_SERVER_PORT
from src.logger import logger

def start_file_server():
    """在 OUTPUT_DIR 目录启动 HTTP 文件服务器"""
    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 切换到输出目录，让服务器以该目录为根目录
    os.chdir(OUTPUT_DIR)
    
    # 自定义请求处理器，增加对 CORS 的支持，方便跨域访问
    class CORSRequestHandler(SimpleHTTPRequestHandler):
        def end_headers(self):
            self.send_header('Access-Control-Allow-Origin', '*')
            super().end_headers()
        
        def log_message(self, format, *args):
            # 使用统一的 logger 记录访问日志
            logger.info(f"HTTP: {self.address_string()} - {format % args}")
    
    # 启动 HTTP 服务器
    server = HTTPServer((WEB_SERVER_HOST, WEB_SERVER_PORT), CORSRequestHandler)
    logger.info(f"📁 HTTP 文件服务器已启动，提供文件服务: {OUTPUT_DIR}")
    logger.info(f"🌐 访问地址: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/")
    logger.info(f"📄 播放列表地址: http://{WEB_SERVER_HOST}:{WEB_SERVER_PORT}/tv.m3u")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("⏹️ HTTP 服务器已停止")
        server.shutdown()

if __name__ == "__main__":
    start_file_server()
