# 🎮 StickAnalyzer v2.1.2 — 补丁更新日志

> 发布日期: 2026-05-25
> v2.1.1 之后的小版本补丁，聚焦在 **配置体验** 和 **代码重构** 上。
> 完全免费，开源 (MIT)，严禁倒卖

------

## 🆕 v2.1.2 主要更新

### 〇、把 exe / zip 重新放回仓库（撤销 v2.1.1 对 Issue #1 的处理）

v2.1.1 里曾经把 `StickAnalyzer.exe` / `StickAnalyzer.zip` 从仓库移除，让发布
产物只走 GitHub Releases。但实际使用中发现：

- 用户更习惯直接从仓库根目录下载，不用进 Releases 页
- 一些自动化工具 / 镜像站只抓仓库内容，Releases 附件抓不到
- 仓库大小受影响有限（这两个文件加起来 ~110MB，git 会增量存储）

所以 v2.1.2 **撤销 Issue #1 的处理决定**：

- `.gitignore` 移除 `*.exe` / `StickAnalyzer*.zip` 排除规则
- 根目录的 `StickAnalyzer.exe` 和 `StickAnalyzer.zip` 加回 git 跟踪
- 用户可以直接 clone 或 download zip 就拿到可运行的程序

### 一、配置文件持久化 + 数据目录默认化（响应 Issue #2）

之前每次启动 GUI 都要重新选键位，数据 CSV 默认放到 cwd（跟 exe 混一起难找）。修复：

- **按键映射自动保存**：录制时（`_start_record()`）自动把当前的开火键 / 开镜键 /
  标记键 / 传感器类型 / 回报率 / 输出目录写入 `~/.stickanalyzer/config.json`
  的 `prefs` 字段
- **二次启动自动恢复**：控制器初始化完成后，`_apply_loaded_prefs()` 读取
  config 把上次保存的值回填到 UI（包括 combobox 显示）
- **数据目录默认化**：
  - Windows: `%USERPROFILE%/Documents/StickAnalyzer/recordings/`
  - 其他平台: `~/StickAnalyzer/recordings/`
  - 启动时自动创建目录，用户不再需要每次手动选

### 二、GUI/CLI 分析逻辑统一（响应 Issue #3）

之前 `analyzer.py main()` 和 GUI 的 `_run_analyzer()` 各自实现了一套分析流水线
（load_csv → detect_fire_bursts → analyze_burst loop → plot → generate_report），
导致 **GUI 漏掉了 noise_floor / weapon_rpm 参数** —— 同样的 CSV 用 GUI 分析和用
CLI 分析结果会不一样。

重构：

- 在 `analyzer.py` 抽出 **`analyze_csv(csv_path, max_events, min_duration, progress_cb)`**
  统一函数
- `progress_cb` 是可选回调签名 `(msg: str) -> None`：
  - **CLI** 传 `print` — 进度打印到 stdout
  - **GUI** 传 `lambda m: self.after(0, self._result_log, m)` — 进度推到日志窗
- 老的 `main()` 和 `_run_analyzer()` 都改成只调 `analyze_csv()`，以后任何分析
  功能改动只改一处
- **GUI 现在跟 CLI 完全等价**（noise_floor / weapon_rpm 都不再漏）

------

## 📦 安装 / 更新

### 已经在用 v2.1.1
直接下载新版 zip，解压覆盖原目录即可。CSV 格式向后兼容。

### 新用户
1. 下载 `StickAnalyzer_v2.1.2.zip`（推荐，onedir 模式）
2. 解压到任意目录
3. 双击 `StickAnalyzer.exe`

或者源码运行：
```bash
git clone https://github.com/q6666666q/stick-analyzer.git
cd stick-analyzer
pip install -r requirements.txt
python main_gui.py
```

------

## 📂 改动文件清单

- `main_gui.py` —— APP_VERSION → v2.1.2，新增 `_default_data_dir()` /
  `_load_user_prefs()` / `_save_user_prefs()` / `_apply_loaded_prefs()`；
  `_start_record()` 加 prefs 保存；默认输出目录改成 Documents/StickAnalyzer/recordings；
  `_run_analyzer()` 改成调 `analyzer.analyze_csv()`
- `analyzer.py` —— 新增 `analyze_csv()` 统一入口函数；`main()` 改成只调
  `analyze_csv(progress_cb=print)`
- `CHANGELOG_v2.1.2.md` / `RELEASE_NOTES_v2.1.2.md` —— 新文件

------

## ✅ 已处理的 GitHub Issues 状态

- **#1** [enhance] exe 存放到 Releases tags 中，仓库仅保留源码
  - v2.1.1 ✓ 处理过（移除根目录 exe/zip）
  - v2.1.2 ✗ **撤销**（用户希望直接从仓库下载，不用进 Releases 页）
- **#2** [feat] 配置文件持久化 + 数据目录默认化 —— ✓ v2.1.2
- **#3** [fix] GUI 与 CLI 的分析逻辑单独实现，应当重构为公用一套逻辑 —— ✓ v2.1.2

------

**作者**：josef_0464
- B 站：https://space.bilibili.com/491671381
- 抖音：josef_0464
- QQ 群：611624374（星辰不妙屋）

> 如果觉得有用，欢迎 ⭐ Star 支持！
