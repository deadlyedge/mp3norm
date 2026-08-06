# MP3 修复与音量标准化 CLI 应用 — Agent 开发指南

## 项目目标

构建一个 **Python + ffmpeg** 的终端图形界面（TUI）应用，用于：

- 批量扫描本地音乐文件夹中的 MP3 文件
- 生成包含总歌曲数、文件夹数、问题统计的扫描报告
- 询问用户是否处理音量问题（标准化/修复编码）
- 显示处理进度条（总进度 + 单文件进度）
- 完成处理后输出摘要报告

目标用户：拥有大量老旧 MP3 收藏的技术用户，希望一键修复音量和编码问题。

---

## 技术栈要求

- **Python 3.14+**
- **ffmpeg**（已安装并在系统 PATH 中）
- **tqdm** 或 **rich**（用于终端进度条和美观输出）
- **subprocess**（调用 ffmpeg 命令）
- **pathlib**（跨平台路径处理）
- **json**（扫描报告存储）

> 可选：`ffmpeg-normalize`（Python 封装，简化 EBU R128 响度标准化）

---

## 功能模块设计

### 1. 文件扫描模块（`scanner.py`）

**职责：**
- 递归扫描指定目录下的所有 `.mp3` 文件
- 统计总文件数、总文件夹数
- 使用 `ffprobe` 或 `ffmpeg` 检测每个文件的编码信息（比特率、采样率、声道数、时长）
- 识别潜在问题文件（如：比特率异常、时长为 0、无法解析头部）

**输出：**
```json
{
  "total_files": 1234,
  "total_folders": 56,
  "files": [
    {
      "path": "/music/artist/album/track01.mp3",
      "bitrate": 128,
      "sample_rate": 44100,
      "channels": 2,
      "duration": 245.3,
      "issues": []
    },
    {
      "path": "/music/artist/album/track02.mp3",
      "bitrate": 0,
      "sample_rate": 0,
      "channels": 0,
      "duration": 0,
      "issues": ["invalid_header", "zero_duration"]
    }
  ],
  "problem_files_count": 15,
  "problem_files": [ ... ]
}
```

**关键函数：**
- `scan_directory(root_path: str) -> dict`
- `analyze_mp3(file_path: str) -> dict`
- `detect_issues(file_info: dict) -> list[str]`

---

### 2. 报告生成模块（`reporter.py`）

**职责：**
- 将扫描结果格式化为可读的终端报告
- 使用 `rich` 或 `tqdm` 美化输出（表格、颜色、图标）
- 可选：保存为 JSON 或 Markdown 文件

**输出示例：**
```
📊 扫描报告
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 总文件夹数：56
🎵 总歌曲数：1,234
⚠️  问题文件数：15

问题文件列表：
  - /music/artist/album/track02.mp3 [invalid_header, zero_duration]
  - /music/artist/album/track15.mp3 [low_bitrate]
```

**关键函数：**
- `print_scan_report(scan_result: dict)`
- `save_report(scan_result: dict, output_path: str)`

---

### 3. 音量处理模块（`normalizer.py`）

**职责：**
- 使用 `ffmpeg` 的 `loudnorm` 滤镜进行 EBU R128 响度标准化
- 或使用 `volume` 滤镜进行简单峰值标准化
- 支持两遍处理（分析 + 应用）以获得更准确结果
- 可选：使用 `mp3gain` 进行无损增益调整（不重新编码）

**ffmpeg 命令示例：**
```bash
# 一遍式响度标准化（目标 -16 LUFS, 真峰值 -1.5 dB）
ffmpeg -i input.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11 output.mp3

# 两遍式（更准确）
ffmpeg -i input.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json -f null -
ffmpeg -i input.mp3 -af loudnorm=I=-16:TP=-1.5:LRA=11:measured_I=...:measured_TP=...:measured_LRA=...:offset=...:linear=true output.mp3
```

