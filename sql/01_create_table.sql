-- ============================================================
-- 01 建表
-- 数据集：天池 UserBehavior（2017-11-25 ~ 2017-12-03，约 1 亿行 / 3GB+）
--
-- 顺序很重要：建表 -> 灌数据 -> 建索引
-- 先灌数据后建索引，比先建索引再灌快好几倍。
-- ============================================================

DROP TABLE IF EXISTS user_behavior;

CREATE TABLE user_behavior (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  user_id       INT UNSIGNED    NOT NULL              COMMENT '用户ID',
  item_id       INT UNSIGNED    NOT NULL              COMMENT '商品ID',
  category_id   INT UNSIGNED    NOT NULL              COMMENT '类目ID',
  behavior_type VARCHAR(10)     NOT NULL              COMMENT 'pv / fav / cart / buy',
  ts            INT UNSIGNED    NOT NULL              COMMENT '原始时间戳（秒）',
  dt            DATETIME        NOT NULL              COMMENT '换算后的时间',
  PRIMARY KEY (id)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COMMENT = '淘宝用户行为明细';

-- 说明：
-- 1) dt 用 DATETIME 而不是字符串，后面才能直接用 DATE()、DATEDIFF()、HOUR()。
-- 2) 三个 ID 用 INT UNSIGNED（上限 42.9 亿）。如果导入时报
--    "Out of range value"，说明有更大的值，改成 BIGINT UNSIGNED 再重建表。
-- 3) 这里故意不建二级索引，索引在 03_create_indexes.sql 里灌完数据后再建。
