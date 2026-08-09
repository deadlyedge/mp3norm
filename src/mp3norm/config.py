"""MP3 Fixer - 集中配置

本模块只存放"纯数据"（常量），不包含任何可执行逻辑。
ffmpeg / ffprobe 命令的组装逻辑保留在各功能模块中，
通过引用本模块的常量来取用参数，从而消除硬编码。

按需修改这里的值即可调整行为，无需改动功能代码。
"""

# ─────────────────────────────────────────────
# 外部命令与超时
# ─────────────────────────────────────────────
FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"

# 标准化处理（每文件）超时时间（秒）
TIMEOUT_SECONDS = 120
# ffprobe 分析单文件超时时间（秒）
FFPROBE_TIMEOUT_SECONDS = 30

# ─────────────────────────────────────────────
# 扫描（scanner）配置
# ─────────────────────────────────────────────
# 支持的音频文件扩展名（小写）
SUPPORTED_EXTENSIONS = {
    ".mp3",
    ".m4a",
    ".flac",
    ".ogg",
    ".wav",
    ".aac",
    ".wma",
    ".opus",
}

# 低于该值（kbps）视为低比特率问题
LOW_BITRATE_THRESHOLD = 64

# 标准采样率列表（Hz），不在列表内视为非标准采样率问题
STANDARD_SAMPLE_RATES = [
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

# ─────────────────────────────────────────────
# 深度扫描（scanner）检测开关
# ─────────────────────────────────────────────
# 深度扫描由 scan_directory(deep=...) 触发；下列分项开关仅在 deep=True 时生效。
# 这些检测需完整解码音频，较慢，大型媒体库建议按需开启用于"深度扫描"，
# 平时可用 deep=False 做"快速扫描"。
ENABLE_LOUDNESS_ANALYSIS = True      # LUFS 响度分析（ebur128，需完整解码，较慢）
ENABLE_INTEGRITY_CHECK = True        # 文件完整性验证（完整解码，较慢）
ENABLE_DUPLICATE_DETECTION = True    # 重复文件检测（按文件大小 + 样本哈希）
DEEP_ANALYSIS_TIMEOUT_SECONDS = 120  # 深度检测单文件超时（秒）

# LUFS 响度检测阈值
LUFS_TOO_LOW = -30.0         # integrated < 该值 → loudness_too_low（声音太小）
LUFS_TOO_HIGH = -6.0         # integrated > 该值 → loudness_too_high（可能削波）
TRUE_PEAK_CLIPPING_DB = 0.0  # true peak > 该值(dBTP) → true_peak_clipping

# 异常短时长检测阈值（秒）
VERY_SHORT_DURATION = 10.0   # 0 < 时长 < 该值 → very_short（可能损坏/截断）
SHORT_TRACK_DURATION = 30.0  # 时长 < 该值 → short_track（短曲/铃声，需人工确认）

# 标签完整性要求的关键字段（按小写比较）
REQUIRED_TAG_FIELDS = ("title", "artist", "album")

# ─────────────────────────────────────────────
# 音量标准化（normalizer）配置
# ─────────────────────────────────────────────
# EBU R128 响度目标值
TARGET_LUFS = -16.0   # 目标响度（LUFS）
TARGET_TP = -1.5      # 目标真峰值（dB）
TARGET_LRA = 11.0     # 目标响度范围（LU）
LINEAR = True         # 是否使用线性缩放（loudnorm linear=true）

# 是否默认使用两遍式处理（更准确）
TWO_PASS = True

# 输出编码参数
OUTPUT_SAMPLE_RATE = 44100   # Hz
OUTPUT_BITRATE = "192k"      # 音频比特率

# 是否保持原始音频格式（否则转为 mp3）
# 默认为 False：将所有格式统一转为 mp3 输出，以确保旧设备读取兼容性。
# 设为 True 则保留输入文件的原始扩展名与格式（此时仅 mp3 应用上面的
# OUTPUT_SAMPLE_RATE / OUTPUT_BITRATE，无损格式不会被强制指定比特率）。
OUTPUT_KEEP_ORIGINAL_FORMAT = False # 是否保持原始音频格式（否则转为 mp3）

# ─────────────────────────────────────────────
# 输出校验
# ─────────────────────────────────────────────
# 输出文件最小有效大小（字节），小于该值视为无效并删除
MIN_VALID_SIZE_BYTES = 1024

# ─────────────────────────────────────────────
# 输出目录
# ─────────────────────────────────────────────
# 处理结果默认输出到原目录下的该子目录名
NORMALIZED_DIR_NAME = "_normalized"

# 扫描时忽略的目录名（按目录名精确匹配，任意层级均生效），
# 避免把处理输出目录 / 系统目录当作输入扫描。
SCAN_EXCLUDED_DIRS = {
    NORMALIZED_DIR_NAME,  # 音量处理输出目录
    "__MACOSX",           # macOS 归档残留
    ".Trash",             # 系统回收站
}

# ─────────────────────────────────────────────
# 输入目录
# ─────────────────────────────────────────────
# 默认输入目录，可用于测试
DEFAULT_INPUT_DIR = "./testMusic"