#!/usr/bin/env python3
"""Build static HTML site from Model Architecture markdown files."""

import html as html_lib
import hashlib
import re
import shutil
import tempfile
import unicodedata
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

SITE_DIR = Path(__file__).parent / "site"
MD_DIR = Path(__file__).parent

SITE_TITLE = "Robotics Knowledge Base"
SITE_SUBTITLE = "机器人模型架构知识库"
SUMMARY_LIMIT = 200
ESCAPED_ASTERISK_SENTINEL = "\ue000"

# Categories -> pages. A page may carry `children`, rendered nested in the
# sidebar and grouped after their parent on the index page.
SECTIONS = [
    {
        "title": "VLA 模型",
        "desc": "视觉-语言-动作 (Vision-Language-Action) 模型架构",
        "pages": [
            {"file": "01.Pi0_Architecture.md", "label": "Pi0"},
            {"file": "02.Pi0.5_Architecture.md", "label": "Pi0.5"},
            {"file": "03.Pi0-FAST_Architecture.md", "label": "Pi0-FAST"},
            {"file": "04.Pi-Star-0.6_Architecture.md", "label": "π*₀.₆ (Pi-Star-0.6)"},
            {"file": "05.Pi0.7_Architecture.md", "label": "π₀.₇ (Pi-0.7)"},
            {"file": "20.Isaac-GR00T-N1.7_Architecture.md", "label": "Isaac-GR00T N1.7"},
            {"file": "06.Isaac-GR00T-N1.6_Architecture.md", "label": "Isaac-GR00T N1.6"},
            {"file": "07.Isaac-GR00T-N1.5_Architecture.md", "label": "Isaac-GR00T N1.5"},
            {"file": "08.ACT_Architecture.md", "label": "ACT"},
            {"file": "09.SmolVLA_Architecture.md", "label": "SmolVLA"},
            {"file": "10.WALL-OSS_Architecture.md", "label": "WALL-OSS / WALL-X"},
            {"file": "11.X-VLA_Architecture.md", "label": "X-VLA"},
            {"file": "12.Psi0_Architecture.md", "label": "Psi0 (ψ₀)"},
            {"file": "22.Helix_Architecture.md", "label": "Helix"},
            {"file": "23.Skild-S1_Architecture.md", "label": "Skild S1"},
        ],
    },
    {
        "title": "世界模型与 WAM",
        "desc": "未来观测预测、世界与动作联合建模",
        "pages": [
            {"file": "24.OpenWAM_Architecture.md", "label": "OpenWAM"},
            {"file": "13.DreamZero_Architecture.md", "label": "DreamZero"},
            {"file": "14.FastWAM_Architecture.md", "label": "Fast-WAM"},
        ],
    },
    {
        "title": "Egocentric / 第一视角学习",
        "desc": "从人类第一视角示范学习空间交互表示与跨本体机器人策略",
        "pages": [
            {"file": "egocentric/25.HumanEgo_Architecture.md", "label": "HumanEgo"},
        ],
    },
    {
        "title": "全身控制 (WBC)",
        "desc": "人形机器人全身控制与运动生成",
        "pages": [
            {
                "file": "15.GR00T-WBC_Overview.md",
                "label": "GR00T-WBC 总览",
                "children": [
                    {"file": "16.Decoupled-WBC_Architecture.md", "label": "Decoupled WBC"},
                    {"file": "17.GEAR-SONIC_Architecture.md", "label": "GEAR-SONIC"},
                    {"file": "18.MotionBricks_Architecture.md", "label": "MotionBricks"},
                ],
            },
        ],
    },
    {
        "title": "3D 视觉与 VLM",
        "desc": "空间理解、深度、位姿与视觉语言模型",
        "pages": [
            {"file": "19.VLM3_Architecture.md", "label": "VLM³"},
        ],
    },
    {
        "title": "部署、评估与运维",
        "desc": "机器人从模型演示到规模化生产的数据、评估与可靠性系统",
        "pages": [
            {"file": "21.Dyna-Deployment-Flywheel_Architecture.md", "label": "Dyna 部署飞轮"},
        ],
    },
]

# Publication dates describe the method/version, never the local file mtime.
# Keep the date's meaning and a primary source alongside it (checked 2026-08).
PAGE_DATES = {
    "01.Pi0_Architecture.md": {
        "month": "2024-10", "kind": "模型首发",
        "source": "https://www.pi.website/blog/pi0",
    },
    "02.Pi0.5_Architecture.md": {
        "month": "2025-04", "kind": "模型首发",
        "source": "https://www.pi.website/blog/pi05",
    },
    "03.Pi0-FAST_Architecture.md": {
        "month": "2025-01", "kind": "方法首发",
        "source": "https://www.pi.website/research/fast",
    },
    "04.Pi-Star-0.6_Architecture.md": {
        "month": "2025-11", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2511.14759",
    },
    "05.Pi0.7_Architecture.md": {
        "month": "2026-04", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2604.15483",
    },
    "06.Isaac-GR00T-N1.6_Architecture.md": {
        "month": "2025-09", "kind": "版本公布",
        "source": "https://investor.nvidia.com/news/press-release-details/2025/NVIDIA-Accelerates-Robotics-Research-and-Development-With-New-Open-Models-and-Simulation-Libraries/default.aspx",
        "note": "N1.6 首次公布；不以之后的代码更新计时。",
    },
    "07.Isaac-GR00T-N1.5_Architecture.md": {
        "month": "2025-05", "kind": "版本公布",
        "source": "https://nvidianews.nvidia.com/news/nvidia-powers-humanoid-robot-industry-with-cloud-to-robot-computing-platforms-for-physical-ai",
        "note": "2025.05 公布；技术详解于 2025.06 发布。",
    },
    "08.ACT_Architecture.md": {
        "month": "2023-04", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2304.13705",
    },
    "09.SmolVLA_Architecture.md": {
        "month": "2025-06", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2506.01844",
    },
    "10.WALL-OSS_Architecture.md": {
        "month": "2025-09", "kind": "模型首发",
        "source": "https://github.com/X-Square-Robot/wall-x#news",
        "note": "初代 WALL-OSS；不是 2026.05 的 WALL-OSS-0.5。",
    },
    "11.X-VLA_Architecture.md": {
        "month": "2025-10", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2510.10274",
    },
    "12.Psi0_Architecture.md": {
        "month": "2026-03", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2603.12263",
    },
    "13.DreamZero_Architecture.md": {
        "month": "2026-02", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2602.15922",
    },
    "14.FastWAM_Architecture.md": {
        "month": "2026-03", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2603.16666",
    },
    "15.GR00T-WBC_Overview.md": {
        "month": "2025-11", "kind": "项目首发",
        "source": "https://github.com/NVlabs/GR00T-WholeBodyControl#news",
        "note": "多方法总览；各子方法的年月分别标注。",
    },
    "16.Decoupled-WBC_Architecture.md": {
        "month": "2025-11", "kind": "代码首发",
        "source": "https://github.com/NVlabs/GR00T-WholeBodyControl#news",
        "note": "按独立控制器的公开代码发布计时。",
    },
    "17.GEAR-SONIC_Architecture.md": {
        "month": "2025-11", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2511.07820",
        "note": "2026.02 开源推理；2026.04 开源训练。",
    },
    "18.MotionBricks_Architecture.md": {
        "month": "2026-04", "kind": "方法预览",
        "source": "https://github.com/NVlabs/GR00T-WholeBodyControl#news",
    },
    "19.VLM3_Architecture.md": {
        "month": "2026-05", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2605.30561",
    },
    "20.Isaac-GR00T-N1.7_Architecture.md": {
        "month": "2026-03", "kind": "版本公布",
        "source": "https://nvidianews.nvidia.com/news/nvidia-expands-open-model-families-to-power-the-next-wave-of-agentic-physical-and-healthcare-ai",
    },
    "21.Dyna-Deployment-Flywheel_Architecture.md": {
        "month": "2026-08", "kind": "文章发布",
        "source": "https://www.dyna.co/research/scaling-customer-deployments",
        "note": "生产系统文章的年月，不是公司或模型首次发布。",
    },
    "22.Helix_Architecture.md": {
        "month": "2025-02", "kind": "模型首发",
        "source": "https://www.figure.ai/news/helix",
        "note": "初代 Helix；不使用后续 Helix 02 的日期。",
    },
    "23.Skild-S1_Architecture.md": {
        "month": "2026-08", "kind": "模型首发",
        "source": "https://skild.ai/blogs/s1",
    },
    "24.OpenWAM_Architecture.md": {
        "month": "2026-09", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2609.07398",
        "note": "OpenWAM-Infra、Study 与 α；按论文公开年月标注。",
    },
    "egocentric/25.HumanEgo_Architecture.md": {
        "month": "2026-05", "kind": "论文首发",
        "source": "https://arxiv.org/abs/2605.24934",
        "note": "v1 于 2026.05 首发；代码与数据于 2026.06 发布，论文 v3 于 2026.09 更新。",
    },
}

# Cross-cutting knowledge domains used by the overview knowledge map. Pages can
# belong to multiple domains; the hexagons count covered documents, not words.
KNOWLEDGE_DOMAINS = [
    {
        "id": "foundation",
        "label": "VLA / WAM",
        "desc": "通用策略与世界动作模型",
    },
    {
        "id": "imitation",
        "label": "模仿学习 / BC",
        "desc": "示范学习、动作分块与监督策略训练",
    },
    {
        "id": "generative",
        "label": "Flow / Diffusion",
        "desc": "连续动作与视频的生成式建模",
    },
    {
        "id": "reinforcement",
        "label": "强化学习 / Online",
        "desc": "PPO、offline RL 与部署经验改进",
    },
    {
        "id": "control",
        "label": "WBC / 运动控制",
        "desc": "全身控制、运动生成与跟踪",
    },
    {
        "id": "perception",
        "label": "VLM / 空间感知",
        "desc": "视觉语言主干、3D 与世界理解",
    },
    {
        "id": "deployment",
        "label": "部署 / 评估",
        "desc": "数据飞轮、可靠性与生产评估",
    },
    {
        "id": "sequence",
        "label": "Token / 序列建模",
        "desc": "动作分词、离散潜变量与序列生成",
    },
]

