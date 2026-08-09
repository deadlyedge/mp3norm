"""
MP3 Fixer - 音量标准化处理模块
使用 ffmpeg 的 loudnorm 滤镜进行 EBU R128 响度标准化
"""

import json
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import config as _cfg


def _audio_output_args(output_path: str) -> list[str]:
    """根据输出格式决定音频编码参数。

    仅当输出为 mp3 时附加采样率与比特率参数；保持其它原始格式（如 flac/wav）
    时不强制指定比特率，避免破坏无损编码。

    Args:
        output_path: 输出文件路径

    Returns:
        ffmpeg 音频输出参数列表（非 mp3 时为空）
    """
    if Path(output_path).suffix.lower() == ".mp3":
        return [
            "-ar",
            str(_cfg.OUTPUT_SAMPLE_RATE),
            "-b:a",
            _cfg.OUTPUT_BITRATE,
        ]
    return []


def normalize_file(
    input_path: str,
    output_path: str,
    target_lufs: float = _cfg.TARGET_LUFS,
    target_tp: float = _cfg.TARGET_TP,
    two_pass: bool = _cfg.TWO_PASS,
) -> bool:
    """
    对单个音频文件进行音量标准化

    Args:
        input_path: 输入文件路径（支持 mp3, m4a, flac, ogg, wav, aac, wma, opus）
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
                _cfg.FFMPEG_BIN,
                "-vn",
                "-i",
                input_path,
                "-af",
                f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={_cfg.TARGET_LRA}:print_format=json",
                "-f",
                "null",
                "-",
            ]

            proc = subprocess.run(
                analyze_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_cfg.TIMEOUT_SECONDS,
                check=False,
            )

            # 从 stderr 中提取 JSON 分析结果
            # ffmpeg loudnorm 输出的 JSON 块前后可能有额外文本，需要精确提取
            json_start = proc.stderr.rfind("{")
            json_end = proc.stderr.rfind("}")
            if json_start == -1 or json_end == -1 or json_end <= json_start:
                # 分析失败，使用一遍式处理
                return _normalize_one_pass(
                    input_path, output_path, target_lufs, target_tp
                )

            analysis = json.loads(proc.stderr[json_start : json_end + 1])

            # 第二遍：应用测量值
            measured_i = analysis.get("input_i", "-16.0")
            measured_tp = analysis.get("input_tp", "-1.5")
            measured_lra = analysis.get("input_lra", "11.0")
            measured_thresh = analysis.get("input_thresh", "-29.8")
            offset = analysis.get("target_offset", "0.0")

            apply_cmd = [
                _cfg.FFMPEG_BIN,
                "-y",
                "-vn",
                "-i",
                input_path,
                "-af",
                (
                    f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={_cfg.TARGET_LRA}:"
                    f"measured_I={measured_i}:measured_TP={measured_tp}:"
                    f"measured_LRA={measured_lra}:measured_thresh={measured_thresh}:"
                    f"offset={offset}:linear={str(_cfg.LINEAR).lower()}"
                ),
                *_audio_output_args(output_path),
                output_path,
            ]

            proc = subprocess.run(
                apply_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=_cfg.TIMEOUT_SECONDS,
                check=False,
            )

            if proc.returncode != 0:
                print(f"⚠️  ffmpeg 两遍式处理失败：{Path(input_path).name}")
                if proc.stderr:
                    print(f"   stderr: {proc.stderr[-200:]}")
                return False

            return _verify_output(output_path)

        else:
            return _normalize_one_pass(input_path, output_path, target_lufs, target_tp)

    except subprocess.TimeoutExpired:
        print(f"⏰ 处理超时：{input_path}")
        return False
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        # JSON 解析失败，fallback 到一遍式处理
        print(f"⚠️  分析数据解析失败，降级为一遍式处理：{Path(input_path).name} - {e}")
        return _normalize_one_pass(input_path, output_path, target_lufs, target_tp)
    except Exception as e:
        print(f"❌ 处理失败：{input_path} - {e}")
        return False


def _normalize_one_pass(
    input_path: str, output_path: str, target_lufs: float, target_tp: float
) -> bool:
    """一遍式响度标准化（简单但精度较低）"""
    cmd = [
        _cfg.FFMPEG_BIN,
        "-y",
        "-vn",
        "-i",
        input_path,
        "-af",
        f"loudnorm=I={target_lufs}:TP={target_tp}:LRA={_cfg.TARGET_LRA}",
        *_audio_output_args(output_path),
        output_path,
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=_cfg.TIMEOUT_SECONDS,
        check=False,
    )

    if proc.returncode != 0:
        print(f"⚠️  ffmpeg 一遍式处理失败：{Path(input_path).name}")
        if proc.stderr:
            print(f"   stderr: {proc.stderr[-200:]}")
        return False

    return _verify_output(output_path)


def _verify_output(
    output_path: str, min_bytes: int = _cfg.MIN_VALID_SIZE_BYTES
) -> bool:
    """
    验证输出文件是否有效

    Args:
        output_path: 输出文件路径
        min_bytes: 最小有效文件大小（字节），默认 1KB

    Returns:
        文件是否有效
    """
    path = Path(output_path)
    if not path.exists():
        print(f"⚠️  输出文件未生成：{path.name}")
        return False
    if path.stat().st_size < min_bytes:
        print(f"⚠️  输出文件过小（{path.stat().st_size} 字节），可能无效：{path.name}")
        path.unlink(missing_ok=True)  # 删除无效文件
        return False
    return True


def batch_normalize(
    files: list,
    output_dir: str,
    progress_callback: Callable | None = None,
    target_lufs: float = _cfg.TARGET_LUFS,
    target_tp: float = _cfg.TARGET_TP,
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

        # 默认转为 mp3 输出（OUTPUT_KEEP_ORIGINAL_FORMAT=False）；
        # 设为 True 时保留输入文件的原始扩展名
        if not _cfg.OUTPUT_KEEP_ORIGINAL_FORMAT:
            relative_path = relative_path.with_suffix(".mp3")

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
