import dsc
import unittest

TEST_TEXT = '''         Index             t      Heatflow            Tr
           [#]           [s]          [mW]          [°C]
             0  0.00000e+000 -8.42906e-002  2.50000e+001
             1  1.00000e+000 -1.02480e-001  2.51667e+001
PET_group2, 02.02.2022 20:36:15'''

class TestDSC(unittest.TestCase):
    def test_parse_regex(self):
        m = dsc.RE_LINE.findall(TEST_TEXT)

    def test_parse_text(self):
        data = dsc.parse_tabulated_txt(TEST_TEXT)
        self.assertEqual(data.Index[0], 0)
        self.assertEqual(data.Index[1], 1)
        self.assertEqual(data.Heatflow[0], -8.42906e-2)
        self.assertEqual(data.Heatflow[1], -1.02480e-1)

if __name__ == '__main__':
    unittest.main()
