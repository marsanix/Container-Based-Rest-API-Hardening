# Tugas Kelompok 5 v2: Hardening Keamanan Transmisi Data REST API Berbasis Docker Container Menggunakan TLS 1.3 Berpola Cipher Suite AES-128-GCM Terhadap Serangan Adversary-in-the-Middle

Mata Kuliah: Network Programming & Administration  
Kelas: IFN41  

Kelompok 5:
- Marsani (230401010282)
- Muhammad Saifulloh (220401010207)
- Kristian Hananiel Hura (220401010289)
- Sukandar (240401020175)

Dosen Pengajar: Abdul Azzam Ajhari, S.Kom., M.Kom  
Program Studi: PJJ INFORMATIKA  
Kampus: UNIVERSITAS SIBER ASIA  
Tahun: 2026  

---

> Proyek ini adalah hasil luaran dari penelitian akademis yang mendemonstrasikan kerentanan arsitektur *microservices* berbasis HTTP terhadap serangan *Man-in-the-Middle* (MITM) berupa *ARP Spoofing*. Melalui simulasi komprehensif menggunakan Docker, dibuktikan secara empiris bahwa serangan *sniffing* (MITRE T1557.001) dapat dengan mudah mencuri kredensial dan data sensitif secara *cleartext*. Sebagai solusi atas masalah tersebut, penelitian ini mengusulkan Arsitektur Keamanan Defense in Depth. Lapis pertama mengamankan *Data in Transit* menggunakan Nginx *Reverse Proxy* dengan terminasi TLS 1.3. Lapis kedua mengamankan *Data at Rest* melalui *Application-Level Encryption* (AES-128-GCM) sebelum masuk ke *database*, memitigasi secara langsung risiko kegagalan kriptografi (OWASP A02:2025). Hasil pengujian dengan *packet analyzer* menunjukkan bahwa arsitektur yang diusulkan 100% efektif menyembunyikan *payload* dari *sniffer* dan melindungi integritas serta kerahasiaan data di level transportasi maupun penyimpanan.

Proyek ini dibangun sebagai pemenuhan Tugas Kelompok untuk mendemonstrasikan simulasi serangan penyadapan jaringan (*Network Sniffing*) tingkat lanjut dan teknik pertahanan berlapis (*Defense in Depth*) dalam arsitektur *Microservices* berbasis Docker.

## 🎯 Tujuan Proyek
1. Mensimulasikan Serangan Nyata: Menggunakan kerentanan *True MITM (ARP Spoofing)* untuk secara diam-diam membelokkan dan mencegat lalu lintas jaringan internal (Layer 2) antara klien dan server tanpa disadari korban.
2. Implementasi Defense in Depth: Mengamankan sistem dengan perlindungan ganda (*Layered Security*):
   - Data in Transit: Mengamankan lalu lintas jaringan dari *sniffing* menggunakan Nginx Reverse Proxy sebagai terminasi TLS 1.3 dengan standar *cipher suite* kriptografi eksklusif (`TLS_AES_128_GCM_SHA256`).
   - Data at Rest: Menerapkan *Application-Level Encryption* menggunakan algoritma AES-128-GCM via pustaka standar *Python Cryptography*. Data sensitif (seperti Gaji Karyawan pada modul CRUD) dienkripsi sebelum pernah menyentuh disk/database, melindungi data meskipun *database server* (MySQL) berhasil dibobol (*post-breach*).
3. Analisis Berbasis Standar Industri: Mengevaluasi kelemahan dan validasi mitigasi berdasarkan pemetaan standar MITRE ATT&CK (Teknik T1557.001) dan risiko global OWASP Top 10:2025 (A02:2025 Cryptographic Failures) secara terukur menggunakan *packet analyzer* (Wireshark).

## 🏗 Topologi Jaringan (Subnet: `10.10.10.0/24`)

```text
┌───────────────────────────────────────────────────────────────────────┐
│                             HOST MACHINE                              │
│                                                                       │
│   ┌─────────────────────┐                                             │
│   │ Client Victim       │                                             │
│   │ (WebTop Container)  │                                             │
│   │ (IP: 10.10.10.40)   │                                             │
│   └─────────┬───────────┘                                             │
│             │                                                         │
│             │   <== ARP Spoofing (Poisoning) ==>                      │
│             │                                                         │
│   ┌─────────▼───────────┐      ┌──────────────────────────────────┐   │
│   │ Attacker (Sniffer)  │      │  Nginx Reverse Proxy             │   │
│   │ Standalone (MITM)   ├──────►  (TLS 1.3 Termination Point)     │   │
│   │ (IP: 10.10.10.50)   │      │  (IP: 10.10.10.10)               │   │
│   └─────────────────────┘      └────┬─────────────────────────┬───┘   │
│                                     │                         │       │
│                        Route: `/`   │                         │ `/api/`
│                    (HTTP Internal)  │                         │       │
│                                     │                         │       │
│                        ┌────────────▼────┐           ┌────────▼────┐  │
│                        │ Frontend Web UI │           │ Backend API │  │
│                        │ (.10.30)        │           │ (.10.20)    │  │
│                        └─────────────────┘           └────────┬────┘  │
│                                                               │       │
│                                                   (AES-128-GCM Enc)   │
│                                                               │       │
│                                                      ┌────────▼────┐  │
│                                                      │ MySQL DB    │  │
│                                                      │ (.10.60)    │  │
│                                                      └─────────────┘  │
│                                                                       │
│   ┌───────────────────────────────────────────────────────────────┐   │
│   │       Docker Bridge Network: secure-net (10.10.10.0/24)       │   │
│   └───────────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────────┘
```

