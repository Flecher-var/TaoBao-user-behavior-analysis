-- ============================================================
-- 06 留存分析（两种口径均予计算，便于对比）
--
-- 口径 A：全站活跃用户回访率 —— 与第一版 Python 的算法一致
-- 口径 B：新客留存（cohort）—— 分母为当天首次出现的用户
--
-- 两者仅分母不同：A 使用「当天所有活跃用户」，B 使用「当天首次出现的用户」。
-- 第一版代码实现的是 A，但 README 按 B 的语义描述，本次已更正。
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
-- 注意：数据集仅有 9 天，最后几天的 Day7 观测不完整，
-- 会显示出偏低的留存率，解读时必须说明，否则结论不成立。
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