**关键函数：**
- `normalize_file(input_path: str, output_path: str, target_lufs: float = -16.0)`
- `batch_normalize(files: list[str], output_dir: str, progress_callback)`

---

### 4. 终端界面模块（`tui.py`）

**职责：**
- 显示欢迎横幅（使用 `pyfiglet` 或 `rich`）
- 引导用户输入扫描路径
- 显示扫描进度条（总文件数进度）
- 打印扫描报告
- 询问用户是否处理音量问题（Y/N）
- 显示处理进度条（总进度 + 当前文件）
- 打印处理完成摘要

**关键函数：**
- `show_welcome_banner()`
- `prompt_scan_path() -> str`
- `show_progress_bar(iterable, description: str)`
- `prompt_yes_no(question: str) -> bool`
- `show_completion_summary(total: int, processed: int, failed: int)`

---

### 5. 主程序入口（`main.py`）

**流程：**
1. 显示欢迎横幅
2. 获取用户输入的扫描路径
3. 调用 `scanner.scan_directory()` 并显示进度
4. 调用 `reporter.print_scan_report()`
5. 询问用户是否处理音量问题
   - 是：调用 `normalizer.batch_normalize()` 并显示进度
   - 否：跳过
6. 显示完成摘要并退出

---

## 开发规范

### 代码风格
- 遵循 **PEP 8**
- 使用 **类型注解**（type hints）
- 函数文档字符串（docstring）使用 **Google 风格**

### 错误处理
- 所有外部命令（ffmpeg/ffprobe）使用 `subprocess.run(..., capture_output=True, text=True)` 并检查返回码
- 文件路径使用 `pathlib.Path` 避免跨平台问题
- 对每个文件的处理失败进行记录，不中断整体流程

### 进度回调
- 使用 `tqdm` 或 `rich.progress` 包装迭代器
- 支持嵌套进度条（总进度 + 单文件进度）

---

## 文件结构

```
mp3-fixer/
├── main.py           # 主程序入口
├── scanner.py        # 文件扫描与问题分析
├── reporter.py       # 报告生成与输出
├── normalizer.py     # 音量标准化处理
├── tui.py            # 终端界面交互
├── utils.py          # 通用工具函数（日志、路径处理等）
├── requirements.txt  # Python 依赖
└── README.md         # 使用说明
```

---

## 依赖安装

```bash
pip install tqdm rich pyfiglet
```

> 确保 `ffmpeg` 和 `ffprobe` 已在系统 PATH 中（可通过 `ffmpeg -version` 验证）

---

## 使用示例

```bash
# 运行应用
python main.py

# 交互式流程：
# 1. 输入扫描路径（如：/music）
# 2. 等待扫描完成，查看报告
# 3. 输入 Y/N 决定是否处理音量
# 4. 等待处理完成，查看摘要
```

---

## 扩展建议（可选）

- 支持配置文件（YAML/JSON）自定义目标 LUFS、输出目录等
- 支持多线程/多进程加速批量处理
- 支持 `mp3gain` 作为无损音量调整选项
- 支持导出日志文件（处理失败的文件列表）
- 支持增量扫描（跳过未变化的文件）

---

## 注意事项

- 处理前建议用户备份原始文件
- 默认输出到原目录的 `_normalized` 子目录，避免覆盖原文件
- 对于编码问题严重的文件，可尝试先修复帧结构（`ffmpeg -i input.mp3 -acodec copy output.mp3`）再进行音量处理

---

## 参考资源

- ffmpeg loudnorm 文档：https://ffmpeg.org/ffmpeg-filters.html#loudnorm
- ffmpeg-normalize 项目：https://github.com/slhck/ffmpeg-normalize
- tqdm 文档：https://tqdm.github.io/
- rich 文档：https://rich.readthedocs.io/

---

**开发提示：** 请按照模块逐一实现，先完成 `scanner.py` 和 `tui.py` 的基础交互，再逐步添加 `normalizer.py` 的处理逻辑。每个模块完成后进行单元测试，确保整体流程稳定。