PAGE_TOPICS = {
    "01.Pi0_Architecture.md": {"foundation", "imitation", "generative", "perception"},
    "02.Pi0.5_Architecture.md": {"foundation", "imitation", "generative", "perception"},
    "03.Pi0-FAST_Architecture.md": {"foundation", "imitation", "sequence"},
    "04.Pi-Star-0.6_Architecture.md": {
        "foundation",
        "imitation",
        "reinforcement",
        "deployment",
        "sequence",
    },
    "05.Pi0.7_Architecture.md": {"foundation", "imitation", "perception"},
    "06.Isaac-GR00T-N1.6_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "perception",
    },
    "07.Isaac-GR00T-N1.5_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "perception",
    },
    "08.ACT_Architecture.md": {"imitation", "sequence"},
    "09.SmolVLA_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "perception",
    },
    "10.WALL-OSS_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "perception",
    },
    "11.X-VLA_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "perception",
    },
    "12.Psi0_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "control",
        "perception",
    },
    "13.DreamZero_Architecture.md": {"foundation", "imitation", "generative"},
    "24.OpenWAM_Architecture.md": {"foundation", "imitation", "generative", "perception"},
    "egocentric/25.HumanEgo_Architecture.md": {"imitation", "generative", "perception"},
    "14.FastWAM_Architecture.md": {"foundation", "imitation", "generative"},
    "15.GR00T-WBC_Overview.md": {"reinforcement", "control", "deployment"},
    "16.Decoupled-WBC_Architecture.md": {"reinforcement", "control", "deployment"},
    "17.GEAR-SONIC_Architecture.md": {
        "reinforcement",
        "control",
        "deployment",
        "sequence",
    },
    "18.MotionBricks_Architecture.md": {
        "generative",
        "control",
        "deployment",
        "sequence",
    },
    "19.VLM3_Architecture.md": {"perception"},
    "20.Isaac-GR00T-N1.7_Architecture.md": {
        "foundation",
        "imitation",
        "generative",
        "perception",
    },
    "21.Dyna-Deployment-Flywheel_Architecture.md": {
        "foundation",
        "generative",
        "deployment",
    },
    "22.Helix_Architecture.md": {
        "foundation",
        "imitation",
        "perception",
        "deployment",
    },
    "23.Skild-S1_Architecture.md": {
        "foundation",
        "imitation",
        "perception",
        "deployment",
    },
}

KNOWLEDGE_PATH_STAGES = [
    {
        "step": "01",
        "kind": "sense",
        "title": "感知与学习信号",
        "flow": "融合 / 训练",
        "nodes": [
            ("VLM / 3D 感知", "视觉 · 语言 · 状态", "19.VLM3_Architecture.html"),
            ("模仿学习 / BC", "示范 · Action Chunk", "08.ACT_Architecture.html"),
            ("Flow / Diffusion", "连续动作生成", "01.Pi0_Architecture.html"),
            ("RL / Online", "经验 · 奖励 · 修正", "04.Pi-Star-0.6_Architecture.html"),
            ("Token / 序列", "FAST · FSQ · VQ", "03.Pi0-FAST_Architecture.html"),
            ("Egocentric", "人类示范 · ICT · 跨本体", "25.HumanEgo_Architecture.html"),
        ],
    },
    {
        "step": "02",
        "kind": "model",
        "title": "策略与世界模型",
        "flow": "生成动作",
        "nodes": [
            ("VLA / ICL", "π 系列 · GR00T · Helix · S1", "23.Skild-S1_Architecture.html"),
            ("WAM", "DreamZero · Fast-WAM · Dyna-2", "13.DreamZero_Architecture.html"),
        ],
    },
    {
        "step": "03",
        "kind": "action",
        "title": "动作与控制",
        "flow": "下发执行",
        "nodes": [
            ("动作序列", "token / flow chunk", "03.Pi0-FAST_Architecture.html"),
            ("WBC / 运动生成", "Decoupled · SONIC · MotionBricks", "15.GR00T-WBC_Overview.html"),
        ],
    },
    {
        "step": "04",
        "kind": "robot",
        "title": "真实机器人",
        "flow": "记录评估",
        "nodes": [
            ("机器人执行", "操作 · 行走 · Loco-manipulation", "15.GR00T-WBC_Overview.html"),
        ],
    },
    {
        "step": "05",
        "kind": "production",
        "title": "生产闭环",
        "flow": "",
        "nodes": [
            ("规模化部署", "SOP · Episode · Telemetry", "21.Dyna-Deployment-Flywheel_Architecture.html"),
            ("失败数据", "语义标签 · 训练切片", "21.Dyna-Deployment-Flywheel_Architecture.html"),
        ],
    },
]


def iter_pages(sections=None):
    """Yield (page, section, depth) for every page, parents before children."""
    if sections is None:
        sections = SECTIONS
    for section in sections:
        for page in section["pages"]:
            yield page, section, 0
            for child in page.get("children", []):
                yield child, section, 1


def html_filename(markdown_filename: str) -> str:
    """Accept a canonical relative source path and keep published HTML flat."""
    if not isinstance(markdown_filename, str) or not markdown_filename:
        raise ValueError(f"invalid Markdown filename: {markdown_filename!r}")
    path = Path(markdown_filename)
    if (
        path.is_absolute()
        or "\\" in markdown_filename
        or re.match(r"^[A-Za-z]:", markdown_filename)
        or any(part in ("", ".", "..") for part in markdown_filename.split("/"))
        or path.as_posix() != markdown_filename
        or path.suffix.lower() != ".md"
    ):
        raise ValueError(f"invalid Markdown filename: {markdown_filename!r}")
    return path.with_suffix(".html").name


def validate_sections(sections=None, md_dir: Path = MD_DIR) -> None:
    """Fail early when the page registry is incomplete or ambiguous."""
    validate_topics = sections is None
    if sections is None:
        sections = SECTIONS

    errors = []
    seen = set()
    # The overview is generated separately; no article may overwrite it.
    output_sources = {"index.html": "generated overview"}
    source_root = md_dir.resolve()
    for page, section, _depth in iter_pages(sections):
        filename = page.get("file")
        label = page.get("label")
        if not isinstance(filename, str):
            errors.append(f"{section.get('title', '<untitled>')}: page has no filename")
            continue
        try:
            output_filename = html_filename(filename)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if filename in seen:
            errors.append(f"duplicate page registration: {filename}")
        seen.add(filename)
        # Case-fold so a build on a case-insensitive filesystem cannot silently
        # overwrite a differently-cased basename from another source folder.
        output_key = output_filename.casefold()
        previous_source = output_sources.get(output_key)
        if previous_source is not None and previous_source != filename:
            errors.append(
                f"duplicate output filename: {output_filename} "
                f"({previous_source}, {filename})"
            )
        else:
            output_sources[output_key] = filename
        if not isinstance(label, str) or not label.strip():
            errors.append(f"{filename}: label must be a non-empty string")
        source_path = md_dir / filename
        if not source_path.resolve().is_relative_to(source_root):
            errors.append(f"Markdown source escapes docs directory: {filename}")
        elif not source_path.is_file():
            errors.append(f"missing Markdown source: {filename}")

    source_files = {
        path.relative_to(md_dir).as_posix()
        for path in md_dir.rglob("*")
        if path.is_file() and path.suffix.lower() == ".md" and re.match(r"^\d+\.", path.name)
    }
    for filename in sorted(source_files - seen):
        errors.append(f"unregistered Markdown source: {filename}")

    if validate_topics:
        for filename in sorted(seen - PAGE_DATES.keys()):
            errors.append(f"page has no publication date: {filename}")
        for filename in sorted(PAGE_DATES.keys() - seen):
            errors.append(f"publication date references an unknown page: {filename}")
        for filename, publication in PAGE_DATES.items():
            if not re.fullmatch(r"[0-9]{4}-(0[1-9]|1[0-2])", publication.get("month", "")):
                errors.append(f"{filename}: invalid publication month (expected YYYY-MM)")
            if not publication.get("kind") or not publication.get("source", "").startswith("https://"):
                errors.append(f"{filename}: publication date needs a kind and HTTPS source")
        domain_ids = {domain["id"] for domain in KNOWLEDGE_DOMAINS}
        for filename in sorted(seen - PAGE_TOPICS.keys()):
            errors.append(f"page has no knowledge-domain tags: {filename}")
        for filename in sorted(PAGE_TOPICS.keys() - seen):
            errors.append(f"topic metadata references an unknown page: {filename}")
        for filename, topics in PAGE_TOPICS.items():
            for topic in sorted(topics - domain_ids):
                errors.append(f"{filename}: unknown knowledge domain: {topic}")

    if errors:
        raise ValueError("Invalid SECTIONS configuration:\n- " + "\n- ".join(errors))


