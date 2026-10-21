# Konversi Koordinat — DMS, Desimal & UTM ke Latitude Longitude (Python)

**Konversi koordinat** dari derajat-menit-detik (DMS) ke desimal, dari desimal ke DMS, dari koordinat geografis ke UTM, dan dari UTM kembali ke latitude longitude bisa Anda lakukan dalam satu perintah dengan tool gratis ini. Cocok untuk mahasiswa geodesi, surveyor, atau siapa pun yang perlu konversi koordinat derajat ke desimal sebelum menempelkannya di Google Maps. Hasil UTM akurat sampai tingkat milimeter (sudah dicocokkan dengan pustaka PROJ), ratusan titik bisa diproses sekaligus dari file CSV, dan semuanya berjalan offline dengan Python biasa.

> 🛠️ Tool gratis & open source ini adalah karya **[JoinBareng](https://joinbareng.com)** — platform patungan langganan premium di Indonesia.

## Daftar Isi

- [Apa Itu Konversi Koordinat?](#apa-itu-konversi-koordinat)
- [Fitur](#fitur)
- [Cara Install & Menjalankan](#cara-install--menjalankan)
- [Cara Pakai dan Contoh Output](#cara-pakai-dan-contoh-output)
- [Rumus Konversi Koordinat & Contoh Hitung Manual](#rumus-konversi-koordinat--contoh-hitung-manual)
- [Tabel Zona UTM Indonesia (46–54)](#tabel-zona-utm-indonesia-4654)
- [Memahami LU, LS, BT, BB, Hemisfer, dan Band](#memahami-lu-ls-bt-bb-hemisfer-dan-band)
- [Kapan Memakai UTM dan Kapan Koordinat Geografis](#kapan-memakai-utm-dan-kapan-koordinat-geografis)
- [Datum: WGS84 dan SRGI2013](#datum-wgs84-dan-srgi2013)
- [Tips & Kesalahan Umum](#tips--kesalahan-umum)
- [FAQ](#faq)
- [Metodologi, Pengujian & Sumber](#metodologi-pengujian--sumber)
- [Tentang Pembuat](#tentang-pembuat)
- [Disclaimer](#disclaimer)
- [Kontribusi](#kontribusi)
- [Lisensi](#lisensi)
- [Dukung Proyek Ini](#dukung-proyek-ini)
- [Tools Lainnya dari Seri Ini](#tools-lainnya-dari-seri-ini)

## Apa Itu Konversi Koordinat?

Satu titik di bumi bisa ditulis dengan beberapa cara. Tugu Monas bisa ditulis `6°10'31,41" LS 106°49'37,75" BT` (DMS), `-6.175392, 106.827153` (derajat desimal, format Google Maps), atau `48S 702178 mE 9317060 mN` (UTM). Ketiganya menunjuk tempat yang sama.

Konversi koordinat adalah proses mengubah satu format ke format lain tanpa memindahkan titiknya. Laporan lapangan lama sering memakai DMS, GPS genggam bisa diatur ke UTM, sedangkan aplikasi peta memakai desimal. Salah konversi bisa membuat titik meleset jauh, bahkan pindah ke belahan bumi lain.

Tool ini menangani empat arah konversi titik koordinat yang paling sering dibutuhkan di Indonesia: DMS → desimal, desimal → DMS, geografis → UTM, dan UTM → geografis.

## Fitur

- **Parser DMS fleksibel**: `6°10'31.4"S`, `-6 10 31.4`, `6° 10' 31,4" LS`, `6:10:31.4 S`, atau menit desimal `3 35,712 LU`. Arah LU/LS/BT/BB maupun N/S/E/W dan koma desimal dikenali.
- **Konversi koordinat desimal ke derajat** dengan pembulatan aman (tidak pernah muncul `59'60"`).
- **Konversi koordinat UTM akurat milimeter** memakai seri Krüger orde n⁶ (Karney, 2011), lengkap dengan zona, hemisfer, band, meridian tengah, dan kode EPSG.
- **Zona bisa dipaksa** (`--zona`) untuk proyek yang melewati batas zona.
- **Batch CSV** (koma maupun titik-koma ala Excel Indonesia); baris salah ditandai di kolom `galat`.
- **Mode interaktif** berbahasa Indonesia, **tanpa dependency** (Python 3.8+).

## Cara Install & Menjalankan

Pastikan Python 3.8 atau lebih baru sudah terpasang (`python3 --version`), lalu:

```bash
git clone https://github.com/redyopa2929/konversi-koordinat.git
cd konversi-koordinat
python3 konversi_koordinat.py
```

Perintah terakhir membuka mode interaktif. Daftar opsi lengkap bisa dilihat dengan `python3 konversi_koordinat.py --help`.

## Cara Pakai dan Contoh Output

Semua output di bawah ini adalah hasil asli menjalankan tool.

### Konversi koordinat derajat ke desimal (DMS → DD)

```text
$ python3 konversi_koordinat.py dms2dd "6°10'31.4\"S" "106°49'37\" BT"
6°10'31.4"S            -> -6,17538889° (lintang)
106°49'37" BT          -> 106,82694444° (bujur)
Google Maps   : -6.175389, 106.826944
```

Baris `Google Maps` sengaja memakai titik desimal agar bisa langsung ditempel ke kolom pencarian peta.

### Konversi koordinat desimal ke derajat (DD → DMS)

```text
$ python3 konversi_koordinat.py dd2dms -6.175392 106.827153 --presisi 3
Lintang (DD)  : -6,17539200°  ->  6°10'31,411" LS
Bujur   (DD)  : 106,82715300°  ->  106°49'37,751" BT
Google Maps   : -6.175392, 106.827153
```

### Konversi geografis ke UTM

```text
$ python3 konversi_koordinat.py dd2utm -6.175392 106.827153
Koordinat     : -6,175392°, 106,827153°
Zona UTM      : 48 Selatan (48S), band lintang 48M, meridian tengah 105° BT
Easting  (X)  : 702.178,12 m
Northing (Y)  : 9.317.060,29 m
EPSG          : 32748 (WGS 84 / UTM zone 48S), 9488 (SRGI2013)
```

Untuk konversi koordinat langsung dari Google Maps, pasangan lintang-bujur boleh ditempel dalam satu argumen. Contoh berikut sekaligus memaksa zona 49:

```text
$ python3 konversi_koordinat.py dd2utm "-6.175392, 106.827153" --zona 49
Koordinat     : -6,175392°, 106,827153°
Zona UTM      : 49 Selatan (49S), band lintang 49M, meridian tengah 111° BT
Easting  (X)  : 37.941,25 m
Northing (Y)  : 9.315.594,74 m
EPSG          : 32749 (WGS 84 / UTM zone 49S), 9489 (SRGI2013)
```

Easting-nya jauh dari 500.000 m karena Monas berada sekitar 4° dari meridian tengah zona 49. Distorsinya sudah besar, jadi pakai zona paksa hanya bila proyek menuntutnya.

### Konversi UTM ke geografis (latitude longitude)

```text
$ python3 konversi_koordinat.py utm2dd 48S 702178.12 9317060.29
Catatan: Huruf 'S' dibaca sebagai Selatan (bukan band S MGRS).
Lintang (DD)  : -6,17539196°  ->  6°10'31,41" LS
Bujur   (DD)  : 106,82715298°  ->  106°49'37,75" BT
Google Maps   : -6.175392, 106.827153
```

Zona boleh ditulis `48`, `48S`, atau `48M` (huruf band). Jika hanya angka, tambahkan `--hemisfer S` atau `--hemisfer N`.

### Batch CSV

File `titik.csv` (format Excel Indonesia):

```text
nama;lat;lon
Monas;-6,175392;106,827153
Titik salah;-95;106
Tugu Yogyakarta;-7,782889;110,367083
```

```text
$ python3 konversi_koordinat.py --csv titik.csv --mode dd2utm
Selesai: 2 baris berhasil, 1 baris gagal -> titik_hasil.csv
```

Isi `titik_hasil.csv`:

```text
nama;lat;lon;utm_zona;utm_hemisfer;utm_band;utm_easting;utm_northing;galat
Monas;-6,175392;106,827153;48;S;M;702178,123;9317060,286;
Titik salah;-95;106;;;;;;"Lintang -95.0 tidak valid; harus di antara -90 dan 90."
Tugu Yogyakarta;-7,782889;110,367083;49;S;M;430215,282;9139651,784;
```

Mode lain: `dms2dd`, `dd2dms`, dan `utm2dd`. Kolom dikenali secara longgar (`lat`/`lintang`, `lon`/`bujur`, `zona`, `hemisfer`, `easting`, `northing`). Bila ada baris gagal, exit code bernilai 1.

### Mode interaktif

```text
=== Konversi Koordinat: DMS • Desimal • UTM (WGS84) ===

1. DMS -> Desimal
2. Desimal -> DMS
3. Desimal -> UTM
4. UTM -> Desimal
5. Batch CSV
0. Keluar
Pilih menu: 3
Lintang, bujur (mis. -6.175392, 106.827153): -7.797068, 110.370529

Koordinat     : -7,797068°, 110,370529°
Zona UTM      : 49 Selatan (49S), band lintang 49M, meridian tengah 111° BT
Easting  (X)  : 430.597,58 m
Northing (Y)  : 9.138.084,76 m
EPSG          : 32749 (WGS 84 / UTM zone 49S), 9489 (SRGI2013)
```

## Rumus Konversi Koordinat & Contoh Hitung Manual

### DMS ke desimal

Satu derajat berisi 60 menit, dan satu menit berisi 60 detik:

```text
DD = derajat + menit/60 + detik/3600
```

Hasilnya diberi tanda negatif untuk LS dan BB. Contoh `6°10'31,4" LS`:

1. 10 ÷ 60 = 0,166667
2. 31,4 ÷ 3.600 = 0,008722
3. 6 + 0,166667 + 0,008722 = 6,175389
4. Karena LS, hasilnya **−6,175389**

### Desimal ke DMS

Ambil bagian bulat sebagai derajat, lalu kalikan sisa pecahan dengan 60 secara berulang. Contoh `106,827153` (positif berarti BT):

1. Derajat = 106, sisa 0,827153
2. 0,827153 × 60 = 49,62918, jadi menit = 49, sisa 0,62918
3. 0,62918 × 60 = 37,7508, jadi detik = 37,75
4. Hasil: **106°49'37,75" BT**

Di dalam kode, detik dihitung sebagai bilangan bulat (misalnya per seratus detik), sehingga tidak pernah muncul "60 detik".

### Menentukan zona UTM

```text
zona            = floor((bujur + 180) / 6) + 1
meridian tengah = 6 × zona − 183
```

Untuk Monas, (106,827 + 180) ÷ 6 = 47,80. Dibulatkan ke bawah menjadi 47, lalu ditambah 1, sehingga zonanya **48**. Meridian tengahnya 6 × 48 − 183 = **105° BT**.

### Rumus UTM (Transverse Mercator)

UTM adalah proyeksi Transverse Mercator dengan faktor skala k₀ = 0,9996 di meridian tengah, false easting 500.000 m, dan false northing 10.000.000 m di selatan ekuator. Tool ini memakai **seri Krüger** sebagaimana dijabarkan Karney (2011):

```text
n  = f / (2 − f)                     f = 1/298,257223563 (WGS84)
A  = a/(1+n) · (1 + n²/4 + n⁴/64 + n⁶/256)
τ' = lintang konformal (dari tan φ dan eksentrisitas e)
ξ' = atan2(τ', cos λ)      η' = asinh(sin λ / √(τ'² + cos²λ))
ξ  = ξ' + Σ αⱼ sin(2jξ') cosh(2jη')
η  = η' + Σ αⱼ cos(2jξ') sinh(2jη')         j = 1…6
E  = 500000 + k₀·A·η
N  = k₀·A·ξ  (+ 10000000 bila di selatan ekuator)
```

λ adalah selisih bujur terhadap meridian tengah. Arah sebaliknya memakai koefisien βⱼ dan iterasi Newton. Menurut Karney, galat seri orde n⁶ ini di bawah 5 nanometer hingga 3.900 km dari meridian tengah, jadi yang membatasi akurasi adalah kualitas data Anda sendiri.

## Tabel Zona UTM Indonesia (46–54)

Wilayah Indonesia membentang kira-kira dari 95° BT sampai 141° BT, sehingga tercakup sembilan zona UTM: 46 sampai 54. Contoh kota di bawah ini dihitung ulang dengan tool ini.

| Zona | Rentang bujur | Meridian tengah | EPSG WGS 84 (N/S) | EPSG SRGI2013 (N/S) | Contoh wilayah |
|---|---|---|---|---|---|
| 46 | 90°–96° BT | 93° BT | 32646 / 32746 | 9476 / – | Sabang, Banda Aceh |
| 47 | 96°–102° BT | 99° BT | 32647 / 32747 | 9477 / 9487 | Medan, Padang |
| 48 | 102°–108° BT | 105° BT | 32648 / 32748 | 9478 / 9488 | Palembang, Jakarta, Bandung |
| 49 | 108°–114° BT | 111° BT | 32649 / 32749 | 9479 / 9489 | Pontianak, Semarang, Surabaya |
| 50 | 114°–120° BT | 117° BT | 32650 / 32750 | 9480 / 9490 | Denpasar, Balikpapan, Makassar |
| 51 | 120°–126° BT | 123° BT | 32651 / 32751 | 9481 / 9491 | Kupang, Manado |
| 52 | 126°–132° BT | 129° BT | 32652 / 32752 | 9482 / 9492 | Ambon, Sorong |
| 53 | 132°–138° BT | 135° BT | 32653 / 32753 | – / 9493 | Manokwari, Timika |
| 54 | 138°–144° BT | 141° BT | 32654 / 32754 | – / 9494 | Jayapura, Merauke |

Kode EPSG SRGI2013 diambil dari basis data EPSG di PROJ 9.8.1, yang hanya memuat kombinasi zona–hemisfer yang mencakup wilayah Indonesia.

## Memahami LU, LS, BT, BB, Hemisfer, dan Band

- **LU (Lintang Utara)** sama dengan N dan bernilai positif, misalnya Medan dan Manado.
- **LS (Lintang Selatan)** sama dengan S dan bernilai negatif, misalnya Jakarta dan Kupang.
- **BT (Bujur Timur)** sama dengan E dan bernilai positif. Seluruh Indonesia berada di BT.
- **BB (Bujur Barat)** sama dengan W dan bernilai negatif. Tidak dipakai untuk wilayah Indonesia.

**Hemisfer** UTM (N atau S) menentukan apakah northing ditambah 10.000.000 m. Karena Indonesia terbelah ekuator, titik di sekitar Pontianak bisa bernorthing mendekati 0 (utara) atau mendekati 10.000.000 (selatan).

**Band lintang** adalah huruf C sampai X (tanpa I dan O) untuk tiap pita 8°. Indonesia tercakup band L (16°–8° LS), M (8° LS–0°), dan N (0°–8° LU). Hati-hati saat konversi koordinat bernotasi "48S": dalam kebiasaan Indonesia S berarti Selatan, sedangkan dalam MGRS S adalah band 32°–40° LU. Tool membaca "48S" sebagai Selatan dan selalu menampilkan catatannya.

## Kapan Memakai UTM dan Kapan Koordinat Geografis

Pakai **koordinat geografis** (desimal atau DMS) bila data akan dibuka di Google Maps, dibagikan lewat chat, atau wilayahnya luas hingga melewati beberapa zona.

Pakai **UTM** bila Anda perlu jarak dan luas dalam meter secara langsung, misalnya untuk mengukur bidang, merencanakan jalan, atau membuat grid sampling, dan bila dokumen proyek mensyaratkan zona tertentu. Ingat, faktor skala UTM berkisar dari 0,9996 di meridian tengah sampai sedikit di atas 1 di tepi zona, jadi pekerjaan berketelitian tinggi tetap butuh koreksi skala dari surveyor yang kompeten. Karena itu, konversi koordinat geografis ke UTM sebaiknya memakai rumus yang presisi dan bisa diperiksa.

## Datum: WGS84 dan SRGI2013

- **SRGI2013** ditetapkan Badan Informasi Geospasial (BIG) pada 17 Oktober 2013 melalui Peraturan Kepala BIG Nomor 15 Tahun 2013 sebagai referensi tunggal pemetaan nasional, menggantikan datum statis DGN95.
- Menurut dokumen BIG, SRGI2013 memakai **elipsoid WGS84** (a = 6.378.137 m, 1/f = 298,257223563), terikat **ITRF2008 epoch 2012.0**, lalu dimutakhirkan ke **epoch 2021.0 (ITRF2014)** lewat SK Kepala BIG Nomor 33.2 Tahun 2021.
- SRGI2013 bersifat **semi-dinamik** karena Indonesia berada di pertemuan beberapa lempeng tektonik yang aktif, sehingga posisi titik bergeser dari tahun ke tahun. BIG menyediakan model deformasi untuk memindahkan koordinat antar-epoch.

Apa artinya bagi konversi koordinat di tool ini? Karena elipsoidnya sama, **rumus proyeksi UTM untuk WGS84 dan SRGI2013 identik**, asalkan lintang dan bujur masukan sudah berada dalam sistem yang dimaksud. Perbedaannya ada pada kerangka referensi dan epoch, dan tool ini **tidak** melakukan transformasi datum maupun epoch. Apakah selisih itu berarti bagi Anda bergantung pada ketelitian yang dibutuhkan. Untuk survei presisi tingkat sentimeter, gunakan layanan transformasi epoch BIG di [srgi.big.go.id](https://srgi.big.go.id/) atau perangkat lunak geodesi. Jangan mencampur data datum lama (ID74 atau DGN95) dengan WGS84/SRGI2013 tanpa transformasi yang benar.

## Tips & Kesalahan Umum

- **Lupa tanda minus.** Kesalahan konversi koordinat yang sering terjadi: `6.175392, 106.827153` tanpa minus akan mendarat di Laut Cina Selatan, bukan di Jakarta.
- **Tertukar urutan.** Google Maps memakai urutan lintang lalu bujur, sedangkan sebagian perangkat lunak GIS memakai x, y (bujur, lintang). Bila muncul pesan lintang melebihi 90°, kemungkinan urutannya tertukar.
- **Menit atau detik ≥ 60.** `6°61'` tidak valid, dan tool menolaknya alih-alih diam-diam menghasilkan angka salah.
- **Easting tanpa zona.** Easting berulang di setiap zona, jadi selalu tulis zona dan hemisfer.
- **Presisi berlebihan.** Enam desimal derajat setara kira-kira 0,1 m, dan dua desimal detik setara kira-kira 0,3 m. Menulis lebih banyak desimal tidak membuat GPS ponsel lebih akurat.

## FAQ

**Apakah konversi koordinat online lebih akurat daripada tool ini?**
Belum tentu. Akurasi situs konversi koordinat online bergantung pada rumus yang dipakai, yang sering tidak dicantumkan. Tool ini memakai seri Krüger orde n⁶ dengan kode terbuka, selisihnya dengan PROJ di bawah 0,001 mm, dan berjalan offline sehingga data lokasi Anda tidak dikirim ke server.

**Bagaimana konversi koordinat UTM ke latitude longitude jika saya hanya punya angka zona?**
Jalankan `utm2dd 49 430597.58 9138084.76 --hemisfer S`. Hemisfer wajib diisi karena northing yang sama bisa berada di utara maupun selatan ekuator.

**Bagaimana konversi titik koordinat GPS yang menampilkan menit desimal?**
Ketik apa adanya, misalnya `dms2dd "6 10,5233 LS"`. Komponen terakhir, baik menit maupun detik, boleh berdesimal.

**Bisakah konversi koordinat derajat ke desimal untuk banyak titik sekaligus?**
Bisa. Simpan titik dalam CSV berkolom `lat` dan `lon`, lalu jalankan `--csv file.csv --mode dms2dd`. Hasilnya ditulis ke `file_hasil.csv`.

**Konversi geografis ke UTM di dekat batas zona, zona mana yang benar?**
Secara standar zona mengikuti bujur, tetapi proyek lintas zona sering memakai satu zona untuk seluruh area. Gunakan `--zona` sesuai ketentuan proyek.

**Apakah hasilnya berlaku untuk SRGI2013?**
Rumus proyeksinya sama karena elipsoidnya WGS84, tetapi tool tidak mengubah epoch atau datum. Lihat bagian [Datum](#datum-wgs84-dan-srgi2013).

**Kenapa hasil konversi koordinat desimal ke derajat saya berbeda 0,01 detik dari aplikasi lain?**
Biasanya karena pembulatan. Pakai `--presisi 3` atau lebih untuk membandingkan.

## Metodologi, Pengujian & Sumber

Akurasi konversi koordinat di sini diuji dengan **18 unit test** (`python3 -m unittest discover -s tests -v`) dan semuanya lulus. Isinya antara lain:

- **Ekuator dan meridian tengah.** Titik (0°, 105° BT) harus menghasilkan easting tepat 500.000 m dan northing 0, dan 48S (500.000; 10.000.000) harus kembali tepat ke (0°, 105°).
- **Pembanding independen.** Tujuh titik (antara lain Monas, Banda Aceh, Kupang, Jayapura) dihitung juga dengan pyproj 3.8.0 / PROJ 9.8.1 di virtualenv terpisah. Untuk Monas, PROJ memberi 48S E 702.178,122709 N 9.317.060,285667. Selisih tool ini kurang dari 0,0005 mm (syarat test: < 1 mm).
- **Round-trip.** 500 titik acak di wilayah Indonesia diubah DD → UTM → DD. Syaratnya selisih < 10⁻⁹ derajat (±0,1 mm), dan hasil aktualnya sekitar 3×10⁻¹⁴ derajat.
- **Parser DMS dan CSV.** Tujuh variasi penulisan Monas harus menghasilkan nilai sama, sepuluh input salah harus ditolak, dan CSV dengan satu baris salah harus tetap diproses.

pyproj hanya dipakai saat pengembangan sebagai pembanding, bukan dependency.

**Sumber rujukan:**

1. Karney, C. F. F. (2011). *Transverse Mercator with an accuracy of a few nanometers*. Journal of Geodesy 85(8), 475–485. [doi:10.1007/s00190-011-0445-3](https://doi.org/10.1007/s00190-011-0445-3), pracetak [arXiv:1002.1417](https://arxiv.org/abs/1002.1417).
2. Snyder, J. P. (1987). *Map Projections — A Working Manual*. USGS Professional Paper 1395. [pubs.usgs.gov](https://pubs.usgs.gov/pp/1395/report.pdf).
3. Defense Mapping Agency (1989). *TM 8358.2 The Universal Grids: UTM and UPS*. [DTIC ADA266497](https://apps.dtic.mil/sti/pdfs/ADA266497.pdf).
4. Badan Informasi Geospasial. [Sistem Referensi Geospasial Indonesia](https://srgi.big.go.id/), info produk [Jaring Kontrol Geodesi](https://srgi.big.go.id/download/info_produk/INFO%20JKG.pdf) dan [Model Deformasi](https://srgi.big.go.id/download/info_produk/INFO%20MODEL%20DEFORMASI.pdf).
5. EPSG Dataset, misalnya [EPSG:9476](https://epsg.io/9476) (SRGI2013 / UTM zone 46N) dan [EPSG:32748](https://epsg.io/32748) (WGS 84 / UTM zone 48S).
6. [PROJ](https://proj.org/) dan [pyproj](https://pyproj4.github.io/pyproj/stable/) sebagai pembanding numerik.

## Tentang Pembuat

Proyek ini adalah karya [JoinBareng](https://joinbareng.com) dan dikelola oleh [@redyopa2929](https://github.com/redyopa2929). JoinBareng adalah platform patungan langganan premium (Netflix, Spotify, YouTube Premium, ChatGPT, dll.) plus marketplace akun digital yang aman dan transparan.

## Disclaimer

Tool ini disediakan apa adanya untuk edukasi dan pekerjaan umum. Hasil konversi koordinat tidak menggantikan pengukuran surveyor berlisensi dan tidak boleh menjadi satu-satunya dasar penetapan batas tanah, batas wilayah, atau dokumen hukum. Tool tidak melakukan transformasi datum maupun epoch.

## Kontribusi

Laporan bug, ide fitur, dan pull request sangat diterima. Buka isu di [github.com/redyopa2929/konversi-koordinat/issues](https://github.com/redyopa2929/konversi-koordinat/issues) dengan contoh input, output yang diharapkan, dan sumber pembandingnya.

## Lisensi

Dirilis di bawah [Lisensi MIT](LICENSE) © 2026 redyopa2929. Bebas dipakai, diubah, dan disebarkan, termasuk untuk keperluan komersial, selama pemberitahuan lisensi tetap dicantumkan.

## Dukung Proyek Ini

Jika tool konversi koordinat ini menghemat waktu Anda di lapangan atau saat menyusun laporan, beri ⭐ star pada repositori ini agar lebih mudah ditemukan rekan surveyor dan mahasiswa. Butuh aplikasi premium seperti ChatGPT untuk menyusun laporan? Hemat biaya langganannya dengan patungan di [JoinBareng](https://joinbareng.com).

## Tools Lainnya dari Seri Ini

- [Kalkulator Jadian](https://github.com/redyopa2929/kalkulator-jadian) — hitung lama hari jadian & anniversary
- [Kalkulator Jasmani Polri](https://github.com/redyopa2929/kalkulator-jasmani-polri) — hitung nilai kesamaptaan jasmani
- [Hitung WR ML](https://github.com/redyopa2929/hitung-wr-ml) — hitung win rate Mobile Legends
- [Tasbih Online](https://github.com/redyopa2929/tasbih-online) — tasbih digital penghitung dzikir
- [Kalkulator Selamatan](https://github.com/redyopa2929/kalkulator-selamatan) — hitung selamatan orang meninggal adat Jawa
- [Terbilang Online](https://github.com/redyopa2929/terbilang-online) — ubah angka ke huruf / terbilang rupiah
- [Kalkulator Saham](https://github.com/redyopa2929/kalkulator-saham) — average down, compounding, ARA/ARB
- [Kalkulator Bangunan](https://github.com/redyopa2929/kalkulator-bangunan) — keramik, hebel, kubikasi, besi
- [Cek Weton](https://github.com/redyopa2929/cek-weton) — cek weton & neptu dari tanggal lahir

---

Terakhir diperbarui: 21 Oktober 2026
