-- Schema for Cloudflare D1 Database: damaged_cylinders
DROP TABLE IF EXISTS damaged_cylinders;

CREATE TABLE damaged_cylinders (
    id INTEGER PRIMARY KEY,
    seq_no TEXT,
    region TEXT,
    zone TEXT,
    dealer_type TEXT,
    ship_to TEXT,
    dealer_name TEXT,
    request_date TEXT,
    origin_depot TEXT,
    return_depot TEXT,
    old_deposit_slip TEXT,
    old_receipt_no TEXT,
    
    -- Cylinder counts
    cyl_4kg INTEGER DEFAULT 0,
    cyl_7kg INTEGER DEFAULT 0,
    cyl_15kg INTEGER DEFAULT 0,
    cyl_15kgFL INTEGER DEFAULT 0,
    cyl_48kg INTEGER DEFAULT 0,
    cyl_48kgLW INTEGER DEFAULT 0,
    cyl_composite INTEGER DEFAULT 0,
    total_cylinders INTEGER DEFAULT 0,

    -- Deposit values
    val_4kg REAL DEFAULT 0,
    val_7kg REAL DEFAULT 0,
    val_15kg REAL DEFAULT 0,
    val_48kg REAL DEFAULT 0,
    total_deposit_val REAL DEFAULT 0,

    -- Remaining cylinders (Exist)
    exist_4kg INTEGER DEFAULT 0,
    exist_7kg INTEGER DEFAULT 0,
    exist_15kg INTEGER DEFAULT 0,
    exist_48kg INTEGER DEFAULT 0,
    total_exist INTEGER DEFAULT 0,

    -- Fix rate costs
    cost_4kg REAL DEFAULT 0,
    cost_7kg REAL DEFAULT 0,
    cost_15kg REAL DEFAULT 0,
    cost_48kg REAL DEFAULT 0,

    -- Forms & References
    return_type TEXT,
    form_no TEXT,
    contract_fee TEXT,
    contract_partial TEXT,
    so_fee TEXT,
    so_partial TEXT,
    new_deposit_slip TEXT,
    new_receipt_no TEXT,
    receipt_fee TEXT,
    pdms_no TEXT,

    -- Financial totals
    revenue_fee REAL DEFAULT 0,
    partial_deposit REAL DEFAULT 0,
    net_refund REAL DEFAULT 0,
    deposit_reduced REAL DEFAULT 0,

    -- Status & Tracking
    status_raw TEXT,
    status_step INTEGER DEFAULT 0,
    want_new_cylinder TEXT,
    end_date TEXT,
    is_completed INTEGER DEFAULT 0,
    cycle_days INTEGER,
    aging_days INTEGER,
    updated_at TEXT DEFAULT (datetime('now', '+7 hours'))
);

-- Index for high performance queries
CREATE INDEX IF NOT EXISTS idx_region ON damaged_cylinders(region);
CREATE INDEX IF NOT EXISTS idx_depot ON damaged_cylinders(return_depot);
CREATE INDEX IF NOT EXISTS idx_status ON damaged_cylinders(status_step);
