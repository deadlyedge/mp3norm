"""
MP3 Fixer - 终端界面交互模块
"""

from pathlib import Path
from typing import Any

# 支持的音频文件扩展名（与 scanner.py 保持一致）
SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac", ".wma", ".opus"}

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import (
        BarColumn,
        Progress,
        TaskProgressColumn,
        TextColumn,
        TimeRemainingColumn,
    )

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    import pyfiglet

    PYFIGLET_AVAILABLE = True
except ImportError:
    PYFIGLET_AVAILABLE = False


def show_welcome_banner():
    """显示欢迎横幅"""
    if PYFIGLET_AVAILABLE:
        try:
            banner = pyfiglet.figlet_format("MP3 Fixer", font="slant")
            if RICH_AVAILABLE:
                console = Console()
                console.print(
                    Panel(
                        f"[bold cyan]{banner}[/bold cyan]\n[bold]批量扫描与音量标准化工具[/bold]",
                        border_style="cyan",
                    )
                )
            else:
                print(banner)
                print("批量扫描与音量标准化工具")
        except Exception:
            _print_simple_banner()
    else:
        _print_simple_banner()


def _print_simple_banner():
    """简单横幅（无 pyfiglet）"""
    print("=" * 60)
    print("🎵 MP3 Fixer - 批量扫描与音量标准化工具")
    print("=" * 60)
    print()


def prompt_scan_path() -> str | None:
    """
    提示用户输入扫描路径

    Returns:
        有效路径字符串或 None
    """
    if RICH_AVAILABLE:
        console = Console()
        path = console.input(
            "[bold green]📂 请输入要扫描的音乐文件夹路径：[/bold green] "
        )
    else:
        path = input("📂 请输入要扫描的音乐文件夹路径：")

    path = path.strip()

    if not path:
        return None

    # 验证路径
    path_obj = Path(path)
    if not path_obj.exists():
        print(f"❌ 路径不存在：{path}")
        return None

    if not path_obj.is_dir():
        print(f"❌ 不是目录：{path}")
        return None

    # 检查是否有音频文件
    audio_count = sum(
        1 for f in path_obj.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    )
    if audio_count == 0:
        print("⚠️  该目录下没有找到支持的音频文件")
        return None

    print(f"✅ 找到 {audio_count} 个音频文件")
    return str(path_obj.absolute())


def show_progress_bar(iterable: Any, description: str = "处理中"):
    """
    显示进度条

    Args:
        iterable: 可迭代对象
        description: 进度描述

    Returns:
        包装后的可迭代对象
    """
    if RICH_AVAILABLE:
        console = Console()

        # 使用 rich 的美观进度条
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(bar_width=40),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task(description, total=len(list(iterable)))

            # 重新转换为列表以便迭代
            iterable_list = list(iterable)
            progress.update(task, total=len(iterable_list))

            for item in iterable_list:
                yield item
                progress.update(task, advance=1)
    else:
        # 使用 tqdm 作为备选
        try:
            from tqdm import tqdm

            for item in tqdm(iterable, desc=description):
                yield item
        except ImportError:
            # 无任何进度条库，直接迭代
            for item in iterable:
                yield item


def prompt_yes_no(question: str) -> bool:
    """
    提示用户输入 Y/N

    Args:
        question: 问题文本

    Returns:
        True 表示是，False 表示否
    """
    if RICH_AVAILABLE:
        console = Console()
        response = (
            console.input(f"[bold yellow]{question}[/bold yellow] ").strip().lower()
        )
    else:
        response = input(question).strip().lower()

    return response in ("y", "yes", "是", "")


def show_completion_summary(total: int, processed: int, failed: int):
    """
    显示处理完成摘要

    Args:
        total: 总文件数
        processed: 成功处理数
        failed: 失败数
    """
    if RICH_AVAILABLE:
        console = Console()
        success_rate = f"📈 成功率：{processed / total * 100:.1f}%" if total > 0 else ""

        console.print()
        console.print(
            Panel(
                f"[bold green]✅ 处理完成![/bold green]\n\n"
                f"📊 总文件数：{total}\n"
                f"✅ 成功处理：{processed}\n"
                f"❌ 处理失败：{failed}\n"
                f"{success_rate}",
                border_style="green",
            )
        )
    else:
        print()
        print("=" * 60)
        print("✅ 处理完成!")
        print(f"📊 总文件数：{total}")
        print(f"✅ 成功处理：{processed}")
        print(f"❌ 处理失败：{failed}")
        if total > 0:
            print(f"📈 成功率：{processed / total * 100:.1f}%")
        print("=" * 60)
