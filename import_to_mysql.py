"""
小批量导入工具（仅导一天 / 仅导 N 行）。全量导入请使用 SQL。

本项目「SQL 化」之后，正式的导入方式为 sql/02_load_data.sql 中的
LOAD DATA LOCAL INFILE —— 1 亿行约十几分钟，一条命令即可完成：

    python run_sql.py --all        # 建表 + LOAD DATA + 建索引 + 跑分析
    python run_sql.py --load       # 仅执行导入环节

保留本脚本的原因：它具备 LOAD DATA 无法实现的两项能力：
  - 仅导入某一天（--date），几分钟即可跑通整条链路（导入 -> SQL 分析 -> 绘图）
  - 仅导入 N 行（--limit），调试 SQL 语法时无需等待全量导入
代价是速度较慢：pandas 分块 + 批量 INSERT，1 亿行需要数小时。

用法：
    python import_to_mysql.py --date 2017-11-25     # 仅导入一天
    python import_to_mysql.py --limit 1000000       # 仅导入 100 万行
    python import_to_mysql.py                       # 全量（不推荐，请使用 LOAD DATA）
"""

import argparse
import os
import sys
import time
from pathlib import Path

try:
    import pandas as pd
    from sqlalchemy import create_engine, text
except ImportError:
    print(
        "缺少依赖。请先执行：\n"
        "    pip install -r requirements.txt"
    )
    sys.exit(1)


# ── 配置区 ────────────────────────────────────────────────
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",          # <- 请修改为实际密码
    "database": "taobao",           # <- 请先在 MySQL 中执行 CREATE DATABASE taobao;
}
CSV_PATH = r"E:/PycharmProjects/TaoBao-user-behavior-analysis/UserBehavior.csv"   # <- 请修改为本机实际路径
# ─────────────────────────────────────────────────────────

PLACEHOLDER_PASSWORD = "你的密码"
PLACEHOLDER_CSV = r"D:/data/UserBehavior.csv"

COLUMNS = ["user_id", "item_id", "category_id", "behavior_type", "ts"]
DTYPES = {
    "user_id": "int64",
    "item_id": "int64",
    "category_id": "int64",
    "behavior_type": "object",
    "ts": "int64",
}
CHUNK_SIZE = 500_000


def build_engine():
    url = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        "?charset=utf8mb4"
    )
    return create_engine(url, pool_recycle=3600)


def preflight():
    """在开始导入前，一次性检查最常见的问题。"""
    ok = True

    # 1) 配置是否仍为占位符
    if DB_CONFIG["password"] == PLACEHOLDER_PASSWORD:
        print("[X] 还没改密码：请把脚本里 DB_CONFIG 的 password 改成你的 MySQL root 密码")
        ok = False
    if CSV_PATH == PLACEHOLDER_CSV and not Path(CSV_PATH).exists():
        print(
            "[X] 还没改数据路径：请把 CSV_PATH 改成 UserBehavior.csv 在本机的位置\n"
            "    （Windows 路径用正斜杠，例如 E:/data/UserBehavior.csv）"
        )
        ok = False

    # 2) 数据文件是否确实存在
    if not Path(CSV_PATH).exists():
        print(f"[X] 找不到数据文件：{CSV_PATH}")
        print("    请确认已从天池下载并解压 UserBehavior.csv，且路径填写正确")
        ok = False
    else:
        size_gb = os.path.getsize(CSV_PATH) / 1024 ** 3
        print(f"[OK] 数据文件 {CSV_PATH}（{size_gb:.2f} GB）")

    if not ok:
        return None

    # 3) 数据库是否可连接、目标表是否已创建
    engine = build_engine()
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"[X] 连不上 MySQL：{exc}")
        print("    检查：MySQL 服务是否在运行 / 用户名密码是否正确 / 端口是否 3306")
        return None

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT COUNT(*) FROM user_behavior"))
    except Exception:
        print("[X] 表 user_behavior 不存在")
        print("    请先在 DBeaver 里执行 sql/01_create_table.sql")
        return None

    print("[OK] 数据库连接正常，目标表已存在")
    return engine


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--date",
        default=None,
        help="只导入某一天，例如 2017-11-25；不传则全量",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最多导入多少行，用于快速测试",
    )
    args = parser.parse_args()

    engine = preflight()
    if engine is None:
        print("\n检查未通过，已中止。先解决上面的问题再运行。")
        return 1

    if args.date:
        day_start = pd.Timestamp(args.date)
        ts_lo = int(day_start.timestamp())
        ts_hi = int((day_start + pd.Timedelta(days=1)).timestamp())
        print(f"\n只导入 {args.date}（ts 区间 {ts_lo} ~ {ts_hi}）")
    else:
        ts_lo = ts_hi = None
        print("\n全量导入")

    total_in = 0
    total_kept = 0
    started = time.time()

    reader = pd.read_csv(
        CSV_PATH,
        header=None,
        names=COLUMNS,
        dtype=DTYPES,
        chunksize=CHUNK_SIZE,
    )

    for idx, chunk in enumerate(reader, start=1):
        total_in += len(chunk)

        if ts_lo is not None:
            chunk = chunk[(chunk["ts"] >= ts_lo) & (chunk["ts"] < ts_hi)]
        if args.limit is not None:
            room = args.limit - total_kept
            if room <= 0:
                break
            chunk = chunk.head(room)
        if chunk.empty:
            continue

        chunk = chunk[
            (chunk["user_id"] >= 0) & (chunk["user_id"] <= 4_294_967_295)
            & (chunk["item_id"] >= 0) & (chunk["item_id"] <= 4_294_967_295)
            & (chunk["category_id"] >= 0) & (chunk["category_id"] <= 4_294_967_295)
            & (chunk["ts"] >= 0) & (chunk["ts"] <= 4_294_967_295)
            ]
        chunk = chunk.copy()
        chunk["dt"] = pd.to_datetime(chunk["ts"], unit="s")

        chunk.to_sql(
            "user_behavior",
            con=engine,
            if_exists="append",
            index=False,
            chunksize=10_000,
            method="multi",          # 批量 INSERT，比默认方式快数倍
        )

        total_kept += len(chunk)
        elapsed = time.time() - started
        print(
            f"  第 {idx} 块 | 已读 {total_in:,} 行 | "
            f"已写入 {total_kept:,} 行 | 用时 {elapsed:,.0f}s"
        )

    print(f"\n完成：读取 {total_in:,} 行，写入 {total_kept:,} 行")
    print("下一步：执行 sql/04_data_quality.sql 核对数据")
    return 0


if __name__ == "__main__":
    sys.exit(main())
