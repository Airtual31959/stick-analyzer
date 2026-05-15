# record_tab.py 与 controller_panel.py 重构与视觉优化方案

针对 `GUI 模块 record 步骤` 的代码（主要集中在 `record_tab.py` 和 `controller_panel.py`），结合 `ui-redesign-plan.md` 的浅色系深度重构与视觉优化要求，现给出以下排版、样式优化的意见与可供其他 Agent 直接执行的代码修复方案：

### 一、 核心问题分析

1. **大杂烩式巨型函数**：`_build_record_tab` 方法长达两三百行，虽然前两步（选择控制器、键位映射）已经抽离成独立方法，但后续的性能模式、记录元数据、输出与录制步骤全挤在主函数中，可读性极差。
2. **魔法值与样式硬编码泛滥**：大量组件直接硬编码了如 `fg_color="#FFFFFF"`, `button_hover_color="#F3F4F6"`, `border_color="#D1D5DB"` 等十六进制颜色。完全没有利用 `theme.py` 统一管理的色彩系统。
3. **“带边框组件”的代码严重冗余**：因为 `customtkinter` 的 `CTkOptionMenu` 不自带外边框，代码中多次通过外包一个 `border_width=1` 的 `CTkFrame` 来实现“线框风”，并且每次都重复手写了 10 个左右的相同属性。
4. **混合布局缺乏规范**：`grid` 和 `pack` 混用，`padx` / `pady` 等外边距随意设置（例如 `pady=(18,0)`, `pady=(6,12)`），未抽象出标准的“表单行”或“章节标题”结构。

---

### 二、 具体重构与修复方案（Agent 执行指南）

#### 1. 消除样式硬编码，强制接入 `theme.py`
**操作方案：**
- 检查 `theme.py` 中是否已定义完整（若没有，需补充）：
  `COLOR_BG = "#FFFFFF"`, `COLOR_PANEL = "#F9FAFB"`, `COLOR_LINE = "#E5E7EB"`, `COLOR_LINE_DARK = "#D1D5DB"`, `COLOR_TEXT = "#111827"`, `COLOR_MUTED = "#6B7280"`, `COLOR_HOVER_BG = "#F3F4F6"`。
- 将 `record_tab.py` 和 `controller_panel.py` 中的十六进制颜色全局替换：
  - `#FFFFFF` -> `COLOR_BG`
  - `#F9FAFB` -> `COLOR_PANEL`
  - `#D1D5DB` / `#E5E7EB` -> 视情况替换为 `COLOR_LINE_DARK` 或 `COLOR_LINE`
  - `#111827` -> `COLOR_TEXT`
  - `#F3F4F6` -> `COLOR_HOVER_BG`

#### 2. 提取高频 UI 复合组件工厂（极致复用）
**操作方案：**
在 `theme.py` 或一个专门的 `ui_utils.py` 中封装“纯粹线框风”的标准化组件构建器。所有涉及下拉框、输入框的地方强制调用这些工厂：

```python
# 示例：线框风格下拉框（解决边框嵌套与样式冗余）
def create_outline_option_menu(parent, variable, values, command=None, width=200):
    wrapper = ctk.CTkFrame(parent, border_width=1, border_color=COLOR_LINE_DARK, 
                           fg_color="transparent", corner_radius=0)
    combo = ctk.CTkOptionMenu(
        wrapper, variable=variable, values=values, width=width, command=command,
        fg_color=COLOR_BG, button_color=COLOR_BG, button_hover_color=COLOR_HOVER_BG,
        text_color=COLOR_TEXT, dropdown_fg_color=COLOR_BG, 
        dropdown_hover_color=COLOR_HOVER_BG, dropdown_text_color=COLOR_TEXT,
        font=FONT_BODY, dropdown_font=FONT_BODY, corner_radius=0
    )
    combo.pack(padx=1, pady=1) # 1px 的边框效果
    return wrapper, combo

# 示例：线框风格输入框
def create_outline_entry(parent, textvariable, width=60):
    return ctk.CTkEntry(
        parent, textvariable=textvariable, width=width,
        fg_color=COLOR_BG, border_color=COLOR_LINE_DARK, border_width=1,
        text_color=COLOR_TEXT, corner_radius=0, font=FONT_BODY
    )

# 示例：标准化章节标题与分割线
def build_section_header(parent, title):
    ctk.CTkLabel(parent, text=title, font=FONT_SECTION, text_color=COLOR_TEXT).pack(anchor="w", padx=10, pady=(18, 0))
    ctk.CTkFrame(parent, height=1, fg_color=COLOR_LINE).pack(fill="x", padx=10, pady=(6, 12))
```
- **重构点**：用工厂函数替换 `controller_panel.py` 中局部的 `create_option_menu`，以及 `record_tab.py` 中 `perf_combo`, `sensor_combo` 等冗长创建代码。