CSS = """\
:root {
    --bg: #ffffff;
    --bg-sidebar: #f8f9fa;
    --bg-code: #f4f5f7;
    --text: #1a1a2e;
    --text-muted: #6c757d;
    --border: #e2e6ea;
    --accent: #2563eb;
    --accent-light: #eff6ff;
    --heading: #0f172a;
    --link: #2563eb;
    --map-sense: #0284c7;
    --map-model: #7c3aed;
    --map-action: #0d9488;
    --map-robot: #16a34a;
    --map-production: #d97706;
    /* Fluid layout metrics — everything scales with the viewport and is
       clamped to a sane min/max, so no width is hard-coded. */
    --sidebar-w: clamp(220px, 17vw, 300px);
    --toc-w: clamp(200px, 15vw, 280px);
    --content-pad: clamp(20px, 3.2vw, 56px);
    --content-max: clamp(640px, 58vw, 1080px);   /* prose reading measure */
    --wide-max: clamp(640px, 76vw, 1500px);      /* diagrams, tables, cards */
    --table-stripe: #f8fafc;
}

@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
        --bg: #0f172a;
        --bg-sidebar: #1e293b;
        --bg-code: #1e293b;
        --text: #e2e8f0;
        --text-muted: #94a3b8;
        --border: #334155;
        --accent: #60a5fa;
        --accent-light: #1e3a5f;
        --heading: #f1f5f9;
        --link: #60a5fa;
        --table-stripe: #1e293b;
        --map-sense: #38bdf8;
        --map-model: #a78bfa;
        --map-action: #2dd4bf;
        --map-robot: #4ade80;
        --map-production: #fbbf24;
    }
}

/* Explicit override via the toggle button */
:root[data-theme="dark"] {
    --bg: #0f172a;
    --bg-sidebar: #1e293b;
    --bg-code: #1e293b;
    --text: #e2e8f0;
    --text-muted: #94a3b8;
    --border: #334155;
    --accent: #60a5fa;
    --accent-light: #1e3a5f;
    --heading: #f1f5f9;
    --link: #60a5fa;
    --table-stripe: #1e293b;
    --map-sense: #38bdf8;
    --map-model: #a78bfa;
    --map-action: #2dd4bf;
    --map-robot: #4ade80;
    --map-production: #fbbf24;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    display: flex;
    min-height: 100vh;
    overflow-x: hidden;
}

/* Sidebar */
.sidebar {
    width: var(--sidebar-w);
    /* Bound the fixed panel so long navigation lists scroll inside it. */
    height: 100vh;
    height: 100dvh;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    padding: 24px 0;
    position: fixed;
    top: 0;
    left: 0;
    overflow-y: auto;
    overscroll-behavior-y: contain;
    z-index: 100;
    transition: transform 0.3s;
}

.sidebar-header {
    padding: 0 20px 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
}

.sidebar-header h2 {
    font-size: 16px;
    color: var(--heading);
    font-weight: 700;
    letter-spacing: -0.02em;
}

.sidebar-header p {
    font-size: 12px;
    color: var(--text-muted);
    margin-top: 4px;
}

.sidebar nav a {
    display: block;
    padding: 8px 20px;
    color: var(--text);
    text-decoration: none;
    font-size: 14px;
    font-weight: 500;
    border-left: 3px solid transparent;
    transition: all 0.15s;
}

.sidebar nav a:hover {
    background: var(--accent-light);
    color: var(--accent);
}

.sidebar nav a.active {
    background: var(--accent-light);
    color: var(--accent);
    border-left-color: var(--accent);
    font-weight: 600;
}

/* Mobile toggle */
.menu-toggle {
    display: none;
    position: fixed;
    top: 12px;
    left: 12px;
    z-index: 200;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 12px;
    cursor: pointer;
    font-size: 18px;
    color: var(--text);
}

/* Theme toggle */
.theme-toggle {
    position: fixed;
    top: 16px;
    right: 16px;
    z-index: 200;
    width: 38px;
    height: 38px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: 50%;
    cursor: pointer;
    font-size: 17px;
    line-height: 1;
    color: var(--text);
    transition: border-color 0.2s, background 0.2s;
}

.theme-toggle:hover {
    border-color: var(--accent);
    color: var(--accent);
}

/* Swap the glyph with the active theme */
.theme-toggle .icon-dark { display: none; }
.theme-toggle .icon-light { display: inline; }

@media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) .theme-toggle .icon-dark { display: inline; }
    :root:not([data-theme="light"]) .theme-toggle .icon-light { display: none; }
}

:root[data-theme="dark"] .theme-toggle .icon-dark { display: inline; }
:root[data-theme="dark"] .theme-toggle .icon-light { display: none; }
:root[data-theme="light"] .theme-toggle .icon-dark { display: none; }
:root[data-theme="light"] .theme-toggle .icon-light { display: inline; }

/* Keep the toggle clear of the in-page TOC on wide screens */
@media (min-width: 1400px) {
    .theme-toggle {
        right: calc(var(--toc-w) + 16px);
    }
}

/* Content */
.content {
    margin-left: var(--sidebar-w);
    flex: 1;
    min-width: 0;
    padding: 40px var(--content-pad) 80px;
}

/* Wide layouts reserve room for the in-page TOC */
@media (min-width: 1400px) {
    .content {
        margin-right: var(--toc-w);
    }
}

/* The column fills whatever space is left, then centres a capped reading
   measure inside it. Blocks that cannot reflow — diagrams, tables, card
   grids — are allowed to run wider than the prose. */
.content-inner {
    max-width: var(--wide-max);
    margin: 0 auto;
}

/* Two classes deep so this beats the per-element `margin: a b c` shorthands
   below, which would otherwise reset margin-inline to 0 and kill the centring. */
.content .content-inner > * {
    max-width: var(--content-max);
    margin-inline: auto;
}

.content .content-inner > .diagram,
.content .content-inner > .table-wrap,
.content .content-inner > .cat,
.content .content-inner > .card-grid,
.content .content-inner > .knowledge-overview,
.content .content-inner > .domain-landscape {
    max-width: var(--wide-max);
}

/* In-page table of contents */
.toc {
    position: fixed;
    top: 0;
    right: 0;
    width: var(--toc-w);
    max-height: 100vh;
    overflow-y: auto;
    padding: 40px 20px 40px 12px;
    border-left: 1px solid var(--border);
    background: var(--bg);
    display: none;
}

@media (min-width: 1400px) {
    .toc {
        display: block;
    }
}

.toc-title {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-muted);
    margin-bottom: 10px;
}

.toc ul {
    list-style: none;
    margin: 0;
    padding: 0;
}

.toc li {
    margin: 0;
}

.toc a {
    display: block;
    padding: 4px 8px;
    font-size: 12.5px;
    line-height: 1.45;
    color: var(--text-muted);
    text-decoration: none;
    border-left: 2px solid var(--border);
    transition: color 0.15s, border-color 0.15s;
}

.toc a:hover {
    color: var(--accent);
}

.toc a.toc-h3 {
    padding-left: 20px;
    font-size: 12px;
}

.toc a.active {
    color: var(--accent);
    border-left-color: var(--accent);
    font-weight: 600;
}

.content h1 {
    font-size: 28px;
    color: var(--heading);
    font-weight: 800;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border);
    letter-spacing: -0.03em;
}

.content h2 {
    font-size: 22px;
    color: var(--heading);
    font-weight: 700;
    margin-top: 40px;
    margin-bottom: 12px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--border);
    letter-spacing: -0.02em;
}

.content h3 {
    font-size: 18px;
    color: var(--heading);
    font-weight: 600;
    margin-top: 28px;
    margin-bottom: 8px;
}

/* Anchor offset so linked headings aren't hidden under the viewport edge */
.content h2, .content h3, .content h4 {
    scroll-margin-top: 24px;
}

/* Heading permalinks: revealed on hover */
.content .headerlink {
    float: right;
    margin-left: 12px;
    color: var(--border);
    text-decoration: none;
    font-weight: 400;
    opacity: 0;
    transition: opacity 0.15s;
}

.content h2:hover .headerlink,
.content h3:hover .headerlink,
.content h4:hover .headerlink {
    opacity: 1;
}

.content .headerlink:hover {
    color: var(--accent);
}

.content h4 {
    font-size: 15px;
    color: var(--heading);
    font-weight: 600;
    margin-top: 20px;
    margin-bottom: 6px;
}

.content p {
    margin-bottom: 12px;
}

.content a {
    color: var(--link);
    text-decoration: none;
}

.content a:hover {
    text-decoration: underline;
}

.content ul, .content ol {
    /* Indent via padding, not margin-left, so the block can still be centred. */
    margin: 8px 0 12px;
    padding-left: 24px;
}

.content li {
    margin-bottom: 4px;
}

.content strong {
    font-weight: 600;
    color: var(--heading);
}

/* Code */
.content code {
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    font-size: 13px;
    background: var(--bg-code);
    padding: 2px 6px;
    border-radius: 4px;
}

.content pre {
    background: var(--bg-code);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 16px 20px;
    overflow-x: auto;
    margin: 12px 0 16px;
    font-size: 13px;
    line-height: 1.6;
}

.content pre code {
    background: none;
    padding: 0;
}

/* Mermaid */
.mermaid {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin: 16px 0;
    text-align: center;
    overflow-x: auto;
}

/* Zoomable diagram wrapper (built by JS around each .mermaid) */
.diagram {
    position: relative;
    margin: 16px 0;
}

.diagram .mermaid {
    margin: 0;
    max-width: 100%;
    overflow: auto;
    contain: layout paint;
    cursor: grab;
}

.diagram .mermaid.is-zoomed {
    max-height: 80vh;
    text-align: left;
}

.diagram .mermaid.is-panning {
    cursor: grabbing;
    user-select: none;
}

.diagram-tools {
    position: absolute;
    top: 8px;
    right: 8px;
    z-index: 5;
    display: flex;
    gap: 2px;
    padding: 2px;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: 6px;
    opacity: 0;
    transition: opacity 0.15s;
}

.diagram:hover .diagram-tools,
.diagram-tools:focus-within {
    opacity: 1;
}

.diagram-tools button {
    width: 26px;
    height: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    line-height: 1;
    color: var(--text-muted);
}

.diagram-tools button:hover {
    background: var(--accent-light);
    color: var(--accent);
}

.diagram-zoom {
    min-width: 40px;
    padding: 0 4px;
    font-size: 11px;
    font-variant-numeric: tabular-nums;
    color: var(--text-muted);
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Fullscreen: the wrapper becomes the whole viewport */
.diagram:fullscreen {
    background: var(--bg);
    padding: 12px;
}

.diagram:fullscreen .mermaid {
    height: 100%;
    max-height: none;
    border: none;
}

/* Touch devices have no hover — keep the controls visible */
@media (hover: none) {
    .diagram-tools { opacity: 1; }
}

/* Tables */
.table-wrap {
    overflow-x: auto;
    margin: 12px 0 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
}

.content table {
    width: 100%;
    border-collapse: collapse;
    margin: 0;
    font-size: 14px;
}

.content th, .content td {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    border-right: 1px solid var(--border);
    text-align: left;
    vertical-align: top;
}

.content th:last-child, .content td:last-child {
    border-right: none;
}

.content tbody tr:last-child td {
    border-bottom: none;
}

.content th {
    background: var(--bg-code);
    font-weight: 600;
    color: var(--heading);
    white-space: nowrap;
    position: sticky;
    top: 0;
}

.content tbody tr:nth-child(even) {
    background: var(--table-stripe);
}

/* Keep inline code readable inside tables */
.content td code, .content th code {
    font-size: 12.5px;
    white-space: nowrap;
}

/* Blockquotes */
.content blockquote {
    border-left: 4px solid var(--accent);
    background: var(--accent-light);
    padding: 12px 16px;
    margin: 12px 0;
    border-radius: 0 6px 6px 0;
}

/* Horizontal rule */
.content hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 32px 0;
}

/* Back to top */
.back-to-top {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--accent);
    color: white;
    border: none;
    border-radius: 50%;
    width: 40px;
    height: 40px;
    font-size: 18px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.3s;
    z-index: 50;
}

.back-to-top.visible {
    opacity: 1;
}

/* Public counters share the page theme and wrap on narrow screens. */
.site-stats {
    margin-top: 40px;
    padding-top: 20px;
    border-top: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 13px;
}

.site-stats-counts {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 24px;
}

.site-stats-counts > span {
    white-space: nowrap;
}

.site-stats-number {
    margin: 0 4px;
    color: var(--text);
    font-variant-numeric: tabular-nums;
}

.site-stats-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 16px;
    margin-top: 6px;
    font-size: 12px;
}

/* Responsive */
@media (max-width: 768px) {
    :root {
        /* No sidebar or TOC below this width — let the text use the full page. */
        --content-max: none;
        --wide-max: none;
    }
    .sidebar {
        transform: translateX(-100%);
    }
    .sidebar.open {
        transform: translateX(0);
    }
    .menu-toggle {
        display: block;
    }
    .content {
        margin-left: 0;
        margin-right: 0;
        padding: 60px 20px 60px;
    }
    .content h1 {
        font-size: 24px;
    }
    .content h2 {
        font-size: 20px;
    }
    .table-wrap {
        font-size: 13px;
    }
}
"""

