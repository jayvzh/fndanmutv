# FnDanmuTV 产品需求文档（PRD）

> 版本：v1.0 ｜ 需求细节与验收标准以 `.trae/specs/extract-standalone-docker-app/` 下 spec 为准；本文是产品视角的归纳，不复制 spec 全文。

## 1. 背景

DanmuTV 原为 MoviePilot V2 插件（弹幕刮削影视版），强依赖 MoviePilot 的插件基类、KV 存储、事件钩子、媒体识别链与 Module Federation 前端宿主，无法独立运行。

本项目将其剥离为**可独立部署的 Docker 全栈应用**：从弹幕 API 后端（[danmu-api](https://github.com/huangxd-/danmu_api)，弹弹 play 兼容协议）获取影视弹幕，转换为 ASS 弹幕字幕，并可与视频原有字幕合并。在不安装 MoviePilot 的任意媒体库环境中使用。

## 2. 目标用户与场景

- 自托管 NAS / 家庭服务器用户，希望为本地影视库自动生成弹幕字幕。
- 电视剧 / 电影 / 动漫等媒体，按文件名与弹弹作品库匹配弹幕。
- 需要批量刮削、失败自动重试、定时增量扫描、手动纠偏匹配、残留字幕清理的一体化 Web 工具。

## 3. 功能需求

| 编号 | 功能 | 说明 |
| --- | --- | --- |
| F1 | 单文件刮削 | 按文件名匹配弹幕，视频同目录产出 `<视频名>.danmu.chs.ass`；有原字幕时合并产出 `<字幕名>.withDanmu.ass` |
| F2 | 目录批量刮削 | 单目录 / 递归（最浅层优先，最深 6 层）；后台串行、每文件间隔 0.5s、429 全局限流退避；支持增量 / 全量（force） |
| F3 | 失败重试 | 弹幕不足 / 限流 / 网络错误入队，指数退避 `[5,30,60,120,240,480]` 分钟，最多 10 次；APScheduler 每 5 分钟处理到期任务 |
| F4 | 手动匹配 | 为目录或单文件绑定弹弹作品与集数偏移；目录级写入媒体目录 `.dandan.anime.json` |
| F5 | 弹幕参数 | 分辨率、字号、透明度、持续时间、屏幕区域、多层弹幕、随机顶/底、密度、宽度扩展；支持保存 / 切换预设方案 |
| F6 | 字幕处理 | 外部字幕（ASS/SRT）合并、中文内嵌字幕提取（ffmpeg），支持 `.strm`（仅弹幕 ASS，不提取内嵌字幕） |
| F7 | 自动刮削 | APScheduler 按间隔（秒，下限 60）定时扫描配置的多个媒体库路径，增量跳过已有有效弹幕；默认关闭 |
| F8 | 仪表盘 | 服务/API 连通状态、媒体库统计、刮削进度、最近运行、下次重试时间（只读，免登录可见） |
| F9 | 目录浏览 | 目录树 / 子目录展开 / 目录统计 / 每文件弹幕条数与手动匹配概览，可在页面发起刮削与字幕清理 |
| F10 | 历史记录 | 全局批量 + 单文件历史（概要保留 100 条），分页查询，可选详情；支持清空 |
| F11 | 残留字幕清理 | 扫描无对应媒体的 `.danmu` 相关 ASS 文件并删除；支持按文件 / 目录清理弹幕与合并字幕 |
| F12 | API 连通检测 | 检测 danmu-api 可达性（`/api/logs` 返回 200 或 401 均视为可达） |
| F13 | Token 认证 | 所有 `/api/*` 业务端点 Bearer Token 认证；dashboard 只读状态接口免鉴权 |
| F14 | 单容器部署 | 多阶段镜像内置 ffmpeg/ffprobe，FastAPI 同时提供 API 与前端静态资源；compose 可选内置 danmu-api |

## 4. 非目标（明确不做）

- 不依赖、不兼容 MoviePilot 插件体系（无 `from app...`、插件事件、`save_data/get_data`）。
- 不接入 TMDB 等外部影视元数据源；媒体识别只做文件名 / 正则解析（原 `useTmdbID` 配置项已移除，固定文件名匹配）。
- 不做多用户 / 权限体系，只有单一访问 Token。
- 不做弹幕编辑器、播放器，只产出标准 ASS 字幕文件。

## 5. 关键业务规则

- 本地弹幕缓存复用：同目录已存在 `<视频名>.danmu.chs.ass` 且 `Dialogue:` 行数 ≥ 100 视为有效，增量刮削跳过 API（仍会尝试字幕合并）。
- 弹弹 commentId 组合规则：`commentId = animeId * 10000 + 归一化集数`；手动匹配优先于文件名匹配。
- 媒体扩展名白名单：`.mp4 .mkv .avi .mov .wmv .flv .ts .m4v`，外加启用 `.strm`（配置开关，默认启用）；隐藏目录（点号开头）跳过。
- 弹幕 / 合并字幕一律**写回视频文件所在目录**，故媒体卷必须可写。
- 批量任务全应用互斥：同一时刻只允许一个批量刮削；中止请求在当前文件处理完后生效。

## 6. 技术约束

- 后端 FastAPI + Pydantic v2 + APScheduler + SQLite（Python 3.12，conda 环境 `danmu`）。
- 前端 Vue 3 + Vite + Vuetify 3 + axios 纯 SPA，无 Module Federation / postMessage / iframe。
- 持久化只用 SQLite；定时任务只用全局唯一 APScheduler 实例。
- 详见 [ARCHITECTURE.md](ARCHITECTURE.md)。