#### 3. 巨型函数拆解（UI 架构模块化）
**操作方案：**
修改 `record_tab.py`，将 `_build_record_tab` 中剩下的步骤代码剥离出去。主函数的职能仅限于流转：

```python
def _build_record_tab(self, parent):
    # ...（初始化 step_host 与 _record_steps）...
    
    self._build_controller_panel(self._record_steps[0])
    self._build_key_mapping_panel(self._record_steps[1])
    self._build_performance_panel(self._record_steps[2])
    self._build_metadata_panel(self._record_steps[3])
    self._build_action_panel(self._record_steps[4])
    
    self._build_record_step_nav(parent)
    self._show_record_step(0)

# 新增方法
def _build_performance_panel(self, parent):
    build_section_header(parent, "3. 性能模式")
    # ...性能模式具体逻辑...

def _build_metadata_panel(self, parent):
    build_section_header(parent, "4. 本次记录元数据")
    # ...提取内部 def 为类方法，保持 UI 构建纯粹...

def _build_action_panel(self, parent):
    # 输出目录与巨型录制按钮的构建逻辑
    # ...
```

#### 4. 逻辑与表现彻底分离（移除闭包）
**操作方案：**
清理 `_build_record_tab` 内嵌的 `_sync_sensor_code`、`_build_rc_row` 等局部函数，将它们提升为类级别的私有方法。
- `_sync_sensor_code(*_)` 变为 `def _on_sensor_label_changed(self, var_name, index, mode):`，使用追踪时绑定到 self。
- `_build_rc_row` 变为 `def _build_rc_row_ui(self, parent, label_text, prefix):`。

#### 5. “巨型操作按钮”视觉对齐方案
**操作方案：**
`btn_record`（开始录制）当前的边框变化逻辑是使用 `bind("<Enter>")` 触发的，这符合重构计划中的“瞬间变色，无渐变”。但需确保：
- 静止态：`fg_color=COLOR_BG`, `border_color=COLOR_TEXT`, `text_color=COLOR_TEXT`, `border_width=1`, `corner_radius=0`。
- 悬停态：边框和文本变为 `COLOR_ACCENT_MAGENTA`，**取消 `hover_color` 的背景变化**（设定为 `hover_color=COLOR_BG` 以保证内部保持纯白，仅仅线框变红），彻底契合线框风 (Line Art)。

### 三、 给执行 Agent 的修复工作流建议：
1. **第一步**：建立 `ui_utils.py` 或扩充 `theme.py`，把上述的基础 UI 元素生成器（带边框下拉、章节 Header、统一 Entry）造好。
2. **第二步**：从 `controller_panel.py` 开始，用新工具函数替换 `_build_key_mapping_panel` 内的手写 UI，消灭 `#111827` 之类的裸露字符串。
3. **第三步**：打开 `record_tab.py`，将 `_build_record_tab` 从中间大刀阔斧地剪开，粘贴出 `_build_performance_panel`、`_build_metadata_panel` 和 `_build_action_panel`。
4. **第四步**：在各个子 panel 方法中，使用第一步封装的工具函数重刷组件；把内部定义的 def 挪到 class 顶层。
