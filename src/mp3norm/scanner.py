"""
MP3 Fixer - 文件扫描与问题分析模块
支持多种音频格式：mp3, m4a, flac, ogg, wav, aac, wma, opus
"""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path

# 支持的音频文件扩展名
SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac", ".wma", ".opus"}


def analyze_mp3(file_path: str) -> dict:
    """
    使用 ffprobe 分析 MP3 文件的编码信息

    Args:
        file_path: MP3 文件路径

    Returns:
        包含文件信息的字典
    """
    result = {
        "path": file_path,
        "bitrate": 0,
        "sample_rate": 0,
        "channels": 0,
        "duration": 0.0,
        "codec": "",
        "issues": [],
    }

    try:
        # 使用 ffprobe 获取音频流信息
        cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=30
        )

        if proc.returncode != 0:
            result["issues"].append("ffprobe_error")
            return result

        data = json.loads(proc.stdout)

        # 提取格式信息
        fmt = data.get("format", {})
        result["duration"] = float(fmt.get("duration", 0))
        result["bitrate"] = int(fmt.get("bit_rate", 0)) // 1000  # 转换为 kbps

        # 提取音频流信息
        streams = data.get("streams", [])
        audio_stream = next(
            (s for s in streams if s.get("codec_type") == "audio"), None
        )

        if audio_stream:
            result["sample_rate"] = int(audio_stream.get("sample_rate", 0))
            result["channels"] = int(audio_stream.get("channels", 0))

            # 记录编解码器类型
            result["codec"] = audio_stream.get("codec_name", "")

        # 检测问题
        result["issues"].extend(detect_issues(result))

    except subprocess.TimeoutExpired:
        result["issues"].append("timeout")
    except json.JSONDecodeError:
        result["issues"].append("parse_error")
    except (OSError, ValueError) as e:
        result["issues"].append("unknown_error", e)

    return result


def detect_issues(file_info: dict) -> list:
    """
    根据文件信息检测潜在问题

    Args:
        file_info: 文件信息字典

    Returns:
        问题列表
    """
    issues = []

    # 零时长
    if file_info["duration"] <= 0:
        issues.append("zero_duration")

    # 零比特率
    if file_info["bitrate"] <= 0:
        issues.append("zero_bitrate")

    # 零采样率
    if file_info["sample_rate"] <= 0:
        issues.append("zero_sample_rate")

    # 零声道数
    if file_info["channels"] <= 0:
        issues.append("zero_channels")

    # 低比特率（< 64 kbps）
    if 0 < file_info["bitrate"] < 64:
        issues.append("low_bitrate")

    # 非标准采样率
    standard_rates = [
        8000,
        11025,
        12000,
        16000,
        22050,
        24000,
        32000,
        44100,
        48000,
        88200,
        96000,
        176400,
        192000,
    ]
    if file_info["sample_rate"] > 0 and file_info["sample_rate"] not in standard_rates:
        issues.append("non_standard_sample_rate")

    return issues


def scan_directory(root_path: str, progress_callback: Callable | None = None) -> dict:
    """
    递归扫描目录下的所有支持格式音频文件

    Args:
        root_path: 根目录路径
        progress_callback: 进度回调函数（可选）

    Returns:
        扫描结果字典
    """
    root = Path(root_path)

    if not root.exists():
        raise FileNotFoundError(f"目录不存在：{root_path}")

    # 收集所有支持格式的音频文件
    audio_files = [
        f for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    total_files = len(audio_files)

    # 统计文件夹数
    folders = {f.parent for f in audio_files}
    total_folders = len(folders)

    # 分析每个文件
    files_info = []
    problem_files = []

    if progress_callback:
        audio_files = progress_callback(audio_files, description="🔍 扫描中")

    for audio_file in audio_files:
        file_info = analyze_mp3(str(audio_file))
        files_info.append(file_info)

        if file_info["issues"]:
            problem_files.append(file_info)

    return {
        "total_files": total_files,
        "total_folders": total_folders,
        "files": files_info,
        "problem_files_count": len(problem_files),
        "problem_files": problem_files,
    }
