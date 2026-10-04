-- ============================================================
-- 04 数据质量核对
-- ============================================================

-- ① 总量与范围
SELECT COUNT(*)                  AS 行为总数,
       COUNT(DISTINCT user_id)   AS 用户数,
       COUNT(DISTINCT item_id)   AS 商品数,
       COUNT(DISTINCT category_id) AS 类目数,
       MIN(dt)                   AS 最早时间,
       MAX(dt)                   AS 最晚时间
FROM user_behavior;

-- ② 行为类型分布（pv 应占绝大多数，buy 最少，这是常识性检查）
SELECT behavior_type AS 行为类型,
       COUNT(*)      AS 次数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
FROM user_behavior
GROUP BY behavior_type
ORDER BY 次数 DESC;

-- ③ 每日行为量与活跃用户（找异常日期 / 大促波动）
SELECT DATE(dt)               AS 日期,
       COUNT(*)               AS 行为数,
       COUNT(DISTINCT user_id) AS 活跃用户
FROM user_behavior
GROUP BY DATE(dt)
ORDER BY 日期;

-- ④ 重复行检查：同一用户、同一商品、同一行为、同一秒出现多条
SELECT COUNT(*) AS 重复行数
FROM (
  SELECT user_id, item_id, behavior_type, ts, COUNT(*) AS c
  FROM user_behavior
  GROUP BY user_id, item_id, behavior_type, ts
  HAVING c > 1
) t;

-- ⑤ 异常活跃用户（疑似爬虫 / 机器账号）
SELECT user_id,
       COUNT(*)          AS 行为数,
       COUNT(DISTINCT DATE(dt)) AS 活跃天数,
       COUNT(*) / COUNT(DISTINCT DATE(dt)) AS 日均行为数
FROM user_behavior
GROUP BY user_id
ORDER BY 行为数 DESC
LIMIT 20;

-- ⑥ 空值检查（COUNT(*) 减 COUNT(列) 就是该列的空值数）
SELECT COUNT(*) - COUNT(user_id)       AS user_id空值,
       COUNT(*) - COUNT(item_id)       AS item_id空值,
       COUNT(*) - COUNT(category_id)   AS category_id空值,
       COUNT(*) - COUNT(behavior_type) AS behavior_type空值,
       COUNT(*) - COUNT(dt)            AS dt空值
FROM user_behavior;

-- ⑦ 越界时间检查（数据应该只覆盖 2017-11-25 ~ 2017-12-03）
SELECT COUNT(*) AS 越界行数
FROM user_behavior
WHERE dt < '2017-11-25 00:00:00'
   OR dt >= '2017-12-04 00:00:00';
