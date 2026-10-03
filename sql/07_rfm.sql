-- ============================================================
-- 07 RFM 用户分层
--
-- 重要限制：本数据集没有商品单价或订单金额，
-- 所以 M（Monetary）无法计算，实际只能做 RF。
-- 你原来的代码文件叫 RFM，函数叫 RF_analysis，README 写 RFM，
-- 三处不一致 —— 这是面试官一定会问的点。
-- 处理方式有两种，选一种并说明：
--   (a) 老实改名成 RF，在 README 写清楚为什么做不了 M；
--   (b) 保留 RFM 的说法，但用 F×客单价代理金额需要额外数据，本数据集做不到。
-- ============================================================

-- ① 分层结果汇总
WITH buy AS (
  SELECT user_id,
         MAX(DATE(dt)) AS last_buy_d,
         COUNT(*)      AS buy_cnt
  FROM user_behavior
  WHERE behavior_type = 'buy'
  GROUP BY user_id
),
snap AS (
  SELECT MAX(DATE(dt)) AS snap_d
  FROM user_behavior
  WHERE behavior_type = 'buy'
),
scored AS (
  SELECT b.user_id,
         DATEDIFF(s.snap_d, b.last_buy_d) AS R,
         b.buy_cnt                        AS F,
         -- R 越小越好：按 R 倒序分 4 档，最小的 R 落在第 4 档
         NTILE(4) OVER (ORDER BY DATEDIFF(s.snap_d, b.last_buy_d) DESC, b.user_id)
           AS r_score,
         -- F 越大越好：按 F 升序分 4 档，最大的 F 落在第 4 档
         NTILE(4) OVER (ORDER BY b.buy_cnt ASC, b.user_id)
           AS f_score
  FROM buy b
  CROSS JOIN snap s
),
seg AS (
  SELECT user_id, R, F, r_score, f_score,
         CASE
           WHEN r_score >= 3 AND f_score >= 3 THEN '重要价值用户'
           WHEN r_score <  3 AND f_score >= 3 THEN '重要保持用户'
           WHEN r_score >= 3 AND f_score <  3 THEN '重要发展用户'
           ELSE '一般挽留用户'
         END AS 用户分层
  FROM scored
)
SELECT 用户分层,
       COUNT(*)                                            AS 人数,
       ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2)   AS 占比,
       ROUND(AVG(R), 1)                                    AS 平均最近购买间隔天,
       ROUND(AVG(F), 1)                                    AS 平均购买次数
FROM seg
GROUP BY 用户分层
ORDER BY 人数 DESC;

-- ② 看单个用户的明细（把上面的 SELECT 换成明细即可）
-- WITH ... seg AS (...) SELECT * FROM seg ORDER BY r_score DESC, f_score DESC LIMIT 100;

-- ── 两个必须知道的技术点 ──────────────────────────────────
-- 1) NTILE 遇到并列值时会任意分配，同样的数据跑两次结果可能不同。
--    所以我在 ORDER BY 里加了 user_id 作为 tie-breaker，保证结果可复现。
--    你原来的 pandas 版本用了 rank(method='first')，思路是一样的。
-- 2) 分档用 >= 3 而不是"大于平均值"。用平均值会因为分数分布不均导致
--    各档人数相差很大；>= 3 保证是干净的 2x2 四象限。