TEMPLATE = """\
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - {site_title}</title>
    <link rel="stylesheet" href="{stylesheet}">
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css">
    <script>
        // Applied before first paint so the saved theme doesn't flash.
        (function () {{
            try {{
                var t = localStorage.getItem('theme');
                if (t === 'dark' || t === 'light') {{
                    document.documentElement.setAttribute('data-theme', t);
                }}
            }} catch (e) {{}}
        }})();
    </script>
</head>
<body>
    <button class="menu-toggle" onclick="document.querySelector('.sidebar').classList.toggle('open')">&#9776;</button>
    <button class="theme-toggle" id="theme-toggle" title="切换日夜模式" aria-label="切换日夜模式">
        <span class="icon-light">&#9790;</span><span class="icon-dark">&#9728;</span>
    </button>

    <aside class="sidebar">
        <div class="sidebar-header">
            <h2>{site_title}</h2>
            <p>{site_subtitle}</p>
        </div>
        <nav>
            <a href="index.html"{index_active}>Overview</a>
{nav_links}
        </nav>
    </aside>

    <main class="content">
      <div class="content-inner">
{content}
        <footer class="site-stats" aria-label="访问统计">
            <div class="site-stats-counts">
                <span>本站浏览<strong class="site-stats-number" id="busuanzi_value_site_pv" data-stat-value>—</strong>次</span>
                <span title="访客数按统计服务的去重口径计算">本站访客<strong class="site-stats-number" id="busuanzi_value_site_uv" data-stat-value>—</strong></span>
                <span>本页浏览<strong class="site-stats-number" id="busuanzi_value_page_pv" data-stat-value>—</strong>次</span>
            </div>
            <div class="site-stats-meta">
                <span>统计由 <a href="https://github.com/soxft/busuanzi" target="_blank" rel="noopener noreferrer">不蒜子（soxft）</a> 提供</span>
                <span class="site-stats-status" role="status" aria-live="polite">统计加载中</span>
            </div>
        </footer>
      </div>
    </main>
{toc}

    <button class="back-to-top" onclick="window.scrollTo({{top:0,behavior:'smooth'}})">&#8593;</button>

    <script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"></script>
    <script defer src="https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
            onload="renderMathInElement(document.querySelector('.content-inner'), {{
                delimiters: [
                    {{ left: '$$', right: '$$', display: true }},
                    {{ left: '$', right: '$', display: false }}
                ],
                ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code', 'option'],
                ignoredClasses: ['mermaid', 'diagram'],
                throwOnError: false
            }});"></script>
    <script>
        // Mermaid destroys the source text when it renders, so keep a copy in
        // order to re-render on theme change.
        document.querySelectorAll('.mermaid').forEach(el => {{
            el.dataset.src = el.textContent;
        }});

        const prefersDark = window.matchMedia('(prefers-color-scheme: dark)');
        function currentTheme() {{
            const forced = document.documentElement.getAttribute('data-theme');
            if (forced) return forced;
            return prefersDark.matches ? 'dark' : 'light';
        }}

        // Most architecture documents use a shared pastel Mermaid palette.
        // Those fills work on white but glow against a dark page, while their
        // dark label colours lose contrast. Translate only Mermaid style
        // declarations at render time so Markdown stays portable and the
        // original light palette is preserved verbatim.
        const darkMermaidPalette = new Map(Object.entries({{
            '#e8f5e9': '#163224', '#f1f8e9': '#193323', '#c8e6c9': '#1d3b28',
            '#e3f2fd': '#142b3d', '#e8f4fd': '#142b3d', '#e1f5ff': '#142b3d',
            '#fff3e0': '#3b2a18', '#fff4e1': '#3b2a18', '#fff8e1': '#3b2a18',
            '#f3e5f5': '#2e2340', '#ede7f6': '#292540',
            '#fce4ec': '#3b202d', '#ffebee': '#3b2028', '#ffe8e8': '#3b2028',
            '#ffcdd2': '#422329', '#fff9c4': '#3a3218',
            '#e0f7fa': '#123238', '#e0f2f1': '#14332f', '#f5f5f5': '#293240',
            '#4caf50': '#4ade80', '#8bc34a': '#a3e635', '#2196f3': '#60a5fa',
            '#ff9800': '#fb923c', '#e91e63': '#f472b6', '#9c27b0': '#c084fc',
            '#673ab7': '#a78bfa', '#ffc107': '#facc15', '#fbc02d': '#fde047',
            '#00bcd4': '#22d3ee', '#009688': '#2dd4bf', '#e53935': '#fb7185',
            '#f44336': '#f87171', '#e57373': '#fca5a5', '#9e9e9e': '#94a3b8',
            '#0f172a': '#e2e8f0', '#1a1a2e': '#e2e8f0'
        }}));

        function mermaidSourceForTheme(source) {{
            if (currentTheme() !== 'dark') return source;
            return source.replace(
                /(fill|stroke|color)\\s*:\\s*(#[0-9a-f]{{6}})/gi,
                (match, property, hex) => {{
                    const mapped = darkMermaidPalette.get(hex.toLowerCase());
                    return mapped ? `${{property}}:${{mapped}}` : match;
                }}
            );
        }}

        function initMermaid() {{
            const dark = currentTheme() === 'dark';
            mermaid.initialize({{
                startOnLoad: false,
                theme: dark ? 'base' : 'default',
                themeVariables: dark ? {{
                    background: '#0f172a',
                    primaryColor: '#1e293b',
                    primaryTextColor: '#e2e8f0',
                    primaryBorderColor: '#60a5fa',
                    secondaryColor: '#172554',
                    tertiaryColor: '#1f2937',
                    lineColor: '#94a3b8',
                    textColor: '#e2e8f0',
                    mainBkg: '#1e293b',
                    nodeBorder: '#64748b',
                    clusterBkg: '#111c31',
                    clusterBorder: '#475569',
                    edgeLabelBackground: '#0f172a',
                    noteBkgColor: '#1e293b',
                    noteTextColor: '#e2e8f0',
                    noteBorderColor: '#64748b',
                    actorBkg: '#1e293b',
                    actorBorder: '#60a5fa',
                    actorTextColor: '#e2e8f0',
                    actorLineColor: '#64748b',
                    signalColor: '#94a3b8',
                    signalTextColor: '#e2e8f0',
                    labelBoxBkgColor: '#1e293b',
                    labelBoxBorderColor: '#64748b',
                    labelTextColor: '#e2e8f0',
                    loopTextColor: '#e2e8f0',
                    activationBkgColor: '#334155',
                    activationBorderColor: '#94a3b8',
                    sequenceNumberColor: '#0f172a'
                }} : {{}},
                flowchart: {{ useMaxWidth: true, htmlLabels: true }},
                securityLevel: 'loose'
            }});
        }}

        function renderMermaid() {{
            const nodes = document.querySelectorAll('.mermaid');
            nodes.forEach(el => {{
                el.removeAttribute('data-processed');
                el.textContent = mermaidSourceForTheme(el.dataset.src);
            }});
            // mermaid.run rejects on its internal font probe in some browsers;
            // the diagrams still render, so swallow it rather than surfacing an
            // unhandled rejection.
            if (!nodes.length) return;
            Promise.resolve(mermaid.run({{ nodes: nodes }}))
                .catch(() => {{}})
                .then(() => nodes.forEach(applyZoom));
        }}

        /* ---------- Diagram zoom ----------
           Scale is tracked as a factor of the diagram's NATURAL size (its
           viewBox), so 100% means 1:1 and one font size looks identical in
           every diagram on the site. Left to itself mermaid's useMaxWidth
           stretches each svg to the container, which blows a 3-node diagram
           up to 3.4x and shrinks a wide one to 0.34x — a 10x spread in
           apparent font size. FIT_MAX caps the auto-fit at 1:1 (never
           upscale) and FIT_MIN stops wide diagrams from shrinking to
           unreadable; anything past that overflows and scrolls/pans. */
        const MIN_Z = 0.3, MAX_Z = 6, STEP = 1.25;
        const FIT_MIN = 0.55, FIT_MAX = 1;
        const PAD = 40;               // .mermaid horizontal padding (20px each side)
        const zoom = new WeakMap();   // .mermaid -> explicit scale; absent = auto-fit

        function naturalSize(svg) {{
            const vb = svg.viewBox && svg.viewBox.baseVal;
            if (vb && vb.width) return {{ w: vb.width, h: vb.height }};
            const r = svg.getBoundingClientRect();
            return {{ w: r.width, h: r.height }};
        }}

        function fitScale(el, nat) {{
            const avail = el.clientWidth - PAD;
            if (!nat.w || avail <= 0) return 1;
            return Math.min(FIT_MAX, Math.max(FIT_MIN, avail / nat.w));
        }}

        function scaleOf(el, nat) {{
            const k = zoom.get(el);
            return k === undefined ? fitScale(el, nat) : k;
        }}

        function applyZoom(el) {{
            const svg = el.querySelector('svg');
            if (!svg) return;
            const nat = naturalSize(svg);
            if (!nat.w) return;
            const k = scaleOf(el, nat);

            const label = el.closest('.diagram')?.querySelector('.diagram-zoom');
            if (label) label.textContent = Math.round(k * 100) + '%';

            // Size the svg explicitly instead of leaving it to useMaxWidth,
            // so the container gets real scrollbars when the diagram overflows.
            svg.style.maxWidth = 'none';
            svg.style.width = (nat.w * k) + 'px';
            svg.style.height = (nat.h * k) + 'px';

            const overflows = nat.w * k > el.clientWidth - PAD + 1;
            el.classList.toggle('is-zoomed', overflows);
            if (!overflows) el.scrollLeft = el.scrollTop = 0;
        }}

        function setZoom(el, k, anchor) {{
            const svg = el.querySelector('svg');
            if (!svg) return;
            const nat = naturalSize(svg);
            const prev = scaleOf(el, nat);
            if (k !== null) k = Math.min(MAX_Z, Math.max(MIN_Z, k));
            const next = k === null ? fitScale(el, nat) : k;
            if (next === prev) return;
            // Keep the point under the cursor (or the viewport centre) put.
            const ax = anchor ? anchor.x : el.clientWidth / 2;
            const ay = anchor ? anchor.y : el.clientHeight / 2;
            const rx = (el.scrollLeft + ax) / prev;
            const ry = (el.scrollTop + ay) / prev;
            if (k === null) zoom.delete(el); else zoom.set(el, k);
            applyZoom(el);
            el.scrollLeft = rx * next - ax;
            el.scrollTop = ry * next - ay;
        }}

        function currentScale(el) {{
            const svg = el.querySelector('svg');
            return svg ? scaleOf(el, naturalSize(svg)) : 1;
        }}

        function setupDiagrams() {{
            document.querySelectorAll('.mermaid').forEach(el => {{
                const wrap = document.createElement('div');
                wrap.className = 'diagram';
                el.parentNode.insertBefore(wrap, el);
                wrap.appendChild(el);

                const tools = document.createElement('div');
                tools.className = 'diagram-tools';
                tools.innerHTML =
                    '<button type="button" data-act="out" title="缩小">&minus;</button>' +
                    '<span class="diagram-zoom">100%</span>' +
                    '<button type="button" data-act="in" title="放大">+</button>' +
                    '<button type="button" data-act="reset" title="适应宽度">&#9633;</button>' +
                    '<button type="button" data-act="full" title="全屏">&#10530;</button>';
                wrap.appendChild(tools);

                tools.addEventListener('click', e => {{
                    const act = e.target.closest('button')?.dataset.act;
                    if (!act) return;
                    const k = currentScale(el);
                    if (act === 'in') setZoom(el, k * STEP);
                    else if (act === 'out') setZoom(el, k / STEP);
                    else if (act === 'reset') setZoom(el, null);
                    else if (act === 'full') {{
                        if (document.fullscreenElement === wrap) document.exitFullscreen();
                        else wrap.requestFullscreen?.();
                    }}
                }});

                // Ctrl/⌘ + wheel zooms; a plain wheel keeps scrolling the page.
                el.addEventListener('wheel', e => {{
                    if (!e.ctrlKey && !e.metaKey) return;
                    e.preventDefault();
                    const r = el.getBoundingClientRect();
                    setZoom(el, currentScale(el) * (e.deltaY < 0 ? STEP : 1 / STEP),
                            {{ x: e.clientX - r.left, y: e.clientY - r.top }});
                }}, {{ passive: false }});

                // Drag to pan once zoomed in.
                let drag = null;
                el.addEventListener('pointerdown', e => {{
                    // Pan only matters once the diagram actually overflows.
                    if (e.button !== 0 || !el.classList.contains('is-zoomed')) return;
                    drag = {{ x: e.clientX, y: e.clientY, l: el.scrollLeft, t: el.scrollTop }};
                    el.setPointerCapture(e.pointerId);
                    el.classList.add('is-panning');
                }});
                el.addEventListener('pointermove', e => {{
                    if (!drag) return;
                    el.scrollLeft = drag.l - (e.clientX - drag.x);
                    el.scrollTop = drag.t - (e.clientY - drag.y);
                }});
                const endDrag = () => {{ drag = null; el.classList.remove('is-panning'); }};
                el.addEventListener('pointerup', endDrag);
                el.addEventListener('pointercancel', endDrag);

                // Double click toggles between auto-fit and true 1:1.
                el.addEventListener('dblclick', () => setZoom(el, zoom.has(el) ? null : 1));
            }});
        }}

        setupDiagrams();
        initMermaid();
        renderMermaid();

        const remeasure = () => document.querySelectorAll('.mermaid').forEach(applyZoom);
        document.addEventListener('fullscreenchange', remeasure);
        window.addEventListener('resize', remeasure);

        // Theme toggle
        const toggle = document.getElementById('theme-toggle');
        toggle.addEventListener('click', () => {{
            const next = currentTheme() === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            try {{ localStorage.setItem('theme', next); }} catch (e) {{}}
            initMermaid();
            renderMermaid();
        }});

        // Follow the OS while the user hasn't made an explicit choice
        prefersDark.addEventListener('change', () => {{
            if (!document.documentElement.getAttribute('data-theme')) {{
                initMermaid();
                renderMermaid();
            }}
        }});

        // Back to top button
        const btn = document.querySelector('.back-to-top');
        window.addEventListener('scroll', () => {{
            btn.classList.toggle('visible', window.scrollY > 300);
        }});

        // Close sidebar on mobile when clicking a link
        document.querySelectorAll('.sidebar nav a').forEach(a => {{
            a.addEventListener('click', () => {{
                document.querySelector('.sidebar').classList.remove('open');
            }});
        }});

        // Overview domain filter: hexagons reveal every document tagged with
        // the selected cross-cutting knowledge domain.
        const domainButtons = Array.from(document.querySelectorAll('.domain-hex'));
        if (domainButtons.length) {{
            const cards = Array.from(document.querySelectorAll('.cat .card'));
            const categories = Array.from(document.querySelectorAll('.cat'));
            const filterStatus = document.getElementById('domain-filter-status');

            const applyDomainFilter = (topic, label) => {{
                let visibleCount = 0;
                cards.forEach(card => {{
                    const topics = (card.dataset.topics || '').split(/\\s+/).filter(Boolean);
                    const visible = !topic || topics.includes(topic);
                    card.hidden = !visible;
                    if (visible) visibleCount += 1;
                }});
                categories.forEach(category => {{
                    const categoryVisibleCount = category.querySelectorAll('.card:not([hidden])').length;
                    category.hidden = categoryVisibleCount === 0;
                    const countBadge = category.querySelector('.cat-count');
                    if (countBadge) countBadge.textContent = categoryVisibleCount;
                }});
                domainButtons.forEach(button => {{
                    const active = button.dataset.topic === topic;
                    button.classList.toggle('is-active', active);
                    button.setAttribute('aria-pressed', active ? 'true' : 'false');
                }});
                if (filterStatus) {{
                    filterStatus.textContent = topic
                        ? `当前显示“${{label}}”领域的 ${{visibleCount}} 篇文档；点击“全部文档”重置。`
                        : `当前显示全部 ${{visibleCount}} 篇文档；一篇文档可以覆盖多个领域。`;
                }}
            }};

            domainButtons.forEach(button => {{
                button.addEventListener('click', () => {{
                    const label = button.querySelector('.domain-label')?.textContent || '';
                    applyDomainFilter(button.dataset.topic || '', label);
                }});
            }});
        }}

        // Highlight the TOC entry for the heading currently in view
        const tocLinks = Array.from(document.querySelectorAll('.toc a'));
        if (tocLinks.length) {{
            const targets = tocLinks
                .map(a => document.getElementById(decodeURIComponent(a.hash.slice(1))))
                .filter(Boolean);
            const setActive = () => {{
                let current = targets[0];
                for (const t of targets) {{
                    if (t.getBoundingClientRect().top <= 120) current = t;
                    else break;
                }}
                tocLinks.forEach(a => a.classList.toggle(
                    'active',
                    current && decodeURIComponent(a.hash.slice(1)) === current.id
                ));
            }};
            setActive();
            let queued = false;
            window.addEventListener('scroll', () => {{
                if (queued) return;
                queued = true;
                requestAnimationFrame(() => {{ setActive(); queued = false; }});
            }});
        }}
    </script>
    <script>
        // Only the production hostname contributes to the shared counters.
        // Local files, localhost and Pages preview deployments never load it.
        (function () {{
            const stats = document.querySelector('.site-stats');
            const status = stats.querySelector('.site-stats-status');
            if (location.protocol !== 'https:' || location.hostname !== 'vla.yilong-zhu.com') {{
                stats.dataset.state = 'preview';
                status.textContent = '本地或预览环境不计数';
                return;
            }}

            const values = Array.from(stats.querySelectorAll('[data-stat-value]'));
            stats.dataset.state = 'loading';
            const unavailable = () => {{
                if (stats.dataset.state === 'ready') return;
                stats.dataset.state = 'unavailable';
                status.textContent = '统计暂不可用';
            }};
            const timeout = setTimeout(unavailable, 8000);
            const observer = new MutationObserver(() => {{
                if (!values.every(el => /^[0-9]+$/.test(el.textContent.trim()))) return;
                observer.disconnect();
                clearTimeout(timeout);
                values.forEach(el => {{
                    el.textContent = Number(el.textContent.trim()).toLocaleString('zh-CN');
                }});
                stats.dataset.state = 'ready';
                status.hidden = true;
            }});
            observer.observe(stats, {{ childList: true, characterData: true, subtree: true }});

            const script = document.createElement('script');
            script.async = true;
            script.src = 'https://busuanzi.9420.ltd/js';
            script.setAttribute('data-prefix', 'busuanzi_value');
            script.onerror = unavailable;
            document.head.appendChild(script);
        }})();
    </script>
</body>
</html>
"""


