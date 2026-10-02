"""
把 sql/ 下的脚本按顺序跑一遍，每个 SELECT 的结果自动存到 results/。

为什么需要它：
  1 亿行的库不适合在 DBeaver 里一条条贴——跑完还不知道结果存哪了。
  这个脚本让「SQL 化」有个正式的入口：一条命令跑完全流程，结果落在 results/，
  后面画图和写 README 都从 results/ 取数，可复现、可对账。

用法（在项目根目录）：
    python run_sql.py --all         全流程：建表 -> 灌数据 -> 建索引 -> 核对 -> 分析
    python run_sql.py               跳过 01/02/03，只跑核对和分析（数据已在库里时用这个）
    python run_sql.py --load        只跑 01/02/03（建表 + 灌数据 + 建索引）
    python run_sql.py --only 05 06  只跑文件名以 05 / 06 开头的脚本
    python run_sql.py --dry-run     只列将要执行的文件，不连数据库

结果文件名规则：results/<脚本名>__<第几条语句>.csv
    例：results/05_funnel__2.csv  = 05_funnel.sql 里的第 2 条 SELECT
导出用 utf-8-sig，Excel 双击打开不乱码。
"""

from __future__ import annotations

import argparse
import csv
import sys
import threading
import time
from pathlib import Path

import pymysql

from preprocess import DB_CONFIG, RESULTS_DIR, SQL_DIR

# 默认跳过的建表/灌数据脚本（数据已经在库里时不该重跑）
SETUP_PREFIXES = ("01", "02", "03")


# ── SQL 切分 ───────────────────────────────────────────────
def split_statements(sql_text: str) -> list[str]:
    """把脚本切成一条条语句。足够应付本项目：整行注释会被去掉，
    分号只在引号外才算分隔符。"""
    cleaned_lines = []
    for line in sql_text.splitlines():
        cleaned_lines.append("" if line.strip().startswith("--") else line)
    text = "\n".join(cleaned_lines)

    statements: list[str] = []
    buf: list[str] = []
    quote: str | None = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\" and quote in ("'", '"'):
                buf.append(ch)
                i += 1
                if i < len(text):
                    buf.append(text[i])
                i += 1
                continue
            if ch == quote:
                quote = None
            buf.append(ch)
        else:
            if ch in ("'", '"', "`"):
                quote = ch
                buf.append(ch)
            elif ch == ";":
                stmt = "".join(buf).strip()
                if stmt:
                    statements.append(stmt)
                buf = []
            else:
                buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def first_keyword(stmt: str) -> str:
    return stmt.lstrip().split(None, 1)[0].upper() if stmt.strip() else ""


# ── 长语句的“还在跑”提示 ───────────────────────────────────
class Heartbeat(threading.Thread):
    """LOAD DATA / 建索引要跑十几分钟，期间没有任何输出，
    这个线程每 30 秒打一行，免得你以为卡死了。"""

    def __init__(self, label: str, every: int = 30):
        super().__init__(daemon=True)
        self.label = label
        self.every = every
        self._stop = threading.Event()
        self.started = time.time()

    def run(self) -> None:
        while not self._stop.wait(self.every):
            print(f"      ... {self.label} 还在跑，已用 {time.time() - self.started:,.0f} 秒")

    def stop(self) -> None:
        self._stop.set()


# ── 打印结果预览 ───────────────────────────────────────────
def preview(columns, rows, limit: int = 8) -> None:
    cols = [str(c) for c in columns]
    body = [["" if v is None else str(v) for v in r] for r in rows[:limit]]
    widths = [len(c) for c in cols]
    for r in body:
        for i, v in enumerate(r):
            widths[i] = max(widths[i], min(len(v), 28))

    def line(values):
        cells = []
        for i, v in enumerate(values):
            v = v[:28]
            pad = widths[i] - sum(2 if ord(ch) > 127 else 1 for ch in v)
            cells.append(v + " " * max(pad, 0))
        return "  " + " | ".join(cells)

    print(line(cols))
    print("  " + "-+-".join("-" * w for w in widths))
    for r in body:
        print(line(r))
    if len(rows) > limit:
        print(f"  ...（共 {len(rows):,} 行，完整结果见导出的 CSV）")


def export_csv(path: Path, columns, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow([str(c) for c in columns])
        w.writerows(rows)


# ── 挑选要跑的文件 ─────────────────────────────────────────
def pick_files(all_files: bool, load_only: bool, only: list[str]) -> list[Path]:
    files = sorted(SQL_DIR.glob("*.sql"))
    if only:
        return [f for f in files if any(f.stem.startswith(p) for p in only)]
    if load_only:
        return [f for f in files if f.stem.startswith(SETUP_PREFIXES)]
    if all_files:
        return files
    return [f for f in files if not f.stem.startswith(SETUP_PREFIXES)]


def connect():
    return pymysql.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        password=DB_CONFIG["password"],
        database=DB_CONFIG["database"],
        charset="utf8mb4",
        local_infile=True,      # LOAD DATA LOCAL INFILE 需要
        autocommit=True,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="按顺序执行 sql/ 下的脚本并导出结果")
    ap.add_argument("--all", action="store_true", help="连建表/灌数据/建索引一起跑")
    ap.add_argument("--load", action="store_true", help="只跑 01/02/03")
    ap.add_argument("--only", nargs="+", default=[], help="只跑指定前缀，如 --only 05 06")
    ap.add_argument("--dry-run", action="store_true", help="只列文件，不执行")
    args = ap.parse_args()

    files = pick_files(args.all, args.load, args.only)
    if not files:
        print("没有匹配到任何 sql 文件")
        return 1

    print(f"准备执行 {len(files)} 个脚本：")
    for f in files:
        print(f"  - sql/{f.name}")
    if args.dry_run:
        return 0

    RESULTS_DIR.mkdir(exist_ok=True)
    conn = connect()
    made: list[Path] = []
    started_all = time.time()

    try:
        with conn.cursor() as cur:
            for f in files:
                sql_text = f.read_text(encoding="utf-8")
                statements = split_statements(sql_text)
                print(f"\n=== {f.name}（{len(statements)} 条语句）===")
                t0 = time.time()

                for idx, stmt in enumerate(statements, start=1):
                    kw = first_keyword(stmt)
                    label = f"{f.name} 第 {idx} 条（{kw}）"
                    print(f"  -> {label}")
                    if kw == "LOAD":
                        print("     （1 亿行，10~20 分钟，别关窗口）")

                    hb = Heartbeat(label)
                    hb.start()
                    try:
                        cur.execute(stmt)
                        if cur.description:
                            rows = cur.fetchall()
                            cols = [d[0] for d in cur.description]
                            out = RESULTS_DIR / f"{f.stem}__{idx:02d}.csv"
                            export_csv(out, cols, rows)
                            made.append(out)
                            print(f"     [{len(rows):,} 行] -> results/{out.name}")
                            preview(cols, rows)
                        else:
                            print(f"     [OK] 影响 {cur.rowcount:,} 行")
                    finally:
                        hb.stop()

                print(f"  用时 {time.time() - t0:,.1f} 秒")
    finally:
        conn.close()

    print(f"\n全部完成，总用时 {time.time() - started_all:,.1f} 秒")
    if made:
        print(f"结果文件（{len(made)} 个）：")
        for p in made:
            print(f"  results/{p.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
