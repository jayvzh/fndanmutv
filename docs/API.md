# DanmuTV REST API 契约（API）

> 版本：v1.0 ｜ 前后端唯一契约来源，对应 [routes.py](../backend/app/api/routes.py)。字段变更必须双端同步并回写本文。

## 1. 通用约定

- Base path：`/api`；开发环境 Vite 代理到后端 `:8021`，生产同源。
- 认证：除两个状态接口外，所有端点要求请求头 `Authorization: Bearer <token>`；缺失 → 401（`未提供认证 Token`），错误 → 403（`Token 无效`）。
- 查询参数用 query string；除注明外请求体为 JSON。
- 健康检查 `GET /health`（无 `/api` 前缀，免鉴权）返回 `{"status":"ok"}`。

## 2. 响应包装

### 标准包装 ApiResponse

绝大多数接口返回：

```json
{ "success": true, "message": "", "data": null }
```

失败为 HTTP 200 + `success=false`（业务失败，参数/状态错误）；认证失败才是 401/403。

### 契约特例（历史原因，勿改）

| 接口 | 特殊形态 |
| --- | --- |
| `GET /config` | **裸 JSON 对象**（配置 dict，不用 ApiResponse 包装） |
| `POST /clean_orphan_subtitles` | **请求体为裸数组** `["/path/a.ass", ...]`（不是 `{"paths":[...]}`） |

## 3. 接口清单（27 个）

### 3.1 认证与状态

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| GET | `/status` | 免 | 刮削进度（仪表盘轮询） |
| GET | `/full_status` | 免 | 仪表盘完整状态 |
| GET | `/auth/verify` | 是 | 校验 Token，返回 `{success:true,message:"ok"}` |

`GET /status` → `data`：

```json
{ "auto_scrape": false, "running": false, "total": 0, "processed": 0,
  "success": 0, "failed": 0, "current_file": null, "duration": 0 }
```

`GET /full_status` → `data`：

```json
{
  "auto_scrape": false, "auto_scrape_mode": "incremental",
  "api_connected": true, "api_message": "...",
  "media_library_accessible": true, "media_library_count": 1,
  "stats": { "total_files": 0, "success_count": 0, "failed_count": 0, "retry_tasks_count": 0 },
  "next_retry_time": null, "last_run": null,
  "running": false, "total": 0, "processed": 0, "success": 0, "failed": 0,
  "current_file": null, "duration": 0
}
```

### 3.2 配置

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/config` | 返回裸配置 dict（字段见 [DATA_MODEL.md](DATA_MODEL.md) §config） |
| POST | `/config` | 请求体为配置 dict（三层合并：默认→旧→入参），返回 `ApiResponse`，`data` 为保存后完整配置；保存后重排定时任务 |
| GET | `/update_path` | 传 `path` 仅改内存中的刮削路径（不落库）；不传则从 DB 恢复。返回 `data:{path}` |

### 3.3 刮削

| 方法 | 路径 | 参数 | 说明 |
| --- | --- | --- | --- |
| GET | `/generate_danmu` | `file_path`（必填） | 同步刮削单文件 |
| GET | `/scrape_directory` | `directory_path`、`recursive=false`、`force=false` | 启动后台批量刮削，立即返回 |
| GET | `/abort_scrape` | — | 请求中止批量任务（当前文件处理完后停） |
| GET | `/generate_danmu_with_path` | `mode=incremental\|full` | 对配置的全部媒体库路径启动刮削 |

- `/generate_danmu` 成功：`data:{danmu_count, file_path, file_name}`；弹幕为 0 / 失败：`success:false` + message，并写单文件历史。
- `/scrape_directory` 成功：`data:{total, skipped, force}`（total 为入队数，不含跳过）；路径非法/无媒体/已有任务运行时 `success:false`。
- `/abort_scrape`：无运行任务时 `success:false`（`没有正在进行的刮削任务`）。
- `/generate_danmu_with_path`：`data:{started,total,mode,message}`；未配置路径时 `started:false`。

### 3.4 目录浏览与统计（data 均为 ApiResponse.data）

| 方法 | 路径 | 参数 | 说明 |
| --- | --- | --- | --- |
| GET | `/scan_path` | `path?`、`current_dir?` | 根目录树 / 指定目录；`current_dir` 等价子目录展开；无参取配置路径（多路径包虚拟根节点） |
| GET | `/scan_subfolder` | `subfolder_path`（必填） | 展开某子目录 |
| GET | `/scan_directory_stats` | `directory_path`（必填） | 递归统计（深 6 层）并落目录记录 |

目录树节点：

```json
// 目录节点
{ "name": "电影", "path": "/media/电影", "type": "directory", "is_root": false,
  "children": [], "manual_match": null, "manual_scope": "directory",
  "directory_path": "/media/电影",
  "scrape_status": { "total_files": 12, "scraped_files": 10 },
  "last_scrape_time": "2026-09-13 10:00:00" }
// 媒体节点
{ "name": "Show.S01E01.mkv", "path": "/media/Show.S01E01.mkv", "type": "media",
  "children": [], "manual_match": {}, "manual_scope": "file",
  "directory_path": "/media", "danmu_count": 1234 }
