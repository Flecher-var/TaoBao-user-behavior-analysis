"""
留存热力图。数据来自 retention.daily_retention()，即 SQL 口径 A 的结果 CSV。

注意：口径 A 的分母为「当天所有活跃用户」，因此该指标为回访率。
末尾几天的 Day7 观测窗口不完整（数据仅到 2017-12-03），热力图右下角会留空或偏浅；
此外 12-02、12-03 的覆盖率接近 100%，落在其上的格子会天然偏深，解读时必须说明。

输出：images/retention_heatmap.png
"""

import matplotlib.pyplot as plt
import seaborn as sns

from preprocess import *
from retention import daily_retention


def plot_retention_heatmap(retention_df):
    cols = [f"Day{i}率" for i in range(1, 8)]
    plot_data = retention_df.set_index("基准日")[cols]
    plot_data.columns = [f"Day{i}" for i in range(1, 8)]

    fig, ax = plt.subplots(figsize=(12, 7))
    sns.heatmap(
        plot_data,
        annot=True,
        fmt=".1f",
        cmap="YlGnBu",
        linewidths=0.5,
        cbar_kws={"label": "回访率 (%)"},
        ax=ax,
    )
    ax.set_title("用户回访率热力图（2017-11-25 ~ 12-03，分母=当日活跃用户）", fontsize=14)
    ax.set_xlabel("距基准日的天数")
    ax.set_ylabel("基准日期")
    plt.xticks(rotation=45)
    plt.savefig(IMAGES_DIR / "retention_heatmap.png")
    plt.close(fig)


def main() -> int:
    ensure_dirs()
    setup_matplotlib()
    plot_retention_heatmap(daily_retention())
    print("已保存 images/retention_heatmap.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
