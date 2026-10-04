-- ============================================================
-- 10 复购 / 加购收藏比 / 付费用户偏好
--
-- 以下几项与第一版一致：复购率、加购/收藏比（2.05，与第一版完全相同）、
-- 购买量 Top 类目，第一版 purchase_analysis.py 均已计算。
-- 本次补充的是 README 中提到但代码中未实现的两项：
-- 复购次数分布、高价值用户的下单时段。
-- ============================================================

-- ① 复购率
--    口径：购买次数 > 1 的用户 / 有过购买行为的用户
--    注意分母为「买过的人」而非全站用户，因此该数值天然偏高，
--    写入 README 时必须附带口径说明。
WITH buy AS (
  SELECT user_id, COUNT(*) AS buy_cnt
  FROM user_behavior
  WHERE behavior_type = 'buy'
  GROUP BY user_id
)
SELECT COUNT(*)                                      AS 购买用户数,
       SUM(buy_cnt > 1)                              AS 复购用户数,
       ROUND(SUM(buy_cnt > 1) * 100.0 / COUNT(*), 2) AS 复购率
FROM buy;

-- ② 有过购买行为的用户里，加购 与 收藏 的频次比
--    （README 中的 2.05 即为该口径，用于论证「加购是比收藏更强的购买信号」）
WITH pay_user AS (
  SELECT DISTINCT user_id
  FROM user_behavior
  WHERE behavior_type = 'buy'
)
SELECT SUM(u.behavior_type = 'cart') AS 加购次数,
       SUM(u.behavior_type = 'fav')  AS 收藏次数,
       ROUND(SUM(u.behavior_type = 'cart')
             / NULLIF(SUM(u.behavior_type = 'fav'), 0), 2) AS 加购收藏比
FROM user_behavior u
JOIN pay_user p ON p.user_id = u.user_id;

-- ③ 复购次数分布：买 1 次 / 2 次 / 3-5 次 / 6 次以上
WITH buy AS (
  SELECT user_id, COUNT(*) AS buy_cnt
  FROM user_behavior
  WHERE behavior_type = 'buy'
  GROUP BY user_id
)
SELECT CASE
         WHEN buy_cnt = 1  THEN '1. 只买过 1 次'
         WHEN buy_cnt = 2  THEN '2. 买过 2 次'
         WHEN buy_cnt <= 5 THEN '3. 买过 3-5 次'
         ELSE                   '4. 买过 6 次以上'
       END AS 购买频次,
       COUNT(*) AS 人数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
FROM buy
GROUP BY 购买频次
ORDER BY 购买频次;

-- ④ 购买量最高的 10 个类目（对应原 purchase_analysis.py 的「品类偏好」）
SELECT category_id             AS 类目ID,
       COUNT(*)                AS 购买次数,
       COUNT(DISTINCT user_id) AS 购买用户数
FROM user_behavior
WHERE behavior_type = 'buy'
GROUP BY category_id
ORDER BY 购买次数 DESC
LIMIT 10;

-- ⑤ 高价值用户（购买次数最多的那批人）的下单时段
--    用于验证「大促 / 晚间下单更集中」这类结论是否成立
WITH buy AS (
  SELECT user_id, COUNT(*) AS buy_cnt
  FROM user_behavior
  WHERE behavior_type = 'buy'
  GROUP BY user_id
),
top_buyer AS (
  SELECT user_id
  FROM buy
  ORDER BY buy_cnt DESC, user_id
  LIMIT 10000
)
SELECT HOUR(u.dt) AS 小时,
       COUNT(*)   AS 下单次数
FROM user_behavior u
JOIN top_buyer t ON t.user_id = u.user_id
WHERE u.behavior_type = 'buy'
GROUP BY HOUR(u.dt)
ORDER BY 小时;
