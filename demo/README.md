# Panduan Demo Manual - Hardening TLS 1.3 pada REST API Docker (Dengan Sniffing Container)

Panduan ini menggunakan container **attacker** khusus yang berada di dalam jaringan yang sama dengan proxy untuk bertindak sebagai *Man in the Middle*. Container ini otomatis merekam seluruh aktivitas jaringan ke dalam file `.pcap` yang nanti bisa Anda buka di Wireshark.

## Prasyarat

- Terminal/CMD harus dibuka di dalam folder `demo`.
- **Docker Desktop** sudah berjalan.
- **Wireshark** sudah terinstal di komputer Host.

## Topologi Jaringan (IP Statis Kelas A)

Untuk mempermudah dokumentasi hasil Wireshark, seluruh container menggunakan IP statis berikut pada *subnet* `10.10.10.0/24`:
- **Nginx Reverse Proxy**: `10.10.10.10`
- **Backend API**: `10.10.10.20`
- **Attacker (Sniffer)**: `10.10.10.10` (Berbagi antarmuka jaringan yang sama dengan Nginx)

---

### Langkah 1: Generate Sertifikat TLS (Lakukan Sekali Saja)

Buka terminal di dalam folder `demo` dan jalankan:

```bash
mkdir nginx\certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout nginx\certs\server.key -out nginx\certs\server.crt -subj "/C=ID/ST=Jakarta/L=Jakarta/O=LabNetworkSecurity/CN=localhost"
```

---

### Langkah 2: SKENARIO A — Baseline HTTP (Tanpa Enkripsi)

1. **Bersihkan dan Siapkan Konfigurasi HTTP**:
   ```bash
   docker-compose down
   copy /Y nginx\nginx-http.conf nginx\nginx.conf
   ```

2. **Jalankan Container**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Mulai Live Sniffing ke Wireshark**:
   Buka terminal *Command Prompt* (CMD) baru, dan jalankan perintah sakti ini (Pastikan Wireshark terinstal di lokasi default):
   ```cmd
   docker exec -i attacker tcpdump -U -i eth0 host 10.10.10.40 and not arp -w - | "C:\Program Files\Wireshark\Wireshark.exe" -k -i -
   ```
   *Jendela Wireshark akan otomatis terbuka dan langsung menampilkan trafik jaringan secara real-time.*

4. **Kirim Data via WebTop (Simulasi Client Asli)**:
   - Buka browser di komputer Host Anda dan kunjungi **`http://localhost:3000`** (Ini adalah antarmuka Desktop Linux dari container `client-victim`).
   - Di dalam antarmuka WebTop tersebut, buka Web Browser bawaan (seperti Firefox/Chromium).
   - Kunjungi alamat internal proxy: **`http://nginx-proxy`** (atau `http://10.10.10.10`).
   - Anda akan melihat halaman "Secure Portal".
   - Klik tombol **Login** (Username & Password sudah terisi otomatis).
   - Di terminal Wireshark Host, paket jaringan dari Client ke Proxy akan langsung tertangkap!

5. **Analisis di Wireshark secara Real-time**:
   - Lihat ke jendela Wireshark yang sedang berjalan.
   - Ketik `http.request.method == POST` di kolom filter.
   - **(AMBIL SCREENSHOT)** — Tunjukkan paket HTTP POST yang tertangkap.
   - Klik Kanan pada paket -> **Follow** -> **TCP Stream**.
   - **(AMBIL SCREENSHOT)** — Tunjukkan "username":"admin" serta password-nya dalam bentuk *cleartext*.
   - Hentikan *capture* (tombol kotak merah) dan tutup Wireshark.

---

### Langkah 3: SKENARIO B — Pasca-Hardening (TLS 1.3 Aktif)

1. **Bersihkan dan Siapkan Konfigurasi TLS 1.3**:
   ```bash
   docker-compose down
   copy /Y nginx\nginx-tls.conf nginx\nginx.conf
   ```

2. **Jalankan Container**:
   ```bash
   docker-compose build
   docker-compose up -d
   ```

3. **Verifikasi Keamanan (Ambil Screenshot)**:
   ```bash
   docker-compose ps
   openssl s_client -connect localhost:443 -tls1_3
   openssl s_client -connect localhost:443 -tls1_2
   ```

4. **Mulai Live Sniffing ke Wireshark**:
   Sama seperti sebelumnya, jalankan perintah ini di CMD baru untuk memulai tangkapan layar Wireshark secara *real-time*:
   ```cmd
   docker exec -i attacker tcpdump -U -i eth0 host 10.10.10.40 and not arp -w - | "C:\Program Files\Wireshark\Wireshark.exe" -k -i -
   ```

5. **Kirim Data Terenkripsi via WebTop**:
   - Di dalam WebTop browser (`http://localhost:3000`), buka tab baru dan kunjungi:
     **`https://nginx-proxy`** (atau `https://10.10.10.10`).
   - *(Abaikan peringatan keamanan / "Your connection is not private", klik Advanced -> Proceed to nginx-proxy).*
   - Di halaman "Secure Portal", klik tombol **Login**.
   - Paket akan langsung terkirim secara aman dan ditangkap oleh Wireshark.

6. **Analisis di Wireshark secara Real-time**:
   - Di jendela Wireshark, ketik `tls` di kolom filter.
   - **(AMBIL SCREENSHOT)** — Tunjukkan paket TLSv1.3 (Client Hello & Server Hello).
   - Klik *Server Hello* -> Buka detail *Transport Layer Security* -> cari *Cipher Suite*.
   - **(AMBIL SCREENSHOT)** — Buktikan Cipher Suite `TLS_AES_128_GCM_SHA256`.
   - Perhatikan paket *Application Data*. **(AMBIL SCREENSHOT)**.
   - Klik Kanan paket *Application Data* -> **Follow** -> **TLS Stream**.
   - **(AMBIL SCREENSHOT)** — Buktikan data hanya berupa karakter acak (*Encrypted*).
   - Hentikan *capture* dan tutup Wireshark.

---

### Langkah 4: Cleanup

Setelah semua screenshot selesai:

```bash
docker-compose down --rmi all --volumes --remove-orphans
```
