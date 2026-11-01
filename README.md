# Robotics Knowledge Base

机器人模型架构知识库 —— VLA、世界模型与 WAM、第一视角数据、全身控制、3D 视觉与 VLM 的架构详解。

**线上地址：** https://vla.yilong-zhu.com/

一个静态站点生成器：把 `docs/` 下所有登记的 Markdown 文章（含分类子目录）编译成 HTML，部署到 Cloudflare Pages。
没有 node 依赖树、没有前端框架 —— 一个 Python 脚本 + 两个 CDN 引入的库（mermaid、KaTeX）。

贡献入口：[CONTRIBUTING](CONTRIBUTING.md) · [文章维护 SOP](docs/ARTICLE_SOP.md)。

## 快速开始

```bash
# Python 3.11+；依赖安装在项目自己的环境中
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 本地构建，不部署
./deploy.sh --build
# 然后浏览器打开 docs/site/index.html

# 回归测试
python -m unittest discover -s tests

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
  21.Dyna-Deployment-Flywheel_Architecture.md
  22.Helix_Architecture.md
  23.Skild-S1_Architecture.md
  24.OpenWAM_Architecture.md       世界模型与 WAM：OpenWAM 架构
  egocentric/                     第一视角数据与方法文章
    25.HumanEgo_Architecture.md
  ARTICLE_SOP.md                  文章写作、登记、检查与发布步骤
  build_site.py                   生成器：模板、CSS、侧栏、页面注册表
  site/                           构建产物，git 忽略，每次构建整体覆盖
CONTRIBUTING.md                   贡献与 PR 流程
deploy.sh                         构建 + 部署
wrangler.toml                     Cloudflare Pages 项目配置
requirements.txt                  已验证的 Python 构建依赖
tests/                            生成器与部署脚本回归测试
```

**`docs/site/` 不进 git，也不要手改** —— 每次 `./deploy.sh` 都会整体重新生成。
md 文件才是唯一来源。

## 新增一篇文档

新增源文件后，需要登记导航、领域和日期信息。完整流程见[文章维护 SOP](docs/ARTICLE_SOP.md)。

1. 在 `docs/` 或分类子目录下建 `NN.名字_Architecture.md`，例如 `docs/egocentric/25.HumanEgo_Architecture.md`。序号用于保持文件名稳定，所有目录中的文件 basename 必须唯一。
2. 在 [`docs/build_site.py`](docs/build_site.py) 的 `SECTIONS` 里注册一行：

```python
{"file": "egocentric/25.HumanEgo_Architecture.md", "label": "HumanEgo"},
```

`SECTIONS` 是分类到页面的映射，**声明顺序**决定侧栏分组、首页卡片分区、以及页面之间的导航顺序，而不是文件名前的数字。
一个页面可以带 `children`，会在侧栏缩进显示、在首页归到父卡片之后。
分类子目录用于组织源码；侧栏类别由 `SECTIONS` 决定，不会按目录自动生成。

3. `PAGE_TOPICS` 和 `PAGE_DATES` 也使用同一完整相对路径作为键。先在 `PAGE_TOPICS` 登记已有领域 ID（可多选），再在 `PAGE_DATES` 登记核实后的年月及一手来源。日期字段示意如下，填写时替换为真实信息：

```python
"egocentric/25.HumanEgo_Architecture.md": {
    "month": "YYYY-MM",  # 方法或版本首发年月；不使用本地文件修改时间
    "kind": "论文首发",  # 也可标明模型、版本、项目或文章发布
    "source": "对应的一手来源 HTTPS 链接",
    "note": "可选：说明论文、开源和后续版本的日期区别。",
},
```

Overview 的知识导图和领域筛选依赖这些登记信息；缺失日期或领域会使构建报错。
日期表示所述方法或版本的首次公开年月，不是知识库文章更新时间。
源码可以位于子目录，输出网页仍为扁平文件，例如上述文章生成 `docs/site/25.HumanEgo_Architecture.html`；站内网页链接使用这个输出名。`ARTICLE_SOP.md` 等维护文档不登记为站点文章。
然后运行 `./deploy.sh --build` 检查，需要上线时再运行 `./deploy.sh`。

