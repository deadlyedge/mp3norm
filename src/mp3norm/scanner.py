"""
MP3 Fixer - 文件扫描与问题分析模块
支持多种音频格式：mp3, m4a, flac, ogg, wav, aac, wma, opus
"""

import hashlib
import json
import os
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

from . import config as _cfg


def analyze_mp3(file_path: str, deep: bool = True) -> dict:
    """
    使用 ffprobe 分析音频文件的编码信息，并可执行深度检测

    Args:
        file_path: 音频文件路径
        deep: 是否执行深度检测（响度/完整性），默认 True

    Returns:
        包含文件信息的字典
    """
    path_obj = Path(file_path)
    result = {
        "path": file_path,
        "size": path_obj.stat().st_size if path_obj.exists() else 0,
        "bitrate": 0,
        "sample_rate": 0,
        "channels": 0,
        "duration": 0.0,
        "codec": "",
        "encoding_mode": "CBR",  # CBR / VBR
        "has_tags": True,
        "tags": {},
        "loudness": None,
        "issues": [],
    }

    try:
        # 使用 ffprobe 获取音频流信息
        cmd = [
            _cfg.FFPROBE_BIN,
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            file_path,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=_cfg.FFPROBE_TIMEOUT_SECONDS,
        )

        if proc.returncode != 0:
            result["issues"].append("ffprobe_error")
            return result

        data = json.loads(proc.stdout)

        # 提取格式信息
        fmt = data.get("format", {})
        result["duration"] = float(fmt.get("duration", 0))

        # 标签完整性：读取 format.tags
        tags = fmt.get("tags") or {}
        result["tags"] = {str(k): str(v) for k, v in tags.items()}
        result["has_tags"] = bool(result["tags"])

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

        # 比特率 / 编码模式（VBR 时 format.bit_rate 常为 "N/A"）
        stream_bit_rate = 0
        if audio_stream:
            try:
                stream_bit_rate = int(audio_stream.get("bit_rate", 0))
            except (ValueError, TypeError):
                stream_bit_rate = 0

        raw_bit_rate = fmt.get("bit_rate")
        if raw_bit_rate in (None, "", "N/A") or not _is_digit(raw_bit_rate):
            result["encoding_mode"] = "VBR"
            # 回退到流平均比特率
            result["bitrate"] = stream_bit_rate // 1000
        else:
            try:
                result["bitrate"] = int(raw_bit_rate) // 1000  # 转换为 kbps
            except (ValueError, TypeError):
                result["bitrate"] = 0

        # 基础问题检测
        result["issues"].extend(detect_issues(result))

        # 深度检测（仅当基础解码正常时执行）
        if deep and not any(
            i in result["issues"] for i in ("ffprobe_error", "parse_error")
        ):
            if _cfg.ENABLE_LOUDNESS_ANALYSIS:
                loudness = analyze_loudness(file_path)
                if loudness:
                    result["loudness"] = loudness
                    result["issues"].extend(_detect_loudness_issues(loudness))

            if _cfg.ENABLE_INTEGRITY_CHECK:
                result["issues"].extend(check_integrity(file_path))

        # 去重并保持顺序
        seen = set()
        result["issues"] = [
            i for i in result["issues"] if not (i in seen or seen.add(i))
        ]

    except subprocess.TimeoutExpired:
        result["issues"].append("timeout")
    except json.JSONDecodeError:
        result["issues"].append("parse_error")
    except (OSError, ValueError):
        result["issues"].append("unknown_error")

    return result


def _is_digit(value) -> bool:
    """判断值是否可解析为数字（用于 bit_rate 容错，避免 VBR 触发 int 异常）"""
    if isinstance(value, (int, float)):
        return True
    if not isinstance(value, str):
        return False
    s = value.strip()
    return s.startswith(("-", "+")) and s[1:].isdigit() or s.isdigit() or "." in s


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
    if 0 < file_info["bitrate"] < _cfg.LOW_BITRATE_THRESHOLD:
        issues.append("low_bitrate")

    # 非标准采样率
    if (
        file_info["sample_rate"] > 0
        and file_info["sample_rate"] not in _cfg.STANDARD_SAMPLE_RATES
    ):
        issues.append("non_standard_sample_rate")

    # 异常短时长
    duration = file_info.get("duration", 0)
    if 0 < duration < _cfg.VERY_SHORT_DURATION:
        issues.append("very_short")
    elif _cfg.VERY_SHORT_DURATION <= duration < _cfg.SHORT_TRACK_DURATION:
        issues.append("short_track")

    # 编码模式：VBR
    if file_info.get("encoding_mode") == "VBR":
        issues.append("vbr_file")

    # 元数据/标签完整性
    if not file_info.get("has_tags", True):
        issues.append("missing_tags")
    else:
        tag_keys = {k.lower() for k in file_info.get("tags", {})}
        missing = [k for k in _cfg.REQUIRED_TAG_FIELDS if k not in tag_keys]
        if missing:
            issues.append("incomplete_tags")

    return issues


