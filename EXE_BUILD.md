# EXE 打包使用指南

## 一键打包

在工程目录下运行：

```bash
python build_exe.py
```

脚本会自动：
1. 检查并安装 PyInstaller
2. 检查 `main_gui.py`，并把 `analyzer.py`、`controller_backend.py`、`error_reporter.py` 作为附加模块打包（如果文件存在）
3. 让你选择打包模式：回车默认 onedir，输入 `2` 选择 onefile
4. onedir 输出到 `dist/StickAnalyzer/StickAnalyzer.exe`，onefile 输出到 `dist/StickAnalyzer.exe`
5. onedir 打包成功后，可按提示自动生成 `dist/StickAnalyzer.zip`

打包过程大约 1-2 分钟，最终 EXE 大小约 80-150MB（包含了 matplotlib、pandas 等所有依赖）。

## 使用方法

### onedir 模式（推荐）

进入 `dist/StickAnalyzer/` 文件夹，双击 `StickAnalyzer.exe` 即可运行，**完全不需要 Python 环境**。

分发时请发送整个 `StickAnalyzer` 文件夹，或发送脚本生成的 `StickAnalyzer.zip`。不要只发送文件夹里的 `StickAnalyzer.exe`，它需要同目录下的 `_internal/` 目录。

启动通常需要 3-8 秒。

### onefile 模式

直接双击 `dist/StickAnalyzer.exe` 即可运行，**完全不需要 Python 环境**。

第一次启动通常需要 30-90 秒，因为 PyInstaller 需要把依赖解压到临时目录。任务管理器里可能短暂出现两个 `StickAnalyzer.exe` 进程，这是 onefile 模式的正常机制。

## GUI 使用流程

### 标签 1：录制摇杆数据

1. 填写元数据（RC 值、曲线版本、武器、场景等）—— 可选，但建议填
2. 输出目录默认使用 `~/.stickanalyzer/data`，可按需选择其他目录
3. 点击 **● 开始录制**
4. 正常打游戏（屏幕上有实时状态显示，按 RB 应看到 FIRE 标记，按方向上键应看到 ADS 标记）
5. 打完后回到 GUI 点 **■ 停止录制**
6. 程序提示是否切换到分析页面

### 标签 2：分析数据

1. CSV 路径会自动填入（刚录的那个），或手动选择历史 CSV
2. 调整参数：最大事件数、最短爆发时长
3. 点 **▶ 开始分析**
4. 结果显示在下方文本框
5. 完成后可点 **📁 打开输出目录** 查看生成的图表

## 改键位

如果你的开火/开镜/标记键和默认不同，直接在 GUI 的「键位映射设置」里选择。
程序会自动保存到 `~/.stickanalyzer/config.json`，下次启动会恢复上次设置。

## 常见问题

### Q: 双击 EXE 没反应？
- 可能被杀软误杀（PyInstaller 打包的 EXE 经常被误判）
- 把 EXE 加入杀软白名单，或用命令行运行看错误：`StickAnalyzer.exe`

### Q: 提示"未检测到任何手柄"？
- 确认手柄连接正常，并被识别为 XBOX 360 兼容控制器
- 在 Windows 设置 → 设备 → 蓝牙和其他设备 里能看到手柄

### Q: 录制时按键没反应（FIRE/ADS 标记不亮）？
- 默认键位是 RB 开火 + LT 开镜
- 如果你的键位不同，直接在 GUI 的「键位映射设置」里选择

### Q: 生成的图中文显示方框？
- 确保系统装了 Microsoft YaHei 字体（Windows 自带）
- 如果是精简版 Windows，可能需要安装中文字体包

### Q: EXE 太大（100MB+）？
- 这是正常的，因为打包了 matplotlib、pandas、numpy 等大库
- 如果想减小，可以用 `--exclude-module` 排除不需要的模块
- 或者改用 nuitka 打包（体积更小但更慢）

### Q: 打包失败？
- 查看错误信息，最常见的是依赖缺失
- 先确认能直接运行：`python main_gui.py`，能跑通再打包
- PyInstaller 版本建议 6.0+