- Nginx Reverse Proxy: `10.10.10.10`
- Backend API: `10.10.10.20`
- Frontend Web UI: `10.10.10.30`
- Client Victim (WebTop): `10.10.10.40`
- Attacker (Sniffer/MITM): `10.10.10.50`
- MySQL Database: `10.10.10.60`

---

## 🚀 Panduan Eksekusi (Demo Manual)

### Prasyarat
- Buka Terminal/CMD di dalam folder `demo`.
- Docker Desktop sudah berjalan aktif di latar belakang.
- Wireshark sudah terinstal di lokasi *default* Windows (`C:\Program Files\Wireshark\Wireshark.exe`).

### Langkah 1: Generate Sertifikat TLS (Lakukan Sekali)
Sertifikat diperlukan agar Nginx Proxy dapat menjalankan mode HTTPS (TLS 1.3).
```bash
cd demo
mkdir nginx\certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx\certs\server.key -out nginx\certs\server.crt -subj "/C=ID/ST=Jakarta/L=Jakarta/O=LabNetworkSecurity/CN=localhost"
```

### Langkah 2: SKENARIO A — Baseline HTTP (Tanpa Enkripsi)
Skenario ini membuktikan kelemahan fatal arsitektur jaringan jika hanya mengandalkan lalu lintas *plaintext* (Data in Transit terekspos).

1. Jalankan Environment HTTP:
   ```bash
   docker-compose down
   copy /Y nginx\nginx-http.conf nginx\nginx.conf
   docker-compose up -d --build
   ```
2. Mulai Live Sniffing (Piping Wireshark Real-Time):
   Buka *Command Prompt* (CMD) Windows yang baru dan jalankan dari folder `demo`:
   ```cmd
   docker exec -i attacker tcpdump -U -i eth0 host 10.10.10.40 and not arp -w - | "C:\Program Files\Wireshark\Wireshark.exe" -k -i -
   ```
3. Simulasi Transmisi Data:
   - Buka *browser* di mesin Host Anda dan kunjungi WebTop Client: `http://localhost:3000`
   - Di dalam *Desktop Environment* WebTop, buka Web Browser (Firefox) dan akses: `http://nginx-proxy`
   - Lakukan Login (admin/rahasia123) dan ujicoba antarmuka CRUD dengan mengisi form Tambah Karyawan.
4. Analisis di Wireshark (Buktikan Kerentanan):
   - Filter Wireshark: `http.request.method == POST`
   - Klik kanan paket HTTP -> Follow -> TCP Stream.
   - Buktikan (*Screenshot*) bahwa kredensial *username*, *password*, serta *data gaji* terlihat jelas secara *cleartext*. Hentikan *capture* (tombol kotak merah) dan tutup Wireshark.

### Langkah 3: SKENARIO B — Pasca-Hardening (TLS 1.3 Aktif)
Skenario ini membuktikan efektivitas enkripsi tingkat lapisan *Transport* dalam mengamankan lalu lintas dari serangan *ARP Spoofing*.

1. Jalankan Environment HTTPS:
   ```bash
   docker-compose down
   copy /Y nginx\nginx-tls.conf nginx\nginx.conf
   docker-compose up -d --build
   ```
2. Mulai Live Sniffing ke Wireshark:
   Jalankan kembali perintah piping Wireshark pada CMD Host Anda:
   ```cmd
   docker exec -i attacker tcpdump -U -i eth0 host 10.10.10.40 and not arp -w - | "C:\Program Files\Wireshark\Wireshark.exe" -k -i -
   ```
3. Simulasi Transmisi Data Aman:
   - Dari Firefox di dalam WebTop (`http://localhost:3000`), kunjungi portal secara aman: `https://nginx-proxy`
   - *(Abaikan peringatan keamanan self-signed certificate, klik Advanced -> Accept the Risk and Continue)*.
   - Lakukan kembali aktivitas Login dan *CRUD Karyawan*.
4. Analisis di Wireshark (Buktikan Mitigasi):
   - Filter Wireshark: `tls`
   - Temukan paket Server Hello. Lihat pada detail tree *Transport Layer Security* untuk membuktikan penggunaan `TLSv1.3` dan Cipher Suite `TLS_AES_128_GCM_SHA256`.
   - Lakukan *Follow TLS Stream* dan buktikan (*Screenshot*) bahwa *payload* aplikasi sepenuhnya tertutup dan tidak terbaca (*Encrypted Application Data*). Hentikan *capture*.

### Langkah 4: Validasi "Defense in Depth" (Data at Rest)
Mendemonstrasikan lapisan keamanan tingkat lanjut. Bahkan jika server *Backend* dapat ditembus dan database MySQL berhasil diakses secara ilegal oleh peretas, data kritikal tetap aman.

Buka terminal Host di dalam folder `demo` dan *query* isi database MySQL secara langsung:
```bash
docker exec -it mysql-db mysql -uroot -prahasia karyawan_db -e "SELECT * FROM employees;"
```
- Buktikan bahwa nilai kolom `salary_encrypted` tidak menampilkan nominal numerik, melainkan untaian string acak *Base64-encoded ciphertext*. Fitur Enkripsi tingkat aplikasi (*Application-Level Encryption* AES-128-GCM) bekerja secara mulus untuk menyandikan data sensitif di level Backend.

### Langkah 5: Cleanup Environment
Hapus semua instans *container*, jaringan, dan *volume* setelah demo presentasi selesai dari folder `demo`:
```bash
docker-compose down --rmi all --volumes --remove-orphans
```