def cjk_slugify(value: str, separator: str = "-") -> str:
    """Slugify that keeps CJK characters.

    The default markdown slugifier strips non-ASCII, which turns headings like
    "2.2 三个编码器" into the useless id "22" and collides across sections.
    """
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"[^\w\s-]", "", value, flags=re.UNICODE).strip().lower()
    value = re.sub(r"[\s{}]+".format(re.escape(separator)), separator, value)
    return value or "section"


def md_to_html(md_text: str):
    """Convert markdown to HTML, preserving mermaid blocks.

    Returns (html, toc_tokens).
    """
    # Extract mermaid blocks before markdown processing
    mermaid_blocks = []

    def replace_mermaid(m):
        idx = len(mermaid_blocks)
        mermaid_blocks.append(m.group(1))
        return f"MERMAID_PLACEHOLDER_{idx}"

    md_text = re.sub(
        r"```mermaid\s*\n(.*?)```",
        replace_mermaid,
        md_text,
        flags=re.DOTALL,
    )

    # Stash LaTeX spans before markdown touches them. Python-Markdown treats a
    # run of backslashes as escapes, so `\\[2pt]` (a KaTeX line break) arrives
    # as `\[2pt]` and blows up the renderer; `_` in subscripts is likewise at
    # risk of becoming <em>. Code fences and inline code are matched by the
    # same pattern purely so that a `$` inside them is never mistaken for a
    # math delimiter -- they are handed back unchanged.
    math_blocks = []

    def stash_math(m):
        if m.group("fence") or m.group("code"):
            return m.group(0)
        math_blocks.append(m.group(0))
        return f"MATHSPAN{len(math_blocks) - 1}ENDMATH"

    md_text = re.sub(
        r"(?P<fence>```.*?```)"
        r"|(?P<code>`[^`\n]*`)"
        r"|(?P<display>\$\$.*?\$\$)"
        r"|(?P<inline>\$(?!\$)[^$\n]+?\$)",
        stash_math,
        md_text,
        flags=re.DOTALL,
    )

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "codehilite", "toc"],
        extension_configs={
            "codehilite": {"guess_lang": False, "css_class": "highlight"},
            "toc": {"slugify": cjk_slugify, "permalink": "#", "toc_depth": "2-3"},
        },
    )
    html = md.convert(md_text)
    toc_tokens = getattr(md, "toc_tokens", [])

    # Restore mermaid blocks. The source has to be HTML-escaped: the JS hands
    # mermaid `el.textContent`, so any unescaped markup in a label is parsed
    # away by the HTML parser before mermaid ever sees it -- `<br/>` becomes a
    # real <br> element and contributes nothing to textContent, which silently
    # runs adjacent label lines together ("...vit-huge-14" + "1280 → 5120" ->
    # "...vit-huge-141280 → 5120"). Escaped, textContent round-trips to the
    # exact source and mermaid does its own <br/> handling.
    # Restore from the highest index down. Otherwise placeholder 1 is a prefix
    # of placeholders 10, 11, ... and a page with more than nine diagrams
    # silently replaces the later sources with diagram 1 plus a trailing digit.
    for i in range(len(mermaid_blocks) - 1, -1, -1):
        block = mermaid_blocks[i]
        safe = html_lib.escape(block, quote=False)
        html = html.replace(
            f"<p>MERMAID_PLACEHOLDER_{i}</p>",
            f'<div class="mermaid">\n{safe}</div>',
        )
        # Also handle case where it's not wrapped in <p>
        html = html.replace(
            f"MERMAID_PLACEHOLDER_{i}",
            f'<div class="mermaid">\n{safe}</div>',
        )

    # Put the LaTeX back, escaped so it is valid HTML. KaTeX reads textContent,
    # so the entities decode back to the original characters before parsing.
    for i, block in enumerate(math_blocks):
        html = html.replace(f"MATHSPAN{i}ENDMATH", html_lib.escape(block, quote=False))

    # Wrap tables so wide ones scroll inside their own box instead of
    # stretching the whole page.
    html = re.sub(r"<table>", '<div class="table-wrap"><table>', html)
    html = re.sub(r"</table>", "</table></div>", html)

    return html, toc_tokens


