-- =====================================================================
-- Seed data for: accounts, projects, employees   (Neon / Postgres)
-- Currency is restricted to INR only, per requirement.
--
-- NOTE ON ORDER: projects.project_lead_id -> employees.employee_id
--                 employees.project_code   -> projects.project_code
-- This is a circular FK. Fix: insert projects with lead = NULL first,
-- then insert employees, then backfill project_lead_id in step 4.
--
-- Assumes the tables/enums already exist exactly as you described
-- (currency ENUM, job_level ENUM with L1-L6). Run with:
--   psql "$DATABASE_URL" -f seed_data.sql
-- or paste directly into the Neon SQL editor.
-- =====================================================================

-- Uncomment to wipe existing rows before reseeding (children first):
-- TRUNCATE employees, projects, accounts RESTART IDENTITY CASCADE;

BEGIN;

-- ---------------------------------------------------------------------
-- 1. ACCOUNTS (6 rows)
--    Covers: multiple fiscal years, fully-spent budget, fully-unspent
--    budget, fractional remaining balance, zero-budget account.
-- ---------------------------------------------------------------------
INSERT INTO accounts (account_id, account_name, fiscal_year, budget_allocated, remaining_budget, currency) VALUES
('ACC001', 'Global Retail Modernization',   2025, 50000000.00, 12500000.00, 'INR'),
('ACC002', 'Healthcare Cloud Migration',    2025, 35000000.00,  8000000.00, 'INR'),
('ACC003', 'BFSI Digital Transformation',   2025, 42000000.00,        0.00, 'INR'),  -- fully utilized
('ACC004', 'Telecom Network Analytics',     2025, 28000000.00, 28000000.00, 'INR'),  -- nothing spent yet
('ACC005', 'Manufacturing IoT Platform',    2025, 60000000.00, 15750000.50, 'INR'),  -- fractional remainder
('ACC006', 'Public Sector eGovernance',     2025,        0.00,        0.00, 'INR')   -- zero-budget account
ON CONFLICT (account_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- 2. PROJECTS (15 rows, 2-4 per account)
--    project_lead_id is NULL here; backfilled in step 4.
-- ---------------------------------------------------------------------
INSERT INTO projects (project_code, project_name, account_id, project_lead_id) VALUES
('PRJ001', 'POS System Upgrade',                'ACC001', NULL),
('PRJ002', 'E-commerce Platform Revamp',        'ACC001', NULL),
('PRJ003', 'Inventory AI Forecasting',          'ACC001', NULL),
('PRJ004', 'EHR Cloud Migration',               'ACC002', NULL),
('PRJ005', 'Patient Portal Redesign',           'ACC002', NULL),
('PRJ006', 'Core Banking Upgrade',              'ACC003', NULL),
('PRJ007', 'Fraud Detection Engine',            'ACC003', NULL),
('PRJ008', 'Mobile Banking App',                'ACC003', NULL),
('PRJ009', 'Regulatory Reporting Automation',   'ACC003', NULL),
('PRJ010', '5G Network Monitoring',             'ACC004', NULL),
('PRJ011', 'Customer Churn Prediction',         'ACC004', NULL),
('PRJ012', 'Predictive Maintenance System',     'ACC005', NULL),
('PRJ013', 'Shop Floor IoT Sensors',            'ACC005', NULL),
('PRJ014', 'Supply Chain Visibility Dashboard', 'ACC005', NULL),
('PRJ015', 'Citizen Services Portal',           'ACC006', NULL)   -- lead intentionally unassigned
ON CONFLICT (project_code) DO NOTHING;

-- ---------------------------------------------------------------------
-- 3. EMPLOYEES (32 rows)
--    Covers every job_level (L1-L6), is_manager TRUE/FALSE, manager_id
--    NULL and populated, project_code NULL and populated. Inserted
--    top-down (org-chart order) so every manager_id already exists
--    by the time its report row is inserted.
--    Dummy login: username = lower(employee_id), password = 'password@123'
-- ---------------------------------------------------------------------
INSERT INTO employees (employee_id, employee_name, job_level, is_manager, manager_id, project_code, username, password) VALUES
-- L6: top of hierarchy, no manager
('EMP001', 'Rajesh Iyer',        'L6', TRUE,  NULL,     NULL,     'emp001', 'password@123'),      -- Delivery Head
('EMP002', 'Meera Krishnan',     'L6', FALSE, NULL,     NULL,     'emp002', 'password@123'),      -- Chief Architect (advisor, unassigned)

-- L5: Program Directors, oversee an account's projects (not tied to one)
('EMP003', 'Arvind Menon',       'L5', TRUE,  'EMP001', NULL,     'emp003', 'password@123'),
('EMP004', 'Sunita Rao',         'L5', TRUE,  'EMP001', NULL,     'emp004', 'password@123'),
('EMP005', 'Vikram Nair',        'L5', TRUE,  'EMP001', NULL,     'emp005', 'password@123'),

-- L4: Project Managers
('EMP006', 'Anita Desai',        'L4', TRUE,  'EMP003', 'PRJ001', 'emp006', 'password@123'),
('EMP007', 'Rohit Sharma',       'L4', TRUE,  'EMP003', 'PRJ002', 'emp007', 'password@123'),
('EMP008', 'Kavya Pillai',       'L4', TRUE,  'EMP003', 'PRJ004', 'emp008', 'password@123'),
('EMP009', 'Deepak Verma',       'L4', TRUE,  'EMP004', 'PRJ006', 'emp009', 'password@123'),
('EMP010', 'Priya Subramaniam',  'L4', TRUE,  'EMP004', 'PRJ008', 'emp010', 'password@123'),
('EMP011', 'Manoj Kumar',        'L4', TRUE,  'EMP005', 'PRJ010', 'emp011', 'password@123'),
('EMP012', 'Lakshmi Narayan',    'L4', TRUE,  'EMP005', 'PRJ012', 'emp012', 'password@123'),

-- L3: Team Leads / senior ICs
('EMP013', 'Suresh Babu',        'L3', TRUE,  'EMP006', 'PRJ001', 'emp013', 'password@123'),
('EMP014', 'Divya Chandran',     'L3', FALSE, 'EMP007', 'PRJ002', 'emp014', 'password@123'),
('EMP015', 'Karthik Raghavan',   'L3', TRUE,  'EMP008', 'PRJ004', 'emp015', 'password@123'),
('EMP016', 'Nandini Rajan',      'L3', FALSE, 'EMP009', 'PRJ006', 'emp016', 'password@123'),
('EMP017', 'Faisal Ahmed',       'L3', TRUE,  'EMP010', 'PRJ008', 'emp017', 'password@123'),
('EMP018', 'Geetha Vijay',       'L3', FALSE, 'EMP011', 'PRJ010', 'emp018', 'password@123'),
('EMP019', 'Harish Chandra',     'L3', TRUE,  'EMP012', 'PRJ012', 'emp019', 'password@123'),
('EMP022', 'Naveen Krishnan',    'L3', TRUE,  'EMP008', 'PRJ005', 'emp022', 'password@123'),
('EMP023', 'Ramya Iyer',         'L3', TRUE,  'EMP009', 'PRJ007', 'emp023', 'password@123'),
('EMP025', 'Pooja Reddy',        'L3', TRUE,  'EMP011', 'PRJ011', 'emp025', 'password@123'),
('EMP026', 'Arjun Menon',        'L3', TRUE,  'EMP012', 'PRJ013', 'emp026', 'password@123'),
('EMP027', 'Bhavana Nair',       'L3', TRUE,  'EMP012', 'PRJ014', 'emp027', 'password@123'),

-- L2: mid-level
('EMP020', 'Swathi Menon',       'L2', FALSE, 'EMP013', 'PRJ001', 'emp020', 'password@123'),
('EMP021', 'Aditya Rao',         'L2', FALSE, 'EMP006', 'PRJ003', 'emp021', 'password@123'),  -- non-manager leading PRJ003
('EMP024', 'Sandeep Joshi',      'L2', TRUE,  'EMP004', 'PRJ009', 'emp024', 'password@123'),  -- matrix report, skips L4/L3
('EMP032', 'Ferdinand D''Souza', 'L2', FALSE, NULL,     'PRJ015', 'emp032', 'password@123'),  -- contractor: no manager, has a project

-- L1: junior
('EMP028', 'Vishal Kumar',       'L1', FALSE, 'EMP020', 'PRJ001', 'emp028', 'password@123'),
('EMP029', 'Anjali Pillai',      'L1', FALSE, 'EMP014', 'PRJ002', 'emp029', 'password@123'),
('EMP030', 'Kiran Babu',         'L1', FALSE, 'EMP015', 'PRJ004', 'emp030', 'password@123'),
('EMP031', 'Sneha Kapoor',       'L1', FALSE, 'EMP003', NULL,     'emp031', 'password@123')       -- bench, awaiting allocation
ON CONFLICT (employee_id) DO NOTHING;

-- ---------------------------------------------------------------------
-- 4. Backfill project_lead_id now that the employees exist
-- ---------------------------------------------------------------------
UPDATE projects SET project_lead_id = 'EMP006' WHERE project_code = 'PRJ001';
UPDATE projects SET project_lead_id = 'EMP007' WHERE project_code = 'PRJ002';
UPDATE projects SET project_lead_id = 'EMP021' WHERE project_code = 'PRJ003';
UPDATE projects SET project_lead_id = 'EMP008' WHERE project_code = 'PRJ004';
UPDATE projects SET project_lead_id = 'EMP022' WHERE project_code = 'PRJ005';
UPDATE projects SET project_lead_id = 'EMP009' WHERE project_code = 'PRJ006';
UPDATE projects SET project_lead_id = 'EMP023' WHERE project_code = 'PRJ007';
UPDATE projects SET project_lead_id = 'EMP010' WHERE project_code = 'PRJ008';
UPDATE projects SET project_lead_id = 'EMP024' WHERE project_code = 'PRJ009';
UPDATE projects SET project_lead_id = 'EMP011' WHERE project_code = 'PRJ010';
UPDATE projects SET project_lead_id = 'EMP025' WHERE project_code = 'PRJ011';
UPDATE projects SET project_lead_id = 'EMP012' WHERE project_code = 'PRJ012';
UPDATE projects SET project_lead_id = 'EMP026' WHERE project_code = 'PRJ013';
UPDATE projects SET project_lead_id = 'EMP027' WHERE project_code = 'PRJ014';
-- PRJ015 stays with project_lead_id = NULL (not yet assigned)

COMMIT;
