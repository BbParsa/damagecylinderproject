import os
import sys
import time
import json
import urllib.request
import urllib.error
from datetime import datetime
import data_loader

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(_BASE_DIR, "d1_config.json")

def load_config():
    # 1. Try environment variables first
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    database_id = os.environ.get("CLOUDFLARE_DATABASE_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")

    # 2. Try d1_config.json
    if not (account_id and database_id and api_token) and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                account_id = account_id or cfg.get("account_id")
                database_id = database_id or cfg.get("database_id")
                api_token = api_token or cfg.get("api_token")
        except Exception as e:
            print(f"[WARN] ไม่สามารถอ่าน {CONFIG_FILE} ได้: {e}")

    # Clean inputs (strip whitespace, quotes, trailing URLs/paths like /home)
    if account_id:
        account_id = str(account_id).strip().strip("'\"").split("/")[0].strip()
    if database_id:
        database_id = str(database_id).strip().strip("'\"")
    if api_token:
        api_token = str(api_token).strip().strip("'\"")

    return account_id, database_id, api_token

def execute_d1_query(account_id, database_id, api_token, sql_query):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/d1/database/{database_id}/query"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json; charset=utf-8"
    }

    body = json.dumps({"sql": sql_query}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("success"):
                return True, data
            else:
                return False, data.get("errors", "Unknown error")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        return False, f"HTTP {e.code}: {err_body}"
    except Exception as e:
        return False, str(e)

def build_sql_statements(records):
    # Escape helper for SQLite
    def sql_val(v):
        if v is None:
            return "NULL"
        if isinstance(v, bool):
            return "1" if v else "0"
        if isinstance(v, (int, float)):
            return str(v)
        # String escape
        s = str(v).replace("'", "''")
        return f"'{s}'"

    cols = [
        'id', 'seq_no', 'region', 'zone', 'dealer_type', 'ship_to', 'dealer_name',
        'request_date', 'origin_depot', 'return_depot', 'old_deposit_slip', 'old_receipt_no',
        'cyl_4kg', 'cyl_7kg', 'cyl_15kg', 'cyl_15kgFL', 'cyl_48kg', 'cyl_48kgLW', 'cyl_composite',
        'total_cylinders', 'val_4kg', 'val_7kg', 'val_15kg', 'val_48kg', 'total_deposit_val',
        'exist_4kg', 'exist_7kg', 'exist_15kg', 'exist_48kg', 'total_exist',
        'cost_4kg', 'cost_7kg', 'cost_15kg', 'cost_48kg',
        'return_type', 'form_no', 'contract_fee', 'contract_partial',
        'so_fee', 'so_partial', 'new_deposit_slip', 'new_receipt_no', 'receipt_fee', 'pdms_no',
        'revenue_fee', 'partial_deposit', 'net_refund', 'deposit_reduced',
        'status_raw', 'status_step', 'want_new_cylinder', 'end_date', 'is_completed',
        'cycle_days', 'aging_days'
    ]

    cols_str = ", ".join(cols)
    statements = []
    
    # 1. Truncate / Delete existing to ensure clean sync
    statements.append("DELETE FROM damaged_cylinders;")

    # 2. Chunk inserts into batches of 30 rows
    chunk_size = 30
    for i in range(0, len(records), chunk_size):
        chunk = records[i:i + chunk_size]
        values_rows = []
        for r in chunk:
            row_vals = [sql_val(r.get(c)) for c in cols]
            values_rows.append(f"({', '.join(row_vals)})")
        
        insert_sql = f"INSERT OR REPLACE INTO damaged_cylinders ({cols_str}) VALUES {', '.join(values_rows)};"
        statements.append(insert_sql)

    return "\n".join(statements)

def sync_data():
    account_id, database_id, api_token = load_config()

    if not account_id or not database_id or not api_token or "ใส่_" in account_id or "ใส่_" in api_token:
        print("=" * 60)
        print(" [แจ้งเตือน] ยังไม่ได้ตั้งค่า Cloudflare D1 Credentials")
        print(" กรุณาเปิดไฟล์ d1_config.json แล้วกรอก:")
        print("   - account_id  : ดูได้จาก Cloudflare Dashboard (ขวามือหน้าหลัก)")
        print("   - database_id : ดูได้จากเมนู Storage & Databases > D1")
        print("   - api_token   : ดูได้จาก My Profile > API Tokens (สิทธิ์ D1 Edit)")
        print("=" * 60)
        return False

    now_str = datetime.now().strftime("%H:%M:%S")
    print(f"[{now_str}] กำลังอ่านข้อมูลล่าสุดจาก {data_loader.EXCEL_FILE}...")

    try:
        res = data_loader.parse_list_record(force=True)
        records = res.get("records", [])
    except Exception as e:
        print(f"[{now_str}] ❌ ไม่สามารถอ่านไฟล์ Excel ได้: {e}")
        return False

    print(f"[{now_str}] แปลงข้อมูลสำเร็จ ({len(records)} รายการ) กำลังส่งขึ้น Cloudflare D1...")
    
    sql_batch = build_sql_statements(records)
    success, resp = execute_d1_query(account_id, database_id, api_token, sql_batch)

    now_str = datetime.now().strftime("%H:%M:%S")
    if success:
        print(f"[{now_str}] ✅ ซิงค์ข้อมูลเข้า Cloudflare D1 Database เรียบร้อยสมบูรณ์!")
        return True
    else:
        print(f"[{now_str}] ❌ เกิดข้อผิดพลาดจาก Cloudflare D1 API: {resp}")
        return False

def watch_mode():
    print("==============================================================")
    print("  LPG Dashboard -> Cloudflare D1 Auto-Sync Watcher Started")
    print(f"  ไฟล์ที่ตรวจจับ: {data_loader.EXCEL_FILE}")
    print("  (ตรวจจับการกด Save ใน Excel และอัปเดตเข้า D1 อัตโนมัติ)")
    print("  กด Ctrl + C เพื่อหยุดการทำงาน")
    print("==============================================================")

    # Initial sync
    sync_data()

    if not os.path.exists(data_loader.EXCEL_FILE):
        return

    last_mtime = os.path.getmtime(data_loader.EXCEL_FILE)
    while True:
        try:
            time.sleep(2)
            if os.path.exists(data_loader.EXCEL_FILE):
                cur_mtime = os.path.getmtime(data_loader.EXCEL_FILE)
                if cur_mtime != last_mtime:
                    last_mtime = cur_mtime
                    sync_data()
        except KeyboardInterrupt:
            print("\nหยุดการทำงาน Watcher เรียบร้อยครับ")
            break
        except Exception as e:
            print(f"Error in watcher loop: {e}")

if __name__ == "__main__":
    if "--watch" in sys.argv:
        watch_mode()
    else:
        sync_data()
