# 摇杆射击行为分析工具 - UI 浅色系深度重构与视觉优化方案

## 一、 核心设计理念 (Design Philosophy)

本次重构抛弃传统软件的厚重感和“AI味”十足的过度设计（**绝对禁止任何形式的渐变色、发光特效、弥散阴影等**）。采用以下原则：
1. **纯粹浅色系 (Pure Light)**：主色调使用极致的纯白 (#FFFFFF) 与极浅灰 (#F9FAFB) 构建空间感。
2. **极简线框 (Line Art)**：界面的分割、按钮的边界均由 1px 的纯色硬线条构成，拒绝厚重的填充区块。
3. **高对比点缀 (High-Contrast Accents)**：在黑白灰的基础色上，**仅使用品红 (Magenta) 和 橙色 (Orange)** 作为交互反馈、图表核心数据线和重要状态的点缀，做到克制且抢眼。

---

## 二、 色彩系统规范 (Color Palette)

在 src/app/adapters/ui/tkinter_app.py 中，定义并严格执行以下全局色彩常量：

*   **基础背景**: 
    *   COLOR_BG = "#FFFFFF" (纯白，用于主背景)
    *   COLOR_PANEL = "#F9FAFB" (极浅灰，用于次级面板、卡片背景)
*   **线条与边框**: 
    *   COLOR_LINE = "#E5E7EB" (浅灰，用于绝大多数的分隔线和组件边框)
    *   COLOR_LINE_DARK = "#D1D5DB" (中灰，用于深色边框或输入框激活前的状态)
*   **文字系统**: 
    *   COLOR_TEXT = "#111827" (近黑色，用于正文和标题，保证强可读性)
    *   COLOR_MUTED = "#6B7280" (中深灰，用于辅助文字、小标题、单位)
*   **品牌点缀色 (禁止渐变)**: 
    *   COLOR_ACCENT_MAGENTA = "#E81E63" (品红，主色调，用于核心操作按钮 Hover 态、高亮提示文字、图表主数据线)
    *   COLOR_ACCENT_ORANGE = "#FF9800" (橙色，辅助提示，用于警告框、图表次要对比线、副按钮的高亮态)
*   **交互状态**: 
    *   COLOR_HOVER_BG = "#F3F4F6" (无背景按钮悬停时的轻微灰色背景)

---

## 三、 核心框架改造 (	kinter_app.py)

1. **底层引擎切换**: 
   将 App(tk.Tk) 替换为 customtkinter.CTk，彻底移除老旧的 	tk 样式配置。
2. **全局模式锁定**: 
   在入口强制设置 ctk.set_appearance_mode("light")。
3. **导航剥离 (Navigation)**:
   *   **移除** 原有的 	tk.Notebook 原生多标签页模式。
   *   **重构为** 顶部极简导航栏 (Top Navbar) 或左侧边栏 (Sidebar)。
   *   **导航样式**：导航菜单（RECORD, ANALYZE, PROMPT, REFERENCE）仅由大写的纯文本构成 (COLOR_MUTED)。选中当前页时，文字变为 COLOR_TEXT 加粗，下方或左侧增加一根 2px 宽的 COLOR_ACCENT_MAGENTA 短线作为指示，无任何背景色块。

---

## 四、 各模块界面重构细则

### 1. 录制与控制器模块 (ecord_tab.py, controller_panel.py)
*   **控制器面板区 (Controller Panel)**:
    *   去掉原先的 LabelFrame 边框，改为简单的文本标题（如 1. 连接控制器），下方垫一根 1px COLOR_LINE。
    *   设备下拉框 (	tk.Combobox) 替换为 CTkOptionMenu：白底 (#FFFFFF)，边框 (#E5E7EB)，文字 (#111827)。
    *   **校准过程**：本底噪声显示的进度条或数值，异常时用 COLOR_ACCENT_ORANGE 标出，正常时用品红。
*   **按键映射与录制区**:
    *   映射选择下拉框全部采用扁平线框风格。
    *   **“开始录制”巨型按钮**：
        *   设计为醒目的线框按钮：order_width=1, order_color="#111827", g_color="#FFFFFF", 	ext_color="#111827"。
        *   **Hover状态**：边框和文字瞬间变为纯正的 COLOR_ACCENT_MAGENTA，无渐变过渡。

### 2. 分析与可视化展示模块 (nalyze_tab.py)
*   **数据大屏设计**:
    *   废弃原始的文本框形式数据输出，抽取分析结果中的关键指标（如：总样本数、采样率、最大稳定度等）。
    *   关键指标使用大字号（如 24pt ~ 36pt）单列显示，数字使用 COLOR_ACCENT_MAGENTA，标签使用 COLOR_MUTED。
*   **Matplotlib 图表极致定制 (No Default Styles)**:
    *   彻底消灭 matplotlib 默认的蓝/橙/绿线条和灰色外框。
    *   ig.patch.set_facecolor('#FFFFFF') & x.set_facecolor('#FFFFFF')，实现背景完美融入。
    *   去边框：只保留 X 轴与 Y 轴的底部/左侧实线 (#E5E7EB)，去除上/右边框（x.spines['top'].set_visible(False)）。
    *   网格线：x.grid(color='#F3F4F6', linestyle='--', linewidth=1)。
    *   **数据线绘图逻辑**：主分析曲线统一改为品红 (#E81E63)，辅助对比曲线或基准线改为橙色 (#FF9800)。线宽可稍微加粗（linewidth=2 或 2.5）以强调其在白底上的存在感。

### 3. AI提示词与参考曲线模块 (prompt_tab.py, inverse_tab.py)
*   **文字内容区**:
    *   核心展示区域（AI生成的调参建议、曲线说明）替换为 CTkTextbox。
    *   属性设置：g_color="#F9FAFB", order_width=1, order_color="#E5E7EB", 字体统一设定为现代无衬线体（例如 Helvetica, Roboto, 缺失则降级为 Microsoft YaHei）。
    *   取消默认的内阴影和深色滚动条。滚动条定制为纯色窄条 (#D1D5DB)。
*   **复制操作**:
    *   右下角的“一键复制”按钮，采用极其干练的实心无渐变按钮：静止态为品红 #E81E63 白字，悬停态轻微调亮 #FF3377（依然保持纯色），不带任何投影和圆角（corner_radius=0 或极小的 4）。

---

## 五、 组件替换标准映射卡 (Component Migration Card)

| 原生 Tkinter/TTK | CustomTkinter 对应方案 | 纯粹线框风 参数强制规范 (拒绝AI感) |
| :--- | :--- | :--- |
| 	k.Tk | CTk | g_color=COLOR_BG |
| 	tk.Frame | CTkFrame | 若作容器：g_color="transparent"。若作卡片：g_color=COLOR_PANEL |
| 	tk.LabelFrame | CTkLabel + CTkFrame(height=1) | **严禁使用全包裹边框**。改用大字号文字 + 底部单线分隔 |
| 	tk.Button (主) | CTkButton | 纯色填涂：g_color=COLOR_ACCENT_MAGENTA, corner_radius=0 |
| 	tk.Button (副) | CTkButton | 纯线条：g_color="transparent", order_color=COLOR_LINE_DARK, order_width=1, 悬停文字边框变品红 |
| 	tk.Label | CTkLabel | 	ext_color=COLOR_TEXT 或 COLOR_MUTED |
| 	tk.Entry | CTkEntry | order_width=1, order_color=COLOR_LINE, g_color="#FFFFFF", 激活态 order_color=COLOR_ACCENT_MAGENTA |
| 	k.Text | CTkTextbox | g_color=COLOR_PANEL, order_width=1, order_color=COLOR_LINE, 无立体效果 |
| 弹窗 (messagebox) | CTkToplevel 自定义弹窗 | 背景纯白，大标题，动作按钮使用纯色块，绝不使用系统默认丑陋弹窗 |

---

## 六、 实施路径计划 (Action Plan)

1. **依赖环境确立**: 保证 customtkinter 安装就绪，并确保系统中安装了支持中英混排且效果较好的无衬线字体。
2. **基建改写 (	kinter_app.py)**: 将所有主窗口的搭建逻辑重构，注入新的 COLOR_* 常量，把 Notebook 换成手工构建的侧边栏/顶部栏和 Frame 切换逻辑。
3. **分拆重写 UI Adapter**:
   - 对 controller_panel.py 和 ecord_tab.py 进行洗稿级重构（功能留存，外观全换）。
   - 重构 nalyze_tab.py，特别关注 matplotlib.pyplot / FigureCanvasTkAgg 的渲染参数（颜色、无边框、无渐变）。
4. **细节审查**: 最后全局跑一遍，保证每个按钮、悬停反馈都是纯粹的颜色切换，绝对杜绝按钮自带的“立体阴影”或“渐变发光”效果。
