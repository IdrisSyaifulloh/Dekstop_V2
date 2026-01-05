# Testing Guide - Backend & Desktop Integration

Panduan untuk testing sistem hybrid online-offline setelah implementasi.

## ⚙️ Setup

### 1. Install Backend Dependencies

```bash
cd backend
pip install -r requirements.txt
```

**Required packages:**
- fastapi
- uvicorn
- sqlalchemy
- psycopg2-binary
- python-dotenv
- pydantic

### 2. Install Desktop App Dependencies

```bash
cd ..  # Back to desktop_app root
pip install requests urllib3
```

### 3. Setup PostgreSQL Database

```sql
-- Create database
CREATE DATABASE Db_Scanning;

-- Verify connection
psql -U postgres -d Db_Scanning
```

Update `backend/.env` with your credentials.

---

## 🧪 Test Scenarios

### Test 1: Backend Standalone

**Start backend:**
```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

**Test health endpoint:**
```bash
curl http://localhost:8000/health
```

**Expected output:**
```json
{
  "status": "healthy",
  "service": "Malware Detection API",
  "version": "1.0.0"
}
```

**Test API docs:**
Open browser: http://localhost:8000/docs

---

### Test 2: Local Queue (Offline Mode)

**Test local queue independently:**
```bash
cd core
python local_queue.py
```

**Expected output:**
```
Added: True
Pending scans: 1
Stats: {'total': 1, 'pending': 1, 'synced': 0}
```

**Check database file:**
```bash
# File should be created
ls ../local_queue.db
```

**Inspect with SQLite:**
```bash
sqlite3 ../local_queue.db
sqlite> SELECT * FROM scan_queue;
sqlite> .exit
```

---

### Test 3: API Client (Online Mode)

**Prerequisites:** Backend must be running

**Test API client:**
```bash
cd core
python api_client.py
```

**Expected output:**
```
Backend health: {'status': 'healthy', ...}
Backend online: True
Save result: {'message': 'File scanned successfully', ...}
History: [...]
```

---

### Test 4: Sync Manager

**Prerequisites:** Backend running

**Test sync manager:**
```bash
cd core
python sync_manager.py
```

**Expected output:**
```
INFO - SyncManager initialized (backend: http://localhost:8000)
INFO - Sync manager started
INFO - Sync loop started
INFO - Syncing X pending scans...
INFO - Sync complete: X synced, 0 failed
```

**Press Ctrl+C to stop**

---

### Test 5: Full Integration (Online)

**Terminal 1 - Start Backend:**
```bash
cd backend
python -m uvicorn main:app --reload
```

**Terminal 2 - Start Desktop App:**
```bash
python main.py
```

**Expected console output:**
```
✅ Sync manager started (backend: http://localhost:8000)
```

**Test flow:**
1. Scan a file using the GUI
2. Check console for sync logs
3. Verify in PostgreSQL:
   ```sql
   SELECT * FROM scan_results ORDER BY created_at DESC LIMIT 5;
   ```

---

### Test 6: Offline Mode

**Stop backend server (Ctrl+C in Terminal 1)**

**In Desktop App:**
1. Scan a file
2. File should scan successfully
3. Check console: `Backend offline, skipping sync`

**Check local queue:**
```bash
sqlite3 local_queue.db
sqlite> SELECT COUNT(*) FROM scan_queue WHERE synced=0;
```

Should show pending scans.

---

### Test 7: Auto-Sync (Connection Restored)

**With desktop app still running:**

**Terminal 1 - Restart Backend:**
```bash
cd backend
python -m uvicorn main:app --reload
```

**Watch desktop app console:**
```
INFO - Backend online
INFO - Syncing X pending scans...
INFO - Sync complete: X synced, 0 failed
```

**Verify in PostgreSQL:**
```sql
SELECT * FROM scan_results ORDER BY created_at DESC;
```

**Check local queue:**
```bash
sqlite3 local_queue.db
sqlite> SELECT COUNT(*) FROM scan_queue WHERE synced=0;
```

Should be 0 (all synced).

---

### Test 8: Deduplication

**Scan the same file twice (online mode)**

**First scan:**
```
Response: {"message": "File scanned successfully", ...}
```

**Second scan (same file):**
```
Response: {"message": "File has already been scanned", ...}
```

**Verify no duplicate in database:**
```sql
SELECT file_hash, COUNT(*) FROM scan_results GROUP BY file_hash HAVING COUNT(*) > 1;
```

Should return empty (no duplicates).

---

### Test 9: Configuration

**Test config manager:**
```bash
cd core
python config_manager.py
```

**Expected output:**
```
Backend URL: http://localhost:8000
Sync interval: 30s
Sync enabled: True
Log level: INFO
```

**Modify config.ini and test again:**
```ini
[Backend]
url = http://192.168.1.100:8000
```

Re-run and verify URL changed.

---

### Test 10: Stress Test

**Add multiple scans while offline:**

1. Stop backend
2. Scan 10+ files
3. Check queue size:
   ```bash
   sqlite3 local_queue.db
   sqlite> SELECT COUNT(*) FROM scan_queue WHERE synced=0;
   ```

4. Start backend
5. Wait for auto-sync (max 30 seconds)
6. Verify all synced:
   ```sql
   SELECT COUNT(*) FROM scan_results;
   ```

---

## ✅ Success Criteria

| Test | Criteria | Status |
|------|----------|--------|
| Backend Health | Returns 200 OK | ⬜ |
| Local Queue | Creates SQLite DB | ⬜ |
| API Client | Connects to backend | ⬜ |
| Sync Manager | Background sync works | ⬜ |
| Online Mode | Direct to PostgreSQL | ⬜ |
| Offline Mode | Saves to local queue | ⬜ |
| Auto-Sync | Syncs when online | ⬜ |
| Deduplication | No duplicates | ⬜ |
| Configuration | Reads config.ini | ⬜ |
| Stress Test | Handles bulk sync | ⬜ |

---

## 🐛 Common Issues

### Issue: Backend won't start

**Error:** `ModuleNotFoundError: No module named 'fastapi'`

**Solution:**
```bash
cd backend
pip install -r requirements.txt
```

### Issue: Database connection failed

**Error:** `could not connect to server`

**Solution:**
1. Check PostgreSQL running
2. Verify credentials in `.env`
3. Check database exists

### Issue: Desktop app can't import modules

**Error:** `ModuleNotFoundError: No module named 'requests'`

**Solution:**
```bash
pip install requests urllib3
```

### Issue: Sync not working

**Check:**
1. Backend running: `curl http://localhost:8000/health`
2. Config URL correct in `config.ini`
3. Firewall not blocking port 8000

---

## 📊 Monitoring During Tests

### Watch Sync Logs
```bash
# Desktop app will show:
INFO - SyncManager - Syncing X pending scans...
INFO - SyncManager - Sync complete: X synced, Y failed
```

### Monitor Database
```sql
-- Watch for new records
SELECT COUNT(*), label FROM scan_results GROUP BY label;

-- Check recent activity
SELECT filename, label, created_at 
FROM scan_results 
ORDER BY created_at DESC 
LIMIT 10;
```

### Monitor Queue
```bash
# Watch pending count
watch -n 1 'sqlite3 local_queue.db "SELECT COUNT(*) FROM scan_queue WHERE synced=0"'
```

---

## 🎯 Next Steps After Testing

Once all tests pass:

1. ✅ Update task.md to mark tests complete
2. ✅ Create walkthrough.md with screenshots
3. ✅ Deploy to production (follow DEPLOYMENT.md)
4. ✅ Add UI status indicators (Phase 7)

---

## 💡 Tips

- Keep backend terminal visible to see API requests
- Use `--reload` flag during development
- Check both console logs and database
- Test network scenarios (WiFi on/off)
- Test with different file types
