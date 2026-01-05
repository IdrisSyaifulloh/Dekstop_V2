# MangoDefend - Deployment Guide

Panduan lengkap untuk deploy backend dan desktop application MangoDefend.

## 📋 Prerequisites

### Backend Server
- Python 3.8 atau lebih baru
- PostgreSQL 12 atau lebih baru
- 2GB RAM minimum
- 10GB disk space

### Desktop Application
- Python 3.8 atau lebih baru
- Windows 10/11, Linux, atau macOS
- 4GB RAM minimum (8GB recommended untuk ML model)
- GPU (optional, untuk performa lebih baik)

---

## 🚀 Backend Deployment

### 1. Setup Database

#### Install PostgreSQL
```bash
# Windows: Download dari https://www.postgresql.org/download/windows/
# Linux (Ubuntu/Debian):
sudo apt update
sudo apt install postgresql postgresql-contrib

# macOS:
brew install postgresql
```

#### Create Database
```sql
-- Login ke PostgreSQL
psql -U postgres

-- Buat database baru
CREATE DATABASE Db_Scanning;

-- Buat user (optional)
CREATE USER mangodefend WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE Db_Scanning TO mangodefend;
```

### 2. Configure Backend

Navigate ke folder backend:
```bash
cd desktop_app/backend
```

Edit file `.env`:
```env
DB_USER=postgres
DB_PASS=your_password_here
DB_HOST=localhost
DB_PORT=5432
DB_NAME=Db_Scanning
```

### 3. Install Dependencies

```bash
# Create virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Run Backend Server

#### Development Mode
```bash
# Windows:
run_backend.bat

# Linux/Mac:
chmod +x run_backend.sh
./run_backend.sh
```

#### Production Mode (Manual)
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 5. Verify Backend

Open browser dan akses:
- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs
- Redoc: http://localhost:8000/redoc

Expected response dari `/health`:
```json
{
  "status": "healthy",
  "service": "Malware Detection API",
  "version": "1.0.0"
}
```

---

## 💻 Desktop Application Deployment

### 1. Install Dependencies

Navigate ke folder desktop_app:
```bash
cd desktop_app
```

Install dependencies:
```bash
# Create virtual environment
python -m venv venv

# Activate
# Windows:
venv\\Scripts\\activate
# Linux/Mac:
source venv/bin/activate

# Install
pip install -r requirements.txt
```

### 2. Configure Desktop App

Edit `config.ini`:
```ini
[Backend]
# Ganti dengan URL backend server Anda
url = http://localhost:8000
timeout = 10
retry_attempts = 3
retry_backoff = 2.0

[Sync]
enabled = true
interval = 30
batch_size = 50
max_queue_size = 1000

[App]
auto_sync = true
show_notifications = true
log_level = INFO
```

**Production Setup:**
Jika backend di server terpisah, ganti URL:
```ini
[Backend]
url = http://192.168.1.100:8000  # IP server backend
```

### 3. Run Desktop App

```bash
# Windows:
python main.py

# Atau gunakan batch file:
run.bat
```

### 4. Verify Installation

Saat aplikasi start, Anda akan melihat:
```
✅ Sync manager started (backend: http://localhost:8000)
```

Jika backend offline:
```
⚠️  Failed to start sync manager: ...
```
(Aplikasi tetap bisa digunakan, hasil scan akan di-queue)

---

## 🔧 Production Deployment

### Backend as Windows Service

#### Using NSSM (Non-Sucking Service Manager)

1. Download NSSM: https://nssm.cc/download
2. Install service:
```cmd
nssm install MangoDefendBackend "C:\\path\\to\\venv\\Scripts\\python.exe" "-m uvicorn main:app --host 0.0.0.0 --port 8000"
nssm set MangoDefendBackend AppDirectory "C:\\path\\to\\desktop_app\\backend"
nssm start MangoDefendBackend
```

#### Using systemd (Linux)

Create `/etc/systemd/system/mangodefend-backend.service`:
```ini
[Unit]
Description=MangoDefend Backend API
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/mangodefend/backend
Environment="PATH=/opt/mangodefend/venv/bin"
ExecStart=/opt/mangodefend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mangodefend-backend
sudo systemctl start mangodefend-backend
sudo systemctl status mangodefend-backend
```

### Desktop App as EXE (Windows)

Build executable menggunakan PyInstaller:
```bash
# Install PyInstaller
pip install pyinstaller

# Build
pyinstaller MangoDefend.spec

# EXE akan ada di folder dist/
```

---

## 🌐 Network Configuration

### Firewall Rules

#### Windows Firewall
```powershell
# Allow backend port
netsh advfirewall firewall add rule name="MangoDefend Backend" dir=in action=allow protocol=TCP localport=8000
```

#### Linux (UFW)
```bash
sudo ufw allow 8000/tcp
sudo ufw reload
```

### CORS Configuration

Untuk production, edit `backend/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://192.168.1.100",  # IP desktop clients
        # Add more IPs as needed
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 📊 Monitoring & Logs

### Backend Logs

Logs akan muncul di console. Untuk production, redirect ke file:
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8000 >> backend.log 2>&1
```

### Desktop App Logs

Sync manager logs akan muncul di console:
```
2025-12-22 08:30:00 - SyncManager - INFO - SyncManager initialized (backend: http://localhost:8000)
2025-12-22 08:30:00 - SyncManager - INFO - Sync manager started
2025-12-22 08:30:30 - SyncManager - INFO - Syncing 5 pending scans...
2025-12-22 08:30:32 - SyncManager - INFO - Sync complete: 5 synced, 0 failed
```

### Database Monitoring

Check queue status:
```sql
-- Connect to database
psql -U postgres -d Db_Scanning

-- Check total scans
SELECT COUNT(*) FROM scan_results;

-- Check recent scans
SELECT * FROM scan_results ORDER BY created_at DESC LIMIT 10;

-- Check by label
SELECT label, COUNT(*) FROM scan_results GROUP BY label;
```

---

## 🔒 Security Best Practices

1. **Database Password**: Gunakan password yang kuat
2. **CORS**: Batasi allowed origins di production
3. **HTTPS**: Gunakan reverse proxy (nginx) dengan SSL
4. **Firewall**: Hanya buka port yang diperlukan
5. **Updates**: Regularly update dependencies

### Example Nginx Config (HTTPS)

```nginx
server {
    listen 443 ssl;
    server_name api.mangodefend.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🐛 Troubleshooting

### Backend tidak bisa connect ke database

**Error**: `could not connect to server: Connection refused`

**Solution**:
1. Check PostgreSQL running: `sudo systemctl status postgresql`
2. Check credentials di `.env`
3. Check PostgreSQL listening: `netstat -an | grep 5432`

### Desktop app tidak bisa connect ke backend

**Error**: `Backend offline, skipping sync`

**Solution**:
1. Check backend running: `curl http://localhost:8000/health`
2. Check firewall rules
3. Check URL di `config.ini`
4. Check network connectivity

### Scan results tidak sync

**Check**:
1. Lihat pending queue: `SELECT COUNT(*) FROM scan_queue WHERE synced=0;`
2. Check sync manager logs
3. Manual sync: Restart desktop app

---

## 📞 Support

Untuk bantuan lebih lanjut:
- Check logs untuk error details
- Verify semua dependencies installed
- Check network connectivity
- Review configuration files

## 🎉 Success Indicators

✅ Backend health check returns 200 OK
✅ Desktop app starts without errors  
✅ Sync manager shows "online" status
✅ Scan results appear in PostgreSQL database
✅ Queue size decreases after sync