def build_toc(toc_tokens) -> str:
    """Render the right-hand in-page table of contents."""
    items = []
    for top in toc_tokens:
        top_id = html_lib.escape(top["id"], quote=True)
        items.append(
            f'                <li><a href="#{top_id}" class="toc-h2">'
            f'{html_lib.escape(top["name"])}</a></li>'
        )
        for sub in top.get("children", []):
            sub_id = html_lib.escape(sub["id"], quote=True)
            items.append(
                f'                <li><a href="#{sub_id}" class="toc-h3">'
                f'{html_lib.escape(sub["name"])}</a></li>'
            )
    if len(items) < 3:
        return ""  # not worth a TOC for very short pages
    return (
        '        <aside class="toc">\n'
        '            <div class="toc-title">本页目录</div>\n'
        "            <ul>\n" + "\n".join(items) + "\n            </ul>\n"
        "        </aside>"
    )


def build_nav(active_file: str, sections=None) -> str:
    """Build navigation links, grouped by category."""
    lines = []
    current_section = None
    for page, section, depth in iter_pages(sections):
        if section is not current_section:
            current_section = section
            section_title = html_lib.escape(section["title"])
            lines.append(f'            <div class="nav-group">{section_title}</div>')
        md_file = page["file"]
        html_file = html_filename(md_file)
        classes = ["nav-child"] if depth else []
        if md_file == active_file:
            classes.append("active")
        attr = f' class="{" ".join(classes)}"' if classes else ""
        label = html_lib.escape(page["label"])
        lines.append(f'            <a href="{html_file}"{attr}>{label}</a>')
    return "\n".join(lines)


def extract_summary(md_text: str, limit: int = SUMMARY_LIMIT) -> str:
    """Extract a plain-text summary from the first prose paragraph."""
    for paragraph in re.split(r"\n\n+", md_text):
        paragraph = paragraph.strip()
        if (
            not paragraph
            or paragraph.startswith("#")
            or paragraph.startswith("```")
            or paragraph.startswith(">")
        ):
            continue

        # Keep the historical U+E000 sentinel: it protects escaped asterisks
        # while Markdown emphasis markers are removed.
        summary = paragraph.replace("\\*", ESCAPED_ASTERISK_SENTINEL)
        summary = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", summary)
        summary = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", summary)
        summary = re.sub(r"<[^>]+>", "", summary)
        summary = summary.replace("**", "").replace("*", "").replace("`", "")
        summary = summary.replace(ESCAPED_ASTERISK_SENTINEL, "*")
        summary = re.sub(r"\s+", " ", summary).strip()
        if len(summary) > limit:
            summary = summary[:limit].rstrip() + "..."
        return summary
    return ""


def build_knowledge_graph() -> str:
    """Render the overview's clickable, responsive learning-deployment path."""
    stages = []
    for stage in KNOWLEDGE_PATH_STAGES:
        nodes = []
        for label, detail, href in stage["nodes"]:
            nodes.append(
                f'                    <a class="knowledge-node" href="{html_lib.escape(href, quote=True)}">\n'
                f'                        <span class="knowledge-node-title">{html_lib.escape(label)}</span>\n'
                f'                        <span class="knowledge-node-detail">{html_lib.escape(detail)}</span>\n'
                "                    </a>"
            )
        flow = html_lib.escape(stage["flow"])
        stages.append(
            f'            <section class="knowledge-stage knowledge-stage-{stage["kind"]}" '
            f'aria-label="第 {stage["step"]} 阶段：{html_lib.escape(stage["title"], quote=True)}">\n'
            '                <header class="knowledge-stage-header">\n'
            f'                    <span class="knowledge-step">{stage["step"]}</span>\n'
            f'                    <h3>{html_lib.escape(stage["title"])}</h3>\n'
            "                </header>\n"
            '                <div class="knowledge-nodes">\n'
            + "\n".join(nodes)
            + "\n                </div>\n"
            "            </section>"
        )
        if flow:
            stages.append(
                '            <div class="knowledge-flow" aria-hidden="true">\n'
                f'                <span>{flow}</span><b>→</b>\n'
                "            </div>"
            )
    return (
        '        <div class="knowledge-path" aria-label="机器人知识从学习到部署的关系图">\n'
        + "\n".join(stages)
        + "\n        </div>\n"
        '        <div class="knowledge-feedback" aria-label="持续学习反馈闭环">\n'
        '            <span class="feedback-mark" aria-hidden="true">↺</span>\n'
        '            <strong>持续学习闭环</strong>\n'
        '            <span>失败 episode</span><span class="feedback-arrow" aria-hidden="true">→</span>\n'
        '            <span>语义标注与训练切片</span><span class="feedback-arrow" aria-hidden="true">→</span>\n'
        '            <span>回流模仿学习 / RL</span>\n'
        "        </div>"
    )


