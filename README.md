# Robotics Knowledge Base

机器人模型架构知识库 —— VLA、全身控制、3D 视觉与 VLM 的架构详解。

**线上地址：** https://vla.yilong-zhu.com/

一个静态站点生成器：把 `docs/*.md` 编译成自包含的 HTML，部署到 Cloudflare Pages。
没有 node 依赖树、没有前端框架 —— 一个 Python 脚本 + 两个 CDN 引入的库（mermaid、KaTeX）。

## 快速开始

```bash
# 依赖（只有两个）
pip install markdown pygments

# 本地构建，不部署
./deploy.sh --build
# 然后浏览器打开 docs/site/index.html

# 构建 + 部署到线上
./deploy.sh

# 构建 + 部署 + 逐页字节校验线上是否与本地一致
./deploy.sh --verify
```

首次部署需要登录 Cloudflare：`npx wrangler login`。

## 目录结构

```
docs/
  01.Pi0_Architecture.md          源文件 —— 改这些
  ...
  20.Isaac-GR00T-N1.7_Architecture.md
  build_site.py                   生成器：模板、CSS、侧栏、页面注册表
  site/                           构建产物，git 忽略，每次构建整体覆盖
deploy.sh                         构建 + 部署
wrangler.toml                     Cloudflare Pages 项目配置
```

**`docs/site/` 不进 git，也不要手改** —— 每次 `./deploy.sh` 都会整体重新生成。
md 文件才是唯一来源。

## 新增一篇文档

两步，缺第二步不会上线：

1. 在 `docs/` 下建 `NN.名字_Architecture.md`，序号决定侧栏顺序。
2. 在 [`docs/build_site.py`](docs/build_site.py) 的 `SECTIONS` 里注册一行：

```python
{"file": "21.你的文档.md", "label": "侧栏显示名"},
```

`SECTIONS` 是分类到页面的映射，决定侧栏分组、首页卡片分区、以及页面之间的导航顺序。
一个页面可以带 `children`，会在侧栏缩进显示、在首页归到父卡片之后。

然后 `./deploy.sh`。

## 写作约定

- **首段即摘要。** 首页卡片的简介取每篇 md 的第一个非标题段落，截断到 200 字符。
  所以第一段要能独立成话，别用「本文将介绍……」开头。
- **mermaid** 用 ```` ```mermaid ```` 围栏。节点标签里的 `<br/>` 会被正确转义；
  节点名请用代码里真实存在的标识符，不要自己编符号名。
- **LaTeX** 行内 `$...$`、块级 `$$...$$`，KaTeX 渲染。
  `pre`/`code`/`.mermaid` 内部不会被解析，代码里的 `$VAR` 是安全的。
- **表格** 会自动包一层 `.table-wrap`（横向滚动 + 表头吸顶）。
- 图表宽度控制在 ~1600px scrollWidth 以内，否则在正文栏里会挤成一团。

## 部署机制

Cloudflare Pages 项目 `vla-model-architecture`，**Direct Upload 模式**。

⚠️ Direct Upload 项目**无法转成 Git 集成**（Cloudflare 的限制，单向不可逆）。
所以 push 到 GitHub 不会自动部署 —— 部署靠本地跑 `./deploy.sh`。
如果以后想要 push 即部署，两条路：GitHub Actions 里跑同样的 wrangler 命令，
或者新建一个 Git 集成项目并把自定义域名迁过去。

两个容易踩的坑：

- **`--branch main` 不能省。** 生产分支是 `main`，跟本地 git 分支叫什么无关。
  漏了这个参数，部署会落到 Preview 环境，线上纹丝不动。`deploy.sh` 里已经写死了。
- **Pages 会自动去掉 `.html`。** 请求 `/foo.html` 会 308 跳到 `/foo`。
  所以校验线上内容必须用 `curl -L` 配无扩展名的 URL，否则拿到空 body。

## 关于 `build_site.py` 的一个提醒

`build_cards()` 里清理简介的那串 `.replace()` 调用含一个 **U+E000 私用区哨兵字符**，
用来在剥离 `*` 之前保护转义过的星号（比如 `π\*₀.₆`）。
它在编辑器里可能显示为空或乱码 —— **这是有意的，别"顺手修好"**。
