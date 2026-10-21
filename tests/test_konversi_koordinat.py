"""Unit test konversi_koordinat. Jalankan: python3 -m unittest discover -s tests -v"""

import csv
import io
import os
import random
import sys
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import konversi_koordinat as kk  # noqa: E402

# Nilai referensi dihitung dengan pyproj 3.8.0 / PROJ 9.8.1 (EPSG:4326 -> EPSG:326xx/327xx)
# di virtualenv terpisah, 21 Oktober 2026. pyproj BUKAN dependency repo ini.
REFERENSI_PROJ = {
    "Monas, Jakarta": (-6.175392, 106.827153, 48, "S", 702178.122709, 9317060.285667),
    "Banda Aceh": (5.5483, 95.3238, 46, "N", 757447.111287, 613778.046505),
    "Medan": (3.5952, 98.6722, 47, "N", 463595.174787, 397389.385102),
    "Kupang": (-10.1772, 123.6070, 51, "S", 566489.289045, 8874933.315132),
    "Jayapura": (-2.5337, 140.7181, 54, "S", 468661.922133, 9719944.781719),
    "Lintang 60 LU (zona 32)": (60.0, 9.0, 32, "N", 500000.0, 6651411.190363),
    "Selandia Baru": (-45.0, 170.5, 59, "S", 460592.350983, 5016928.012408),
}


class TestUTM(unittest.TestCase):
    def test_ekuator_di_meridian_tengah(self):
        u = kk.dd_ke_utm(0.0, 105.0)
        self.assertEqual((u.zona, u.hemisfer, u.band), (48, "N", "N"))
        self.assertEqual(u.easting, 500000.0)
        self.assertAlmostEqual(u.northing, 0.0, places=9)

    def test_ekuator_dari_selatan_utm_ke_dd(self):
        lat, lon = kk.utm_ke_dd(48, "S", 500000.0, 10000000.0)
        self.assertAlmostEqual(lat, 0.0, places=12)
        self.assertAlmostEqual(lon, 105.0, places=12)

    def test_meridian_tengah_easting_tepat_500000(self):
        for lat in (-10.0, -6.0, 3.5, 45.0):
            self.assertEqual(kk.dd_ke_utm(lat, 117.0).easting, 500000.0)
        # Northing di meridian tengah = panjang busur meridian x 0,9996 (+10 juta di selatan)
        self.assertAlmostEqual(kk.dd_ke_utm(-6.0, 105.0).northing, 9336795.432607, places=3)

    def test_cocok_dengan_proj_tingkat_milimeter(self):
        for nama, (lat, lon, zona, hemi, e, n) in REFERENSI_PROJ.items():
            with self.subTest(nama):
                u = kk.dd_ke_utm(lat, lon)
                self.assertEqual((u.zona, u.hemisfer), (zona, hemi))
                self.assertLess(abs(u.easting - e), 1e-3)
                self.assertLess(abs(u.northing - n), 1e-3)

    def test_utm_ke_dd_monas(self):
        lat, lon = kk.utm_ke_dd(48, "S", 702178.122709, 9317060.285667)
        self.assertAlmostEqual(lat, -6.175392, places=9)
        self.assertAlmostEqual(lon, 106.827153, places=9)

    def test_round_trip_presisi_1e9_derajat(self):
        acak = random.Random(2929)
        for _ in range(500):
            lat, lon = acak.uniform(-11.5, 6.5), acak.uniform(94.5, 141.5)
            u = kk.dd_ke_utm(lat, lon)
            lat2, lon2 = kk.utm_ke_dd(u.zona, u.hemisfer, u.easting, u.northing)
            self.assertLess(abs(lat2 - lat), 1e-9)
            self.assertLess(abs(lon2 - lon), 1e-9)

    def test_paksa_zona_tetangga(self):
        u = kk.dd_ke_utm(-8.0, 107.999999, zona=48)
        self.assertLess(abs(u.easting - 830743.732018), 1e-3)
        self.assertLess(abs(u.northing - 9114496.241508), 1e-3)
        with self.assertRaises(kk.KoordinatError):
            kk.dd_ke_utm(-6.0, 106.8, zona=52)  # terlalu jauh dari meridian tengah

    def test_zona_band_dan_epsg(self):
        self.assertEqual(kk.zona_utm(-6.2, 106.8), 48)
        self.assertEqual(kk.zona_utm(0, 180), 60)
        self.assertEqual(kk.zona_utm(60, 5), 32)   # pengecualian Norwegia
        self.assertEqual(kk.zona_utm(78, 15), 33)  # pengecualian Svalbard
        self.assertEqual(kk.band_lintang(-6.2), "M")
        self.assertEqual(kk.band_lintang(-10.2), "L")
        self.assertEqual(kk.band_lintang(84), "X")
        self.assertEqual(kk.meridian_tengah(54), 141)
        self.assertEqual(kk.kode_epsg(48, "S"), {"wgs84": 32748, "srgi2013": 9488})
        self.assertEqual(kk.kode_epsg(46, "N")["srgi2013"], 9476)

    def test_parse_zona(self):
        self.assertEqual(kk.parse_zona("48M")[:2], (48, "S"))
        self.assertEqual(kk.parse_zona("49N")[:2], (49, "N"))
        zona, hemi, catatan = kk.parse_zona("48S")
        self.assertEqual((zona, hemi), (48, "S"))
        self.assertIsNotNone(catatan)
        self.assertEqual(kk.parse_zona("50", "utara")[:2], (50, "N"))
        for salah in ("61S", "48", "abc", "48I"):
            with self.subTest(salah), self.assertRaises(kk.KoordinatError):
                kk.parse_zona(salah)