def build_domain_landscape(sections=None) -> str:
    """Render topic coverage as a filterable honeycomb of document counts."""
    if sections is None:
        sections = SECTIONS
    pages = [page for page, _section, _depth in iter_pages(sections)]
    total = len(pages)
    counts = {
        domain["id"]: sum(
            domain["id"] in PAGE_TOPICS.get(page["file"], set()) for page in pages
        )
        for domain in KNOWLEDGE_DOMAINS
    }
    max_count = max(counts.values(), default=1)
    positions = [
        (2, 1),
        (3, 1),
        (4, 1),
        (1, 2),
        (5, 2),
        (2, 3),
        (3, 3),
        (4, 3),
    ]
    cells = [
        '            <button class="domain-hex domain-hex-all is-active" '
        'type="button" data-topic="" aria-pressed="true" '
        'style="--hex-col:3;--hex-row:2;--hex-heat:100%" '
        f'aria-label="显示全部 {total} 篇文档">\n'
        f'                <span class="domain-count">{total}</span>\n'
        '                <span class="domain-label">全部文档</span>\n'
        '                <span class="domain-unit">点击重置</span>\n'
        "            </button>"
    ]
    for domain, (col, row) in zip(KNOWLEDGE_DOMAINS, positions):
        count = counts[domain["id"]]
        heat = 14 + round(30 * count / max_count)
        topic = html_lib.escape(domain["id"], quote=True)
        label = html_lib.escape(domain["label"])
        desc = html_lib.escape(domain["desc"])
        cells.append(
            '            <button class="domain-hex" type="button" '
            f'data-topic="{topic}" aria-pressed="false" '
            f'style="--hex-col:{col};--hex-row:{row};--hex-heat:{heat}%" '
            f'aria-label="{label}，覆盖 {count} 篇文档。{desc}">\n'
            f'                <span class="domain-count">{count}</span>\n'
            f'                <span class="domain-label">{label}</span>\n'
            '                <span class="domain-unit">篇文档</span>\n'
            "            </button>"
        )
    return (
        '        <div class="domain-honeycomb" '
        'aria-label="知识领域覆盖分布">\n'
        + "\n".join(cells)
        + "\n        </div>\n"
        '        <p class="domain-filter-status" id="domain-filter-status" '
        'aria-live="polite">当前显示全部文档；一篇文档可以覆盖多个领域。</p>'
    )


def build_publication_meta(filename: str) -> str:
    """Render a source-backed method date, not a document freshness claim."""
    publication = PAGE_DATES.get(filename)
    if not publication:
        return '<div class="card-meta"><span class="card-date-pending">年月待核实</span></div>'
    month = html_lib.escape(publication["month"], quote=True)
    kind = html_lib.escape(publication["kind"])
    source = html_lib.escape(publication["source"], quote=True)
    note = html_lib.escape(publication.get("note", ""))
    note_html = f'<p class="card-date-note">{note}</p>' if note else ""
    return (
        '<div class="card-meta">'
        f'<span class="card-date"><time datetime="{month}">{month.replace("-", ".")}</time>'
        f'<span class="card-date-kind">{kind}</span></span>'
        f'<a class="card-date-source" href="{source}" target="_blank" '
        f'rel="noopener noreferrer" aria-label="查看{kind}年月来源">来源 ↗</a>'
        f'</div>{note_html}'
    )


def build_cards(pages, md_dir: Path = MD_DIR) -> str:
    """Render index cards for a flat list of page dicts."""
    cards = []
    for page in pages:
        md_file, label = page["file"], page["label"]
        html_file = html_filename(md_file)
        content = (md_dir / md_file).read_text(encoding="utf-8")
        desc = html_lib.escape(extract_summary(content))
        safe_label = html_lib.escape(label)
        topics = " ".join(sorted(PAGE_TOPICS.get(md_file, set())))
        topic_attr = html_lib.escape(topics, quote=True)
        klass = "card card-lead" if page.get("children") else "card"
        badge = ""
        if page.get("children"):
            badge = '                <span class="card-badge">总览 · 从这里开始</span>\n'
        elif page.get("_child"):
            badge = '                <span class="card-badge card-badge-sub">细分</span>\n'
        cards.append(
            f'            <div class="{klass}" data-topics="{topic_attr}">\n'
            f"{badge}"
            f'                <h3><a href="{html_file}">{safe_label}</a></h3>\n'
            f"                {build_publication_meta(md_file)}\n"
            f"                <p>{desc}</p>\n"
            f"            </div>"
        )

    return "\n".join(cards)


def build_index_page(sections=None, md_dir: Path = MD_DIR) -> str:
    """Build index/overview page content, one card grid per category."""
    if sections is None:
        sections = SECTIONS
    total = sum(1 for _ in iter_pages(sections))
    blocks = [
        f"        <h1>{html_lib.escape(SITE_TITLE)}</h1>",
        f"        <p>{html_lib.escape(SITE_SUBTITLE)} —— 按主题分类，共 {total} 篇文档。</p>",
        (
            '        <section class="knowledge-overview">\n'
            '            <h2 class="overview-section-title">知识导图</h2>\n'
            '            <p class="overview-section-desc">'
            '从感知与学习目标出发，经过 VLA / WAM 产生动作，'
            '再连接全身控制与生产数据闭环。点击主要节点可进入代表文档。'
            "</p>\n"
            '            <div class="knowledge-map">\n'
            + build_knowledge_graph()
            + "\n            </div>\n"
            "        </section>"
        ),
        (
            '        <section class="domain-landscape">\n'
            '            <h2 class="overview-section-title">知识领域覆盖</h2>\n'
            '            <p class="overview-section-desc">'
            '六边形中的数字是涉及该领域的文档数，颜色深浅表示相对覆盖量。'
            '标签可重叠；点击六边形可筛选下方文档。'
            "</p>\n"
            + build_domain_landscape(sections)
            + "\n        </section>"
        ),
        (
            '        <p class="publication-guide">'
            '<strong>方法年月</strong> · 卡片标注所述方法 / 版本的首次公开年月，'
            '并区分论文、模型、代码、项目和文章；不是本文修改时间。'
            '点击「来源」可核对。日期较新不等于效果更好。</p>'
        ),
    ]
    for section in sections:
        flat = []
        for page in section["pages"]:
            flat.append(page)
            for child in page.get("children", []):
                flat.append(dict(child, _child=True))
        blocks.append(
            '        <section class="cat">\n'
            f'            <h2 class="cat-title">{html_lib.escape(section["title"])}'
            f'<span class="cat-count">{len(flat)}</span></h2>\n'
            f'            <p class="cat-desc">{html_lib.escape(section["desc"])}</p>\n'
            '            <div class="card-grid">\n'
            + build_cards(flat, md_dir)
            + "\n            </div>\n"
            "        </section>"
        )
    return "\n".join(blocks)


def build_highlight_css() -> str:
    """Pygments colour rules, light theme + dark theme.

    The codehilite extension emits <span class="k">/<span class="n"> markup, but
    without these rules every code block renders as flat monochrome text.

    Dark rules are emitted twice: once under the OS media query (scoped so an
    explicit light choice wins) and once under [data-theme="dark"] for the
    manual toggle.
    """
    light = HtmlFormatter(style="default").get_style_defs(".highlight")
    dark_media = HtmlFormatter(style="github-dark").get_style_defs(
        ':root:not([data-theme="light"]) .highlight'
    )
    dark_manual = HtmlFormatter(style="github-dark").get_style_defs(
        ':root[data-theme="dark"] .highlight'
    )
    indented = "\n".join("    " + line for line in dark_media.splitlines())
    return (
        "\n/* Syntax highlighting (Pygments) */\n"
        f"{light}\n"
        ".highlight pre, .highlight { background: none; }\n\n"
        "@media (prefers-color-scheme: dark) {\n"
        f"{indented}\n"
        "}\n\n"
        f"{dark_manual}\n"
    )


