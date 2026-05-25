# 🎮 StickAnalyzer v2.1.1

v2.1 补丁更新,主要修复**高 DPI 屏幕(笔记本 150% 缩放)按钮看不到**的问题。

完全免费 · 开源 · 严禁倒卖

---

## 🐛 主要修复

### 高 DPI 屏幕适配
- **DPI 感知**: 启用 `SetProcessDpiAwareness`,Windows 不再强制按系统缩放比拉伸 GUI
- **窗口尺寸动态计算**: 按屏幕高度 92% 自适应,避免溢出任务栏
- **滚动条**: 录制 Tab + 参考曲线 Tab 加垂直滚动条,可滚动看到下方按钮
- **可调整大小**: 窗口右下角可拖拽,最小 800x500
- **Tk 字体同步**: scaling 跟随系统 DPI,字体不会过小

### 仓库整洁(响应 Issue #1)
- 移除根目录的 .exe / .zip(改用 GitHub Releases 分发)
- .gitignore 加打包产物排除规则
- EXE_BUILD.md 重写(老版本说改键位要改源码,过时)

---

## 📥 下载

- **`StickAnalyzer_v2.1.1.zip`** — 推荐,onedir 模式,启动快(3-8 秒),53MB
- 源码: `git clone https://github.com/q6666666q/stick-analyzer.git`

---

## 🔄 升级

老版用户直接覆盖原目录即可,**配置文件 / 已录 CSV 完全向后兼容**。

完整更新日志见 [CHANGELOG_v2.1.1.md](CHANGELOG_v2.1.1.md)。

---

## ⏭️ 已知未在本版本范围内的 Issues

- #2 配置文件持久化(按键映射二次启动需重选;数据目录默认化)
- #3 GUI/CLI 分析逻辑统一(refactor)

会在下个版本处理。

---

> v2.1 主版本(腰射/开镜不对称 + 走位/站桩对比 + 过冲细分等)发布说明见 [RELEASE_NOTES_v2.1.md](RELEASE_NOTES_v2.1.md)
