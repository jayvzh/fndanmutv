# 项目编码约定（conventions）

> 只记录项目专属约定：目录放置理由、自定义命名/缩写、历史技术债及绕开姿势。
> 通用编程规范不写。更新时机：发现新的项目专属约定时。

## 目录与模块约定
- [danmu_generator.py](../backend/app/danmu_generator.py)（约 1600 行）是**引擎层**，迁移自 MoviePilot 插件：`DanmuAPI` / `DanmuConverter` / `SubtitleProcessor` / `StrmProcessor` / 单例 `danmu_generator()`。应用层逻辑（HTTP、SQLite、调度、配置）放在 `services/`，不要把 FastAPI/数据库代码塞进引擎。
- 引擎里的类名与方法签名尽量保持插件原貌，便于日后对照上游插件同步变更；需要改造时在本仓库内改，不回写 `references/`。
- `services/danmu_service.py` 是刮削编排（状态机/互斥/重试/历史），`scan_service.py` 管目录树扫描，`media_parser.py` 只做文件名解析；新业务按此边界归位。
- 持久化统一走 [database.py](../backend/app/database.py) 的标准库 `sqlite3` 封装，**不引 ORM**；定时任务只允许注册到 `services/scheduler.py` 的唯一 BackgroundScheduler，禁止各处自行 new scheduler。
- HTTP 出口统一 `src/api/index.js`（axios 实例 + Token 注入），页面不直接 fetch。

## 命名与业务缩写
- 弹幕数据源是弹弹 play 兼容协议的 danmu-api；代码里 "dandan"/"danmu" 混用，配置与产物命名以 **danmu** 为准（如 `.danmu.chs.ass`）。
- `commentId = animeId * 10000 + episode`（danmu-api 约定，引擎内换算，不要手写魔法数）。
- 媒体目录侧固定文件名：
  - `.danmu.chs.ass`：有效弹幕产物，"有效"= 文件存在且 `Dialogue:` 行 ≥ 100；
  - `.dandan.anime.json`：手动匹配结果缓存（`DanmuAPI.MANUAL_MATCH_FILE`），供重扫复用。
- 环境变量统一 `DANMUTV_` 前缀（pydantic-settings）；鉴权 Token 读取顺序：`ADMIN_TOKEN` 优先，其次 `DANMUTV_TOKEN`，都未配置时启动随机生成并打印到日志。
- 接口包装统一 `ApiResponse{success,message,data}`；**两个历史契约特例除外**：`GET /config` 返裸 dict、`POST /clean_orphan_subtitles` 收裸数组，详见 [API.md](API.md)。

## 技术债与绕开姿势
- `config` 表保留了插件时代的废弃字段（`enabled`、`density`、`useTmdbID`），代码不读取；配置读写以 `AppConfig` 为准，勿重新启用这些字段。表结构迁移只增不改（见 [DATA_MODEL.md](DATA_MODEL.md)）。
- spec/引擎注释中"详情只留最近 20 条"与实现不符，实际行为见 [pitfalls.md](pitfalls.md)；改历史裁剪时一并处理。
- 自动扫描间隔最小 60 秒、重试 Job 固定 5 分钟轮询，下限在 `scheduler.py` 常量里，不要从配置侧绕过。
- `fn-app/` 是绿联云（UGOS）打包工程，独立于主应用构建；改部署产物时注意两套 compose（`docker-compose.yml` 内置 danmu-api；`docker-compose.standalone.yml` 用 host 网络外挂）都要顾及。
