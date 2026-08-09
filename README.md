# 🎵 MP3 Fixer

批量扫描与音量标准化 CLI 应用 — 修复老旧 MP3 收藏的音量和编码问题

## ✨ 功能特性

- 🔍 **批量扫描**：递归扫描指定目录下的所有 MP3 文件
- 📊 **详细报告**：显示总歌曲数、文件夹数、编码信息统计、问题文件列表
- 🎚️ **音量标准化**：使用 ffmpeg 的 EBU R128 loudnorm 滤镜进行响度标准化
- 📈 **进度显示**：美观的终端进度条（rich/tqdm）
- 🛠️ **问题检测**：自动识别零时长、低比特率、非标准采样率等问题

## 🚀 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 确保已安装 ffmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
从 [ffmpeg 官网](https://ffmpeg.org/download.html) 下载并添加到 PATH

**Linux:**
```bash
sudo apt install ffmpeg    # Debian/Ubuntu
sudo yum install ffmpeg    # CentOS/RHEL
```

验证安装：
```bash
ffmpeg -version
ffprobe -version
```

### 3. 运行应用

```bash
python main.py
```

### 4. 交互式流程

1. 输入要扫描的音乐文件夹路径（如：`/music` 或 `D:\Music`）
2. 等待扫描完成，查看扫描报告
3. 输入 `Y` 或 `N` 决定是否处理音量问题
4. 等待处理完成，查看摘要报告

## 📁 输出结构

处理后的文件会保存到原目录下的 `_normalized` 子目录，保持原有文件夹结构：

```
/music/
├── artist1/
│   ├── album1/
│   │   ├── track01.mp3
│   │   └── track02.mp3
├── _normalized/          # 处理后的文件
│   └── artist1/
│       └── album1/
│           ├── track01.mp3
│           └── track02.mp3
```

## ⚙️ 配置选项

所有可调参数集中在 `config.py` 中，修改后无需改动功能代码：

```python
# config.py（节选）
TARGET_LUFS = -16.0      # 目标响度（LUFS）
TARGET_TP = -1.5         # 目标真峰值（dB）
TARGET_LRA = 11.0        # 目标响度范围（LU）
TWO_PASS = True          # 是否使用两遍处理（更准确但更慢）
OUTPUT_SAMPLE_RATE = 44100
OUTPUT_BITRATE = "192k"
SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".flac", ".ogg", ".wav", ".aac", ".wma", ".opus"}
```

## 📋 扫描报告示例

```
╭──────────────────────────────────────────────────────────────╮
│                    📊 扫描报告                               │
╰──────────────────────────────────────────────────────────────╯

📁 总文件夹数：56
🎵 总歌曲数：1,234
⚠️  问题文件数：15

问题文件列表：
┌─────────────────────────────────────────────────────────────┐
│ 文件路径                        问题                        │
├─────────────────────────────────────────────────────────────┤
│ track02.mp3                    zero_duration, zero_bitrate │
│ track15.mp3                    low_bitrate                  │
└─────────────────────────────────────────────────────────────┘

📈 编码信息统计：
┌──────────────┬────────┐
│ 比特率 (kbps) │ 文件数 │
├──────────────┼────────┤
│ 320          │ 856    │
│ 256          │ 234    │
│ 128          │ 129    │
│ 0            │ 15     │
└──────────────┴────────┘
```

## 🛠️ 模块说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序入口 |
| `scanner.py` | 文件扫描与问题分析 |
| `reporter.py` | 报告生成与输出 |
| `normalizer.py` | 音量标准化处理 |
| `tui.py` | 终端界面交互 |
| `requirements.txt` | Python 依赖 |

## 🔧 扩展建议

- 支持配置文件（YAML/JSON）自定义参数
- 支持 `mp3gain` 进行无损增益调整
- 支持多线程/多进程加速处理
- 支持增量扫描（跳过未变化的文件）
- 添加日志文件记录处理失败的文件

## ⚠️ 注意事项

- 处理前建议备份原始文件
- 默认输出到 `_normalized` 子目录，不会覆盖原文件
- 对于编码问题严重的文件，可能无法完全修复

## 📄 许可证

MIT License

## 🙏 致谢

- [ffmpeg](https://ffmpeg.org/) - 强大的多媒体处理工具
- [rich](https://github.com/Textualize/rich) - 美观的终端输出库
- [tqdm](https://github.com/tqdm/tqdm) - 快速进度条库