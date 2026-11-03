import copy
import unittest

from gr7_presence.config import DEFAULTS
from gr7_presence.detector import Target
from gr7_presence.gr7_state import PresetInfo, parse_buffer
from gr7_presence.i18n import Translator, format_duration
from gr7_presence.presence import build_activity, build_cards, fit
from gr7_presence.stats import Summary

from tests import sinteticos

TRACK = "Banda Fictícia Primeira Canção"


class FakeConfig(dict):
    def __getitem__(self, key):
        return self.get(key, DEFAULTS.get(key))


def summary(**kw):
    base = dict(today=4320, week=20000, total=196200, sessions=87, streak=5, best_streak=9,
                top_presets=[], top_amps=[], recent=[])
    base.update(kw)
    return Summary(**base)


class CardsTest(unittest.TestCase):
    def setUp(self):
        self.cfg = FakeConfig(copy.deepcopy(DEFAULTS))
        self.t = Translator("pt")
        self.preset = parse_buffer(sinteticos.tle())
        self.target = Target("standalone", 123, 1_700_000_000.0)

    def test_standalone_cards(self):
        cards = build_cards(self.preset, self.target, summary(), self.cfg, self.t, [TRACK])
        self.assertEqual([c.key for c in cards], ["rig", "style", "tape", "stats"])
        rig, style, tape, stats = cards
        self.assertEqual(rig.details, "🎸 Riff Pesado")
        self.assertEqual(rig.state, "🔊 Van 51 · Skreamer → PsycheDelay → Vintage Verb")
        self.assertIn("Control Room Pro", rig.small_text)   # a cadeia completa fica no hover
        self.assertEqual(style.state, "🤘 Metal · Hi Gain · Distorted")
        self.assertEqual(style.small_text, "Preset de fábrica por Autora Fictícia")
        self.assertEqual(tape.details, "🎶 Backing track")
        self.assertEqual(tape.state, TRACK)
        self.assertEqual(stats.state, "⏱ Hoje 1h12 · 🔥 5 dias seguidos")
        self.assertEqual(stats.small_image, "fire")
        self.assertEqual(stats.small_text, "54h30 tocados em 87 sessões")

    def test_long_chain_is_shortened(self):
        preset = parse_buffer(sinteticos.ngrr())
        rig = build_cards(preset, self.target, None, self.cfg, self.t)[0]
        self.assertEqual(rig.state, "🔊 Plex · AutoFilter → Stomp Compressor → Tube Compressor +3")
        self.assertTrue(rig.small_text.endswith("PsycheDelay → Studio Reverb"))

    def test_no_track_no_tape_card(self):
        cards = build_cards(self.preset, self.target, summary(), self.cfg, self.t, [])
        self.assertNotIn("tape", [c.key for c in cards])

    def test_toggles(self):
        self.cfg.update(show_backing_track=False, show_tags=False, show_rack_chain=False, show_streak=False)
        cards = build_cards(self.preset, self.target, summary(), self.cfg, self.t, ["Faixa"])
        self.assertEqual([c.key for c in cards], ["rig", "stats"])
        self.assertEqual(cards[0].state, "🔊 Van 51")
        self.assertEqual(cards[1].state, "⏱ Hoje 1h12 · Total 54h30")
        self.assertEqual(cards[1].small_image, "clock")

    def test_hide_preset_name(self):
        self.cfg["show_preset"] = False
        cards = build_cards(self.preset, self.target, summary(), self.cfg, self.t)
        self.assertEqual(cards[0].details, "🎸 Tocando guitarra")

    def test_no_preset_still_has_a_card(self):
        self.cfg["show_stats"] = False
        cards = build_cards(None, self.target, None, self.cfg, self.t)
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].details, "🎸 Tocando guitarra")

    def test_plugin_mode(self):
        target = Target("plugin", 9, 1_700_000_000.0, host="REAPER")
        cards = build_cards(self.preset, target, summary(), self.cfg, self.t, ["Faixa"])
        self.assertTrue(all(c.details == "🎛️ Guitar Rig 7 no REAPER" for c in cards))
        self.assertEqual([c.key for c in cards], ["stats"])

    def test_empty_rack_and_scratch(self):
        empty = build_cards(self.preset, self.target, summary(), self.cfg, self.t, [], "empty")
        self.assertEqual([c.key for c in empty], ["rack", "stats"])
        self.assertEqual(empty[0].details, "🎛️ Rack vazio")
        self.assertEqual(empty[0].state, "🔧 Começando um timbre do zero")
        self.assertTrue(all("Riff" not in c.details for c in empty))   # nada do preset antigo
        scratch = build_cards(self.preset, self.target, summary(), self.cfg, self.t, ["Faixa"], "scratch")
        self.assertEqual([c.key for c in scratch], ["rack", "tape", "stats"])
        self.assertEqual(scratch[0].details, "🎛️ Timbre próprio")
        self.assertEqual(scratch[2].details, "🎛️ Timbre próprio")

    def test_preset_without_details(self):
        cards = build_cards(PresetInfo(name="Meu Timbre"), self.target, summary(), self.cfg, self.t)
        self.assertEqual([c.key for c in cards], ["stats"])
        self.assertEqual(cards[0].details, "🎸 Meu Timbre")

    def test_english(self):
        cards = build_cards(self.preset, self.target, summary(), self.cfg, Translator("en"))
        self.assertEqual(cards[-1].state, "⏱ Today 1h12 · 🔥 5-day streak")


