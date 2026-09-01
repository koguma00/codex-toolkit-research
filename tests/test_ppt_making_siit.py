import json
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "research-toolkit-manager"
SKILL = PLUGIN / "skills" / "ppt-making-siit"
ASSETS = SKILL / "assets"


class PptMakingSiitPackagingTests(unittest.TestCase):
    def test_plugin_bundles_skill_and_version(self):
        manifest = json.loads(
            (PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["version"], "0.3.0")
        self.assertTrue((SKILL / "SKILL.md").is_file())
        self.assertTrue((SKILL / "agents" / "openai.yaml").is_file())

    def test_reference_assets_exist(self):
        expected = [
            ASSETS / "siit-reference-template.pptx",
            ASSETS / "siit-noto-sans-kr.thmx",
            ASSETS / "logos" / "kaist.png",
            ASSETS / "logos" / "siit.png",
        ]
        for path in expected:
            self.assertTrue(path.is_file(), path)
        self.assertEqual(len(list((ASSETS / "previews").glob("*.svg"))), 7)

    def test_ooxml_fonts_are_normalized(self):
        for path in (
            ASSETS / "siit-reference-template.pptx",
            ASSETS / "siit-noto-sans-kr.thmx",
        ):
            fonts = set()
            with ZipFile(path) as archive:
                for name in archive.namelist():
                    if not name.endswith(".xml"):
                        continue
                    try:
                        root = ET.fromstring(archive.read(name))
                    except ET.ParseError:
                        continue
                    for element in root.iter():
                        if "typeface" in element.attrib:
                            fonts.add(element.attrib["typeface"])
            self.assertEqual(fonts, {"Noto Sans KR"}, path)

    def test_template_is_sanitized(self):
        path = ASSETS / "siit-reference-template.pptx"
        with ZipFile(path) as archive:
            names = archive.namelist()
            slides = [
                name
                for name in names
                if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
            ]
            self.assertEqual(len(slides), 7)
            self.assertFalse(
                any(
                    marker in name
                    for name in names
                    for marker in (
                        "notesSlide",
                        "comments",
                        "customXml",
                        "embeddings",
                    )
                )
            )
            xml_payload = b"\n".join(
                archive.read(name)
                for name in names
                if name.endswith((".xml", ".rels"))
            )
        for private_text in (
            "고준원",
            "김준모",
            "지속가능한 실시간 멀티모달",
            "/home/ubuntu",
        ):
            self.assertNotIn(private_text.encode("utf-8"), xml_payload)


if __name__ == "__main__":
    unittest.main()
