-- ============================================================
-- 06 留存分析（两个口径，务必都跑，然后对比）
--
-- 口径 A：全站回访率 —— 对齐你原来 Python 里的算法
-- 口径 B：新客留存率 —— 真正的 cohort 留存口径
--
-- 两者的差别在于分母：A 用"当天所有活跃用户"，B 用"当天首次出现的用户"。
-- 你原来的代码是 A，但 README 写成了 B 的意思，这是要修正的地方。
-- ============================================================

-- ── 口径 A：全站活跃用户回访率 ──────────────────────────
WITH daily AS (
  SELECT DISTINCT user_id, DATE(dt) AS d
  FROM user_behavior
),
base AS (
  SELECT d, COUNT(*) AS base_users
  FROM daily
  GROUP BY d
),
r AS (
  SELECT d0.d                        AS base_d,
         DATEDIFF(d1.d, d0.d)        AS day_offset,
         COUNT(DISTINCT d1.user_id)  AS retained
  FROM daily d0
  JOIN daily d1
    ON d0.user_id = d1.user_id
   AND d1.d > d0.d
   AND DATEDIFF(d1.d, d0.d) <= 7
  GROUP BY d0.d, day_offset
)
SELECT b.d                        AS 基准日,
       b.base_users               AS 基准活跃用户,
       MAX(CASE WHEN r.day_offset = 1 THEN r.retained END) AS Day1,
       MAX(CASE WHEN r.day_offset = 2 THEN r.retained END) AS Day2,
       MAX(CASE WHEN r.day_offset = 3 THEN r.retained END) AS Day3,
       MAX(CASE WHEN r.day_offset = 4 THEN r.retained END) AS Day4,
       MAX(CASE WHEN r.day_offset = 5 THEN r.retained END) AS Day5,
       MAX(CASE WHEN r.day_offset = 6 THEN r.retained END) AS Day6,
       MAX(CASE WHEN r.day_offset = 7 THEN r.retained END) AS Day7
FROM base b
LEFT JOIN r ON b.d = r.base_d
GROUP BY b.d, b.base_users
ORDER BY b.d;

-- ── 口径 B：新客留存（cohort）────────────────────────────
-- 注意：数据集只有 9 天，最后几天的 Day7 是观测不完整的，
-- 会显示出偏低的留存率，解读时必须说明，否则结论是错的。
WITH first_seen AS (
  SELECT user_id, DATE(MIN(dt)) AS first_d
  FROM user_behavior
  GROUP BY user_id
),
daily AS (
  SELECT DISTINCT user_id, DATE(dt) AS d
  FROM user_behavior
),
cohort AS (
  SELECT f.first_d AS cohort_d,
         f.user_id,
         DATEDIFF(dl.d, f.first_d) AS day_offset
  FROM first_seen f
  JOIN daily dl ON f.user_id = dl.user_id
  WHERE DATEDIFF(dl.d, f.first_d) BETWEEN 0 AND 7
)
SELECT cohort_d AS 首日,
       COUNT(DISTINCT user_id) AS 新增用户,
       ROUND(COUNT(DISTINCT CASE WHEN day_offset = 1 THEN user_id END)
             * 100.0 / COUNT(DISTINCT user_id), 2) AS 次日留存率,
       ROUND(COUNT(DISTINCT CASE WHEN day_offset = 3 THEN user_id END)
             * 100.0 / COUNT(DISTINCT user_id), 2) AS 三日留存率,
       ROUND(COUNT(DISTINCT CASE WHEN day_offset = 7 THEN user_id END)
             * 100.0 / COUNT(DISTINCT user_id), 2) AS 七日留存率
FROM cohort
GROUP BY cohort_d
ORDER BY cohort_d;