## 日常维护：预览、推送与发布

GitHub 保存源码，Cloudflare Pages 托管生成后的网页，两者分别操作：

1. 激活上面的 Python 环境，修改 `docs/` 中的文章源文件（可在分类子目录内）；新增页面还需登记导航、领域与日期。
2. 运行 `./deploy.sh --build`，打开 `docs/site/index.html` 检查内容、图表和导航。
3. 提交并推送功能分支到 GitHub，创建 Pull Request，合并到 `main`。
4. 更新本地 `main` 后运行 `./deploy.sh --verify`，构建并发布生产站点，然后逐页校验。

```bash
# 功能分支示例；先确认 git diff 里是本次要发布的改动
git switch -c docs/your-topic
./deploy.sh --build
git diff --check
git add docs/分类目录/你的文档.md docs/build_site.py
git commit -m "docs: update model architecture"
git push -u origin docs/your-topic
```

首次推送需要本机可用的 GitHub 登录凭据；首次发布需要 `npx wrangler login`。
`./deploy.sh --verify` **会先发布生产站点**，不是只读检查；本地检查使用 `--build`。
发布脚本固定上传到生产分支 `main`，所以即使从功能分支执行也会更新正式网站。

若以后需要“推送 `main` 自动上线”，可以保留当前 Direct Upload 项目，增加 GitHub Actions：
安装 `requirements.txt` → 运行 `./deploy.sh --build` → 使用 `cloudflare/wrangler-action@v4` 执行
`pages deploy docs/site --project-name=vla-model-architecture --branch=main`。
这需要在仓库 Actions secrets 中设置 `CLOUDFLARE_API_TOKEN`（目标账户的 Cloudflare Pages Edit 权限）和
`CLOUDFLARE_ACCOUNT_ID`。当前仓库没有启用这个自动发布工作流。
参考 [Cloudflare 官方 CI 指南](https://developers.cloudflare.com/pages/how-to/use-direct-upload-with-continuous-integration/)。

## 公开访问统计

首页与全部文章页底部显示「本站浏览」「本站访客」「本页浏览」，使用
[soxft 开源不蒜子](https://github.com/soxft/busuanzi)的公共计数服务，无需账户或 API 密钥。
样式和加载逻辑统一放在 `docs/build_site.py`，重新构建并发布后生效。

脚本使用 `https://busuanzi.9420.ltd/js`，通过 `data-prefix="busuanzi_value"` 兼容页面现有的计数标签。
该服务独立于原版不蒜子，历史计数不会自动继承；此次切换用于解决原接口持续超时的问题。

- 只有 `https://vla.yilong-zhu.com` 加载计数脚本；本地文件、localhost 与 Pages 预览域名不计数。
- 统计异步加载，不阻塞正文。服务不可用时显示「—」及「统计暂不可用」，不会把失败伪装成 0。
- 数字按统计服务的口径累计；访客数是服务去重后的估计，不等于精确人数，也不能补回接入前的历史流量。
- 这是第三方公开计数，不提供站长私有的趋势与来源分析。若另需后台分析，可以在 Cloudflare Pages
  项目中启用 Web Analytics；注意自动注入脚本可能影响 `--verify` 的整页字节比较。

如以后迁移正式域名，需要同步修改模板中的 hostname 判断，避免把新站或预览站计入当前统计。

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

`extract_summary()` 通过 `ESCAPED_ASTERISK_SENTINEL` 使用 **U+E000 私用区哨兵字符**，
用来在剥离 `*` 之前保护转义过的星号（比如 `π\*₀.₆`）。
它在编辑器里可能显示为空或乱码 —— **这是有意的，别"顺手修好"**。
