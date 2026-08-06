"""
MP3 Fixer - 音量标准化处理模块
使用 ffmpeg 的 loudnorm 滤镜进行 EBU R128 响度标准化
"""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any


def normalize_file(
    input_path: str,
    output_path: str,
    target_lufs: float = -16.0,
    target_tp: float = -1.5,
    two_pass: bool = True,
) -> bool:
    """
    对单个 MP3 文件进行音量标准化

    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        target_lufs: 目标响度（LUFS），默认 -16.0
        target_tp: 目标真峰值（dB），默认 -1.5
        two_pass: 是否使用两遍处理（更准确）

    Returns:
        处理是否成功
    """
    try:
        if two_pass:
            # 第一遍：分析
            analyze_cmd = [
                "ffmpeg",
                "-i",
                input_path,
                "-af",
                f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:print_format=json",
                "-f",
                "null",
                "-",
            ]

            proc = subprocess.run(
                analyze_cmd, capture_output=True, text=True, timeout=120, check=False
            )

            # 从 stderr 中提取 JSON 分析结果
            json_start = proc.stderr.rfind("{")
            if json_start == -1:
                # 分析失败，使用一遍式处理
                return _normalize_one_pass(
                    input_path, output_path, target_lufs, target_tp
                )

            analysis = json.loads(proc.stderr[json_start:])

            # 第二遍：应用测量值
            measured_i = analysis.get("input_i", "-16.0")
            measured_tp = analysis.get("input_tp", "-1.5")
            measured_lra = analysis.get("input_lra", "11.0")
            measured_thresh = analysis.get("input_thresh", "-29.8")
            offset = analysis.get("target_offset", "0.0")

            apply_cmd = [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-af",
                (
                    f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11:"
                    f"measured_I={measured_i}:measured_TP={measured_tp}:"
                    f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
                    f"offset={offset}:linear=true"
                ),
                "-ar",
                "44100",
                "-b:a",
                "192k",
                output_path,
            ]

            proc = subprocess.run(
                apply_cmd, capture_output=True, text=True, timeout=120, check=False
            )

            return proc.returncode == 0

        else:
            return _normalize_one_pass(input_path, output_path, target_lufs, target_tp)

    except subprocess.TimeoutExpired:
        print(f"⏰ 处理超时：{input_path}")
        return False
    except Exception as e:
        print(f"❌ 处理失败：{input_path} - {e}")
        return False


def _normalize_one_pass(
    input_path: str, output_path: str, target_lufs: float, target_tp: float
) -> bool:
    """一遍式响度标准化（简单但精度较低）"""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-af",
        f"loudnorm=I={target_lufs}:TP={target_tp}:LRA=11",
        "-ar",
        "44100",
        "-b:a",
        "192k",
        output_path,
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
    return proc.returncode == 0


def batch_normalize(
    files: list,
    output_dir: str,
    progress_callback: Callable | None = None,
    target_lufs: float = -16.0,
    target_tp: float = -1.5,
) -> dict[str, Any]:
    """
    批量处理多个 MP3 文件的音量标准化

    Args:
        files: 输入文件路径列表
        output_dir: 输出目录
        progress_callback: 进度回调函数
        target_lufs: 目标响度
        target_tp: 目标真峰值

    Returns:
        处理结果字典 {processed: int, failed: int, failed_files: list}
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    processed = 0
    failed = 0
    failed_files = []

    if progress_callback:
        files = progress_callback(files, description="🎚️  处理中")

    for input_file in files:
        # 生成输出文件名（保持相对路径结构）
        input_p = Path(input_file)
        relative_path = input_p.relative_to(input_p.anchor)
        output_file = output_path / relative_path
        output_file.parent.mkdir(parents=True, exist_ok=True)

        success = normalize_file(
            str(input_file),
            str(output_file),
            target_lufs=target_lufs,
            target_tp=target_tp,
        )

        if success:
            processed += 1
        else:
            failed += 1
            failed_files.append(input_file)

    return {"processed": processed, "failed": failed, "failed_files": failed_files}