class ActivityTest(unittest.TestCase):
    def setUp(self):
        self.cfg = FakeConfig(copy.deepcopy(DEFAULTS))
        self.t = Translator("pt")
        self.target = Target("standalone", 123, 1_700_000_000.5)

    def test_payload(self):
        preset = parse_buffer(sinteticos.tle())
        card = build_cards(preset, self.target, None, self.cfg, self.t)[0]
        act = build_activity(card, self.target, self.cfg, self.t, "Guitar Rig 7 Pro", "7.0.2")
        self.assertEqual(act["type"], 0)
        self.assertEqual(act["timestamps"], {"start": 1_700_000_000_500})
        self.assertEqual(act["assets"]["large_image"], "gr7_logo")
        self.assertEqual(act["assets"]["large_text"], "Guitar Rig 7 Pro · v7.0.2")
        self.assertEqual(len(act["buttons"]), 1)   # o segundo botão vem vazio por padrão

    def test_buttons_are_validated(self):
        self.cfg["buttons"] = [
            {"label": "Meu canal no YouTube com um nome bem comprido", "url": "https://youtube.com/@x"},
            {"label": "Ruim", "url": "javascript:alert(1)"},
        ]
        card = build_cards(None, self.target, None, self.cfg, self.t)[0]
        act = build_activity(card, self.target, self.cfg, self.t, None, None)
        self.assertEqual(len(act["buttons"]), 1)
        self.assertLessEqual(len(act["buttons"][0]["label"]), 32)

    def test_resolver_maps_images(self):
        card = build_cards(parse_buffer(sinteticos.tle()), self.target, None, self.cfg, self.t)[0]
        act = build_activity(card, self.target, self.cfg, self.t, None, None, lambda k: "https://cdn/" + k)
        self.assertEqual(act["assets"]["large_image"], "https://cdn/gr7_logo")
        self.assertEqual(act["assets"]["small_image"], "https://cdn/amp")

    def test_activity_type(self):
        self.cfg["activity_type"] = "listening"
        card = build_cards(None, self.target, None, self.cfg, self.t)[0]
        self.assertEqual(build_activity(card, self.target, self.cfg, self.t, None, None)["type"], 2)


class HelpersTest(unittest.TestCase):
    def test_fit(self):
        self.assertIsNone(fit(""))
        self.assertIsNone(fit("a"))
        self.assertEqual(fit("  ok  "), "ok")
        long = "🎸" * 100   # cada emoji vale 2 unidades UTF-16
        out = fit(long)
        self.assertLessEqual(len(out.encode("utf-16-le")) // 2, 128)
        self.assertTrue(out.endswith("…"))

    def test_format_duration(self):
        self.assertEqual(format_duration(30), "0min")
        self.assertEqual(format_duration(540), "9min")
        self.assertEqual(format_duration(3725), "1h02")
        self.assertEqual(format_duration(400 * 3600), "400h")


if __name__ == "__main__":
    unittest.main()
