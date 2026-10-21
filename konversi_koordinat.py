#!/usr/bin/env python3
"""Konversi koordinat: DMS <-> derajat desimal (DD) <-> UTM (elipsoid WGS84).

Proyeksi UTM memakai seri Krüger orde n^6 (Karney 2011, "Transverse Mercator
with an accuracy of a few nanometers"), sehingga hasilnya akurat sampai jauh
di bawah satu milimeter di dalam zona. Hanya memakai standard library Python.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import re
import sys
from typing import Dict, List, NamedTuple, Optional, Tuple

# --- Konstanta elipsoid WGS84 (dipakai juga oleh SRGI2013) dan UTM ---------
A_WGS84 = 6378137.0
F_WGS84 = 1 / 298.257223563
K0 = 0.9996
FALSE_EASTING = 500000.0
FALSE_NORTHING_SELATAN = 10000000.0
HURUF_BAND = "CDEFGHJKLMNPQRSTUVWX"  # band 8 derajat dari 80 LS s.d. 84 LU


class KoordinatError(ValueError):
    """Kesalahan input koordinat (pesan berbahasa Indonesia)."""


class UTM(NamedTuple):
    zona: int
    hemisfer: str  # "N" (utara) atau "S" (selatan)
    easting: float
    northing: float
    band: str


def _koefisien_kruger(f: float) -> Tuple[float, List[float], List[float]]:
    """Hitung A (rectifying radius) serta koefisien alpha & beta orde n^6."""
    n = f / (2 - f)
    n2, n3, n4, n5, n6 = n**2, n**3, n**4, n**5, n**6
    a_rect = A_WGS84 / (1 + n) * (1 + n2 / 4 + n4 / 64 + n6 / 256)
    alpha = [
        n / 2 - 2 * n2 / 3 + 5 * n3 / 16 + 41 * n4 / 180 - 127 * n5 / 288 + 7891 * n6 / 37800,
        13 * n2 / 48 - 3 * n3 / 5 + 557 * n4 / 1440 + 281 * n5 / 630 - 1983433 * n6 / 1935360,
        61 * n3 / 240 - 103 * n4 / 140 + 15061 * n5 / 26880 + 167603 * n6 / 181440,
        49561 * n4 / 161280 - 179 * n5 / 168 + 6601661 * n6 / 7257600,
        34729 * n5 / 80640 - 3418889 * n6 / 1995840,
        212378941 * n6 / 319334400,
    ]
    beta = [
        n / 2 - 2 * n2 / 3 + 37 * n3 / 96 - n4 / 360 - 81 * n5 / 512 + 96199 * n6 / 604800,
        n2 / 48 + n3 / 15 - 437 * n4 / 1440 + 46 * n5 / 105 - 1118711 * n6 / 3870720,
        17 * n3 / 480 - 37 * n4 / 840 - 209 * n5 / 4480 + 5569 * n6 / 90720,
        4397 * n4 / 161280 - 11 * n5 / 504 - 830251 * n6 / 7257600,
        4583 * n5 / 161280 - 108847 * n6 / 3991680,
        20648693 * n6 / 638668800,
    ]
    return a_rect, alpha, beta


A_RECT, ALPHA, BETA = _koefisien_kruger(F_WGS84)
E_ECC = math.sqrt(F_WGS84 * (2 - F_WGS84))  # eksentrisitas pertama


# --- Zona & band --------------------------------------------------------------
def meridian_tengah(zona: int) -> int:
    """Bujur meridian tengah (derajat) sebuah zona UTM."""
    return zona * 6 - 183


def zona_utm(lat: float, lon: float) -> int:
    """Nomor zona UTM standar, termasuk pengecualian Norwegia & Svalbard."""
    _cek_lat_lon(lat, lon)
    zona = int((lon + 180) // 6) + 1
    if zona > 60:  # bujur tepat 180
        zona = 60
    if 56 <= lat < 64 and 3 <= lon < 12:
        zona = 32
    if 72 <= lat <= 84 and 0 <= lon < 42:
        zona = 31 if lon < 9 else 33 if lon < 21 else 35 if lon < 33 else 37
    return zona


def band_lintang(lat: float) -> str:
    """Huruf band lintang UTM/MGRS (C..X, tanpa I dan O)."""
    if not -80 <= lat <= 84:
        raise KoordinatError("Lintang di luar cakupan UTM (80° LS s.d. 84° LU).")
    return HURUF_BAND[min(int((lat + 80) // 8), len(HURUF_BAND) - 1)]


def kode_epsg(zona: int, hemisfer: str) -> Dict[str, Optional[int]]:
    """Kode EPSG 'WGS 84 / UTM' dan 'SRGI2013 / UTM' (bila terdaftar)."""
    wgs = (32600 if hemisfer == "N" else 32700) + zona
    srgi = None
    if hemisfer == "N" and 46 <= zona <= 52:
        srgi = 9476 + zona - 46
    elif hemisfer == "S" and 47 <= zona <= 54:
        srgi = 9487 + zona - 47
    return {"wgs84": wgs, "srgi2013": srgi}


# --- Validasi & parsing angka ------------------------------------------------
def _cek_lat_lon(lat: float, lon: float) -> None:
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise KoordinatError("Koordinat harus berupa angka.")
    if not -90 <= lat <= 90:
        raise KoordinatError(f"Lintang {lat} tidak valid; harus di antara -90 dan 90.")
    if not -180 <= lon <= 180:
        raise KoordinatError(f"Bujur {lon} tidak valid; harus di antara -180 dan 180.")


def parse_angka(teks: str) -> float:
    """Ubah teks angka ke float; menerima koma desimal & titik ribuan Indonesia."""
    s = str(teks).strip().replace(" ", "")
    if "," in s and "." in s:  # format Indonesia: 9.317.060,29
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    elif s.count(".") > 1:  # 9.317.060 -> titik ribuan
        s = s.replace(".", "")
    try:
        return float(s)
    except ValueError:
        raise KoordinatError(f"'{teks}' bukan angka yang valid.") from None


def pisah_pasangan(teks: str) -> Tuple[str, str]:
    """Pisahkan 'lat, lon' (mis. salinan Google Maps) menjadi dua teks."""
    s = teks.strip()
    if ";" in s:
        bagian = s.split(";")
    elif s.count(",") == 1 and ("." in s or re.search(r",\s", s)):
        bagian = s.split(",")
    else:
        bagian = re.sub(r"(\d),(\d)", r"\1.\2", s).split()
    bagian = [b.strip() for b in bagian if b.strip()]
    if len(bagian) != 2:
        raise KoordinatError("Masukkan dua nilai: lintang dan bujur, contoh: -6.175392, 106.827153")
    return bagian[0], bagian[1]


# --- DMS <-> DD -----------------------------------------------------------------
_ARAH = {
    "N": ("lat", 1), "U": ("lat", 1), "LU": ("lat", 1),
    "S": ("lat", -1), "LS": ("lat", -1),
    "E": ("lon", 1), "T": ("lon", 1), "BT": ("lon", 1),
    "W": ("lon", -1), "B": ("lon", -1), "BB": ("lon", -1),
}
_GANTI_SIMBOL = {"º": "°", "˚": "°", "′": "'", "’": "'", "‘": "'", "´": "'",
                 "″": '"', "”": '"', "“": '"', "''": '"'}


def dms_ke_dd(teks: str) -> Tuple[float, Optional[str]]:
    """Parse DMS fleksibel -> (derajat desimal, sumbu 'lat'/'lon'/None).

    Contoh yang diterima: 6°10'31.4"S, -6 10 31.4, 6° 10' 31,4" LS,
    106°49'37" BT, S 6 10 31.4, 6:10:31.4 S, 6°10.523' S, -6.175392.
    """
    s = str(teks).strip().upper()
    if not s:
        raise KoordinatError("Koordinat kosong.")
    for lama, baru in _GANTI_SIMBOL.items():
        s = s.replace(lama, baru)
    huruf = re.findall(r"[A-Z]+", s)
    if len(huruf) > 1:
        raise KoordinatError(f"Arah ganda/tidak dikenal pada '{teks}'.")
    sumbu, faktor = None, 1
    if huruf:
        if huruf[0] not in _ARAH:
            raise KoordinatError(f"Arah '{huruf[0]}' tidak dikenal. Pakai LU/LS/BT/BB atau N/S/E/W.")
        sumbu, faktor = _ARAH[huruf[0]]
        s = s.replace(huruf[0], " ")
    negatif = s.lstrip().startswith("-")
    s = re.sub(r"(\d),(\d)", r"\1.\2", s)  # koma desimal
    angka = re.findall(r"\d+(?:\.\d+)?", s)
    sisa = re.sub(r"\d+(?:\.\d+)?", " ", s)
    digit_pertama = re.search(r"\d", s)
    tanda_lain = digit_pertama and re.search(r"[+\-]", s[digit_pertama.start():])  # +/- hanya di depan
    if not angka or len(angka) > 3 or re.search(r"[^\s°'\":+\-]", sisa) or tanda_lain:
        raise KoordinatError(f"Format koordinat '{teks}' tidak dikenali.")
    if negatif and faktor == 1 and huruf:
        raise KoordinatError(f"Tanda minus bertentangan dengan arah {huruf[0]} pada '{teks}'.")
    if any("." in a for a in angka[:-1]):
        raise KoordinatError("Hanya komponen terakhir (menit/detik) yang boleh berdesimal.")
    nilai = [float(a) for a in angka] + [0.0, 0.0]
    d, m, dt = nilai[0], nilai[1], nilai[2]
    if m >= 60 or dt >= 60:
        raise KoordinatError("Menit dan detik harus kurang dari 60.")
    hasil = d + m / 60 + dt / 3600
    if negatif or faktor < 0:
        hasil = -hasil
    batas = 90 if sumbu == "lat" else 180
    if abs(hasil) > batas:
        nama = "Lintang" if sumbu == "lat" else "Bujur"
        raise KoordinatError(f"{nama} {abs(hasil):.6f}° melebihi batas {batas}°.")
    return hasil, sumbu


def dd_ke_dms(nilai: float, sumbu: str = "lat", presisi: int = 2) -> Tuple[int, int, float, str]:
    """Derajat desimal -> (derajat, menit, detik, arah N/S/E/W)."""
    if sumbu not in ("lat", "lon"):
        raise KoordinatError("Sumbu harus 'lat' atau 'lon'.")
    _cek_lat_lon(nilai, 0.0) if sumbu == "lat" else _cek_lat_lon(0.0, nilai)
    if not 0 <= presisi <= 8:
        raise KoordinatError("Presisi detik harus 0 sampai 8 desimal.")
    skala = 10**presisi
    unit = round(abs(nilai) * 3600 * skala)  # bilangan bulat -> bebas galat 59,999"
    d, sisa = divmod(unit, 3600 * skala)
    m, s_unit = divmod(sisa, 60 * skala)
    arah = ("N" if nilai >= 0 else "S") if sumbu == "lat" else ("E" if nilai >= 0 else "W")
    return int(d), int(m), s_unit / skala, arah


def format_dms(nilai: float, sumbu: str = "lat", presisi: int = 2, gaya: str = "id") -> str:
    """Format DMS, gaya 'id' (6°10'31,40" LS) atau 'en' (6°10'31.40" S)."""
    d, m, s, arah = dd_ke_dms(nilai, sumbu, presisi)
    detik = f"{s:0{3 + presisi if presisi else 2}.{presisi}f}"
    if gaya == "id":
        detik = detik.replace(".", ",")
        arah = {"N": "LU", "S": "LS", "E": "BT", "W": "BB"}[arah]
    return f"{d}°{m:02d}'{detik}\" {arah}"


# --- DD <-> UTM (Krüger/Karney) -------------------------------------------------
def dd_ke_utm(lat: float, lon: float, zona: Optional[int] = None) -> UTM:
    """Lintang/bujur WGS84 (derajat desimal) -> koordinat UTM."""
    _cek_lat_lon(lat, lon)
    band = band_lintang(lat)
    if zona is None:
        zona = zona_utm(lat, lon)
    elif not 1 <= zona <= 60:
        raise KoordinatError("Zona UTM harus 1 sampai 60.")
    dlon = (lon - meridian_tengah(zona) + 180) % 360 - 180
    if abs(dlon) > 9:
        raise KoordinatError(f"Titik terlalu jauh ({dlon:.1f}°) dari meridian tengah zona {zona}.")
    phi, lam = math.radians(lat), math.radians(dlon)
    tau = math.tan(phi)
    sigma = math.sinh(E_ECC * math.atanh(E_ECC * tau / math.sqrt(1 + tau * tau)))
    taup = tau * math.sqrt(1 + sigma * sigma) - sigma * math.sqrt(1 + tau * tau)
    xip = math.atan2(taup, math.cos(lam))
    etap = math.asinh(math.sin(lam) / math.sqrt(taup * taup + math.cos(lam) ** 2))
    xi, eta = xip, etap
    for j, a in enumerate(ALPHA, start=1):
        xi += a * math.sin(2 * j * xip) * math.cosh(2 * j * etap)
        eta += a * math.cos(2 * j * xip) * math.sinh(2 * j * etap)
    hemisfer = "N" if lat >= 0 else "S"
    easting = FALSE_EASTING + K0 * A_RECT * eta
    northing = K0 * A_RECT * xi + (FALSE_NORTHING_SELATAN if hemisfer == "S" else 0.0)
    return UTM(zona, hemisfer, easting, northing, band)


def parse_hemisfer(teks: str) -> str:
    t = str(teks).strip().upper()
    if t in ("N", "U", "UTARA", "NORTH", "LU"):
        return "N"
    if t in ("S", "SELATAN", "SOUTH", "LS"):
        return "S"
    raise KoordinatError(f"Hemisfer '{teks}' tidak dikenal. Pakai N/U (utara) atau S (selatan).")


def parse_zona(teks: str, hemisfer: Optional[str] = None) -> Tuple[int, str, Optional[str]]:
    """Parse '48', '48S', '48M' -> (zona, hemisfer, catatan)."""
    m = re.fullmatch(r"\s*(\d{1,2})\s*([A-Za-z]?)\s*", str(teks))
    if not m:
        raise KoordinatError(f"Zona '{teks}' tidak valid. Contoh: 48, 48S, atau 48M.")
    zona, huruf, catatan = int(m.group(1)), m.group(2).upper(), None
    if not 1 <= zona <= 60:
        raise KoordinatError("Zona UTM harus 1 sampai 60.")
    if hemisfer:
        return zona, parse_hemisfer(hemisfer), None
    if not huruf:
        raise KoordinatError("Hemisfer belum diisi. Tulis N (utara) atau S (selatan), mis. 48S.")
    if huruf == "S":
        catatan = "Huruf 'S' dibaca sebagai Selatan (bukan band S MGRS)."
        return zona, "S", catatan
    if huruf not in HURUF_BAND:
        raise KoordinatError(f"Huruf '{huruf}' bukan hemisfer maupun band lintang yang valid.")
    return zona, ("N" if huruf >= "N" else "S"), None


def utm_ke_dd(zona: int, hemisfer: str, easting: float, northing: float) -> Tuple[float, float]:
    """Koordinat UTM -> (lintang, bujur) derajat desimal WGS84."""
    if not 1 <= zona <= 60:
        raise KoordinatError("Zona UTM harus 1 sampai 60.")
    hemisfer = parse_hemisfer(hemisfer)
    if not 0 < easting < 1000000:
        raise KoordinatError("Easting harus di antara 0 dan 1.000.000 m (umumnya 160.000-840.000 m).")
    if not 0 <= northing <= 10000000:
        raise KoordinatError("Northing harus di antara 0 dan 10.000.000 m.")
    y = northing - (FALSE_NORTHING_SELATAN if hemisfer == "S" else 0.0)
    xi, eta = y / (K0 * A_RECT), (easting - FALSE_EASTING) / (K0 * A_RECT)
    xip, etap = xi, eta
    for j, b in enumerate(BETA, start=1):
        xip -= b * math.sin(2 * j * xi) * math.cosh(2 * j * eta)
        etap -= b * math.cos(2 * j * xi) * math.sinh(2 * j * eta)
    sinh_etap, cos_xip = math.sinh(etap), math.cos(xip)
    taup = math.sin(xip) / math.sqrt(sinh_etap**2 + cos_xip**2)
    tau = taup  # iterasi Newton untuk lintang dari lintang konformal
    e2 = E_ECC * E_ECC
    for _ in range(10):
        sigma = math.sinh(E_ECC * math.atanh(E_ECC * tau / math.sqrt(1 + tau * tau)))
        taui = tau * math.sqrt(1 + sigma * sigma) - sigma * math.sqrt(1 + tau * tau)
        dtau = ((taup - taui) / math.sqrt(1 + taui * taui)
                * (1 + (1 - e2) * tau * tau) / ((1 - e2) * math.sqrt(1 + tau * tau)))
        tau += dtau
        if abs(dtau) < 1e-14:
            break
    lat = math.degrees(math.atan(tau))
    lon = math.degrees(math.atan2(sinh_etap, cos_xip)) + meridian_tengah(zona)
    lon = (lon + 180) % 360 - 180
    return lat, lon


# --- Format angka Indonesia ------------------------------------------------------
def fmt_angka(x: float, desimal: int = 2) -> str:
    """1234567.891 -> '1.234.567,89'."""
    s = f"{x:,.{desimal}f}"
    return s.replace(",", "_").replace(".", ",").replace("_", ".")


def _fmt_csv(x: float, desimal: int, koma: bool) -> str:
    s = f"{x:.{desimal}f}"
    return s.replace(".", ",") if koma else s


# --- Batch CSV ---------------------------------------------------------------------
_KOLOM = {
    "lat": ("lat", "latitude", "lintang"),
    "lon": ("lon", "lng", "long", "longitude", "bujur"),
    "zona": ("zona", "zone", "utm_zona"),
    "hemisfer": ("hemisfer", "hemisphere", "hemi", "utm_hemisfer"),
    "easting": ("easting", "x", "e", "utm_easting"),
    "northing": ("northing", "y", "n", "utm_northing"),
}
MODE_CSV = ("dms2dd", "dd2dms", "dd2utm", "utm2dd")


def _cari_kolom(header: List[str], kunci: str) -> Optional[str]:
    peta = {h.strip().lower(): h for h in header}
    for nama in _KOLOM[kunci]:
        if nama in peta:
            return peta[nama]
    return None


def proses_baris(baris: Dict[str, str], kolom: Dict[str, Optional[str]], mode: str,
                 presisi: int, koma: bool) -> Dict[str, str]:
    """Konversi satu baris CSV; kembalikan kolom-kolom hasil."""
    if mode in ("dms2dd", "dd2dms", "dd2utm"):
        lat_t, lon_t = baris[kolom["lat"]], baris[kolom["lon"]]
        if mode == "dms2dd":
            lat, _ = dms_ke_dd(lat_t)
            lon, _ = dms_ke_dd(lon_t)
            _cek_lat_lon(lat, lon)
            return {"lat_dd": _fmt_csv(lat, 8, koma), "lon_dd": _fmt_csv(lon, 8, koma)}
        lat, lon = parse_angka(lat_t), parse_angka(lon_t)
        _cek_lat_lon(lat, lon)
        if mode == "dd2dms":
            return {"lat_dms": format_dms(lat, "lat", presisi, "id" if koma else "en"),
                    "lon_dms": format_dms(lon, "lon", presisi, "id" if koma else "en")}
        u = dd_ke_utm(lat, lon)
        return {"utm_zona": str(u.zona), "utm_hemisfer": u.hemisfer, "utm_band": u.band,
                "utm_easting": _fmt_csv(u.easting, 3, koma),
                "utm_northing": _fmt_csv(u.northing, 3, koma)}
    hemi = baris.get(kolom["hemisfer"]) if kolom["hemisfer"] else None
    zona, hemisfer, _ = parse_zona(baris[kolom["zona"]], hemi or None)
    lat, lon = utm_ke_dd(zona, hemisfer, parse_angka(baris[kolom["easting"]]),
                         parse_angka(baris[kolom["northing"]]))
    return {"lat_dd": _fmt_csv(lat, 8, koma), "lon_dd": _fmt_csv(lon, 8, koma)}


def proses_csv(path_masuk: str, path_keluar: str, mode: str, presisi: int = 2) -> Tuple[int, int]:
    """Konversi seluruh baris CSV; hasil ditulis ke path_keluar. Return (sukses, gagal)."""
    if mode not in MODE_CSV:
        raise KoordinatError(f"Mode '{mode}' tidak dikenal. Pilih: {', '.join(MODE_CSV)}.")
    try:
        with open(path_masuk, newline="", encoding="utf-8-sig") as f:
            sampel = f.read(4096)
            f.seek(0)
            try:
                dialek = csv.Sniffer().sniff(sampel, delimiters=",;\t")
            except csv.Error:
                dialek = csv.excel
            pembaca = csv.DictReader(f, dialect=dialek)
            header = list(pembaca.fieldnames or [])
            semua = list(pembaca)
    except OSError as e:
        raise KoordinatError(f"Tidak bisa membaca file '{path_masuk}': {e.strerror}.") from None
    perlu = ("lat", "lon") if mode != "utm2dd" else ("zona", "easting", "northing")
    kolom = {k: _cari_kolom(header, k) for k in _KOLOM}
    hilang = [k for k in perlu if not kolom[k]]
    if hilang:
        raise KoordinatError(f"Kolom wajib tidak ditemukan: {', '.join(hilang)}. Header: {header}")
    koma = dialek.delimiter == ";"  # CSV titik-koma (Excel Indonesia) -> koma desimal
    keluaran, sukses, gagal = [], 0, 0
    for baris in semua:
        try:
            hasil = proses_baris(baris, kolom, mode, presisi, koma)
            hasil["galat"] = ""
            sukses += 1
        except (KoordinatError, KeyError, TypeError) as e:
            hasil = {"galat": str(e)}
            gagal += 1
        keluaran.append({**baris, **hasil})
    kolom_baru = [k for r in keluaran for k in r if k not in header]
    kolom_akhir = header + list(dict.fromkeys(kolom_baru))
    with open(path_keluar, "w", newline="", encoding="utf-8-sig") as f:
        penulis = csv.DictWriter(f, fieldnames=kolom_akhir, delimiter=dialek.delimiter)
        penulis.writeheader()
        penulis.writerows(keluaran)
    return sukses, gagal


# --- Tampilan ------------------------------------------------------------------------
def teks_utm(lat: float, lon: float, zona: Optional[int] = None) -> str:
    u = dd_ke_utm(lat, lon, zona)
    nama_hemi = "utara" if u.hemisfer == "N" else "selatan"
    cm = meridian_tengah(u.zona)
    epsg = kode_epsg(u.zona, u.hemisfer)
    baris = [
        f"Koordinat     : {fmt_angka(lat, 6)}°, {fmt_angka(lon, 6)}°",
        f"Zona UTM      : {u.zona} {nama_hemi.capitalize()} ({u.zona}{u.hemisfer}), band lintang "
        f"{u.zona}{u.band}, meridian tengah {abs(cm)}° {'BT' if cm >= 0 else 'BB'}",
        f"Easting  (X)  : {fmt_angka(u.easting, 2)} m",
        f"Northing (Y)  : {fmt_angka(u.northing, 2)} m",
        f"EPSG          : {epsg['wgs84']} (WGS 84 / UTM zone {u.zona}{u.hemisfer})"
        + (f", {epsg['srgi2013']} (SRGI2013)" if epsg["srgi2013"] else ""),
    ]
    return "\n".join(baris)


def teks_dd(lat: float, lon: float, presisi: int = 2) -> str:
    return "\n".join([
        f"Lintang (DD)  : {fmt_angka(lat, 8)}°  ->  {format_dms(lat, 'lat', presisi)}",
        f"Bujur   (DD)  : {fmt_angka(lon, 8)}°  ->  {format_dms(lon, 'lon', presisi)}",
        f"Google Maps   : {lat:.6f}, {lon:.6f}",
    ])


def _lat_lon_dari_args(nilai: List[str]) -> Tuple[float, float]:
    if len(nilai) == 1:
        nilai = list(pisah_pasangan(nilai[0]))
    if len(nilai) != 2:
        raise KoordinatError("Masukkan lintang dan bujur (2 nilai).")
    lat, lon = parse_angka(nilai[0]), parse_angka(nilai[1])
    _cek_lat_lon(lat, lon)
    return lat, lon


def _dms_pasangan(nilai: List[str]) -> List[Tuple[float, str]]:
    hasil = []
    for i, t in enumerate(nilai):
        dd, sumbu = dms_ke_dd(t)
        hasil.append((dd, sumbu or ("lat" if i == 0 else "lon")))
    return hasil


def jalankan_perintah(args: argparse.Namespace) -> str:
    if args.perintah == "dms2dd":
        if not 1 <= len(args.nilai) <= 2:
            raise KoordinatError("Masukkan 1 atau 2 koordinat DMS.")
        hasil = _dms_pasangan(args.nilai)
        teks = [f"{t!s:<22} -> {fmt_angka(dd, 8)}° ({'lintang' if s == 'lat' else 'bujur'})"
                for t, (dd, s) in zip(args.nilai, hasil)]
        if len(hasil) == 2:
            teks.append(f"Google Maps   : {hasil[0][0]:.6f}, {hasil[1][0]:.6f}")
        return "\n".join(teks)
    lat_lon = _lat_lon_dari_args(args.nilai) if args.perintah in ("dd2dms", "dd2utm") else None
    if args.perintah == "dd2dms":
        return teks_dd(lat_lon[0], lat_lon[1], args.presisi)
    if args.perintah == "dd2utm":
        return teks_utm(lat_lon[0], lat_lon[1], args.zona)
    zona, hemi, catatan = parse_zona(args.zona_utm, args.hemisfer)
    lat, lon = utm_ke_dd(zona, hemi, parse_angka(args.easting), parse_angka(args.northing))
    return (f"Catatan: {catatan}\n" if catatan else "") + teks_dd(lat, lon, args.presisi)


def mode_interaktif() -> None:
    print("=== Konversi Koordinat: DMS • Desimal • UTM (WGS84) ===")
    menu = ("\n1. DMS -> Desimal\n2. Desimal -> DMS\n3. Desimal -> UTM\n"
            "4. UTM -> Desimal\n5. Batch CSV\n0. Keluar")
    while True:
        print(menu)
        pilihan = input("Pilih menu: ").strip()
        try:
            if pilihan == "0":
                print("Sampai jumpa!")
                return
            if pilihan == "1":
                lat, _ = dms_ke_dd(input("Lintang DMS (mis. 6°10'31,4\" LS): "))
                lon, _ = dms_ke_dd(input("Bujur DMS  (mis. 106°49'37\" BT): "))
                _cek_lat_lon(lat, lon)
                print("\n" + teks_dd(lat, lon))
            elif pilihan in ("2", "3"):
                lat, lon = _lat_lon_dari_args([input("Lintang, bujur (mis. -6.175392, 106.827153): ")])
                if pilihan == "2":
                    p = input("Presisi detik [2]: ").strip()
                    print("\n" + teks_dd(lat, lon, int(p) if p else 2))
                else:
                    print("\n" + teks_utm(lat, lon))
            elif pilihan == "4":
                zona_t = input("Zona (mis. 48S / 48M / 49N): ")
                zona, hemi, catatan = parse_zona(zona_t, None if re.search(r"[A-Za-z]", zona_t)
                                                 else input("Hemisfer (N/S): "))
                e = parse_angka(input("Easting (m): "))
                n = parse_angka(input("Northing (m): "))
                lat, lon = utm_ke_dd(zona, hemi, e, n)
                print(("\nCatatan: " + catatan) if catatan else "")
                print(teks_dd(lat, lon))
            elif pilihan == "5":
                masuk = input("File CSV masukan: ").strip()
                mode = input(f"Mode ({'/'.join(MODE_CSV)}): ").strip().lower()
                keluar = _nama_keluaran(masuk)
                ok, gagal = proses_csv(masuk, keluar, mode)
                print(f"\nSelesai: {ok} baris berhasil, {gagal} gagal -> {keluar}")
            else:
                print("Pilihan tidak dikenal.")
        except (KoordinatError, ValueError) as e:
            print(f"\nGalat: {e}")


def _nama_keluaran(path: str) -> str:
    dasar, _ = os.path.splitext(path)
    return f"{dasar}_hasil.csv"


class ParserID(argparse.ArgumentParser):
    """ArgumentParser dengan pesan galat berbahasa Indonesia."""

    _TERJEMAHAN = (("the following arguments are required", "argumen wajib belum diisi"),
                   ("unrecognized arguments", "argumen tidak dikenal"),
                   ("invalid choice", "pilihan tidak valid"),
                   ("choose from", "pilih dari"),
                   ("expected one argument", "butuh satu nilai"),
                   ("expected at least one argument", "butuh minimal satu nilai"),
                   ("invalid int value", "bukan bilangan bulat"),
                   ("argument ", "argumen "))

    def error(self, message: str) -> None:  # type: ignore[override]
        for en, idn in self._TERJEMAHAN:
            message = message.replace(en, idn)
        print(f"Galat: {message}\nKetik '{self.prog} --help' untuk bantuan.", file=sys.stderr)
        sys.exit(2)


def buat_parser() -> argparse.ArgumentParser:
    p = ParserID(
        prog="konversi_koordinat.py",
        description="Konversi koordinat DMS <-> desimal <-> UTM (WGS84/SRGI2013). "
                    "Tanpa argumen = mode interaktif.")
    p.add_argument("--csv", help="file CSV untuk konversi massal")
    p.add_argument("--mode", choices=MODE_CSV, help="mode konversi CSV")
    p.add_argument("--output", help="file CSV hasil (default: <nama>_hasil.csv)")
    p.add_argument("--presisi", type=int, default=2, help="jumlah desimal detik (default 2)")
    sub = p.add_subparsers(dest="perintah", metavar="PERINTAH")
    s = sub.add_parser("dms2dd", help="DMS -> derajat desimal")
    s.add_argument("nilai", nargs="+", help="1-2 koordinat DMS, mis. \"6°10'31.4\\\"S\"")
    s = sub.add_parser("dd2dms", help="derajat desimal -> DMS")
    s.add_argument("nilai", nargs="+", help="lintang bujur, mis. -6.175392 106.827153")
    s.add_argument("--presisi", type=int, default=2, help="jumlah desimal detik")
    s = sub.add_parser("dd2utm", help="derajat desimal -> UTM")
    s.add_argument("nilai", nargs="+", help="lintang bujur")
    s.add_argument("--zona", type=int, help="paksa zona tertentu (opsional)")
    s = sub.add_parser("utm2dd", help="UTM -> derajat desimal")
    s.add_argument("zona_utm", help="zona, mis. 48 / 48S / 48M")
    s.add_argument("easting")
    s.add_argument("northing")
    s.add_argument("--hemisfer", help="N (utara) atau S (selatan)")
    s.add_argument("--presisi", type=int, default=2, help="jumlah desimal detik")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        if not argv:
            mode_interaktif()
            return 0
        args = buat_parser().parse_args(argv)
        if args.csv:
            if not args.mode:
                raise KoordinatError("Opsi --mode wajib diisi bersama --csv.")
            keluar = args.output or _nama_keluaran(args.csv)
            ok, gagal = proses_csv(args.csv, keluar, args.mode, args.presisi)
            print(f"Selesai: {ok} baris berhasil, {gagal} baris gagal -> {keluar}")
            return 1 if gagal else 0
        if not args.perintah:
            buat_parser().print_help()
            return 2
        print(jalankan_perintah(args))
        return 0
    except KoordinatError as e:
        print(f"Galat: {e}", file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nDibatalkan.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