CARD_CSS = """
/* Overview knowledge map */
.knowledge-overview,
.domain-landscape {
    margin-top: 36px;
}

.overview-section-title {
    margin: 0 0 6px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.overview-section-desc {
    color: var(--text-muted);
    font-size: 14px;
    margin: 0 0 16px;
}

.knowledge-map {
    margin-top: 20px;
}

.knowledge-path {
    display: flex;
    align-items: stretch;
    gap: 0;
}

.knowledge-stage {
    --stage-accent: var(--accent);
    position: relative;
    display: flex;
    flex-direction: column;
    flex: 1 1 0;
    min-width: 0;
    padding: 18px 14px 16px;
    overflow: hidden;
    border: 1px solid color-mix(in srgb, var(--stage-accent) 30%, var(--border));
    border-radius: 16px;
    background:
        linear-gradient(145deg,
            color-mix(in srgb, var(--stage-accent) 12%, var(--bg-code)),
            var(--bg-code) 58%);
    box-shadow: 0 12px 28px color-mix(in srgb, var(--stage-accent) 8%, transparent);
}

.knowledge-stage:first-child {
    flex-grow: 1.28;
}

.knowledge-stage::before {
    content: "";
    position: absolute;
    inset: 0 0 auto;
    height: 4px;
    background: var(--stage-accent);
}

.knowledge-stage-sense { --stage-accent: var(--map-sense); }
.knowledge-stage-model { --stage-accent: var(--map-model); }
.knowledge-stage-action { --stage-accent: var(--map-action); }
.knowledge-stage-robot { --stage-accent: var(--map-robot); }
.knowledge-stage-production { --stage-accent: var(--map-production); }

.knowledge-stage-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 14px;
}

.knowledge-stage-header h3 {
    margin: 0;
    color: var(--heading);
    font-size: 14px;
    font-weight: 700;
    line-height: 1.25;
}

.knowledge-step {
    color: var(--stage-accent);
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.08em;
}

.knowledge-nodes {
    display: grid;
    flex: 1;
    align-content: center;
    gap: 8px;
}

.knowledge-node {
    display: block;
    min-width: 0;
    padding: 10px 10px 9px;
    border: 1px solid color-mix(in srgb, var(--stage-accent) 16%, var(--border));
    border-radius: 10px;
    background: color-mix(in srgb, var(--bg) 86%, var(--stage-accent));
    color: var(--text);
    text-decoration: none;
    transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
}

.knowledge-node:hover {
    transform: translateY(-2px);
    border-color: var(--stage-accent);
    box-shadow: 0 7px 16px color-mix(in srgb, var(--stage-accent) 13%, transparent);
    text-decoration: none;
}

.knowledge-node:focus-visible {
    outline: 2px solid var(--stage-accent);
    outline-offset: 2px;
}

.knowledge-node-title,
.knowledge-node-detail {
    display: block;
}

.knowledge-node-title {
    color: var(--heading);
    font-size: 12px;
    font-weight: 700;
    line-height: 1.25;
}

.knowledge-node-detail {
    margin-top: 3px;
    color: var(--text-muted);
    font-size: 10px;
    line-height: 1.35;
}

.knowledge-flow {
    flex: 0 0 42px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: var(--text-muted);
    text-align: center;
}

.knowledge-flow span {
    max-width: 42px;
    font-size: 9px;
    line-height: 1.2;
}

.knowledge-flow b {
    color: var(--accent);
    font-size: 22px;
    font-weight: 500;
    line-height: 1;
}

.knowledge-feedback {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
    margin: 14px 24px 0;
    padding: 10px 16px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--map-production) 10%, var(--bg-code));
    color: var(--text-muted);
    font-size: 12px;
}

.knowledge-feedback strong {
    color: var(--heading);
}

.feedback-mark {
    color: var(--map-production);
    font-size: 20px;
    line-height: 1;
}

.feedback-arrow {
    color: var(--map-production);
}

/* Filterable honeycomb: counts are tagged-document coverage, not percentages. */
.domain-honeycomb {
    display: grid;
    grid-template-columns: repeat(5, minmax(112px, 172px));
    grid-template-rows: repeat(3, minmax(124px, 150px));
    justify-content: center;
    align-items: center;
    gap: 2px 8px;
    margin: 12px auto 4px;
}

.domain-hex {
    grid-column: var(--hex-col);
    grid-row: var(--hex-row);
    place-self: center;
    width: min(100%, 164px);
    aspect-ratio: 1.1547;
    border: 0;
    padding: 22px 20px;
    clip-path: polygon(25% 0, 75% 0, 100% 50%, 75% 100%, 25% 100%, 0 50%);
    background: color-mix(in srgb, var(--accent) var(--hex-heat), var(--bg));
    color: var(--text);
    cursor: pointer;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    font: inherit;
    transition: transform 0.16s ease, filter 0.16s ease, background 0.16s ease;
}

.domain-hex:hover {
    transform: translateY(-3px);
    filter: drop-shadow(0 5px 7px color-mix(in srgb, var(--accent) 28%, transparent));
}

.domain-hex:focus-visible {
    filter: drop-shadow(0 0 0.35rem var(--accent));
}

.domain-hex.is-active {
    background: var(--accent);
    color: var(--bg);
    filter: drop-shadow(0 5px 8px color-mix(in srgb, var(--accent) 36%, transparent));
}

.domain-count {
    font-size: clamp(24px, 2.2vw, 34px);
    font-weight: 800;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}

.domain-label {
    margin-top: 6px;
    font-size: 13px;
    font-weight: 700;
    line-height: 1.25;
}

.domain-unit {
    margin-top: 3px;
    color: currentColor;
    opacity: 0.72;
    font-size: 11px;
    line-height: 1.2;
}

.domain-filter-status {
    min-height: 1.7em;
    margin: 8px 0 0;
    text-align: center;
    color: var(--text-muted);
    font-size: 13px;
}

[hidden] {
    display: none !important;
}

@media (max-width: 700px) {
    .knowledge-path {
        flex-direction: column;
        gap: 0;
    }

    .knowledge-stage,
    .knowledge-stage:first-child {
        flex: none;
        width: 100%;
    }

    .knowledge-flow {
        flex: 0 0 46px;
        flex-direction: row;
        gap: 8px;
    }

    .knowledge-flow span {
        max-width: none;
        font-size: 10px;
    }

    .knowledge-flow b {
        transform: rotate(90deg);
    }

    .knowledge-feedback {
        flex-wrap: wrap;
        gap: 6px 8px;
        margin-inline: 0;
        border-radius: 14px;
        text-align: center;
    }

    .domain-honeycomb {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        grid-template-rows: none;
        gap: 8px;
        max-width: 360px;
    }

    .domain-hex {
        grid-column: auto !important;
        grid-row: auto !important;
        width: 100%;
        max-width: 164px;
    }

    .domain-hex-all {
        grid-column: 1 / -1 !important;
    }
}

/* Index cards */
.card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 16px;
    margin-top: 24px;
}

.card {
    background: var(--bg-code);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px 24px;
    transition: border-color 0.2s, box-shadow 0.2s;
}

.card:hover {
    border-color: var(--accent);
    box-shadow: 0 2px 12px rgba(37, 99, 235, 0.08);
}

.card h3 {
    margin: 0 0 8px;
    font-size: 17px;
}

.card h3 a {
    color: var(--accent);
    text-decoration: none;
}

.card p {
    font-size: 13px;
    color: var(--text-muted);
    line-height: 1.6;
    margin: 0;
}

.publication-guide {
    margin-top: 32px;
    padding: 12px 16px;
    border-left: 3px solid var(--accent);
    border-radius: 4px;
    background: var(--bg-code);
    color: var(--text-muted);
    font-size: 13px;
    line-height: 1.7;
}

.card-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px 12px;
    margin: 0 0 12px;
    font-size: 12px;
}

.card-date {
    display: inline-flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 8px;
    padding: 4px 9px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
}

.card-date time {
    color: var(--heading);
    font-size: 14px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.035em;
}

.card-date-kind, .card-date-pending {
    color: var(--text-muted);
}

.card-date-source {
    color: var(--link);
    white-space: nowrap;
}

.card .card-date-note {
    margin: -4px 0 10px;
    font-size: 12px;
}

/* Category sections on the index page */
.cat {
    margin-top: 44px;
}

.cat:first-of-type {
    margin-top: 28px;
}

.cat-title {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 4px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.cat-count {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-muted);
    background: var(--bg-code);
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 1px 9px;
}

.cat-desc {
    font-size: 13px;
    color: var(--text-muted);
    margin: 0;
}

.cat .card-grid {
    margin-top: 16px;
}

/* Overview card that owns sub-documents */
.card-lead {
    border-color: var(--accent);
    background: var(--accent-light);
}

.card-badge {
    display: inline-block;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.02em;
    color: var(--accent);
    background: var(--bg);
    border: 1px solid var(--accent);
    border-radius: 4px;
    padding: 1px 7px;
    margin-bottom: 8px;
}

.card-badge-sub {
    color: var(--text-muted);
    border-color: var(--border);
    background: var(--bg);
}

/* Sidebar category headings */
.sidebar nav .nav-group {
    padding: 16px 20px 6px;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-muted);
}

.sidebar nav a.nav-child {
    padding-left: 36px;
    font-size: 13px;
    color: var(--text-muted);
}

.sidebar nav a.nav-child::before {
    content: "└ ";
    opacity: 0.5;
}

.sidebar nav a.nav-child.active {
    color: var(--accent);
}
"""


def render_site(output_dir: Path, sections=None, md_dir: Path = MD_DIR) -> int:
    """Render a complete site into an empty output directory."""
    if sections is None:
        sections = SECTIONS
    output_dir.mkdir(parents=True, exist_ok=True)
    css = CSS + CARD_CSS + build_highlight_css()
    stylesheet = f"style-{hashlib.sha256(css.encode('utf-8')).hexdigest()[:12]}.css"
    (output_dir / stylesheet).write_text(css, encoding="utf-8")

    # Build index page
    index_html = TEMPLATE.format(
        stylesheet=stylesheet,
        title="Overview",
        site_title=html_lib.escape(SITE_TITLE),
        site_subtitle=html_lib.escape(SITE_SUBTITLE),
        content=build_index_page(sections, md_dir),
        nav_links=build_nav("", sections),
        toc="",
        index_active=' class="active"',
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")
    print("  index.html")

    # Build each page
    count = 0
    for page, section, _depth in iter_pages(sections):
        md_file, label = page["file"], page["label"]
        md_path = md_dir / md_file
        md_content = md_path.read_text(encoding="utf-8")

        html_content, toc_tokens = md_to_html(md_content)
        html_file = html_filename(md_file)

        page_html = TEMPLATE.format(
            stylesheet=stylesheet,
            title=html_lib.escape(label),
            site_title=html_lib.escape(SITE_TITLE),
            site_subtitle=html_lib.escape(SITE_SUBTITLE),
            content=f"        {html_content}",
            nav_links=build_nav(md_file, sections),
            toc=build_toc(toc_tokens),
            index_active="",
        )

        (output_dir / html_file).write_text(page_html, encoding="utf-8")
        print(f"  [{section['title']}] {html_file}")
        count += 1

    # Keep already-shared links alive: map every pre-numbering URL to its new one.
    rules = []
    for page, _section, _depth in iter_pages(sections):
        new_stem = html_filename(page["file"])[:-len(".html")]
        old_stem = re.sub(r"^\d+\.", "", new_stem)
        if old_stem == new_stem:
            continue
        rules.append(f"/{old_stem} /{new_stem} 301")
        rules.append(f"/{old_stem}.html /{new_stem} 301")
    # Preserve the OpenWAM URL used in the initial local review.
    if any(html_filename(page["file"]) == "24.OpenWAM_Architecture.html"
           for page, _, _ in iter_pages(sections)):
        rules.append("/21.OpenWAM_Architecture /24.OpenWAM_Architecture 301")
        rules.append("/21.OpenWAM_Architecture.html /24.OpenWAM_Architecture 301")
    (output_dir / "_redirects").write_text("\n".join(rules) + "\n", encoding="utf-8")
    print(f"  _redirects ({len(rules)} rules)")

    return count


def replace_site(staging_dir: Path, site_dir: Path) -> None:
    """Replace a generated site while preserving the old one on failure."""
    backup_dir = staging_dir.with_name(staging_dir.name + "-previous")
    if site_dir.exists():
        site_dir.replace(backup_dir)
    try:
        staging_dir.replace(site_dir)
    except BaseException:
        if backup_dir.exists():
            backup_dir.replace(site_dir)
        raise
    else:
        if backup_dir.exists():
            shutil.rmtree(backup_dir)


def main() -> None:
    """Validate, render to a staging directory, then replace the old build."""
    validate_sections()
    staging_dir = Path(tempfile.mkdtemp(prefix=".site-build-", dir=MD_DIR))
    try:
        count = render_site(staging_dir)
        replace_site(staging_dir, SITE_DIR)
    finally:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)

    print(f"\nDone! {count} pages + index built in {SITE_DIR}/")


if __name__ == "__main__":
    main()
