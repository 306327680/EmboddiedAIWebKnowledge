# 参与维护

欢迎补充模型与数据集介绍、修正技术事实、更新一手来源，或改进阅读体验。文章写作与登记步骤见 [文章维护 SOP](docs/ARTICLE_SOP.md)，安装和构建见 [README](README.md#快速开始)。

## 一次贡献怎样完成

1. 从最新 `main` 创建功能分支，确认准备修改的文章及对应来源。
2. 修改 Markdown 源文档。新增文章可放在 `docs/` 或分类子目录，例如 `docs/egocentric/25.HumanEgo_Architecture.md`；保持文件名和已有公开链接稳定。
3. 在 `docs/build_site.py` 登记 `SECTIONS`、`PAGE_TOPICS`、`PAGE_DATES`。新增类别或知识导图入口的操作见 SOP。
4. 激活项目环境，运行 `./deploy.sh --build`、`python -m unittest discover -s tests`、`git diff --check`，检查生成页面。
5. 提交源码，推送功能分支并创建 Pull Request。说明改了什么、依据哪些官方资料、完成了哪些检查，以及仍有何处无法核实。
6. PR 合并到 `main` 后，从最新 `main` 构建并发布。**GitHub 推送本身不会更新线上网站**；`./deploy.sh --verify` 会先发布生产站点，再逐页校验。

## 提交内容

- 提交文章源文件、登记信息，以及本次确有修改的维护文档或代码。
- `docs/site/` 是生成结果，不要手改或提交；构建时会整体替换。
- 不提交 `.venv/`、`.wrangler/`、缓存、账户信息或访问凭据。
- 事实结论附一手来源；区分论文报告、官方代码行为、本地推断与实际验证。人类视频中的动作标注、离线预测和真机执行成功分别说明。

分类子目录只改变源文件的组织方式：`docs/egocentric/25.HumanEgo_Architecture.md` 仍生成 `docs/site/25.HumanEgo_Architecture.html`。因此，所有文章的文件名（不含目录）必须唯一。
