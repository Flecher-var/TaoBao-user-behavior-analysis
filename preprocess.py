"""
数据处理层（SQL 化之后）。

原来的 preprocess.py 用 pandas 读 3.6 GB 的 CSV、分块清洗、再 concat 成一个大
DataFrame：1 亿行全量加载要十几 GB 内存，这也是这个项目必须改成 SQL 的原因。
现在这一层只剩两件事——连数据库、把结果取成 DataFrame。
清洗、聚合、漏斗、留存、RFM 全部在 sql/ 里用 SQL 完成。

其它脚本里的 `from preprocess import *` 仍然有效：
    build_engine()        建数据库连接
    query(sql)            跑一条查询，返回 DataFrame
    read_sql_file(path)   读 sql/ 目录下的脚本原文（指标口径的唯一定义处）
    ensure_dirs()         保证 results/ 和 images/ 存在
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ── 改这里 ────────────────────────────────────────────────
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",       # <- 改成你的 MySQL 密码
    "database": "taobao",
}

PROJECT_DIR = Path(__file__).resolve().parent
SQL_DIR = PROJECT_DIR / "sql"
RESULTS_DIR = PROJECT_DIR / "results"
IMAGES_DIR = PROJECT_DIR / "images"
DATA_FILE = PROJECT_DIR / "UserBehavior.csv"
# ─────────────────────────────────────────────────────────

# 画图用的中文字体（Windows 自带）
FONT_CANDIDATES = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]


def build_engine() -> Engine:
    url = (
        f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}"
        f"@{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}"
        "?charset=utf8mb4"
    )
    return create_engine(url, pool_recycle=3600, pool_pre_ping=True)


def query(sql: str, engine: Engine | None = None) -> pd.DataFrame:
    """跑一条 SELECT，返回 DataFrame。"""
    engine = engine or build_engine()
    return pd.read_sql(text(sql), engine)


def scalar(sql: str, engine: Engine | None = None):
    """只要一个值（COUNT 之类）。"""
    df = query(sql, engine)
    return df.iloc[0, 0] if len(df) else None


def read_sql_file(path: str | Path) -> str:
    """读 sql/ 下的脚本原文。"""
    p = Path(path)
    if not p.is_absolute():
        p = SQL_DIR / p
    return p.read_text(encoding="utf-8")


def load_result(filename: str) -> pd.DataFrame:
    """读 run_sql.py 导出的结果 CSV（results/<脚本名>__<第几条语句>.csv）。"""
    p = RESULTS_DIR / filename
    if not p.exists():
        raise FileNotFoundError(
            f"找不到 {p}。\n"
            "画图脚本读的是 run_sql.py 导出的结果，请先在项目根目录执行：\n"
            "    python run_sql.py            # 数据已在库里时\n"
            "    python run_sql.py --all      # 第一次跑（建表 + 灌数据 + 建索引）"
        )
    return pd.read_csv(p, encoding="utf-8-sig")


def read_result(script: str, statement: int) -> pd.DataFrame:
    """按「脚本名 + 第几条语句」读结果。

    例：read_result('05_funnel', 2) -> results/05_funnel__02.csv
    编号和 sql/ 里的语句顺序一一对应（注释行不算语句）。
    """
    return load_result(f"{script}__{statement:02d}.csv")


def ensure_dirs() -> None:
    RESULTS_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)


def setup_matplotlib() -> None:
    """统一字体和保存参数：图里中文不会变方块，存出来的图也不是糊的。"""
    import matplotlib

    matplotlib.use("Agg")          # 不弹窗，直接存文件
    matplotlib.rcParams["font.sans-serif"] = FONT_CANDIDATES
    matplotlib.rcParams["axes.unicode_minus"] = False
    matplotlib.rcParams["figure.dpi"] = 120
    matplotlib.rcParams["savefig.dpi"] = 150
    matplotlib.rcParams["savefig.bbox"] = "tight"


def main() -> int:
    """冒烟测试：连上库，看一眼数据在不在。"""
    engine = build_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    n = scalar("SELECT COUNT(*) FROM user_behavior", engine)
    print(f"[OK] 连上 {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    print(f"[OK] user_behavior 现有 {n:,} 行")
    if n == 0:
        print("     -> 还没有数据，先跑 python run_sql.py --all")
        return 1

    df = query(
        """
        SELECT behavior_type AS 行为, COUNT(*) AS 次数
        FROM user_behavior
        GROUP BY behavior_type
        ORDER BY 次数 DESC
        """,
        engine,
    )
    print(df.to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