// 多路径虚拟根
{ "name": "根目录", "path": "", "type": "root", "is_root": true, "children": [] }
```

`/scan_directory_stats` 的 `data`：

```json
{ "directory_path": "/media", "total_files": 12, "scraped_files": 10,
  "dir_stats": { "/media": { "total_files": 12, "scraped_files": 10 } } }
```

### 3.5 字幕清理

| 方法 | 路径 | 参数/体 | 说明 |
| --- | --- | --- | --- |
| GET | `/scan_orphan_subtitles` | `path?` | 扫描无对应媒体（.mp4/.mkv/.strm）的含 `danmu` 的 `.ass` |
| POST | `/clean_orphan_subtitles` | **裸数组 body** | 删除指定孤儿字幕 |
| GET | `/clean_subtitles` | `file_path?` 或 `directory_path?` | 删除弹幕/合并字幕（目录递归） |

`scan_orphan_subtitles` data：

```json
{ "scanning": false,
  "orphan_subtitles": [{ "path": "/media/x.danmu.chs.ass", "size": 12345,
                         "modified_time": "2026-09-13 10:00:00" }],
  "total_found": 1, "scan_path": "/media" }
```

`clean_orphan_subtitles` data：`{cleaned_count, failed_count, cleaned_paths}`。
`clean_subtitles` data：`{deleted: [文件名/相对路径]}`；无删除时 data 为 null。

### 3.6 搜索与手动匹配

| 方法 | 路径 | 参数/体 | 说明 |
| --- | --- | --- | --- |
| GET | `/search_danmu` | `keyword`（必填）、`type?` | 透传弹弹 `/api/v2/search/anime`，成功原样返回上游 JSON（含 `animes`） |
| POST | `/manual_match` | ManualMatchRequest body | 保存目录/文件级匹配 |
| GET | `/remove_manual_match` | `scope?`、`file_path?`、`directory?` | 移除匹配（directory 同时删 `.dandan.anime.json`） |

`ManualMatchRequest`：

```json
{ "file_path": null, "directory": "/media/Show", "scope": "directory",
  "episodeOffset": null,
  "anime": { "animeId": 1234, "animeTitle": "...", "imageUrl": null,
             "type": "tvseries", "typeDescription": "...",
             "episodeCount": 12, "rating": null, "startDate": null } }
```

`/manual_match` 返回 data：`{directory, file_path, manual_match:{...}}`。

### 3.7 重试任务

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/retry_tasks` | 列出全部重试任务 |
| GET | `/process_retry_tasks` | 立即同步处理一轮到期任务 |
| GET | `/clear_retry_tasks` | 清空（message 含清除条数） |
| GET | `/remove_retry_task` | 参数 `file_path`，移除单个 |

`retry_tasks` data：

```json
{ "tasks": {
    "/media/a.mkv": { "retry_count": 1, "last_attempt": "2026-09-13 10:00:00",
      "file_path": "/media/a.mkv", "last_danmu_count": 0, "error_type": "no_data",
      "next_retry_time": "2026-09-13 10:15:00", "error_message": "本地弹幕数量不足" } },
  "total": 1, "min_danmu_count": 100, "max_retry_times": 10 }
```

`process_retry_tasks` data：`{processed, success, failed, removed, remaining}`；遇 429 提前结束本轮。

### 3.8 历史

| 方法 | 路径 | 参数 | 说明 |
| --- | --- | --- | --- |
| GET | `/history` | `page=1`、`page_size=20`（1..100）、`include_details=false` | 分页历史 |
| POST | `/clear_history` | — | 清空全部历史 |

`history` data：

```json
{ "items": [ { /* record */ } ], "history": [ /* 与 items 同值，兼容前端 */ ],
  "total": 35, "page": 1, "page_size": 20, "has_more": true }
```

record（batch）：`{id, timestamp, type:"batch", path, processed, success, failed, duration, aborted, details?}`；
record（single）：`{id, timestamp, type:"single", path, file, processed:1, success, failed, danmu_count, duration:0, aborted:false, message, details?}`。
`include_details=false` 时每条移除 `details`。

### 3.9 外部 API 检测

| 方法 | 路径 | 参数 | 说明 |
| --- | --- | --- | --- |
| GET | `/api_status` | `api_url?`（不传用配置） | 探测 `GET {url}/api/logs` |

返回 data：`{reachable:bool, message, url}`。200 可达；401 也视为可达（提示需在地址中配置 Token）；超时 5s。

## 4. 外部 danmu-api 端点（引擎调用，非本服务契约）

| 方法 | 路径 | 用途 |
| --- | --- | --- |
| GET | `/api/logs` | 连通性探测（200/401 均可达） |
| GET | `/api/v2/search/anime?keyword=&type=` | 作品搜索 |
| POST | `/api/v2/match` | body `{"fileName":"标题.S01E01"}`，取 `matches[0].episodeId` |
| GET | `/api/v2/comment/{comment_id}?format=json&duration=true` | 下载弹幕评论 |

URL 可形如 `http://host:9321/<token>`，路径段 token 由 `DanmuAPI.set_api_url` 拆分后拼到所有端点前。
