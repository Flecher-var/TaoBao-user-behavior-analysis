-- ============================================================
-- 05 用户级漏斗
--
-- 本文件修正第一版的主要问题：
-- 原实现直接用 value_counts() 统计行为次数，得到 32.94，那是「事件比」，
-- 不能称为转化率——同一用户点击 30 次会被计为 30 次。
-- 正确口径是先 GROUP BY user_id，将行为压缩为用户级 0/1 标记，再去重计数。
--
-- 另一处修正：收藏(fav) 与 加购(cart) 是并列分支，并非先后步骤。
-- 用户可能直接加购而不收藏，也可能仅收藏不加购，因此不能排成单一链条。
-- ============================================================

-- ① 总体漏斗（一行输出，适合直接写入 README）
WITH user_flag AS (
  SELECT user_id,
         MAX(behavior_type = 'pv')   AS did_pv,
         MAX(behavior_type = 'fav')  AS did_fav,
         MAX(behavior_type = 'cart') AS did_cart,
         MAX(behavior_type = 'buy')  AS did_buy
  FROM user_behavior
  GROUP BY user_id
)
SELECT COUNT(*)                                      AS 全站用户数,
       SUM(did_pv)                                   AS 浏览用户,
       SUM(did_cart)                                 AS 加购用户,
       SUM(did_fav)                                  AS 收藏用户,
       SUM(GREATEST(did_cart, did_fav))              AS 加购或收藏用户,
       SUM(did_buy)                                  AS 购买用户,
       ROUND(SUM(did_cart) * 100.0 / SUM(did_pv), 2) AS 浏览到加购率,
       ROUND(SUM(did_fav)  * 100.0 / SUM(did_pv), 2) AS 浏览到收藏率,
       ROUND(SUM(did_buy)  * 100.0
             / SUM(GREATEST(did_cart, did_fav)), 2)  AS 加购收藏到购买率,
       ROUND(SUM(did_buy)  * 100.0 / SUM(did_pv), 2) AS 浏览到购买率
FROM user_flag;

-- ② 分层级明细（便于绘制漏斗图）
WITH user_flag AS (
  SELECT user_id,
         MAX(behavior_type = 'pv')   AS did_pv,
         MAX(behavior_type = 'fav')  AS did_fav,
         MAX(behavior_type = 'cart') AS did_cart,
         MAX(behavior_type = 'buy')  AS did_buy
  FROM user_behavior
  GROUP BY user_id
),
lv AS (
  SELECT 1 AS 层级, '浏览(pv)'   AS 环节, COUNT(*) AS 用户数 FROM user_flag WHERE did_pv = 1
  UNION ALL
  SELECT 2, '加购或收藏', COUNT(*) FROM user_flag WHERE did_cart = 1 OR did_fav = 1
  UNION ALL
  SELECT 3, '购买(buy)',  COUNT(*) FROM user_flag WHERE did_buy = 1
)
SELECT 层级,
       环节,
       用户数,
       ROUND(用户数 * 100.0 / MAX(用户数) OVER (), 2) AS 占首层比例,
       ROUND(用户数 * 100.0
             / LAG(用户数) OVER (ORDER BY 层级), 2)   AS 相对上一层转化率
FROM lv
ORDER BY 层级;

-- ③ 类目转化率排行
--    第一版仅考察「购买量最高的类目」，但「卖得多」不等于「转化好」，
--    能指导运营的是转化率。HAVING 用于排除样本量过小的类目，避免长尾噪声。
WITH user_cat AS (
  SELECT category_id,
         user_id,
         MAX(behavior_type = 'pv')  AS did_pv,
         MAX(behavior_type = 'buy') AS did_buy
  FROM user_behavior
  GROUP BY category_id, user_id
)
SELECT category_id       AS 类目ID,
       SUM(did_pv)       AS 浏览用户,
       SUM(did_buy)      AS 购买用户,
       ROUND(SUM(did_buy) * 100.0 / SUM(did_pv), 2) AS 转化率
FROM user_cat
GROUP BY category_id
HAVING SUM(did_pv) >= 1000
ORDER BY 转化率 DESC
LIMIT 20;
