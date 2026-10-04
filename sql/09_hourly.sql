-- ============================================================
-- 09 小时级活跃分布 + 核心时段
--
-- 这一条专门修掉原项目里的一个逻辑错误：
--   preprocess.py 先按「热度」降序排小时、再算累计百分比，然后把这一组
--   「最热的小时」的 min 和 max 打印成「85% 流量集中在 X 点到 Y 点」。
--   但热门小时未必连续（可能是 12、20、21、22 点），中间的小时并不热，
--   直接说成「X 点到 Y 点」是错的。
--   正确做法：按小时的自然顺序 0 -> 23 累计，看累计占比在哪一刻越过 85%。
-- ============================================================

-- ① 24 小时分布（按自然顺序，不是按热度）
WITH hourly AS (
  SELECT HOUR(dt) AS h,
         COUNT(*) AS behaviors
  FROM user_behavior
  GROUP BY HOUR(dt)
)
SELECT h AS 小时,
       behaviors AS 行为数,
       ROUND(behaviors * 100.0 / SUM(behaviors) OVER (), 2) AS 占比,
       ROUND(SUM(behaviors) OVER (ORDER BY h) * 100.0
             / SUM(behaviors) OVER (), 2) AS 累计占比
FROM hourly
ORDER BY h;

-- ② 核心时段：从 0 点开始累加，累计占比刚越过 85% 的那个小时
WITH hourly AS (
  SELECT HOUR(dt) AS h, COUNT(*) AS behaviors
  FROM user_behavior
  GROUP BY HOUR(dt)
),
cum AS (
  SELECT h,
         SUM(behaviors) OVER (ORDER BY h) AS running,
         SUM(behaviors) OVER ()            AS total
  FROM hourly
)
SELECT MIN(h) AS 起始小时,
       MIN(CASE WHEN running >= total * 0.85 THEN h END) AS 覆盖85百分比的小时,
       ROUND(100.0 * MIN(CASE WHEN running >= total * 0.85 THEN running END)
             / MAX(total), 2) AS 该小时累计占比
FROM cum;

-- ③ 双十二前后（12-01 ~ 12-03）的逐小时对比，看大促时段偏移
SELECT DATE(dt) AS 日期,
       HOUR(dt) AS 小时,
       COUNT(*) AS 行为数
FROM user_behavior
WHERE dt >= '2017-12-01'
GROUP BY DATE(dt), HOUR(dt)
ORDER BY 日期, 小时;