def analyze_loudness(file_path: str) -> dict | None:
    """使用 ffmpeg 的 ebur128 滤镜分析响度（LUFS / LRA / 真峰值）。

    Args:
        file_path: 音频文件路径

    Returns:
        响度信息字典（integrated/lra/true_peak/peak）；失败时返回 None
    """
    cmd = [
        _cfg.FFMPEG_BIN,
        "-hide_banner",
        "-i",
        file_path,
        "-af",
        "ebur128=peak=true",
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=_cfg.DEEP_ANALYSIS_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return None

    if proc.returncode != 0:
        return None

    text = proc.stderr

    def _extract(pattern: str) -> float | None:
        match = re.search(pattern, text)
        return float(match.group(1)) if match else None

    return {
        "integrated": _extract(r"I:\s*(-?\d+(?:\.\d+)?)\s+LUFS"),
        "lra": _extract(r"LRA:\s*(-?\d+(?:\.\d+)?)\s+LU"),
        "true_peak": _extract(r"True peak:\s*(-?\d+(?:\.\d+)?)\s+dBTP"),
        "peak": _extract(r"Peak:\s*(-?\d+(?:\.\d+)?)\s+dBFS"),
    }


def _detect_loudness_issues(loudness: dict) -> list[str]:
    """根据响度测量值检测音量问题。"""
    issues = []
    integrated = loudness.get("integrated")
    if integrated is not None:
        if integrated < _cfg.LUFS_TOO_LOW:
            issues.append("loudness_too_low")
        elif integrated > _cfg.LUFS_TOO_HIGH:
            issues.append("loudness_too_high")

    true_peak = loudness.get("true_peak")
    if true_peak is not None and true_peak > _cfg.TRUE_PEAK_CLIPPING_DB:
        issues.append("true_peak_clipping")
    return issues


def check_integrity(file_path: str) -> list[str]:
    """尝试完整解码文件，检测音频数据是否损坏/截断。

    Args:
        file_path: 音频文件路径

    Returns:
        检测到的问题列表
    """
    cmd = [
        _cfg.FFMPEG_BIN,
        "-v",
        "error",
        "-i",
        file_path,
        "-f",
        "null",
        "-",
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=_cfg.DEEP_ANALYSIS_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return []

    issues = []
    low = (proc.stderr or "").lower()
    if proc.returncode != 0 or "invalid data" in low or "error" in low:
        issues.append("decode_error")
    if "truncat" in low or "header missing" in low or "ended prematurely" in low:
        issues.append("truncated_file")
    if "corrupt" in low:
        issues.append("corrupt_frame")

    # 去重并保持顺序
    seen = set()
    return [i for i in issues if not (i in seen or seen.add(i))]


def _sample_hash(file_path: str, sample: int = 1024) -> str:
    """对文件头尾样本做 SHA-256 哈希，用于快速识别重复文件。"""
    path = Path(file_path)
    size = path.stat().st_size
    digest = hashlib.sha256()
    digest.update(f"{size}:".encode())
    with open(path, "rb") as f:
        digest.update(f.read(sample))
        if size > sample:
            f.seek(-min(sample, size), 2)
            digest.update(f.read(sample))
    return digest.hexdigest()


def _mark_duplicates(files_info: list) -> None:
    """按文件大小 + 样本哈希标记重复文件（后出现者标记 duplicate_of:路径）。"""
    by_size: dict[int, list] = {}
    for info in files_info:
        by_size.setdefault(info.get("size", 0), []).append(info)

    for size, group in by_size.items():
        if len(group) < 2 or size <= 0:
            continue
        seen_hash: dict[str, str] = {}
        for info in sorted(group, key=lambda x: x["path"]):
            file_hash = _sample_hash(info["path"])
            if file_hash in seen_hash:
                dup = f"duplicate_of:{seen_hash[file_hash]}"
                if dup not in info["issues"]:
                    info["issues"].append(dup)
            else:
                seen_hash[file_hash] = info["path"]


def _count_duplicates(files_info: list) -> int:
    """统计被标记为重复的文件数量。"""
    return sum(
        1
        for info in files_info
        for i in info.get("issues", [])
        if i.startswith("duplicate_of:")
    )


def _iter_audio_files(root: Path):
    """递归遍历目录，跳过被忽略的输出/系统目录，产出支持的音频文件。

    Args:
        root: 根目录 Path 对象

    Yields:
        匹配 SUPPORTED_EXTENSIONS 且不在被忽略目录内的文件 Path
    """
    for dirpath, dirnames, filenames in os.walk(root):
        # 原地修改 dirnames 以剪枝：不进入被忽略的目录
        dirnames[:] = [
            d for d in dirnames if d not in _cfg.SCAN_EXCLUDED_DIRS
        ]
        for name in filenames:
            path = Path(dirpath) / name
            if path.suffix.lower() in _cfg.SUPPORTED_EXTENSIONS:
                yield path


def scan_directory(
    root_path: str, progress_callback: Callable | None = None, deep: bool = True
) -> dict:
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

    # 收集所有支持格式的音频文件（跳过被忽略的输出/系统目录）
    audio_files = list(_iter_audio_files(root))
    total_files = len(audio_files)

    # 统计文件夹数
    folders = {f.parent for f in audio_files}
    total_folders = len(folders)

    # 分析每个文件
    files_info = []

    if progress_callback:
        audio_files = progress_callback(audio_files, description="🔍 扫描中")

    for audio_file in audio_files:
        files_info.append(analyze_mp3(str(audio_file), deep=deep))

    # 重复文件检测（事后统一处理，需全部文件的大小信息）
    if deep and _cfg.ENABLE_DUPLICATE_DETECTION:
        _mark_duplicates(files_info)

    problem_files = [f for f in files_info if f["issues"]]

    return {
        "total_files": total_files,
        "total_folders": total_folders,
        "files": files_info,
        "problem_files_count": len(problem_files),
        "problem_files": problem_files,
        "duplicates_found": _count_duplicates(files_info),
    }
