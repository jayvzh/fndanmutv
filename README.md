# MoviePilot-PluginsV2

MoviePilot三方插件市场：<https://github.com/jxxghp/MoviePilot-Plugins>

### 使用

添加 `https://raw.githubusercontent.com/jayvzh/MoviePilot-PluginsV2/main/` 到 PLUGIN\_MARKET

### [弹幕刮削(影视版)](https://github.com/jayvzh/MoviePilot-PluginsV2/blob/main/plugins.v2/danmutv/README.md)

自动刮削新入库文件，可以全局文件刮削或手动刮削指定目录。
通过 [danmu-api](https://github.com/huangxd-/danmu_api) 从影视源获取弹幕数据，转换为 ASS 格式字幕文件。
`.danmu.chs.ass` 为刮削出来的纯弹幕，`.withDanmu.ass` 为原生字幕与弹幕合并后的文件，方便不支持双字幕的播放器使用。

**功能特性：**

- 支持电视剧、电影、动漫等多种媒体类型的弹幕获取
- 多层弹幕效果，可选 2 层/3 层，彩色弹幕优先显示
- 智能缓存重试策略，优化限流处理

**注意：需要自行准备** **[danmu-api](https://github.com/huangxd-/danmu_api)** **后端服务。**
