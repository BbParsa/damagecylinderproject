import io
import os
import ctypes
import warnings
from ctypes import wintypes
from datetime import datetime
import openpyxl

warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_LOCAL_EXCEL = os.path.join(_BASE_DIR, "DamagedCylinderProjectData.xlsx")
_PARENT_EXCEL = os.path.normpath(os.path.join(_BASE_DIR, "..", "DamagedCylinderProjectData.xlsx"))

if os.path.exists(_LOCAL_EXCEL):
    EXCEL_FILE = _LOCAL_EXCEL
elif os.path.exists(_PARENT_EXCEL):
    EXCEL_FILE = _PARENT_EXCEL
else:
    EXCEL_FILE = "DamagedCylinderProjectData.xlsx"

GENERIC_READ = 0x80000000
FILE_SHARE_READ = 1
FILE_SHARE_WRITE = 2
FILE_SHARE_DELETE = 4
OPEN_EXISTING = 3
FILE_ATTRIBUTE_NORMAL = 0x80

_cache_mtime = None
_cache_records = []

def read_excel_shared(filename):
    handle = ctypes.windll.kernel32.CreateFileW(
        filename, GENERIC_READ,
        FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
        None, OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, None
    )
    if handle == -1:
        err = ctypes.windll.kernel32.GetLastError()
        raise PermissionError(f"Cannot open file {filename}, Windows error code: {err}")
    try:
        size = ctypes.windll.kernel32.GetFileSize(handle, None)
        buf = ctypes.create_string_buffer(size)
        bytes_read = wintypes.DWORD()
        ctypes.windll.kernel32.ReadFile(handle, buf, size, ctypes.byref(bytes_read), None)
        return io.BytesIO(buf.raw[:bytes_read.value])
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)

