import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import notas_da_versao  # noqa: E402

from gr7_presence.update_page import note_sections  # noqa: E402

CHANGELOG = """# Histórico

## [Não lançado]

## [2.0.0] - 2026-01-02

### Mudanças
- **Item com sublista:**
  - primeiro subitem, que é comprido e
    continua na linha de baixo;
  - segundo subitem.
- Item simples que também
  continua embaixo.

## [1.9.0] - 2026-01-01

### Correções
- Outra coisa.

[2.0.0]: https://exemplo.invalid/compare
"""

ITEM = re.compile(r"^\s*[-*] ", re.M)


class ReleaseNotesTest(unittest.TestCase):
    def test_sublist_keeps_its_lines_and_continuations_are_joined(self):
        self.assertEqual(notas_da_versao.release_notes("2.0.0", CHANGELOG),
                         "### Mudanças\n"
                         "- **Item com sublista:**\n"
                         "  - primeiro subitem, que é comprido e continua na linha de baixo;\n"
                         "  - segundo subitem.\n"
                         "- Item simples que também continua embaixo.\n")

    def test_new_window_reads_the_sublist_as_subitems(self):
        notes = notas_da_versao.release_notes("2.0.0", CHANGELOG)
        self.assertEqual(note_sections(notes), [("Mudanças", [
            ("Item com sublista:", 0),
            ("primeiro subitem, que é comprido e continua na linha de baixo;", 1),
            ("segundo subitem.", 1),
            ("Item simples que também continua embaixo.", 0)])])

    def test_old_versions_show_each_item_on_its_own_line(self):
        # Até a 1.3.1, a janela de atualização trocava cada "- " do começo da linha por "• ".
        notes = notas_da_versao.release_notes("2.0.0", CHANGELOG)
        bullets = [line for line in ITEM.sub("• ", notes).splitlines() if line.startswith("• ")]
        self.assertEqual(len(bullets), 4)

    def test_missing_section_stops_the_release(self):
        with self.assertRaises(SystemExit):
            notas_da_versao.release_notes("3.0.0", CHANGELOG)

    def test_no_item_of_the_real_changelog_is_glued_to_another(self):
        changelog = (notas_da_versao.ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        versions = re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)
        self.assertTrue(versions)
        for version in versions + ["Não lançado"]:   # o que vai virar a próxima release também
            m = re.search(rf"^## \[{re.escape(version)}\][^\n]*\n(.*?)(?=^## \[|^\[[^\]]+\]: |\Z)",
                          changelog, re.M | re.S)
            if not m or not m[1].strip():
                continue                               # Não lançado vazio, logo depois de uma release
            notes = notas_da_versao.release_notes(version, changelog)
            self.assertEqual(len(ITEM.findall(notes)), len(ITEM.findall(m[1])), version)


if __name__ == "__main__":
    unittest.main()
