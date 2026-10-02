"""
用户价值分层（R + F）。

数据来源：results/07_rfm__01.csv（run_sql.py 跑 sql/07_rfm.sql 导出的）。
执行顺序：python run_sql.py  然后  python rfm.py

为什么不是 RFM：数据集没有商品单价和订单金额，M（Monetary）算不出来。
原项目「文件名叫 RFM、函数叫 RF_analysis、README 写 RFM」三处不一致，
这里统一改成 RF，并在 README 里说明原因——主动承认限制比含糊带过好。

分档口径见 sql/07_rfm.sql：
    R = 期末日期 - 该用户最近一次购买日期（越小越好）
    F = 购买次数（越大越好）
    各自 NTILE(4) 分 4 档，>=3 视为高，交叉成 2x2 四象限。

注意：R 与 F 高度相关（买得多的人通常最近也买过），而 NTILE 强制分成两高两低，
所以两个混合象限人数会完全相等，这是分档方式的产物，不要过度解读。

输出：images/rfm_segments.png
"""

import matplotlib.pyplot as plt

from preprocess import *


def plot(df) -> None:
    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.bar(df["用户分层"], df["人数"], color="#4C72B0")
    for x, (n, p) in enumerate(zip(df["人数"], df["占比"])):
        ax.text(x, n, f"{n:,}\n{p:.2f}%", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("人数")
    ax.set_ylim(0, float(df["人数"].max()) * 1.25)
    ax.set_title("RF 用户价值分层（按期末购买时间与购买次数各分 4 档）")
    ax.grid(axis="y", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)
    plt.savefig(IMAGES_DIR / "rfm_segments.png")
    plt.close(fig)


def main() -> int:
    ensure_dirs()
    setup_matplotlib()
    df = read_result("07_rfm", 1)
    print(df.to_string(index=False))
    plot(df)
    print("\n已保存 images/rfm_segments.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
