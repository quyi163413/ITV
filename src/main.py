# src/main.py
"""IPTV 智能管理 GUI 工具 - 程序入口"""

import sys
import traceback
from pathlib import Path

# 处理打包后的路径问题
if getattr(sys, 'frozen', False):
    base_path = Path(sys._MEIPASS)
else:
    base_path = Path(__file__).parent.parent

# 将 base_path 添加到 sys.path 的最前面
if str(base_path) not in sys.path:
    sys.path.insert(0, str(base_path))

# 调试：将 sys.path 写入文件，方便排查
try:
    with open("path_debug.log", "w", encoding="utf-8") as f:
        f.write(f"base_path: {base_path}\n")
        f.write(f"sys.path: {sys.path}\n")
        f.write(f"frozen: {getattr(sys, 'frozen', False)}\n")
        # 检查 src 目录是否存在
        src_dir = base_path / "src"
        f.write(f"src_dir exists: {src_dir.exists()}\n")
        if src_dir.exists():
            f.write(f"src_dir contents: {list(src_dir.iterdir())}\n")
            gui_dir = src_dir / "gui"
            f.write(f"gui_dir exists: {gui_dir.exists()}\n")
            if gui_dir.exists():
                f.write(f"gui_dir contents: {list(gui_dir.iterdir())}\n")
except:
    pass

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
        error_msg = traceback.format_exc()
        try:
            with open("error.log", "w", encoding="utf-8") as f:
                f.write(error_msg)
        except:
            pass
        print("=" * 60)
        print("程序启动失败！错误信息已写入 error.log")
        print("=" * 60)
        print(error_msg)
        input("按 Enter 键退出...")
        sys.exit(1)


if __name__ == "__main__":
    main()
