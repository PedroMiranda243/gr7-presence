import unittest
from unittest import mock

from gr7_presence import ui_kit as K


class MaskTest(unittest.TestCase):
    def test_rounded_corners(self):
        m = K.rounded_mask(40, 30, 10)
        self.assertEqual(m.size, (40, 30))
        self.assertEqual(m.getpixel((0, 0)), 0)           # canto de fora
        self.assertEqual(m.getpixel((20, 15)), 255)       # meio
        self.assertEqual(m.getpixel((20, 0)), 255)        # borda reta
        self.assertTrue(any(0 < m.getpixel((x, y)) < 255 for x in range(10) for y in range(10)))   # canto suavizado

    def test_radius_bigger_than_box(self):
        self.assertEqual(K.rounded_mask(6, 6, 50).size, (6, 6))

    def test_gradient_directions(self):
        down = K.gradient(10, 50, "#FF0000", "#0000FF")
        self.assertGreater(down.getpixel((5, 0))[0], 200)    # vermelho em cima
        self.assertGreater(down.getpixel((5, 49))[2], 200)   # azul embaixo
        across = K.gradient(50, 10, "#FF0000", "#0000FF", horizontal=True)
        self.assertGreater(across.getpixel((0, 5))[0], 200)  # vermelho à esquerda
        self.assertGreater(across.getpixel((49, 5))[2], 200)

    def test_radial_light_fades(self):
        light = K.radial_light(200, 100, 100, 0, 80, 80, [(0, (255, 179, 71, 0.4)), (1, (0, 0, 0, 0))])
        self.assertGreater(light.getpixel((100, 1))[3], light.getpixel((100, 60))[3])
        self.assertEqual(light.getpixel((199, 99))[3], 0)

    def test_focus_ring_is_a_rounded_outline(self):
        ring = K.ring_image(52, 34, 17, K.AMBER, 2)          # a chave: pílula inteira
        self.assertEqual(ring.mode, "RGBA")
        self.assertEqual(ring.getpixel((26, 0))[3], 255)     # borda de cima cheia
        self.assertEqual(ring.getpixel((26, 33))[3], 255)    # e a de baixo, sem falha
        self.assertEqual(ring.getpixel((26, 17))[3], 0)      # o meio fica transparente
        self.assertEqual(ring.getpixel((0, 0))[3], 0)        # o canto é redondo
        self.assertTrue(any(0 < ring.getpixel((x, y))[3] < 255 for x in range(8) for y in range(8)))   # suavizado


class IconTest(unittest.TestCase):
    def test_every_icon_draws_something(self):
        for name in K.ICONS:
            img = K.icon_image(name, 24, "#FFFFFF")
            self.assertEqual(img.size, (24, 24))
            self.assertGreater(img.getchannel("A").getextrema()[1], 128, name)

    def test_path_parser(self):
        (pts, closed), = K._path_points("M1 2h3v4l-1 1Z")
        self.assertTrue(closed)
        self.assertEqual(pts, [(1, 2), (4, 2), (4, 6), (3, 7)])


class PainterTest(unittest.TestCase):
    def test_scale(self):
        p = K.Painter(100, 50, 1.5)
        self.assertEqual(p.img.size, (150, 75))
        self.assertEqual(p.px(10), 15)

    def test_fit_and_wrap(self):
        p = K.Painter(1, 1, 1.0)
        style = K.Style(13)
        long = "Um nome de preset comprido demais para caber na coluna"
        cut = p.fit(long, style, 120)
        self.assertTrue(cut.endswith("…"))
        self.assertLessEqual(p.measure(cut, style), 120)
        self.assertEqual(p.fit("Curto", style, 120), "Curto")
        lines = p.wrap(long, style, 120)
        self.assertGreater(len(lines), 1)
        self.assertEqual(" ".join(lines), long)

    def test_without_archivo_uses_segoe(self):
        K._font.cache_clear()
        self.addCleanup(K._font.cache_clear)
        with mock.patch.object(K, "ARCHIVO", K.ASSETS / "nao-existe.ttf"):
            f = K.font(K.Style(20, 800, display=True, width=125), 1.0)
        self.assertGreater(f.getlength("Estatísticas"), 0)

    def test_archivo_is_shipped(self):
        self.assertTrue(K.ARCHIVO.exists())
        self.assertTrue((K.ARCHIVO.parent / "OFL.txt").exists())   # a licença vai junto

    def test_segmented_regions(self):
        p = K.Painter(400, 60, 1.0)
        clicked = []
        w, h, regions = K.segmented(p, 390, 10, ["A", "Bb", "Ccc"], 1, ["a", "b", "c"],
                                    [lambda k=k: clicked.append(k) for k in "abc"])
        self.assertEqual([r.key for r in regions], ["a", "b", "c"])
        self.assertAlmostEqual(regions[-1].x1, 390 - 4, delta=1)
        regions[2].action()
        self.assertEqual(clicked, ["c"])


if __name__ == "__main__":
    unittest.main()
