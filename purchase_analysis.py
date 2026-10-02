"""
付费行为分析：复购、加购收藏比、类目偏好、活跃时段（SQL 算，本脚本只读结果画图）。

数据来源：run_sql.py 导出的 CSV
    results/10_repurchase__01.csv   复购率
    results/10_repurchase__02.csv   加购 / 收藏比
    results/10_repurchase__03.csv   复购次数分布
    results/10_repurchase__04.csv   购买量 Top10 类目
    results/10_repurchase__05.csv   高价值用户的下单时段
    results/09_hourly__01.csv       24 小时活跃分布
执行顺序：python run_sql.py  然后  python purchase_analysis.py

对应原版 purchase_analysis.py 的几件事：
    转化比 PV/Buy  -> 改用用户级漏斗，见 funnel.py（事件比没有业务含义）
    品类偏好       -> sql/10 ④
    复购率         -> sql/10 ①
    加购/收藏比    -> sql/10 ②
另外补上原 README 提到过、但代码里没有实现的两件事：小时分布、高价值用户下单时段。

输出：images/hourly_activity.png、images/top_categories.png
"""

import matplotlib.pyplot as plt

from preprocess import *


def plot_hourly(df) -> None:
    fig, ax = plt.subplots(figsize=(10, 4.2))
    ax.bar(df["小时"], df["行为数"], color="#4C72B0", label="每小时行为数")
    ax.set_xlabel("小时（0-23）")
    ax.set_ylabel("行为数")
    ax.set_xticks(range(0, 24))

    ax2 = ax.twinx()
    ax2.plot(df["小时"], df["累计占比"], color="#C44E52", marker="o", ms=3, label="累计占比(%)")
    ax2.axhline(85, color="gray", linestyle="--", linewidth=1)
    ax2.set_ylabel("累计占比 (%)")
    ax2.set_ylim(0, 105)

    ax.set_title("24 小时活跃分布（累计占比按 0->23 自然顺序，虚线=85%）")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9)
    plt.savefig(IMAGES_DIR / "hourly_activity.png")
    plt.close(fig)


def plot_top_categories(df) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.5))
    data = df.iloc[::-1]                      # 从下往上画，最大的类目在最上面
    labels = data["类目ID"].astype(str)
    ax.barh(labels, data["购买次数"], color="#55A868")
    for i, v in enumerate(data["购买次数"]):
        ax.text(v, i, f" {v:,}", va="center", fontsize=9)
    ax.set_xlabel("购买次数")
    ax.set_ylabel("类目 ID")
    ax.set_xlim(0, float(df["购买次数"].max()) * 1.18)
    ax.set_title("购买量 Top 10 类目（买得多 ≠ 转化好，转化率排行见 sql/05 ③）")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    plt.savefig(IMAGES_DIR / "top_categories.png")
    plt.close(fig)


def main() -> int:
    ensure_dirs()
    setup_matplotlib()

    summary = read_result("10_repurchase", 1)
    cart_fav = read_result("10_repurchase", 2)
    dist = read_result("10_repurchase", 3)
    cats = read_result("10_repurchase", 4)
    hourly = read_result("09_hourly", 1)

    print("=== 复购率 ===")
    print(summary.to_string(index=False))
    print("\n=== 付费用户的加购 / 收藏 ===")
    print(cart_fav.to_string(index=False))
    print("\n=== 复购次数分布 ===")
    print(dist.to_string(index=False))
    print("\n=== 购买量 Top 10 类目 ===")
    print(cats.to_string(index=False))
    print("\n=== 小时分布（前 5 行）===")
    print(hourly.head().to_string(index=False))

    plot_hourly(hourly)
    plot_top_categories(cats)
    print("\n已保存 images/hourly_activity.png、images/top_categories.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
