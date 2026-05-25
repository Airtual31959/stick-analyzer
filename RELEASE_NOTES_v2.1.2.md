# 🎮 StickAnalyzer v2.1.2

v2.1.1 之后的小版本补丁，解决用户反馈的 **Issue #2 配置持久化** 和 **Issue #3 GUI/CLI 逻辑重复** 两个问题。

完全免费 · 开源 · 严禁倒卖

---

## ✨ 主要更新

### 配置文件持久化 + 数据目录默认化（Issue #2）
- 按键映射 / 传感器 / 回报率 / 输出目录等设置自动保存到 `~/.stickanalyzer/config.json`
- **二次启动自动恢复**，不再每次重选
- 数据 CSV 默认放 `Documents/StickAnalyzer/recordings/`（Windows）

### GUI/CLI 分析逻辑统一（Issue #3）
- 抽出 `analyzer.analyze_csv()` 统一入口函数
- GUI 和 CLI 走同一套流水线（progress_cb 模式）
- **修复 GUI 之前漏传 noise_floor / weapon_rpm 参数**导致结果跟 CLI 不一致的隐 bug

### exe / zip 重新放回仓库（撤销 v2.1.1 对 Issue #1 的处理）
- `StickAnalyzer.exe` 和 `StickAnalyzer.zip` 重新加到仓库根目录
- `.gitignore` 移除对应排除规则
- 用户可以直接从仓库下载，不用进 Releases 页

---

## 📥 下载

- **`StickAnalyzer_v2.1.2.zip`** —— 推荐，onedir 模式，启动快（3-8 秒），约 55MB
- 源码：`git clone https://github.com/q6666666q/stick-analyzer.git`

---

## 🔄 升级

v2.1.1 用户直接覆盖原目录即可。CSV 格式向后兼容。

完整变更日志见 [CHANGELOG_v2.1.2.md](CHANGELOG_v2.1.2.md)。

---

## ✅ 已处理的 Issues 状态

| Issue | 标题 | 状态 |
|------|------|------|
| **#1** | exe 存放到 Releases tags 中，仓库仅保留源码 | v2.1.1 处理过 → **v2.1.2 撤销**（exe/zip 重新放回仓库） |
| **#2** | 配置文件持久化 + 数据目录默认化 | ✓ **v2.1.2** |
| **#3** | GUI 与 CLI 的分析逻辑单独实现，应当重构为公用一套逻辑 | ✓ **v2.1.2** |

---

> v2.1.1 发布说明见 [RELEASE_NOTES_v2.1.1.md](RELEASE_NOTES_v2.1.1.md)
> v2.1 主版本（腰射/开镜不对称 + 走位/站桩对比 + 过冲细分等）见 [RELEASE_NOTES_v2.1.md](RELEASE_NOTES_v2.1.md)
