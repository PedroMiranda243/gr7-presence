import string
import unittest

from gr7_presence.i18n import STRINGS, Translator, format_time


class TranslationsTest(unittest.TestCase):
    def test_both_languages_have_every_key(self):
        self.assertEqual(set(STRINGS["pt"]) ^ set(STRINGS["en"]), set())

    def test_same_placeholders(self):
        fields = lambda s: {f for _, f, _, _ in string.Formatter().parse(s) if f}
        for key, text in STRINGS["pt"].items():
            self.assertEqual(fields(text), fields(STRINGS["en"][key]), key)

    def test_lists_have_the_right_size(self):
        for lang in STRINGS:
            t = Translator(lang)
            self.assertEqual(len(t("weekdays_short").split(",")), 7)
            self.assertEqual(len(t("weekday_initials").split(",")), 7)
            self.assertEqual(len(t("months_short").split(",")), 12)

    def test_dates(self):
        self.assertEqual(Translator("pt")("date_short", d=5, m=8), "05/08")
        self.assertEqual(Translator("en")("date_short", d=5, m=8), "08/05")


class FormatTimeTest(unittest.TestCase):
    def test_like_the_mockup(self):
        self.assertEqual(format_time(42 * 60), "42 min")
        self.assertEqual(format_time(30), "0 min")
        self.assertEqual(format_time(352 * 60), "5 h 52")
        self.assertEqual(format_time(352 * 60, long=True), "5 h 52 min")
        self.assertEqual(format_time(65 * 60), "1 h 05")
        self.assertEqual(format_time(86 * 3600), "86 h")


if __name__ == "__main__":
    unittest.main()