class TestDMS(unittest.TestCase):
    def test_parser_dms_fleksibel(self):
        target = -(6 + 10 / 60 + 31.4 / 3600)
        for teks in ("6°10'31.4\"S", "-6 10 31.4", "6° 10' 31,4\" LS", "S 6 10 31.4",
                     "6:10:31.4 S", "6°10′31.4″ LS", "6°10'31.4''S"):
            with self.subTest(teks):
                nilai, sumbu = kk.dms_ke_dd(teks)
                self.assertAlmostEqual(nilai, target, places=12)
        nilai, sumbu = kk.dms_ke_dd("106°49'37\" BT")
        self.assertAlmostEqual(nilai, 106 + 49 / 60 + 37 / 3600, places=12)
        self.assertEqual(sumbu, "lon")
        self.assertAlmostEqual(kk.dms_ke_dd("74°0'21\" W")[0], -74.005833333, places=8)
        self.assertAlmostEqual(kk.dms_ke_dd("3 35,712 LU")[0], 3.5952, places=10)

    def test_parser_dms_menolak_input_salah(self):
        for teks in ("6 61 0 S", "6 10 75", "95 0 0 LU", "200 BT", "6 10 31 X",
                     "-6 10 31 LU", "6 -10 3", "", "abc", "6.5 10 0"):
            with self.subTest(teks), self.assertRaises(kk.KoordinatError):
                kk.dms_ke_dd(teks)

    def test_dd_ke_dms_dan_pembulatan(self):
        self.assertEqual(kk.format_dms(-6.175392, "lat"), "6°10'31,41\" LS")
        self.assertEqual(kk.format_dms(106.827153, "lon", 3, "en"), "106°49'37.751\" E")
        # 10,99999999° tidak boleh tampil sebagai 10°59'60,00"
        self.assertEqual(kk.format_dms(10.99999999, "lat"), "11°00'00,00\" LU")
        self.assertEqual(kk.format_dms(-0.5, "lon", 0), "0°30'00\" BB")
        self.assertEqual(kk.dd_ke_dms(-6.175392, "lat", 2), (6, 10, 31.41, "S"))

    def test_round_trip_dms(self):
        for nilai in (-6.175392, 106.827153, 0.000001, -179.999999):
            sumbu = "lat" if abs(nilai) <= 90 else "lon"
            teks = kk.format_dms(nilai, sumbu, presisi=6)
            self.assertAlmostEqual(kk.dms_ke_dd(teks)[0], nilai, places=9)


class TestAngkaDanCLI(unittest.TestCase):
    def test_parse_angka_dan_format(self):
        self.assertEqual(kk.parse_angka("-6,175392"), -6.175392)
        self.assertEqual(kk.parse_angka("9.317.060,29"), 9317060.29)
        self.assertEqual(kk.parse_angka("702178.12"), 702178.12)
        self.assertEqual(kk.fmt_angka(9317060.2857, 2), "9.317.060,29")
        self.assertEqual(kk.pisah_pasangan("-6.175392, 106.827153"), ("-6.175392", "106.827153"))
        self.assertEqual(kk.pisah_pasangan("-6,175392 106,827153"), ("-6.175392", "106.827153"))
        with self.assertRaises(kk.KoordinatError):
            kk.parse_angka("enam")

    def test_validasi_rentang(self):
        with self.assertRaises(kk.KoordinatError):
            kk.dd_ke_utm(-85, 106)  # di luar cakupan UTM
        with self.assertRaises(kk.KoordinatError):
            kk.utm_ke_dd(48, "S", 1500000, 9300000)
        with self.assertRaises(kk.KoordinatError):
            kk.utm_ke_dd(0, "S", 500000, 9300000)

    def test_cli_exit_code(self):
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(kk.main(["dd2utm", "-6.175392", "106.827153"]), 0)
        self.assertIn("702.178,12", out.getvalue())
        with redirect_stdout(io.StringIO()), unittest.mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(kk.main(["dd2utm", "95", "10"]), 1)

    def test_batch_csv_titik_koma(self):
        with tempfile.TemporaryDirectory() as tmp:
            masuk = os.path.join(tmp, "titik.csv")
            keluar = os.path.join(tmp, "hasil.csv")
            with open(masuk, "w", encoding="utf-8", newline="") as f:
                f.write("nama;lat;lon\nMonas;-6,175392;106,827153\nSalah;95;10\n")
            sukses, gagal = kk.proses_csv(masuk, keluar, "dd2utm")
            self.assertEqual((sukses, gagal), (1, 1))
            with open(keluar, encoding="utf-8-sig", newline="") as f:
                baris = list(csv.DictReader(f, delimiter=";"))
            self.assertEqual(baris[0]["utm_zona"], "48")
            self.assertEqual(baris[0]["utm_easting"], "702178,123")
            self.assertEqual(baris[0]["utm_northing"], "9317060,286")
            self.assertIn("Lintang", baris[1]["galat"])

    def test_batch_csv_utm_ke_dd(self):
        with tempfile.TemporaryDirectory() as tmp:
            masuk = os.path.join(tmp, "utm.csv")
            keluar = os.path.join(tmp, "hasil.csv")
            with open(masuk, "w", encoding="utf-8", newline="") as f:
                f.write("zona,easting,northing\n48S,702178.122709,9317060.285667\n")
            self.assertEqual(kk.proses_csv(masuk, keluar, "utm2dd"), (1, 0))
            with open(keluar, encoding="utf-8-sig", newline="") as f:
                baris = next(csv.DictReader(f))
            self.assertAlmostEqual(float(baris["lat_dd"]), -6.175392, places=7)
            self.assertAlmostEqual(float(baris["lon_dd"]), 106.827153, places=7)


if __name__ == "__main__":
    unittest.main()
