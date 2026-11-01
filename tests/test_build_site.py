import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from docs import build_site


class RegistryTests(unittest.TestCase):
    def test_current_registry_is_valid(self):
        build_site.validate_sections()

    def test_registry_requires_valid_source_backed_publication_dates(self):
        key = "08.ACT_Architecture.md"
        invalid_dates = [
            {"month": "2023-13", "kind": "论文首发", "source": "https://example.com"},
            {"month": "2023-04", "kind": "论文首发", "source": ""},
        ]
        for publication in invalid_dates:
            with self.subTest(publication=publication):
                with patch.dict(build_site.PAGE_DATES, {key: publication}):
                    with self.assertRaisesRegex(ValueError, "publication"):
                        build_site.validate_sections()
        with patch.dict(build_site.PAGE_DATES, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "page has no publication date"):
                build_site.validate_sections()

    def test_registry_rejects_duplicates_and_missing_sources(self):
        sections = [
            {
                "title": "Test",
                "desc": "Test pages",
                "pages": [
                    {"file": "missing.md", "label": "First"},
                    {"file": "missing.md", "label": "Second"},
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "duplicate page registration"):
                build_site.validate_sections(sections, Path(temp_dir))

    def test_registry_rejects_unregistered_numbered_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            md_dir = Path(temp_dir)
            (md_dir / "01.Orphan.md").write_text("# Orphan", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unregistered Markdown source"):
                build_site.validate_sections([], md_dir)

    def test_registry_discovers_unregistered_nested_numbered_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            md_dir = Path(temp_dir)
            nested = md_dir / "egocentric"
            nested.mkdir()
            (nested / "25.Orphan.md").write_text("# Orphan", encoding="utf-8")
            (nested / "CONTRIBUTING.md").write_text("# Guide", encoding="utf-8")
            with self.assertRaisesRegex(
                ValueError, r"unregistered Markdown source: egocentric/25\.Orphan\.md"
            ):
                build_site.validate_sections([], md_dir)

    def test_registry_rejects_flat_output_collisions(self):
        for second_name in ("25.Shared.md", "25.shared.md"):
            with self.subTest(second_name=second_name), tempfile.TemporaryDirectory() as temp_dir:
                md_dir = Path(temp_dir)
                filenames = ["first/25.Shared.md", f"second/{second_name}"]
                for filename in filenames:
                    source = md_dir / filename
                    source.parent.mkdir()
                    source.write_text("# Shared", encoding="utf-8")
                sections = [{
                    "title": "Test", "desc": "Test pages",
                    "pages": [{"file": name, "label": name} for name in filenames],
                }]
                with self.assertRaisesRegex(ValueError, "duplicate output filename"):
                    build_site.validate_sections(sections, md_dir)

    def test_registry_reserves_the_generated_overview_filename(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            md_dir = Path(temp_dir)
            (md_dir / "index.md").write_text("# Article", encoding="utf-8")
            sections = [{
                "title": "Test", "desc": "Test pages",
                "pages": [{"file": "index.md", "label": "Article"}],
            }]
            with self.assertRaisesRegex(ValueError, "duplicate output filename: index.html"):
                build_site.validate_sections(sections, md_dir)

    def test_registry_rejects_sources_that_escape_through_a_symlink(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            md_dir = root / "docs"
            md_dir.mkdir()
            outside = root / "outside.md"
            outside.write_text("# Outside", encoding="utf-8")
            (md_dir / "25.Outside.md").symlink_to(outside)
            sections = [{
                "title": "Test", "desc": "Test pages",
                "pages": [{"file": "25.Outside.md", "label": "Outside"}],
            }]
            with self.assertRaisesRegex(ValueError, "source escapes docs directory"):
                build_site.validate_sections(sections, md_dir)

    def test_html_filename_accepts_canonical_nested_sources_but_keeps_output_flat(self):
        self.assertEqual(build_site.html_filename("01.Example.md"), "01.Example.html")
        self.assertEqual(
            build_site.html_filename("egocentric/25.HumanEgo_Architecture.md"),
            "25.HumanEgo_Architecture.html",
        )
        for invalid in (
            "", "/example.md", "../example.md", "nested/../example.md",
            "./example.md", "nested/./example.md", "nested//example.md",
            "nested/example.md/", r"nested\example.md", "C:/example.md",
            "example.txt", "example",
        ):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                build_site.html_filename(invalid)


class RenderingTests(unittest.TestCase):
    def test_sidebar_is_viewport_bounded_and_scrolls_independently(self):
        sidebar = re.search(r"\.sidebar\s*\{([^}]+)\}", build_site.CSS).group(1)
        self.assertIn("height: 100vh;", sidebar)
        self.assertIn("height: 100dvh;", sidebar)
        self.assertNotIn("min-height:", sidebar)
        self.assertIn("overflow-y: auto;", sidebar)
        self.assertIn("overscroll-behavior-y: contain;", sidebar)

    def test_overview_dates_cover_every_method_and_link_to_sources(self):
        index = build_site.build_index_page()
        total = sum(1 for _ in build_site.iter_pages())
        self.assertEqual(index.count('<time datetime="'), total)
        self.assertEqual(index.count('class="card-date-source"'), total)
        self.assertIn('<time datetime="2023-04">2023.04</time>', index)
        self.assertIn('href="https://arxiv.org/abs/2304.13705"', index)
        self.assertIn("不是本文修改时间", index)
        self.assertIn("2026.02 开源推理；2026.04 开源训练", index)

    def test_publication_meta_escapes_notes_and_handles_unknown_pages(self):
        with patch.dict(build_site.PAGE_DATES, {
            "test.md": {"month": "2026-08", "kind": "A < B", "note": "<script>",
                        "source": "https://example.com/?a=1&b=2"},
        }):
            meta = build_site.build_publication_meta("test.md")
        self.assertIn("A &lt; B", meta)
        self.assertIn("&lt;script&gt;", meta)
        self.assertIn("a=1&amp;b=2", meta)
        self.assertIn("年月待核实", build_site.build_publication_meta("unknown.md"))

    def test_overview_contains_knowledge_map_and_domain_counts(self):
        index = build_site.build_index_page()
        self.assertIn('class="knowledge-path"', index)
        self.assertEqual(index.count('class="knowledge-stage knowledge-stage-'), 5)
        self.assertIn('class="knowledge-feedback"', index)
        self.assertIn('class="domain-honeycomb"', index)
        self.assertEqual(index.count('class="domain-hex'), 9)
        self.assertIn('data-topic="reinforcement"', index)
        self.assertIn('data-topics="foundation generative imitation perception"', index)
        self.assertIn("23.Skild-S1_Architecture.html", index)
        self.assertIn("VLA / ICL", index)

    def test_summary_is_plain_text_and_cards_escape_html(self):
        source = (
            "# Title\n\n> metadata\n\n"
            "**A & B** uses [a link](https://example.com), `code`, "
            "<span>markup</span>, and pi\\*."
        )
        self.assertEqual(
            build_site.extract_summary(source),
            "A & B uses a link, code, markup, and pi*.",
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            md_dir = Path(temp_dir)
            (md_dir / "page.md").write_text(source, encoding="utf-8")
            cards = build_site.build_cards(
                [{"file": "page.md", "label": "A < B"}], md_dir
            )
        self.assertIn("A &lt; B", cards)
        self.assertIn("A &amp; B", cards)
        self.assertNotIn("<span>", cards)

    def test_markdown_preserves_mermaid_math_and_wraps_tables(self):
        source = """# Page

## 三个编码器

```mermaid
flowchart LR
    A[one<br/>two] --> B
```

Inline $x_y$.

| A | B |
|---|---|
| 1 | 2 |
"""
        html, toc = build_site.md_to_html(source)
        self.assertIn('<div class="mermaid">', html)
        self.assertIn("one&lt;br/&gt;two", html)
        self.assertIn("$x_y$", html)
        self.assertIn('<div class="table-wrap"><table>', html)
        self.assertEqual(toc[0]["id"], "三个编码器")

    def test_more_than_nine_mermaid_blocks_restore_exact_sources(self):
        sources = [f'flowchart LR\n    N{i}["diagram {i}"]' for i in range(12)]
        markdown_source = "\n\n".join(
            f"```mermaid\n{source}\n```" for source in sources
        )

        html, _toc = build_site.md_to_html(markdown_source)

        self.assertEqual(html.count('class="mermaid"'), 12)
        for i in range(12):
            self.assertEqual(html.count(f'diagram {i}"'), 1)

    def test_mermaid_palette_adapts_to_dark_theme(self):
        self.assertIn("const darkMermaidPalette", build_site.TEMPLATE)
        self.assertIn("if (currentTheme() !== 'dark') return source", build_site.TEMPLATE)
        self.assertIn("'#e8f5e9': '#163224'", build_site.TEMPLATE)
        self.assertIn(
            "el.textContent = mermaidSourceForTheme(el.dataset.src)",
            build_site.TEMPLATE,
        )
        self.assertIn("theme: dark ? 'base' : 'default'", build_site.TEMPLATE)

    def test_rendered_site_has_no_broken_local_page_links(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "site"
            count = build_site.render_site(output_dir)
            self.assertEqual(count, sum(1 for _ in build_site.iter_pages()))
            generated = {path.name for path in output_dir.iterdir()}
            stylesheets = [name for name in generated if name.endswith(".css")]
            self.assertEqual(len(stylesheets), 1)
            self.assertRegex(stylesheets[0], r"^style-[0-9a-f]{12}\.css$")
            for page in output_dir.glob("*.html"):
                for href in re.findall(r'href="([^"]+)"', page.read_text(encoding="utf-8")):
                    if href.startswith(("#", "http://", "https://")):
                        continue
                    target = href.split("#", 1)[0].removeprefix("./")
                    self.assertIn(target, generated, f"{page.name} -> {target}")

    def test_nested_source_renders_flat_with_working_links_and_redirects(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            md_dir = root / "docs"
            nested_dir = md_dir / "egocentric"
            nested_dir.mkdir(parents=True)
            root_name = "01.Pi0_Architecture.md"
            nested_name = "egocentric/25.HumanEgo_Architecture.md"
            (md_dir / root_name).write_text(
                "# Root\n\n[HumanEgo](./25.HumanEgo_Architecture.html)", encoding="utf-8"
            )
            (md_dir / nested_name).write_text(
                "# HumanEgo\n\n[Root](./01.Pi0_Architecture.html)", encoding="utf-8"
            )
            sections = [
                {"title": "Root", "desc": "Root pages", "pages": [
                    {"file": root_name, "label": "Root"},
                ]},
                {"title": "Egocentric", "desc": "First-person learning", "pages": [
                    {"file": nested_name, "label": "HumanEgo"},
                ]},
            ]
            build_site.validate_sections(sections, md_dir)
            output_dir = root / "site"
            self.assertEqual(build_site.render_site(output_dir, sections, md_dir), 2)
            self.assertTrue((output_dir / "25.HumanEgo_Architecture.html").is_file())
            self.assertFalse((output_dir / "egocentric").exists())

            index = (output_dir / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="25.HumanEgo_Architecture.html"', index)
            self.assertIn('class="nav-group">Egocentric</div>', index)
            for filename in ("01.Pi0_Architecture.html", "25.HumanEgo_Architecture.html"):
                page = output_dir / filename
                source = page.read_text(encoding="utf-8")
                for href in re.findall(r'href="([^"]+)"', source):
                    if href.startswith(("#", "http://", "https://")):
                        continue
                    target = href.split("#", 1)[0]
                    self.assertTrue((page.parent / target).is_file(), f"{filename} -> {href}")
            redirects = (output_dir / "_redirects").read_text(encoding="utf-8")
            self.assertIn("/HumanEgo_Architecture /25.HumanEgo_Architecture 301\n", redirects)
            self.assertIn("/HumanEgo_Architecture.html /25.HumanEgo_Architecture 301\n", redirects)
            self.assertNotIn("/egocentric/", redirects)

    def test_stylesheet_filename_changes_with_css_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            first, second = Path(temp_dir) / "first", Path(temp_dir) / "second"
            sections = [{"title": "Test", "desc": "Test", "pages": [build_site.SECTIONS[0]["pages"][0]]}]
            build_site.render_site(first, sections=sections)
            with patch.object(build_site, "CARD_CSS", build_site.CARD_CSS + "\n/* changed */"):
                build_site.render_site(second, sections=sections)
            self.assertNotEqual(next(first.glob("*.css")).name, next(second.glob("*.css")).name)

    def test_site_replacement_removes_stale_outputs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            site_dir = root / "site"
            staging_dir = root / "staging"
            site_dir.mkdir()
            staging_dir.mkdir()
            (site_dir / "stale.html").write_text("old", encoding="utf-8")
            (staging_dir / "index.html").write_text("new", encoding="utf-8")

            build_site.replace_site(staging_dir, site_dir)

            self.assertFalse((site_dir / "stale.html").exists())
            self.assertEqual((site_dir / "index.html").read_text(), "new")
            self.assertFalse(staging_dir.exists())


if __name__ == "__main__":
    unittest.main()
