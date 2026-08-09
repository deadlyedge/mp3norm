"""
MP3 Fixer - 批量扫描与音量标准化 CLI 应用
主程序入口
"""

import sys
from pathlib import Path

# 同时支持两种运行方式：
#   1) 作为包/模块运行  : python -m mp3norm.main  或 console script（mp3norm）
#   2) 脚本直接运行      : python src/mp3norm/main.py
# 当以脚本直接运行时没有父级包，相对导入会失败，此时将包根目录 src/ 加入
# 模块搜索路径，随后统一使用绝对导入（mp3norm.*），同包代码只加载一份。
if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mp3norm import config as _cfg
from mp3norm.normalizer import batch_normalize
from mp3norm.reporter import print_scan_report
from mp3norm.scanner import scan_directory
from mp3norm.tui import (
    prompt_scan_path,
    prompt_yes_no,
    show_completion_summary,
    show_progress_bar,
    show_welcome_banner,
)


def main():
    # 1. 显示欢迎横幅
    show_welcome_banner()

    # 2. 获取扫描路径
    root_path = prompt_scan_path()
    if not root_path:
        print("❌ 未提供有效路径，退出程序。")
        return

    # 3. 扫描目录
    print("\n🔍 开始扫描音频文件...\n")
    scan_result = scan_directory(root_path, progress_callback=show_progress_bar)

    # 4. 显示扫描报告
    print("\n")
    print_scan_report(scan_result)

    # 5. 询问是否处理音量
    if not prompt_yes_no(
        f"\n❓ 是否要对全部 {scan_result['total_files']} 个文件进行音量标准化？(Y/n): "
    ):
        print("\n👋 已跳过音量处理，程序结束。")
        return

    # 6. 获取输出目录
    output_dir = Path(root_path) / _cfg.NORMALIZED_DIR_NAME
    output_dir.mkdir(exist_ok=True)
    print(f"\n📂 输出目录：{output_dir}")

    # 7. 批量处理音量
    print("\n🎚️  开始音量标准化处理...\n")

    # 只处理没有严重问题的文件（或全部文件，根据需求调整）
    files_to_process = [f["path"] for f in scan_result["files"]]

    results = batch_normalize(
        files_to_process, str(output_dir), progress_callback=show_progress_bar
    )

    # 8. 显示完成摘要
    total = len(files_to_process)
    processed = results["processed"]
    failed = results["failed"]

    show_completion_summary(total, processed, failed)

    print(f"\n✅ 处理完成！结果已保存至：{output_dir}")


if __name__ == "__main__":
    main()
