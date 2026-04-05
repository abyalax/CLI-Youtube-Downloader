# YouTube Audio Bulk Downloader

Script Python untuk download audio dari YouTube secara massal dengan fitur resume dan skip duplicate.

## 🎯 Fitur

✅ Download audio dari multiple YouTube links  
✅ Download single link langsung  
✅ Format output: MP3 (192 kbps)  
✅ Resume downloads (skip file yang sudah ada)  
✅ Skip duplicate (jika URL sudah pernah didownload)  
✅ Log history di `download_log.json`  
✅ Default output ke Music folder user  
✅ Cross-platform (Windows, macOS, Linux)  
✅ Error handling & progress display

## 📋 Requirement

- Python 3.7+
- Node.js atau Bun (untuk YouTube extraction)
- FFmpeg (untuk convert audio ke MP3)
- Library: `yt-dlp`

## 🚀 Setup

### 1. Install Node.js atau Bun (Required for YouTube extraction)

**Windows:**

- Download dari: https://nodejs.org/ (pilih LTS version)
- Jalankan installer dan ikuti langkah-langkahnya
- Verify dengan: `node --version`

**macOS:**

```bash
brew install node
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install nodejs npm
```

### 2. Install Python Dependencies dengan UV (Recommended)

**Install UV jika belum ada:**

```bash
# Windows/macOS/Linux
pip install uv
```

**Kemudian install dependencies:**

```bash
uv sync
```

**Alternative: Install dengan pip**

```bash
pip install -r requirements.txt
```

Atau install langsung:

```bash
pip install yt-dlp
```

### 3. Install FFmpeg

**Windows - OPSI 1: Menggunakan Chocolatey (Recommended)**

Jika belum install Chocolatey, buka PowerShell as Admin dan jalankan:

```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

Kemudian install FFmpeg:

```powershell
choco install ffmpeg -y
```

Restart command prompt/PowerShell dan test:

```bash
ffmpeg -version
```

**Windows - OPSI 2: Manual Download**

1. Download dari: https://ffmpeg.org/download.html
2. Pilih **Full build** untuk Windows
3. Extract ke folder, contoh: `C:\ffmpeg`
4. Tambahkan ke System PATH:
   - Buka **Control Panel** → **System and Security** → **System** → **Advanced system settings**
   - Klik **Environment Variables**
   - Under **System variables**, cari dan klik **Path** → **Edit**
   - Klik **New** dan tambahkan: `C:\ffmpeg\bin`
   - Klik **OK** beberapa kali
5. Restart command prompt dan test: `ffmpeg -version`

**Jika masih error, gunakan opsi custom path:**

```bash
python main.py links.txt --ffmpeg-path "C:\ffmpeg\bin"
```

**macOS (menggunakan Homebrew):**

```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**

```bash
sudo apt-get install ffmpeg
```

### 4. Verifikasi Instalasi

```bash
node --version        # Should show version
ffmpeg -version       # Should show version
uv --version          # Should show uv version
python main.py --help # Should show help message
```

## 📝 Cara Penggunaan

### Mode 1: Download dari File (Multiple Links)

#### Step 1: Buat File Links

Buat file `links.txt` dengan YouTube links (satu URL per baris):

```
https://www.youtube.com/watch?v=dQw4w9WgXcQ
https://www.youtube.com/watch?v=jNQXAC9IVRw
https://www.youtube.com/watch?v=9bZkp7q19f0
```

#### Step 2: Jalankan Script

```bash
# Download ke Music folder (default)
python main.py links.txt

# Download ke custom folder
python main.py links.txt -o my_music

# Download tanpa skip duplicate
python main.py links.txt --no-resume
```

### Mode 2: Download Single Link

```bash
# Download single link ke Music folder
python main.py --link "https://youtu.be/fLexgOxsZu0"

# Download ke custom folder
python main.py --link "https://youtu.be/fLexgOxsZu0" -o my_music
```

### Options Lengkap

| Option          | Deskripsi                                | Contoh                                                   |
| --------------- | ---------------------------------------- | -------------------------------------------------------- |
| `links.txt`     | File dengan list links                   | `python main.py links.txt`                               |
| `--link`        | Download single link                     | `python main.py --link "https://youtu.be/xxxxx"`         |
| `-o, --output`  | Output directory (default: Music folder) | `python main.py links.txt -o folder`                     |
| `--no-resume`   | Disable resume mode                      | `python main.py links.txt --no-resume`                   |
| `--ffmpeg-path` | Custom FFmpeg path                       | `python main.py links.txt --ffmpeg-path "C:\ffmpeg\bin"` |

### Contoh Penggunaan Lengkap

```bash
# File mode - ke Music folder
python main.py links.txt

# File mode - custom folder
python main.py links.txt -o Bruno_Mars

# File mode - tanpa resume (download semua)
python main.py links.txt --no-resume

# Single link - ke Music folder
python main.py --link "https://youtu.be/fLexgOxsZu0"

# Single link - custom folder
python main.py --link "https://youtu.be/fLexgOxsZu0" -o my_playlist

# Custom FFmpeg path
python main.py links.txt --ffmpeg-path "C:\ffmpeg\bin"
```

## 📊 Output

Struktur folder setelah download:

```
Music/
├── "Song Title 1".mp3
├── "Song Title 2".mp3
├── "Song Title 3".mp3
└── download_log.json
```

**File `download_log.json` berisi:**

```json
{
  "https://www.youtube.com/watch?v=dQw4w9WgXcQ": {
    "title": "Rick Astley - Never Gonna Give You Up",
    "downloaded_at": "2024-01-15T10:30:45.123456"
  }
}
```

## ⚠️ Troubleshooting

### Error: "ffmpeg and ffprobe not found"

**Solusi 1: Install FFmpeg via Chocolatey (Windows - Recommended)**

```powershell
# Buka PowerShell as Administrator
choco install ffmpeg -y
# Restart PowerShell/cmd setelah selesai
ffmpeg -version
```

**Solusi 2: Download Manual FFmpeg (Windows)**

1. Download full build dari: https://ffmpeg.org/download.html
2. Extract ke: `C:\ffmpeg`
3. Tambah ke PATH di Environment Variables
4. Restart command prompt

**Solusi 3: Gunakan Custom FFmpeg Path**

```bash
python main.py links.txt --ffmpeg-path "C:\ffmpeg\bin"
```

### Error: "yt-dlp not found"

```bash
pip install --upgrade yt-dlp
```

### Error: "No supported JavaScript runtime"

Install Node.js dari https://nodejs.org/ (LTS version recommended)

### Download stuck/timeout

- Cek koneksi internet
- Coba dengan `--no-resume` untuk reset
- Hapus log file dan coba lagi

### Video/Link tidak valid

- Pastikan URL format valid (gunakan full link)
- Coba buka di browser untuk memastikan video masih tersedia
- Beberapa video mungkin di-restrict atau memerlukan login

## 💡 Tips

1. **Batch Download**: Masukkan semua link di `links.txt`, script akan otomatis download semua
2. **Resume Otomatis**: Jika download terputus, jalankan script lagi - akan melanjutkan dari file yang sudah ada
3. **Monitor Progress**: Lihat `download_log.json` untuk history download
4. **Custom Folder**: Gunakan `-o nama_folder` untuk organize file
5. **Default Music Folder**: Semua download otomatis ke Music folder user Anda (cross-platform)

## 📜 License

MIT License

## 🆘 Support

Jika ada error, cek output lengkap error message untuk debugging.
