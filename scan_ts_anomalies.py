"""
扫描 UserBehavior.csv 里 ts 列的异常值。

背景：导入时报
    DataError: (1264, "Out of range value for column 'ts' at row 6225")
说明某些行的 ts 放不进 INT UNSIGNED（合法范围 0 ~ 4,294,967,295）。

用法：
    python scan_ts_anomalies.py

把下面的 CSV_PATH 改成你的实际路径再跑。
"""

import pandas as pd

# ── 改这里 ────────────────────────────────────────────────
CSV_PATH = r"E:/PycharmProjects/TaoBao-user-behavior-analysis/UserBehavior.csv"
# ─────────────────────────────────────────────────────────

COLUMNS = ["user_id", "item_id", "category_id", "behavior_type", "ts"]
DTYPES = {
    "user_id": "int64",
    "item_id": "int64",
    "category_id": "int64",
    "behavior_type": "object",
    "ts": "int64",
}

TS_MAX_UNSIGNED = 4_294_967_295          # INT UNSIGNED 的上限


def main() -> None:
    total = 0
    neg_count = 0
    over_count = 0
    samples: list[dict] = []

    reader = pd.read_csv(
        CSV_PATH,
        header=None,
        names=COLUMNS,
        dtype=DTYPES,
        chunksize=1_000_000,
    )

    for idx, chunk in enumerate(reader, start=1):
        total += len(chunk)

        bad = chunk[(chunk["ts"] < 0) | (chunk["ts"] > TS_MAX_UNSIGNED)]
        neg_count += int((chunk["ts"] < 0).sum())
        over_count += int((chunk["ts"] > TS_MAX_UNSIGNED).sum())

        if len(samples) < 10 and len(bad):
            for _, row in bad.head(10 - len(samples)).iterrows():
                samples.append(dict(row))

        print(
            f"第 {idx} 块 | 已扫 {total:>12,} 行 | "
            f"负数 {neg_count:>8,} | 超上限 {over_count:>8,}"
        )

    print()
    print("=" * 56)
    print(f"总行数              : {total:,}")
    print(f"ts 为负数           : {neg_count:,}")
    print(f"ts 超过 42.9 亿     : {over_count:,}")
    print(f"异常合计            : {neg_count + over_count:,}")
    print("=" * 56)

    if samples:
        print("\n异常样本（最多 10 条）：")
        for s in samples:
            ts = s["ts"]
            print(
                f"  ts={ts:<22} "
                f"user_id={s['user_id']:<10} "
                f"item_id={s['item_id']:<10} "
                f"behavior={s['behavior_type']}"
            )
    else:
        print("\n没有发现 ts 异常。")


if __name__ == "__main__":
    main()
