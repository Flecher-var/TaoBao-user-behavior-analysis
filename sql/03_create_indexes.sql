-- ============================================================
-- 03 建索引（必须在数据导入完成后执行）
-- 无索引时，后续的留存分析会慢到无法接受。
-- ============================================================

-- 用于按时间过滤 / 按天分组
CREATE INDEX idx_dt ON user_behavior (dt);

-- 行为漏斗、RFM、加购转化均会先按 behavior_type 过滤
CREATE INDEX idx_behavior_dt ON user_behavior (behavior_type, dt);

-- 按用户聚合时使用（留存、RFM 的核心）
CREATE INDEX idx_user_dt ON user_behavior (user_id, dt);

-- 分析索引占用（可选，用于查看磁盘使用量）
SELECT INDEX_NAME,
       ROUND(STAT_VALUE * @@innodb_page_size / 1024 / 1024, 1) AS 大小MB
FROM mysql.innodb_index_stats
WHERE database_name = DATABASE()
  AND table_name = 'user_behavior'
  AND stat_name = 'size'
ORDER BY STAT_VALUE DESC;

-- 慢查询时可使用 EXPLAIN 检查是否命中索引，例如：
-- EXPLAIN SELECT COUNT(*) FROM user_behavior WHERE behavior_type = 'buy';
