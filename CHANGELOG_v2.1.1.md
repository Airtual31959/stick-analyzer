# 🎮 StickAnalyzer v2.1.1 — 补丁更新日志

> 发布日期: 2026-05-09
> 这是 v2.1 的小版本补丁,聚焦在 **GUI 体验** 和 **仓库整洁** 上。
> 完全免费,开源 (MIT),严禁倒卖

------

## 🆕 v2.1.1 主要修复

### 一、高 DPI 屏幕适配(核心修复)

笔记本玩家常见痛点 —— 14 / 15 寸笔记本默认系统缩放 125% / 150% / 175%,启动 GUI 时:
- 窗口被 Windows 强制按缩放比拉伸
- 高度被拉伸超过屏幕,**底部按钮(包括"开始录制"按钮)看不到**

v2.1.1 加了三层防护:

1. **DPI 感知** (`SetProcessDpiAwareness`):
   - 告诉 Windows "我自己处理 DPI",不要强制拉伸
   - GUI 元素按物理像素渲染,不再溢出屏幕

2. **窗口尺寸动态计算**:
   - 基础尺寸 1000x1100
   - 按 DPI 缩放比放大: 150% 缩放下变 1500x1650
   - 但**不超过屏幕高度的 92%**(留任务栏空间),低分辨率屏自动缩小
   - 1080p 屏幕 + 150% 缩放(逻辑分辨率 1280x720)→ 实际窗口被限制到 720*0.92 = 662px

3. **垂直滚动条**:
   - ① 录制 Tab + ④ 参考曲线 Tab 内容最长,加 `ScrollableFrame` 包装
   - 窗口高度不够时可以**滚动看到下方按钮**
   - 鼠标滚轮支持,只在 canvas 区域内滚动(避免跟其他控件冲突)

4. **可调整大小** + **最小尺寸 800x500**:
   - 窗口右下角可拖拽
   - 防止误缩到完全无法操作

### 二、Tk 字体缩放同步

`SetProcessDpiAwareness` 之后,默认 Tk 字体会显得过小。加了 `tk.call('tk', 'scaling', ...)` 让字体跟随系统 DPI:
- 150% 缩放 → Tk scaling 2.0,字体放大 1.5x
- 175% 缩放 → Tk scaling 2.33,字体放大 1.75x

### 三、仓库瘦身(响应 Issue #1)

- 移除根目录的 `StickAnalyzer.exe` / `StickAnalyzer.zip`(从 git tracking)
- `.gitignore` 加规则: `*.exe` / `StickAnalyzer*.zip` 等打包产物不再进仓库
- 后续发布只通过 **GitHub Releases** 上传 zip 附件

### 四、EXE_BUILD.md 文档更新

旧版还在说"改键位要改 main_gui.py 源码"(过时,GUI 早就支持键位下拉选)。重写为:
- 当前 v2.1+ 实际打包流程
- 改键位的多种方式(GUI 下拉 / 改默认值)
- v2.1+ 的常见问题(SDL 跨线程修复 / 高 DPI / 高回报率手柄)

------

## 📦 安装 / 更新

### 已经在用 v2.1
直接下载新版 zip,解压覆盖原目录即可。无新功能,但 GUI 显示问题会改善。

### 新用户
1. 下载 `StickAnalyzer_v2.1.1.zip`(推荐,onedir 模式)
2. 解压到任意目录
3. 双击 `StickAnalyzer.exe`

或者源码运行:
```bash
git clone https://github.com/q6666666q/stick-analyzer.git
cd stick-analyzer
pip install -r requirements.txt
python main_gui.py
```

------

## 📂 改动文件清单

- `main_gui.py` — APP_VERSION → v2.1.1, 加 `_enable_high_dpi_awareness()` 函数 + `ScrollableFrame` 类, App 接收 dpi_scale 参数, 录制/参考曲线 Tab 包装滚动条
- `analyzer.py` / `controller_backend.py` / `build_exe.py` / `stick_logger.py` — 版本号 v2.1 → v2.1.1
- `README.md` — 加 v2.1.1 补丁说明段(置顶)+ 版本徽章更新
- `.gitignore` — 加 `*.exe` / `StickAnalyzer*.zip` 排除规则
- `EXE_BUILD.md` — 完整重写(旧版过时)
- `CHANGELOG_v2.1.1.md` / `RELEASE_NOTES_v2.1.1.md` — 新文件
- **移除**: `StickAnalyzer.exe` / `StickAnalyzer.zip`(改用 Releases 分发)

------

## ⏭️ 未在 v2.1.1 范围内的 Issues

收到的另外两个 issues 是中型 refactor,暂未处理:

- **#2 配置文件持久化**: 按键映射在二次启动时仍需重新选;数据文件默认放固定目录而非用户手选
- **#3 GUI/CLI 分析逻辑统一**: `analyzer.py main()` 和 GUI 调用的分析逻辑需要重构去重

会在下个版本(v2.2 或 v2.1.2)处理。

------

**作者**: josef_0464
- B 站: https://space.bilibili.com/491671381
- 抖音: josef_0464
- QQ 群: 611624374(星辰不妙屋)

> 如果觉得有用,欢迎 ⭐ Star 支持!
