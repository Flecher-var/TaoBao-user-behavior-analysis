-- ============================================================
-- 02 导入数据（全量 1 亿行，约 10~20 分钟）
--
-- 采用 LOAD DATA 而非 Python 的 to_sql：
--   1 亿行用 to_sql 逐行插入需数小时；LOAD DATA 是 MySQL 的批量导入通道，
--   同一份数据十几分钟即可完成导入。这也是本项目「SQL 化」的第一步——
--   数据导入不应由 Python 承担。
--
-- 前提：MySQL 的 datadir 不能位于 C 盘（C 盘剩余空间不足 10 GB，无法容纳数据表与 3 个索引）。
--   若尚未迁移，请先以管理员身份运行 outputs/mysql_移库到E盘.ps1，将数据目录迁移至 E 盘。
--
-- 执行顺序：01 建表 -> 02 导入数据 -> 03 建索引。
--   必须先导入数据后建索引，否则建索引会慢数倍。
-- ============================================================

-- ① 服务端开关：允许客户端上传本地文件（需要 SUPER 权限，重启 MySQL 后失效）
--    若 my.ini 中已配置 local_infile=1，可跳过本行。
SET GLOBAL local_infile = 1;

-- ② 客户端同样需要开启该选项，取决于所使用的数据库客户端：
--    命令行：mysql --local-infile=1 -u root -p taobao
--    DBeaver：右键连接 -> 编辑连接 -> 驱动属性 -> allowLoadLocalInfile = true
--    Navicat：在连接属性中勾选「允许导入本地文件」
--    本项目：python run_sql.py --all 会自动携带该参数（连接参数 local_infile=True）

-- ③ 清空后导入（路径按本机实际位置修改，Windows 路径使用正斜杠或双反斜杠）
TRUNCATE TABLE user_behavior;

LOAD DATA LOCAL INFILE 'E:/PycharmProjects/TaoBao-user-behavior-analysis/UserBehavior.csv'
INTO TABLE user_behavior
CHARACTER SET utf8mb4
FIELDS TERMINATED BY ','
LINES  TERMINATED BY '\n'
(@user_id, @item_id, @category_id, @behavior_type, @ts)
SET user_id       = @user_id,
    item_id       = @item_id,
    category_id   = @category_id,
    behavior_type = @behavior_type,
    -- 原始数据中有 318 行 ts 为负数。LOAD DATA 遇到越界值不会报错，而是「截断并产生
    -- 一条 warning」：负数会被截断为 0；但 FROM_UNIXTIME(负数) 返回 NULL，会使 NOT NULL
    -- 的 dt 列写入失败，因此此处先用 IF() 将越界值压缩为 0，下一步再连同其它脏数据一并删除。
    ts            = IF(@ts BETWEEN 0 AND 4294967295, @ts, 0),
    dt            = FROM_UNIXTIME(IF(@ts BETWEEN 0 AND 4294967295, @ts, 0));

-- ④ 清洗：删除时间窗口之外的全部记录（两端均需删除）
--    数据集标称覆盖 2017-11-25 ~ 2017-12-03 共 9 天，实测原始 CSV 中有 55,576 行
--    落在该窗口之外（约占 0.055%）：
--      · 318 行    ts < 0              （已被上面的 IF() 压缩为 0）
--      · 52,830 行 早于 2017-11-25     （最远至 182 天前，其中 39,124 行位于 11-24）
--      · 2,428 行  晚于 2017-12-03     （最近为 12-04，最远至 2037-04-09）
--    仅删除左端是最易犯的错误：右端数据会污染 MAX(dt)、每日行为量，以及 RF 分层的
--    「期末日期」（snap_d 变为 2037 年，导致所有用户的 R 值失真）。
--    注意：本步骤在建索引之前为全表扫描，1 亿行约需 1~2 分钟；
--    若已先执行 03 建立索引，则会走 idx_dt，仅需数秒。
DELETE FROM user_behavior
WHERE dt <  '2017-11-25 00:00:00'
   OR dt >= '2017-12-04 00:00:00';

-- ⑤ 结果核对：窗口外行数必须为 0，导入行数必须为 100,095,231
SELECT COUNT(*)                AS 导入行数,
       COUNT(DISTINCT user_id) AS 用户数,
       MIN(dt)                 AS 最早时间,
       MAX(dt)                 AS 最晚时间,
       SUM(dt <  '2017-11-25 00:00:00'
        OR dt >= '2017-12-04 00:00:00') AS 窗口外行数
FROM user_behavior;

-- ── 常见问题 ──────────────────────────────────────────────
-- · 报 "The used command is not allowed with this MySQL version"
--   = local_infile 未开启，请返回 ① 和 ②。
-- · 报 "Out of range value for column 'ts'" = 当前执行的并非本脚本，
--   而是旧的 import_to_mysql.py（该脚本未过滤越界值）。请改用本脚本，或先以
--   import_to_mysql.py --limit 1000000 小批量验证流程。
-- · 原始 CSV 无表头，因此不需要 IGNORE 1 LINES。
-- · 预期结果：100,095,231 行（原始 100,150,807 行 - 窗口外 55,576 行），
--   时间范围 2017-11-25 00:00:00 ~ 2017-12-03 23:59:59，
--   且 ⑤ 中的「窗口外行数」必须为 0。
-- · 清洗条件（本文件）与校验条件（04_data_quality.sql 第 ⑦ 条）必须使用同一套边界，
--   否则会出现「导入看似成功、数字对不上」的情况。
-- · 全量导入约占用 12~15 GB（数据表 + 3 个索引），因此 datadir 必须位于 E 盘。
