# src/main.py
"""IPTV 智能管理 GUI 工具 - 程序入口"""

import sys
import traceback
from pathlib import Path

# 将项目根目录添加到 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    try:
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
        # 将错误写入 error.log 文件
        error_msg = traceback.format_exc()
        try:
            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_msg)
        except:
            pass
        
        # 在控制台输出错误并等待用户按键
        print("=" * 60)
        print("程序启动失败！")
        print("错误信息已写入 error.log")
        print("=" * 60)
        print(error_msg)
        input("按 Enter 键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
