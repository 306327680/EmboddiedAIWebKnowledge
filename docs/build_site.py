#!/usr/bin/env python3
"""Build static HTML site from Model Architecture markdown files."""

import html as html_lib
import os
import re
import unicodedata
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter

SITE_DIR = Path(__file__).parent / "site"
MD_DIR = Path(__file__).parent

SITE_TITLE = "Robotics Knowledge Base"
SITE_SUBTITLE = "机器人模型架构知识库"

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
            {"file": "13.DreamZero_Architecture.md", "label": "DreamZero"},
            {"file": "14.FastWAM_Architecture.md", "label": "Fast-WAM"},
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
]


def iter_pages():
    """Yield (page, section, depth) for every page, parents before children."""
    for section in SECTIONS:
        for page in section["pages"]:
            yield page, section, 0
            for child in page.get("children", []):
                yield child, section, 1

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
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans SC", sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.7;
    display: flex;
    min-height: 100vh;
}

/* Sidebar */
.sidebar {
    width: var(--sidebar-w);
    min-height: 100vh;
    background: var(--bg-sidebar);
    border-right: 1px solid var(--border);
    padding: 24px 0;
    position: fixed;
    top: 0;
    left: 0;
    overflow-y: auto;
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
.content .content-inner > .card-grid {
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
    overflow: auto;
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
    <link rel="stylesheet" href="style.css">
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

        function initMermaid() {{
            mermaid.initialize({{
                startOnLoad: false,
                theme: currentTheme() === 'dark' ? 'dark' : 'default',
                flowchart: {{ useMaxWidth: true, htmlLabels: true }},
                securityLevel: 'loose'
            }});
        }}

        function renderMermaid() {{
            const nodes = document.querySelectorAll('.mermaid');
            nodes.forEach(el => {{
                el.removeAttribute('data-processed');
                el.textContent = el.dataset.src;
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
    for i, block in enumerate(mermaid_blocks):
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
        items.append(
            f'                <li><a href="#{top["id"]}" class="toc-h2">'
            f'{html_lib.escape(top["name"])}</a></li>'
        )
        for sub in top.get("children", []):
            items.append(
                f'                <li><a href="#{sub["id"]}" class="toc-h3">'
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


def build_nav(active_file: str) -> str:
    """Build navigation links, grouped by category."""
    lines = []
    current_section = None
    for page, section, depth in iter_pages():
        if section is not current_section:
            current_section = section
            lines.append(f'            <div class="nav-group">{section["title"]}</div>')
        md_file = page["file"]
        html_file = md_file.replace(".md", ".html")
        classes = ["nav-child"] if depth else []
        if md_file == active_file:
            classes.append("active")
        attr = f' class="{" ".join(classes)}"' if classes else ""
        lines.append(f'            <a href="{html_file}"{attr}>{page["label"]}</a>')
    return "\n".join(lines)


def build_cards(pages) -> str:
    """Render index cards for a flat list of page dicts."""
    cards = []
    for page in pages:
        md_file, label = page["file"], page["label"]
        html_file = md_file.replace(".md", ".html")
        # Read first paragraph as description
        md_path = MD_DIR / md_file
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Get the overview paragraph (first paragraph after first heading)
        paragraphs = re.split(r"\n\n+", content)
        desc = ""
        for p in paragraphs:
            p = p.strip()
            if (
                p
                and not p.startswith("#")
                and not p.startswith("```")
                and not p.startswith(">")  # skip the paper/metadata blockquote
            ):
                # Truncate to ~150 chars
                # Preserve escaped asterisks (e.g. π\*₀.₆) by stashing them
                # before stripping bold/emphasis markers.
                desc = (
                    p[:200]
                    .replace("\\*", "")
                    .replace("**", "")
                    .replace("*", "")
                    .replace("", "*")
                )
                if len(p) > 200:
                    desc += "..."
                desc = desc.replace("`", "")
                break
        klass = "card card-lead" if page.get("children") else "card"
        badge = ""
        if page.get("children"):
            badge = '                <span class="card-badge">总览 · 从这里开始</span>\n'
        elif page.get("_child"):
            badge = '                <span class="card-badge card-badge-sub">细分</span>\n'
        cards.append(
            f'            <div class="{klass}">\n'
            f"{badge}"
            f'                <h3><a href="{html_file}">{label}</a></h3>\n'
            f"                <p>{desc}</p>\n"
            f"            </div>"
        )

    return "\n".join(cards)


def build_index_page() -> str:
    """Build index/overview page content, one card grid per category."""
    total = sum(1 for _ in iter_pages())
    blocks = [
        f"        <h1>{SITE_TITLE}</h1>",
        f"        <p>{SITE_SUBTITLE} —— 按主题分类,共 {total} 篇文档。</p>",
    ]
    for section in SECTIONS:
        flat = []
        for page in section["pages"]:
            flat.append(page)
            for child in page.get("children", []):
                flat.append(dict(child, _child=True))
        blocks.append(
            '        <section class="cat">\n'
            f'            <h2 class="cat-title">{section["title"]}'
            f'<span class="cat-count">{len(flat)}</span></h2>\n'
            f'            <p class="cat-desc">{section["desc"]}</p>\n'
            '            <div class="card-grid">\n'
            + build_cards(flat)
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


def main():
    SITE_DIR.mkdir(exist_ok=True)

    # Write CSS with card grid styles appended
    card_css = """
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
    with open(SITE_DIR / "style.css", "w", encoding="utf-8") as f:
        f.write(CSS + card_css + build_highlight_css())

    # Build index page
    index_html = TEMPLATE.format(
        title="Overview",
        site_title=SITE_TITLE,
        site_subtitle=SITE_SUBTITLE,
        content=build_index_page(),
        nav_links=build_nav(""),
        toc="",
        index_active=' class="active"',
    )
    with open(SITE_DIR / "index.html", "w", encoding="utf-8") as f:
        f.write(index_html)
    print("  index.html")

    # Build each page
    count = 0
    for page, section, _depth in iter_pages():
        md_file, label = page["file"], page["label"]
        md_path = MD_DIR / md_file
        with open(md_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        html_content, toc_tokens = md_to_html(md_content)
        html_file = md_file.replace(".md", ".html")

        page_html = TEMPLATE.format(
            title=label,
            site_title=SITE_TITLE,
            site_subtitle=SITE_SUBTITLE,
            content=f"        {html_content}",
            nav_links=build_nav(md_file),
            toc=build_toc(toc_tokens),
            index_active="",
        )

        with open(SITE_DIR / html_file, "w", encoding="utf-8") as f:
            f.write(page_html)
        print(f"  [{section['title']}] {html_file}")
        count += 1

    # Keep already-shared links alive: map every pre-numbering URL to its new one.
    rules = []
    for page, _section, _depth in iter_pages():
        new_stem = page["file"][:-len(".md")]
        old_stem = re.sub(r"^\d+\.", "", new_stem)
        if old_stem == new_stem:
            continue
        rules.append(f"/{old_stem} /{new_stem} 301")
        rules.append(f"/{old_stem}.html /{new_stem} 301")
    with open(SITE_DIR / "_redirects", "w", encoding="utf-8") as f:
        f.write("\n".join(rules) + "\n")
    print(f"  _redirects ({len(rules)} rules)")

    print(f"\nDone! {count} pages + index built in {SITE_DIR}/")


if __name__ == "__main__":
    main()
