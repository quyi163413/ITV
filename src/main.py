# src/main.py
"""IPTV 智能管理 GUI 工具 - 程序入口"""

import sys
import os
import traceback
from pathlib import Path


def main():
    try:
        # 确保当前目录在 sys.path 中（解决打包后模块找不到的问题）
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
        
        # 如果是打包环境，添加父目录
        if getattr(sys, 'frozen', False):
            # PyInstaller 打包环境
            base_dir = Path(sys.executable).parent
            if str(base_dir) not in sys.path:
                sys.path.insert(0, str(base_dir))
        else:
            # 开发环境
            base_dir = current_dir.parent
            if str(base_dir) not in sys.path:
                sys.path.insert(0, str(base_dir))
        
        from PySide6.QtWidgets import QApplication
        from PySide6.QtCore import Qt
        from src.gui.main_window import IPTVMainWindow
        from src.utils.logger_handler import setup_gui_logging

        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QApplication(sys.argv)
        app.setApplicationName("IPTV 智能管理工具")
        app.setOrganizationName("IPTVCollector")
        
        setup_gui_logging()
        
        window = IPTVMainWindow()
        window.show()
        
        sys.exit(app.exec())
    
    except Exception as e:
        error_msg = traceback.format_exc()
        try:
            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_msg)
        except:
            pass
        
        print("=" * 60)
        print("程序启动失败！")
        print("错误信息已写入 error.log")
        print("=" * 60)
        print(error_msg)
        input("按 Enter 键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
