"""报告和绘图适配器。"""

__all__ = [
    "MatplotlibPlotter",
    "TextReportRenderer",
]


def __getattr__(name: str):
    if name == "MatplotlibPlotter":
        from .matplotlib_plotter import MatplotlibPlotter

        return MatplotlibPlotter
    if name == "TextReportRenderer":
        from .text_report_renderer import TextReportRenderer

        return TextReportRenderer
    raise AttributeError(name)