def parse_list_record(filename=EXCEL_FILE, force=False):
    global _cache_mtime, _cache_records

    if not os.path.exists(filename):
        return {"error": f"File {filename} not found", "records": []}

    current_mtime = os.path.getmtime(filename)
    if not force and _cache_mtime == current_mtime and _cache_records:
        return {
            "mtime": current_mtime,
            "mtime_str": datetime.fromtimestamp(current_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            "records": _cache_records,
            "cached": True
        }

    bio = read_excel_shared(filename)
    wb = openpyxl.load_workbook(bio, data_only=True)
    ws = wb['ListRecord']

    headers = [ws.cell(2, c).value for c in range(1, 59)]
    
    cyl_cols = ['4 kg.', '7 kg.', '15 kg.', '15 kgFL.', '48 kg.', '48 kg L/W.', 'Composite']
    val_cols = ['4 kg.Value', '7 kg.Value', '15 kg.Value', '15 kgFL.Value', '48 kg.Value', '48 kg L/W.Value', 'Composite.Value']
    cost_cols = ['4 kg.Cost', '7 kg.Cost', '15 kg.Cost', '15 kgFL.Cost', '48 kg.Cost', '48 kg L/W.Cost', 'Composite.Cost']
    exist_cols = ['4 kg.Exist', '7 kg.Exist', '15 kg.Exist', '15 kgFL.Exist', '48 kg.Exist', '48 kg L/W.Exist', 'Composite.Exist']

    records = []
    seen_ids = set()
    reference_date = datetime.now()

    for r_idx in range(3, ws.max_row + 1):
        row_vals = [ws.cell(r_idx, c).value for c in range(1, 59)]
        row_dict = dict(zip(headers, row_vals))

        dealer_name = row_dict.get('ชื่อผู้แทนจำหน่าย')
        if not dealer_name or str(dealer_name).strip() == '':
            continue

        def safe_float(v):
            if v is None: return 0.0
            try: return float(v)
            except: return 0.0

        def safe_int(v):
            if v is None: return 0
            try: return int(float(v))
            except: return 0

        # Dates
        req_date = row_dict.get('วันที่แจ้ง')
        req_date_str = req_date.strftime('%Y-%m-%d') if isinstance(req_date, datetime) else (str(req_date)[:10] if req_date else '')

        end_date = row_dict.get('วันที่จบProcess')
        end_date_str = end_date.strftime('%Y-%m-%d') if isinstance(end_date, datetime) else (str(end_date)[:10] if end_date else '')

        is_completed = bool(end_date_str)

        cycle_days = None
        aging_days = None
        if is_completed and isinstance(req_date, datetime) and isinstance(end_date, datetime):
            cycle_days = (end_date - req_date).days
        elif isinstance(req_date, datetime):
            aging_days = (reference_date - req_date).days

        # Cylinders
        c_4 = safe_int(row_dict.get('4 kg.'))
        c_7 = safe_int(row_dict.get('7 kg.'))
        c_15 = safe_int(row_dict.get('15 kg.'))
        c_15fl = safe_int(row_dict.get('15 kgFL.'))
        c_48 = safe_int(row_dict.get('48 kg.'))
        c_48lw = safe_int(row_dict.get('48 kg L/W.'))
        c_comp = safe_int(row_dict.get('Composite'))
        tot_cyl = c_4 + c_7 + c_15 + c_15fl + c_48 + c_48lw + c_comp

        # Values
        v_4 = safe_float(row_dict.get('4 kg.Value'))
        v_7 = safe_float(row_dict.get('7 kg.Value'))
        v_15 = safe_float(row_dict.get('15 kg.Value'))
        v_48 = safe_float(row_dict.get('48 kg.Value'))
        tot_val = safe_float(row_dict.get('4 kg.Value')) + safe_float(row_dict.get('7 kg.Value')) + safe_float(row_dict.get('15 kg.Value')) + safe_float(row_dict.get('48 kg.Value'))

        # Exist
        e_4 = safe_int(row_dict.get('4 kg.Exist'))
        e_7 = safe_int(row_dict.get('7 kg.Exist'))
        e_15 = safe_int(row_dict.get('15 kg.Exist'))
        e_48 = safe_int(row_dict.get('48 kg.Exist'))
        tot_exist = e_4 + e_7 + e_15 + e_48

        # Costs
        co_4 = safe_float(row_dict.get('4 kg.Cost'))
        co_7 = safe_float(row_dict.get('7 kg.Cost'))
        co_15 = safe_float(row_dict.get('15 kg.Cost'))
        co_48 = safe_float(row_dict.get('48 kg.Cost'))

        # Financial totals
        rev_fee = safe_float(row_dict.get('รวมรายได้ค่าดำเนินการคืนถังทำลาย'))
        part_dep = safe_float(row_dict.get('รวมเงินถัง Partial'))
        net_ref = safe_float(row_dict.get('รวมเงินมัดจำที่เหลือจากหักลบกลบหนี้'))
        dep_red = safe_float(row_dict.get('เจ้าหนี้เงินมัดจาที่ลดลงได้'))

        # IDs - ensure uniqueness even if Excel has duplicate/typo row numbers
        raw_id = row_dict.get('ลำดับ')
        parsed_id = safe_int(raw_id) if raw_id is not None else None
        if parsed_id is not None and parsed_id > 0 and parsed_id not in seen_ids:
            item_id = parsed_id
        else:
            item_id = len(records) + 1
        seen_ids.add(item_id)

        ship_to = safe_int(row_dict.get('Ship-To'))

        status_raw = str(row_dict.get('สถานะดำเนินการ') or 'ไม่ระบุ')
        status_step = 0
        if '.' in status_raw:
            try: status_step = int(status_raw.split('.')[0])
            except: pass

        item = {
            'id': item_id,
            'seq_no': str(row_dict.get('เลขลำดับคืนถังทำลาย') or ''),
            'region': str(row_dict.get('ส่วนขาย') or ''),
            'zone': str(row_dict.get('เขตการขาย') or ''),
            'dealer_type': str(row_dict.get('ประเภทผู้แทนจำหน่าย') or ''),
            'ship_to': str(ship_to) if ship_to != 0 else '',
            'dealer_name': str(dealer_name).strip(),
            'request_date': req_date_str,
            'origin_depot': str(row_dict.get('คลังต้นทาง') or ''),
            'return_depot': str(row_dict.get('คลัง/โรงซ่อมที่คืน') or ''),
            'old_deposit_slip': str(safe_int(row_dict.get('ใบมัดจำที่คืน')) or ''),
            'old_receipt_no': str(safe_int(row_dict.get('ใบเสร็จที่คืน')) or ''),
            'cyl_4kg': c_4,
            'cyl_7kg': c_7,
            'cyl_15kg': c_15,
            'cyl_15kgFL': c_15fl,
            'cyl_48kg': c_48,
            'cyl_48kgLW': c_48lw,
            'cyl_composite': c_comp,
            'total_cylinders': tot_cyl,
            'val_4kg': v_4,
            'val_7kg': v_7,
            'val_15kg': v_15,
            'val_48kg': v_48,
            'total_deposit_val': tot_val,
            'exist_4kg': e_4,
            'exist_7kg': e_7,
            'exist_15kg': e_15,
            'exist_48kg': e_48,
            'total_exist': tot_exist,
            'cost_4kg': co_4,
            'cost_7kg': co_7,
            'cost_15kg': co_15,
            'cost_48kg': co_48,
            'return_type': str(row_dict.get('เต็มจำนวน/Partial') or ''),
            'form_no': str(row_dict.get('เลขแบบฟอร์ม') or ''),
            'contract_fee': str(row_dict.get('เลขcontract ค่าบริการคืนถังทำลาย') or ''),
            'contract_partial': str(row_dict.get('เลขcontract มัดจำ Partial') or ''),
            'so_fee': str(row_dict.get('SaleOrder_ค่าบริการคืนถังทำลาย') or ''),
            'so_partial': str(row_dict.get('SaleOrder_ค่ามัดจำPartial') or ''),
            'new_deposit_slip': str(row_dict.get('ใบมัดจำใหม่') or ''),
            'new_receipt_no': str(row_dict.get('ใบเสร็จรับเงินใหม่') or ''),
            'receipt_fee': str(row_dict.get('ใบเสร็จรับเงินค่าดำเนินการคืนถังทำลาย') or ''),
            'pdms_no': str(row_dict.get('PDMS_No.') or ''),
            'revenue_fee': rev_fee,
            'partial_deposit': part_dep,
            'net_refund': net_ref,
            'deposit_reduced': dep_red,
            'status_raw': status_raw,
            'status_step': status_step,
            'want_new_cylinder': str(row_dict.get('ประสงค์มัดจำถังใหม่') or ''),
            'end_date': end_date_str,
            'is_completed': is_completed,
            'cycle_days': cycle_days,
            'aging_days': aging_days
        }
        records.append(item)

    wb.close()
    _cache_mtime = current_mtime
    _cache_records = records

    return {
        "mtime": current_mtime,
        "mtime_str": datetime.fromtimestamp(current_mtime).strftime("%Y-%m-%d %H:%M:%S"),
        "records": records,
        "cached": False
    }

if __name__ == '__main__':
    res = parse_list_record(force=True)
    print(f"Loaded {len(res['records'])} records at {res['mtime_str']}")
