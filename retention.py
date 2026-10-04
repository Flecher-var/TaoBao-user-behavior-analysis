"""
留存分析：两种口径均予计算（由 SQL 计算，本脚本仅整理结果）。

数据来源：results/06_retention__01.csv（口径 A）、results/06_retention__02.csv（口径 B），
由 run_sql.py 执行 sql/06_retention.sql 时导出。
执行顺序：python run_sql.py  随后  python retention.py

口径 A：全站活跃用户回访率 —— 分母为「当天所有活跃用户」。
        严格而言是回访率，并非留存率。
口径 B：新客留存（cohort）—— 分母为「当天首次出现的用户」，这才是留存。
两者分母不同，结论完全不同。

⚠ 读取留存结果前应先查看目标日的用户覆盖率：12-02 / 12-03 的活跃用户占全站 98% 以上，
任何「目标日落在两天」的留存率都会自动接近 98%，那是覆盖率而非留存。

输出：results/retention_daily.csv、results/retention_cohort.csv（含留存率的整理版）
"""

import pandas as pd

from preprocess import *


def daily_retention() -> pd.DataFrame:
    """口径 A：将 CSV 中的留存人数换算为留存率（%）。"""
    df = read_result("06_retention", 1)
    for i in range(1, 8):
        df[f"Day{i}率"] = (df[f"Day{i}"] / df["基准活跃用户"] * 100).round(2)
    return df


def cohort_retention() -> pd.DataFrame:
    """口径 B：新客留存。数据集仅有 9 天，末尾几天的 7 日留存观测不完整。"""
    return read_result("06_retention", 2)


def main() -> int:
    ensure_dirs()

    daily = daily_retention()
    rate_cols = ["基准日", "基准活跃用户"] + [f"Day{i}率" for i in range(1, 8)]
    print("=== 口径 A：全站活跃用户回访率（%）===")
    print(daily[rate_cols].to_string(index=False))

    cohort = cohort_retention()
    print("\n=== 口径 B：新客留存（%）===")
    print(cohort.to_string(index=False))

    daily.to_csv(RESULTS_DIR / "retention_daily.csv", index=False, encoding="utf-8-sig")
    cohort.to_csv(RESULTS_DIR / "retention_cohort.csv", index=False, encoding="utf-8-sig")
    print("\n已保存 results/retention_daily.csv、results/retention_cohort.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
