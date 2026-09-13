# DanmuTV 数据模型（DATA_MODEL）

> 版本：v1.0 ｜ SQLite 表结构的唯一事实来源，对应 [database.py](../backend/app/database.py)。
> 数据库文件：`$DANMUTV_DATA_DIR/danmutv.db`（默认 `/data/danmutv.db`，本地开发为项目根 `data/`）。

## 1. 通用约定

- 引擎：SQLite，`PRAGMA journal_mode=WAL`、`synchronous=NORMAL`、`foreign_keys=ON`，连接超时 30s。
- 时间字段：业务时间字符串格式 `YYYY-MM-DD HH:MM:SS`（或秒级 ISO），历史 `timestamp` 为秒级 ISO。
- 复杂结构一律以 `*_json` 文本列存 UTF-8 JSON（`ensure_ascii=False`）。
- 建表只用 `CREATE TABLE IF NOT EXISTS`；旧库兼容用 `ALTER TABLE ADD COLUMN`（失败忽略），**迁移只增不改不删**。
- 写操作经进程级 `_write_lock` 串行化。

## 2. 表结构

### config（单行配置）

| 列 | 类型 | 说明 |
| --- | --- | --- |
| id | INTEGER PK | 恒为 1（`CHECK (id = 1)`） |
| config_json | TEXT NOT NULL | `AppConfig` 序列化 JSON |

首次启动写入默认配置；`DANMUTV_DANMU_API_URL` 存在时覆盖默认 `danmu_api_url`。

配置项（见 [models.py](../backend/app/models.py) `AppConfig`）：

| 键 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| width / height | int | 1920 / 1080 | ASS 画布分辨率 |
| fontsize | int | 48 | 字号 |
| alpha | float | 0.6 | 透明度（保存时强制修正） |
| duration | int | 14 | 弹幕持续时间（秒） |
| path | str | "" | 媒体库路径，多个用换行分隔；Docker 可由 `DANMUTV_MEDIA_DIR` 注入默认值 |
| auto_scrape | bool | false | 是否启用定时自动刮削 |
| auto_scrape_mode | str | incremental | `incremental` / `full` |
| auto_scrape_interval | int | 3600 | 自动刮削间隔（秒，调度下限 60） |
| enable_retry_task | bool | true | 启用 5 分钟重试任务 |
| enable_history_details | bool | false | 是否记录成功文件的明细 |
| screen_area | str | quarter | 弹幕屏幕区域：full/half/third/quarter |
| enable_strm | bool | true | 是否处理 `.strm` |
| danmu_api_url | str | http://danmu-api:9321 | 弹幕 API 地址，可在末段带 `/token` |
| enable_multi_layer | bool | true | 多层弹幕 |
| multi_layer_count | int | 2 | 层数 2/3（保存时强制 int） |
| random_top_bottom | bool | false | 随机顶/底弹幕 |
| top_ratio / bottom_ratio | int | 0 / 0 | 顶部/底部随机比例 |
| density_count | int | 5000 | 弹幕密度：0=全部；典型 3000/5000/8000 |
| width_scale | float | 1.2 | 宽度扩展（超宽屏，保存时强制 float） |

已废弃：`enabled`（保存时剔除）、旧 `density`（百分比，迁移为 density_count）、`useTmdbID`（固定文件名匹配）。

### retry_tasks（重试队列）

| 列 | 类型 | 说明 |
| --- | --- | --- |
| file_path | TEXT PK | 视频绝对路径 |
| retry_count | INTEGER | 已重试次数（达 10 删除放弃） |
| last_attempt | TEXT | 上次尝试时间 |
| last_danmu_count | INTEGER | 上次弹幕条数 |
| error_type | TEXT | `rate_limit` / `no_match` / `no_data` / `network` / `unknown` |
| next_retry_time | TEXT | 到期时间（退避序列，错误类型设下限） |
| error_message | TEXT | 错误信息（后加列，兼容旧库） |

### manual_matches（手动匹配，两级）

| 列 | 类型 | 说明 |
| --- | --- | --- |
| scope | TEXT | `directory` / `file`（联合主键） |
| path | TEXT | 目录路径或文件绝对路径 |
| data_json | TEXT | 匹配信息 JSON |

`data_json` 关键字段：`animeId`(int)、`animeTitle`、`imageUrl`、`type`、`typeDescription`、`episodeCount`、`rating`、`startDate`、`source`（`manual`/`manual_file`/`legacy-id-file`）、`scope`、`updatedAt`、可选 `episodeOffset`。

- directory 级：DB 之外**另写**媒体目录下 `.dandan.anime.json`，引擎刮削该目录任意文件时自动加载并应用集数偏移。
- file 级：仅存 DB/内存，不写 json，只对该文件生效。
- 读取兼容旧版 `<animeId>.id` 文件：自动转写为 json 并删除旧文件。

### directory_records（目录刮削记录）

| 列 | 类型 | 说明 |
| --- | --- | --- |
| path | TEXT PK | 目录绝对路径 |
| data_json | TEXT | `{scrape_status:{total_files,scraped_files}, last_scrape_time, retry_info, history}` |

### global_history（全局历史）

| 列 | 类型 | 说明 |
| --- | --- | --- |
| id | TEXT PK | 毫秒时间戳字符串 |
| timestamp | TEXT NOT NULL | 秒级 ISO 时间 |
| type | TEXT | `batch` / `single` |
| path | TEXT | 批量目录标签或单文件路径 |
| processed / success / failed | INTEGER | 计数 |
| duration | REAL | 耗时（秒；单文件为 0） |
| aborted | INTEGER | 批量是否被中止（默认 0） |
| details_json | TEXT | 可选明细 `[{file, result, danmu_count, error}]` |

索引：`idx_history_ts ON global_history(timestamp DESC)`。概要最多保留 100 条（内存裁剪 + 加载 SQL `LIMIT 100`）；成功明细仅在 `enable_history_details=true` 时记录，失败明细始终记录。

## 3. 媒体目录侧文件（非 DB）

| 文件 | 产生位置 | 说明 |
| --- | --- | --- |
| `<base>.danmu.chs.ass` | 视频同目录 | 弹幕字幕；`Dialogue:` 行数 ≥100 才算"有效" |
| `<字幕主名>.withDanmu.ass` | 原字幕同目录 | 弹幕 + 原字幕合并产物（UTF-8 BOM），原字幕保留 |
| `<base>.<lang>.ass` | 视频同目录 | 从视频提取的中文内嵌字幕（已存在则跳过） |
| `.dandan.anime.json` | 被匹配目录 | 目录级手动匹配（见上） |

## 4. 前端本地存储

- localStorage 键 `fndanmutv_token`：访问 Token；401/403 时自动清除。
