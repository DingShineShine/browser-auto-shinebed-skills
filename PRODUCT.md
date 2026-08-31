# browser-auto-shinebed 产品说明

`browser-auto-shinebed` 是 Shinebed 对 `browser-act` 的增强入口。它保留原始 `browser-act` 的命令能力，例如 `state`、`click`、`input`、`eval`、`network`、`wait`、`screenshot` 和文件上传，同时增加 AdsPower 浏览器模式，并用 Forge Mode 帮团队把验证过的网站流程固化成可复用的 Codex Skill。

这个仓库是公开的薄仓库：只放安装入口、Forge references 和精选 workflow skills。完整实现、测试输出、截图、下载文件、客户数据和业务账号信息不放在这里。

## 浏览器模式

### chrome-direct

`chrome-direct` 直接连接用户已经打开的本地 Chrome。

适合：

- 复用当前真实登录态。
- 需要使用用户当前 Chrome 环境的网站任务。
- TikTok 评论等依赖已登录浏览器会话的抓取流程。

注意：

- 自动化任务会占用当前 Chrome。
- 任务运行时，Agent 会控制这个本地浏览器窗口。
- 首次创建或连接 direct 浏览器时，应由用户确认。

### chrome

`chrome` 由 `browser-act` 启动和管理独立 Chrome/Chromium profile。

适合：

- 同一平台多个账号隔离运行。
- 长期复用不同 profile。
- 公开页面抓取、商品评论采集、页面检查等不一定依赖用户当前 Chrome 的任务。
- 需要通过 `browser-act browser list` 选择并打开指定 browser record 的流程。

这个模式通常是公开数据抓取 workflow skill 的默认选择，例如 Costco、Chewy 这类产品评论抓取。

### adspower / ads

`adspower` 或 `ads` 模式通过 AdsPower Local API 启动指定 AdsPower profile，然后把 AdsPower 返回的 CDP endpoint 交给原始 `browser-act` session server。

适合：

- AdsPower 指纹浏览器环境。
- 代理、店铺、账号需要强隔离的业务流程。
- 多店铺、多账号、多地区 profile 的浏览器自动化。

使用方式上，通常只在打开浏览器时指定 AdsPower profile：

```bash
browser-act --session ads1 browser open adspower:<user_id> https://example.com
```

会话打开以后，后续页面操作仍然使用正常 `browser-act` 命令：

```bash
browser-act --session ads1 state
browser-act --session ads1 click 1
browser-act --session ads1 eval "..."
browser-act --session ads1 network requests
browser-act session close ads1
```

## Forge Mode

Forge Mode 用来把一次验证过的网站流程提炼成可复用的 Codex Skill。它适合把重复执行的浏览器任务固化下来，例如：

- 商品评论、视频评论、价格、库存等数据抓取。
- 后台报表下载、筛选、导出、上传。
- 需要分页、滚动、网络抓包、DOM 提取或浏览器侧 `eval` 的稳定流程。
- 需要每天、每周或按需重复执行的网站工作流。

Forge Mode 的产物通常是一个可安装的 Skill 包：

```text
output/{skill-name}/{capability-name}/
|-- SKILL.md
`-- scripts/
    `-- {script-name}.py
```

其中：

- `SKILL.md` 描述适用场景、前置条件、执行命令、参数、分页方式、成功标准和已知限制。
- `scripts/*.py` 只负责生成给 `browser-act eval` 执行的浏览器侧 JavaScript，不保存业务数据，也不直接调用 `browser-act`。
- `output/` 只是本地创作目录。确认可公开发布后，才把整理好的 skill 包挑选进这个薄仓库。

这个仓库里的公开 workflow skills，例如 `costco-product-reviews-scrape`、`chewy-product-reviews-scrape` 和 `tiktok-video-comments-scrape`，就是这种 Forge 产物发布后的形态。

## 安装方式

先安装核心入口 Skill：

```text
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/browser-auto-shinebed
```

然后按需要安装具体 workflow Skill：

```text
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/costco-product-reviews-scrape
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/chewy-product-reviews-scrape
https://github.com/DingShineShine/browser-auto-shinebed-skills/tree/main/tiktok-video-comments-scrape
```

安装完成后，新开任务或在下一轮对话中自然描述需求即可，例如：

```text
抓取这个 TikTok 视频的所有评论和回复，并保存成 JSON。
```

## 公开边界

这个薄仓库可以公开包含：

- Codex Skill 安装入口。
- Forge Mode references。
- 已整理、可复用、可安装的 workflow skills。
- 不含敏感数据的 helper scripts。

这个薄仓库不应包含：

- 私有 Python 实现源码和开发测试工程。
- `output/` 下的一次性运行结果。
- 截图、报告、PPT、下载文件和调试缓存。
- 客户数据、店铺数据、评论原始导出文件。
- AdsPower profile id、业务账号、cookie、token、密码或 API key。
