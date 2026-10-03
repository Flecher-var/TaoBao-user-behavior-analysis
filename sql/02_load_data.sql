-- ============================================================
-- 02 灌数据（全量 1 亿行，10~20 分钟）
--
-- 为什么用 LOAD DATA 而不是 Python 的 to_sql：
--   1 亿行用 to_sql 一行行插要跑几个小时，LOAD DATA 是 MySQL 的批量导入通道，
--   同一份数据十几分钟就能进去。这也是本项目「SQL 化」的第一步——
--   导入不该由 Python 来干。
--
-- 前提：MySQL 的 datadir 不能放在 C 盘（C 盘只剩 10 GB，装不下表 + 3 个索引）。
--   还没搬的话先跑 outputs/mysql_移库到E盘.ps1（管理员），把数据目录搬到 E 盘。
--
-- 顺序：01 建表 -> 02 灌数据 -> 03 建索引
--   必须先灌数据后建索引，反过来会慢好几倍。
-- ============================================================

-- ① 服务端开关：允许客户端上传本地文件（需要 SUPER 权限，重启 MySQL 后失效）
--    my.ini 里已经写了 local_infile=1 的话，这行可以跳过。
SET GLOBAL local_infile = 1;

-- ② 客户端也要带开关，看你用什么连数据库：
--    命令行：mysql --local-infile=1 -u root -p taobao
--    DBeaver：右键连接 -> 编辑连接 -> 驱动属性 -> allowLoadLocalInfile = true
--    Navicat：连接属性里勾选 "允许导入本地文件"
--    本项目：python run_sql.py --all 会自动带（连接参数里 local_infile=True）

-- ③ 清空后导入（路径按本机实际位置改，Windows 路径用正斜杠或双反斜杠）
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
    -- 原始数据里有 318 行 ts 是负数。LOAD DATA 碰到越界值不会报错，而是「截断 + 一条
    -- warning」：负数会被拧成 0；但 FROM_UNIXTIME(负数) 是 NULL，会把 NOT NULL 的
    -- dt 列写坏，所以这里用 IF() 先把越界值压成 0，下一步连同别的脏行一起删。
    ts            = IF(@ts BETWEEN 0 AND 4294967295, @ts, 0),
    dt            = FROM_UNIXTIME(IF(@ts BETWEEN 0 AND 4294967295, @ts, 0));

-- ④ 清洗：把时间窗口之外的行全部删掉（两头都要删）
--    数据集标称覆盖 2017-11-25 ~ 2017-12-03 这 9 天，实测原始 CSV 里有 55,576 行
--    落在这个窗口之外（约占 0.055%）：
--      · 318 行    ts < 0              （被上面的 IF() 压成了 0）
--      · 52,830 行 2017-11-25 之前     （散落到 182 天前，其中 39,124 行就在 11-24）
--      · 2,428 行  2017-12-03 之后     （最近的是 12-04，最远的到 2037-04-09）
--    只删左边是最容易犯的错：右边那批会污染 MAX(dt)、每日行为量，以及 RF 分层的
--    「期末日期」（snap_d 变成 2037 年，所有人的 R 值一起失真）。
--    注意：这一步在建索引之前是全表扫描，1 亿行大约一两分钟；
--    如果先跑过 03 建了索引，这里会走 idx_dt，几秒钟。
DELETE FROM user_behavior
WHERE dt <  '2017-11-25 00:00:00'
   OR dt >= '2017-12-04 00:00:00';

-- ⑤ 核对结果：窗口外行数必须是 0，导入行数必须是 100,095,231
SELECT COUNT(*)                AS 导入行数,
       COUNT(DISTINCT user_id) AS 用户数,
       MIN(dt)                 AS 最早时间,
       MAX(dt)                 AS 最晚时间,
       SUM(dt <  '2017-11-25 00:00:00'
        OR dt >= '2017-12-04 00:00:00') AS 窗口外行数
FROM user_behavior;

-- ── 踩坑备忘 ──────────────────────────────────────────────
-- · 报 "The used command is not allowed with this MySQL version"
--   = local_infile 没开，回到 ① 和 ②。
-- · 报 "Out of range value for column 'ts'" = 你跑的不是这份 SQL，
--   而是老的 import_to_mysql.py（那份没挡越界值）。要么换这份，要么先用
--   import_to_mysql.py --limit 1000000 小批量跑通流程。
-- · 原始 CSV 没有表头，所以不需要 IGNORE 1 LINES。
-- · 期望结果：100,095,231 行（原始 100,150,807 行 - 窗口外 55,576 行），
--   时间范围 2017-11-25 00:00:00 ~ 2017-12-03 23:59:59，
--   并且 ⑤ 里的「窗口外行数」必须是 0。
-- · 清洗条件（这里）和校验条件（04_data_quality.sql 第 ⑦ 条）必须用同一套边界，
--   否则会出现"导入看着成功、数字对不上"的情况。
-- · 全量导入大约占 12~15 GB（表 + 3 个索引），所以 datadir 必须在 E 盘。
