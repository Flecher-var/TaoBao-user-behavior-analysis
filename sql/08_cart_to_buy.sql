-- ============================================================
-- 08 加购到购买的时间间隔
--
-- 这条是为补一个缺口：第一版 README 里写了"加购后的短时间窗口内转化更集中"，
-- 但代码里根本没有计算时间间隔的逻辑。这次把它真算出来了，
-- 结果和原来那句话正好相反（71.68% 的成交发生在加购 1 小时之后）。
--
-- 口径说明：统计"同一用户对同一商品"从首次加购到首次购买的时间差。
-- 这不是真实的会话路径（数据集没有 session_id），要在 README 里注明。
-- ============================================================

-- ① 加购 → 购买 的整体转化率
WITH cart AS (
  SELECT user_id, item_id, MIN(dt) AS cart_dt
  FROM user_behavior
  WHERE behavior_type = 'cart'
  GROUP BY user_id, item_id
),
buy AS (
  SELECT user_id, item_id, MIN(dt) AS buy_dt
  FROM user_behavior
  WHERE behavior_type = 'buy'
  GROUP BY user_id, item_id
),
paired AS (
  SELECT c.user_id, c.item_id, c.cart_dt, b.buy_dt
  FROM cart c
  JOIN buy b
    ON c.user_id = b.user_id
   AND c.item_id = b.item_id
  WHERE b.buy_dt >= c.cart_dt
)
SELECT (SELECT COUNT(*) FROM cart)   AS 加购商品对数,
       (SELECT COUNT(*) FROM paired) AS 加购后购买对数,
       ROUND((SELECT COUNT(*) FROM paired) * 100.0
             / (SELECT COUNT(*) FROM cart), 2) AS 加购到购买转化率;

-- ② 时间间隔分布（这就是 README 里那句结论的依据）
WITH cart AS (
  SELECT user_id, item_id, MIN(dt) AS cart_dt
  FROM user_behavior
  WHERE behavior_type = 'cart'
  GROUP BY user_id, item_id
),
buy AS (
  SELECT user_id, item_id, MIN(dt) AS buy_dt
  FROM user_behavior
  WHERE behavior_type = 'buy'
  GROUP BY user_id, item_id
),
paired AS (
  SELECT TIMESTAMPDIFF(MINUTE, c.cart_dt, b.buy_dt) AS gap_min
  FROM cart c
  JOIN buy b
    ON c.user_id = b.user_id
   AND c.item_id = b.item_id
  WHERE b.buy_dt >= c.cart_dt
)
SELECT CASE
         WHEN gap_min <= 10   THEN '1. 10分钟内'
         WHEN gap_min <= 60   THEN '2. 10分钟-1小时'
         WHEN gap_min <= 360  THEN '3. 1-6小时'
         WHEN gap_min <= 1440 THEN '4. 6-24小时'
         ELSE '5. 超过24小时'
       END AS 时间窗口,
       COUNT(*) AS 商品对数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS 占比
FROM paired
GROUP BY 时间窗口
ORDER BY 时间窗口;
