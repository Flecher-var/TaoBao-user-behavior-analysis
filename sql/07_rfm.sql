-- ============================================================
-- 07 RFM 用户分层
--
-- 本数据集无商品单价与订单金额，M（Monetary）无法计算，因此仅计算 RF。
-- 第一版存在三处不一致：文件名为「用户分层（RFM）」、函数名为 RF_analysis、
-- README 写作 RFM。本次统一为 RF，并在 README 中说明无法计算 M 的原因。
-- （也考虑过以 F×客单价代理金额，但同样依赖金额数据，无法实现。）
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

-- ② 查看单个用户明细（将上面的 SELECT 替换为明细查询即可）
-- WITH ... seg AS (...) SELECT * FROM seg ORDER BY r_score DESC, f_score DESC LIMIT 100;

-- ── 两个必要的技术说明 ────────────────────────────────────
-- 1) NTILE 遇到并列值时会任意分配，相同数据两次执行可能得到不同结果。
--    因此 ORDER BY 中加入了 user_id 作为 tie-breaker，以保证结果可复现。
--    原 pandas 版本使用 rank(method='first')，思路一致。
-- 2) 分档采用 >= 3 而非「大于平均值」。使用平均值会因分数分布不均导致
--    各档人数差异很大；>= 3 保证为规整的 2x2 四象限。
