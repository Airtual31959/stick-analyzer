# EXE 打包使用指南 (v2.1+)

## 一键打包

```bash
python build_exe.py
```

启动后会询问打包模式:
- **`1` onedir（推荐）⭐** —— 输出 `dist/StickAnalyzer/` 文件夹（11MB exe + 一堆依赖），启动快（3-8 秒），杀软误报率低，分发为 zip
- **`2` onefile** —— 输出单个 `dist/StickAnalyzer.exe`（约 80-150MB），启动慢（30-90 秒），任务管理器会显示 2 个进程（PyInstaller bootloader 机制，不是 bug）

如果想跳过交互直接打包,用 PyInstaller 直接调:

```bash
python -m PyInstaller --onedir --windowed --name=StickAnalyzer --clean --noconfirm \
  --hidden-import=matplotlib.backends.backend_agg \
  --hidden-import=matplotlib.backends.backend_tkagg \
  --hidden-import=pygame --hidden-import=XInput \
  --hidden-import=pandas --hidden-import=numpy --hidden-import=PIL \
  --hidden-import=tkinter --hidden-import=tkinter.ttk \
  --hidden-import=tkinter.filedialog --hidden-import=tkinter.messagebox \
  --hidden-import=tkinter.scrolledtext \
  "--add-data=analyzer.py;." \
  "--add-data=controller_backend.py;." \
  "--add-data=error_reporter.py;." \
  main_gui.py
```

打包过程约 1-3 分钟。

## 输出位置

| 模式 | 位置 | 分发方式 |
|------|------|----------|
| onedir | `dist/StickAnalyzer/StickAnalyzer.exe` | 把整个 `StickAnalyzer/` 文件夹打 zip 分发 |
| onefile | `dist/StickAnalyzer.exe` | 直接发单文件 |

## 使用方法

直接双击 `StickAnalyzer.exe`,**完全不需要 Python 环境**。

## 改键位

> v2.0+ 起改键位**不需要改源码** —— GUI 启动后在「② 键位映射设置」区域可以直接下拉选开火/开镜/标记键。

GUI 已支持的逻辑键位:
- ABXY / 方向键 / LB/RB / LT/RT / L3/R3 / START/BACK
- DualSense Edge 背键 FN1/FN2/RB1/RB2
- Switch Pro Controller 按键

按键标签会根据手柄类型自动切换显示(PS 显示 × ○ □ △,XBOX 显示 A B X Y)。

## 改默认键位(可选)

如果你想让 GUI 启动时默认就是某个键(而不是 RB 开火),可以改 `main_gui.py` 顶部:

```python
DEFAULT_FIRE_BUTTON = "RIGHT_SHOULDER"   # RB / R1
DEFAULT_ADS_BUTTON = "TRIGGER_LEFT"      # LT / L2
```

可选值: 看 `controller_backend.py` 顶部 `LOGICAL_BUTTONS` 列表。

## 常见问题

### Q: 双击 EXE 没反应？
- 可能被杀软误杀(PyInstaller 打包的 EXE 经常被误判)
- 把 EXE 加入杀软白名单
- 或命令行运行看错误: `StickAnalyzer.exe`

### Q: 提示"未检测到任何手柄"？
- 确认手柄连接(USB 插稳 / 蓝牙配对完成)
- 点 GUI 里的 **🔄 刷新设备列表** 按钮
- v2.1 起 XBOX 风格手柄默认走 XInput,如果还识别不到,检查 Windows 设备管理器是否显示该手柄

### Q: 录制时只有扳机能识别,RB/A/B 等按键失效？
- v2.1 已修复(SDL 跨线程 bug,启用 `SDL_JOYSTICK_THREAD`)
- 确认你用的是 v2.1+ 版本

### Q: 高 DPI 笔记本(150%/175% 缩放)按钮看不到？
- v2.1 已加 DPI 感知 + 可调整窗口大小
- 窗口右下角可以拖动调整尺寸
- ① 录制 Tab 和 ④ 参考曲线 Tab 内容可滚动

### Q: 生成的图中文显示方框？
- 确保系统装了 Microsoft YaHei 字体(Windows 自带)

### Q: EXE 太大(100MB+)？
- 这是正常的,因为打包了 matplotlib / pandas / numpy 等大库
- onedir 模式 zip 后约 50MB,onefile 模式约 80-150MB
- 如果想减小,可以用 `--exclude-module` 排除不需要的模块
- 或者改用 nuitka 打包(体积更小但更慢)

### Q: 打包失败？
- 查看错误信息,最常见的是依赖缺失
- 先确认能直接运行: `python main_gui.py`,能跑通再打包
- PyInstaller 版本建议 6.0+

### Q: 任务管理器显示两个 StickAnalyzer.exe 进程？
- 如果你用的是 onefile 单文件版,这是 PyInstaller bootloader 的正常机制(一个负责解压临时文件,一个是真正的程序),不是 bug
- 如果想避免,用 onedir(zip)版,只有一个进程
