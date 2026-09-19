# 旅行者档案维护说明

这是 Alesia0411 的 GitHub Profile README。主题使用独立 SVG 卡片，借鉴原神菜单的星空、米白与浅金视觉语言；图形由本仓库代码绘制，不依赖图床、第三方统计服务或游戏素材。

## 日常更新

只修改 `profile/` 下的 JSON 文件，再运行：

```sh
python scripts/build_profile.py
```

需要 Python 3.8 或更新版本，无需安装依赖。双击 `preview/index.html` 可查看本地效果；预览页只是检查工具，真正发布的是根目录 `README.md` 和 `assets/`。

提交到 GitHub 的 `main` 分支后，Actions 会校验配置并自动提交生成文件。也可以在 Actions 中手动运行 **Build profile**。不要手动编辑生成的 README、SVG 或预览页，下一次生成会覆盖它们。

| 要修改的内容 | 配置文件 |
| --- | --- |
| 昵称、简介、签名、状态、配色 | `profile/profile.json` |
| 模块顺序与左右排列 | `profile/layout.json` |
| 身份、方向、教育、联系信息 | `profile/modules/about.json` |
| 技能分组和标签 | `profile/modules/skills.json` |
| 当前项目、学习、近期目标 | `profile/modules/now.json` |
| 代表项目、职责、技术栈、仓库链接 | `profile/modules/projects.json` |
| 教育、实践、开源经历 | `profile/modules/journey.json` |
| 兴趣与日常 | `profile/modules/interests.json` |
| 游戏名称、服务器、UID、状态 | `profile/modules/games.json` |
| GitHub、博客、作品集和邮箱链接 | `profile/modules/contact.json` |

所有“待填写”都是明确的空位，不代表真实技能或经历。当前游戏名称来自设计方案，不表示已确认正在游玩。UID 请始终写成字符串，例如 `"uid": "012345678"`，保留前导零。没有公开链接时保留 `"url": ""`，不会生成失效按钮。有效链接使用 `https://`；邮箱使用 `mailto:name@example.com`。

## 添加条目

在模块的 `items` 数组添加一个相同结构的对象即可；技能模块使用 `groups` 和 `tags`。卡片高度会自动增长，长文本会折行，不会用省略号丢失内容。桌面端卡片按 `columns`（1–3）排列，手机端自动单列显示。

例如新增游戏：

```json
{
  "title": "你的游戏",
  "server": "你的服务器",
  "uid": "012345678",
  "status": "偶尔上线",
  "accent": "#3b8f88"
}
```

技能分组：

```json
{"label": "编程语言", "tags": ["Python", "TypeScript", "C++"]}
```

项目：

```json
{
  "title": "项目名称",
  "body": "解决的问题与项目价值",
  "contribution": "你实际承担的职责与成果",
  "tags": ["Python", "FastAPI"],
  "url": "https://github.com/Alesia0411/项目仓库"
}
```

项目链接和联系方式会作为真正可点击的 HTML 链接放在卡片下方。GitHub 以图片方式显示 SVG，图片内部无法放置可交互按钮。页面末尾提供可展开的完整文字版，可搜索、选择并复制 UID。

## 排序、隐藏与新增模块

`profile/layout.json` 的每个数组是一行：一个模块占满行，两个模块在桌面并排、手机堆叠。例如：

```json
{"rows": [["about", "skills"], ["now"], ["projects"], ["games"], ["contact"]]}
```

隐藏模块可将 `"enabled": false` 加在该模块 JSON 顶层，或从布局移除。隐藏模块不会出现在图卡、文字版或链接中。

新增模块通常不必编写 Python。新建 `profile/modules/books.json`：

```json
{
  "type": "cards",
  "title": "我的书架",
  "subtitle": "READING NOTES",
  "columns": 2,
  "items": [
    {"title": "正在阅读的书", "label": "READING", "body": "一句话介绍你的收获"},
    {"title": "下一本书", "label": "UP NEXT", "body": "你希望探索的主题"}
  ]
}
```

再把 `["books"]` 插入布局即可。可复用的类型有 `facts`、`skills`、`cards`、`projects`、`timeline`、`games`、`links`，字段参考已有模块。模块 ID 仅用小写英文字母、数字、短横线或下划线，以字母开头。

需要全新视觉结构时，在 `scripts/profile_ui.py` 实现渲染函数并加入 `RENDERERS`；同步更新 `scripts/build_profile.py` 的字段验证和 `text_lines()` 文字版输出。`templates/preview.html` 只控制本地预览的外围。

## 检查与发布

```sh
python -m unittest discover -s tests -v
python scripts/build_profile.py
python scripts/build_profile.py --check
```

主页仓库必须是公开的 **Alesia0411/Alesia0411**，README 位于默认分支根目录。提交本仓库全部源文件和生成文件；无需部署 GitHub Pages。

如果首次发布需要手动完成：

1. 在 GitHub 创建公开仓库 `Alesia0411`。
2. 将此目录的文件提交到该仓库的 `main` 分支。
3. 访问 `https://github.com/Alesia0411` 查看效果。
4. 如自动更新被组织策略或分支保护拦截，仍可在本地运行生成命令并提交结果，不必为了自动更新关闭保护。

Actions 仅在更新生成文件的 job 获得 `contents: write`，PR 检查为只读，不需要额外 PAT。自动提交只包含 README、生成卡片、可选头像与预览页，失败时会显示在 Actions 页面中。

## GitHub 展示边界

- 本项目美化 Profile README，不修改 GitHub 的全局 CSS、导航或原生模块。
- 仓库列表、贡献热力图、活动、成就与关注关系均由 GitHub 提供真实数据；本项目不模拟数字。
- `assets/avatar.svg` 是配套可选头像，仅用于预览，没有替换账号当前头像。
- 手机通过 `<picture>` 选择专门生成的单列 SVG；不支持该元素的客户端回退到桌面版或文字版。
- SVG 使用系统字体，Windows、macOS 和移动设备的字形可能略有不同。
- 本地预览只近似 GitHub 的外围布局，最终以 GitHub 渲染为准。

官方参考：[Profile README](https://docs.github.com/en/account-and-profile/concepts/personal-profile)、[README 图片与 picture 元素](https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/quickstart-for-writing-on-github)。
