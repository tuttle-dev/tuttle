import flet
from flet.matplotlib_chart import MatplotlibChart

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider

matplotlib.use("svg")
from flet import UserControl

from custom_flet.custom_mat_chart import CustomMatplotlibChart
from res.colors import BLACK_COLOR, GRAY_COLOR, PRIMARY_COLOR, WHITE_COLOR
from res.fonts import BODY_1_SIZE


class BarChart(UserControl):
    """Displays a bar chart"""

    def __init__(
        self,
        x_items_labels: list,
        values: list,
        y_label: str,
        chart_title: str = "",
        x_label: str = "legend",
        legend: str = "",
        bar_color: str = PRIMARY_COLOR,
        labels_color: str = GRAY_COLOR,
    ):
        super().__init__()
        self.figure, self.axes = plt.subplots()
        legends_per_item = []
        bar_colors = []
        first_item = True
        GOOD_WIDTH_FOR_SEVEN_ITEMS = 0.6
        total_items = len(x_items_labels)
        for i in range(0, total_items):
            """prefix color with _ to not display this color in legend
            we only use 1 color but the legends and bar_colors parameters
            need to be of same size as our x items
            """
            legend_for_item = legend if first_item else "_" + legend
            legends_per_item.append(legend_for_item)
            bar_colors.append(bar_color)
            first_item = False

        self.axes.bar(x_items_labels, values, label=legends_per_item, color=bar_colors)
        self.axes.set_ylabel(y_label)
        self.axes.set_xlabel(x_label)
        self.axes.spines["top"].set_visible(False)
        self.axes.spines["right"].set_visible(False)
        self.apply_labels_color(labels_color)
        self._chart_title = chart_title
        self._set_title_color(labels_color)
        self.axes.legend(
            title="",
            facecolor=WHITE_COLOR,
            edgecolor=WHITE_COLOR,
            framealpha=1,
            loc="best",
        )

    def apply_labels_color(self, color: str):
        self.axes.yaxis.label.set_color(color)
        self.axes.xaxis.label.set_color(color)
        self.axes.spines["bottom"].set_color(color)
        self.axes.spines["left"].set_color(color)
        self.axes.tick_params(axis="x", colors=color)
        self.axes.tick_params(axis="y", colors=color)

    def _set_title_color(self, color: str):
        self.axes.set_title(
            self._chart_title, color=color, fontsize=BODY_1_SIZE, loc="left", y=1.05
        )

    def update(self):
        self.chart.update()

    def build(self):
        self.chart = CustomMatplotlibChart(
            self.figure,
            isolated=True,
        )
        return self.chart
