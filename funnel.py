"""
用户级转化漏斗：SQL 算，本脚本只读结果画图。

数据来源（run_sql.py 跑 sql/05_funnel.sql 时导出的两份 CSV）：
    results/05_funnel__01.csv   漏斗总览（一行）
    results/05_funnel__02.csv   漏斗分层明细
所以执行顺序是：
    python run_sql.py      然后    python funnel.py

口径（见 sql/05_funnel.sql）：
  * 所有比例都按「去重用户数」算，不是行为事件数之比。
  * 收藏(fav) 和加购(cart) 是并列分支，不是先后步骤，所以漏斗是
    「浏览 -> 加购或收藏 -> 购买」三段，不是四段链。
以前那种直接 value_counts() 得到「33 次点击换 1 次购买」的算法是错的——
那是事件比，同一个用户点 30 次会算 30 次。

输出：images/funnel.png
"""

import pandas as pd
import matplotlib.pyplot as plt

from preprocess import *


def plot(steps: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    y = list(range(len(steps)))
    names = list(steps["环节"])
    values = list(steps["用户数"])
    ax.barh(y, values, color=["#4C72B0", "#DD8452", "#55A868"])

    top = max(values) if values else 1
    for i, v in enumerate(values):
        rate = steps["相对上一层转化率"].iloc[i]
        label = f"{v:,}"
        if pd.notna(rate):
            label += f"   上一层转化 {rate:.2f}%"
        ax.text(v + top * 0.01, i, label, va="center", fontsize=10)

    ax.set_yticks(y)
    ax.set_yticklabels(names)
    ax.invert_yaxis()
    ax.set_xlabel("用户数")
    ax.set_xlim(0, top * 1.3)
    ax.set_title("用户级转化漏斗（去重用户口径）")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    plt.savefig(IMAGES_DIR / "funnel.png")
    plt.close(fig)


def main() -> int:
    ensure_dirs()
    setup_matplotlib()

    overall = read_result("05_funnel", 1)
    steps = read_result("05_funnel", 2)

    print("=== 漏斗总览（一行）===")
    print(overall.T.to_string(header=False))
    print("\n=== 漏斗分层 ===")
    print(steps.to_string(index=False))

    plot(steps)
    print("\n已保存 images/funnel.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
