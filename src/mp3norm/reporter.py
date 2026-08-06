
"""
MP3 Fixer - 报告生成与输出模块
"""

import json
from pathlib import Path

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def print_scan_report(scan_result: dict, use_rich: bool = True):
    """
    打印扫描报告到终端
    
    Args:
        scan_result: 扫描结果字典
        use_rich: 是否使用 rich 美化输出
    """
    if use_rich and RICH_AVAILABLE:
        _print_report_rich(scan_result)
    else:
        _print_report_plain(scan_result)


def _print_report_rich(scan_result: dict):
    """使用 rich 美化输出"""
    console = Console()
    
    # 标题
    console.print(Panel("[bold blue]📊 扫描报告[/bold blue]", border_style="blue"))
    console.print()
    
    # 统计信息
    console.print(f"[bold green]📁 总文件夹数：[/bold green] {scan_result['total_folders']}")
    console.print(f"[bold green]🎵 总歌曲数：[/bold green] {scan_result['total_files']}")
    console.print(f"[bold yellow]⚠️  问题文件数：[/bold yellow] {scan_result['problem_files_count']}")
    console.print()
    
    # 问题文件列表（如果有）
    if scan_result["problem_files"]:
        console.print("[bold red]问题文件列表：[/bold red]")
        console.print()
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("文件路径", style="dim", width=60)
        table.add_column("问题", style="red")
        
        for file_info in scan_result["problem_files"][:20]:  # 最多显示 20 个
            path = Path(file_info["path"]).name
            issues = ", ".join(file_info["issues"])
            table.add_row(path, issues)
        
        console.print(table)
        
        if scan_result["problem_files_count"] > 20:
            console.print(f"\n... 还有 {scan_result['problem_files_count'] - 20} 个问题文件未显示")
    
    # 编码信息统计
    console.print()
    console.print("[bold cyan]📈 编码信息统计：[/bold cyan]")
    
    # 按编解码器统计
    codecs = {}
    for f in scan_result["files"]:
        codec = f.get("codec", "unknown")
        codecs[codec] = codecs.get(codec, 0) + 1
    
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("编解码器")
    table.add_column("文件数")
    
    for codec, count in sorted(codecs.items(), key=lambda x: -x[1]):
        table.add_row(codec, str(count))
    
    console.print(table)


def _print_report_plain(scan_result: dict):
    """纯文本输出"""
    print("=" * 60)
    print("📊 扫描报告")
    print("=" * 60)
    print(f"📁 总文件夹数：{scan_result['total_folders']}")
    print(f"🎵 总歌曲数：{scan_result['total_files']}")
    print(f"⚠️  问题文件数：{scan_result['problem_files_count']}")
    print()
    
    if scan_result["problem_files"]:
        print("问题文件列表：")
        for file_info in scan_result["problem_files"][:20]:
            path = Path(file_info["path"]).name
            issues = ", ".join(file_info["issues"])
            print(f"  - {path} [{issues}]")
        
        if scan_result["problem_files_count"] > 20:
            print(f"\n... 还有 {scan_result['problem_files_count'] - 20} 个问题文件未显示")
    
    print()
    print("=" * 60)


def save_report(scan_result: dict, output_path: str):
    """
    保存扫描报告为 JSON 文件
    
    Args:
        scan_result: 扫描结果字典
        output_path: 输出文件路径
    """
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output, "w", encoding="utf-8") as f:
        json.dump(scan_result, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 报告已保存至：{output}")