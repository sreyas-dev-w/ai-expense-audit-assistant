"""seed master data: accounts, projects, employees

Revision ID: 3fc459b1feb6
Revises: eb26ffaee5ae
Create Date: 2026-09-16 00:00:00.000000+00:00

Source of truth: data/seed/sql/seed_data.sql

Seeds the reference/master tables the expense pipeline depends on. The SQL
is equivalent to data/seed/sql/seed_data.sql, minus the explicit transaction
(Alembic wraps each migration in one) and with idempotent inserts so a
partial reseed never fails.

NOTE ON ORDER: projects.project_lead_id -> employees.employee_id and
employees.project_code -> projects.project_code form a circular FK.
Projects are inserted with project_lead_id NULL first, then employees,
then project leads are backfilled.

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '3fc459b1feb6'
down_revision: Union[str, None] = 'eb26ffaee5ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO accounts (account_id, account_name, fiscal_year, budget_allocated, remaining_budget, currency) VALUES
        ('ACC001', 'Global Retail Modernization',   2025, 50000000.00, 12500000.00, 'INR'),
        ('ACC002', 'Healthcare Cloud Migration',    2025, 35000000.00,  8000000.00, 'INR'),
        ('ACC003', 'BFSI Digital Transformation',   2025, 42000000.00,        0.00, 'INR'),
        ('ACC004', 'Telecom Network Analytics',     2025, 28000000.00, 28000000.00, 'INR'),
        ('ACC005', 'Manufacturing IoT Platform',    2025, 60000000.00, 15750000.50, 'INR'),
        ('ACC006', 'Public Sector eGovernance',     2025,        0.00,        0.00, 'INR')
        ON CONFLICT (account_id) DO NOTHING
        """
    )

    op.execute(
        """
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
        ('PRJ015', 'Citizen Services Portal',           'ACC006', NULL)
        ON CONFLICT (project_code) DO NOTHING
        """
    )

    op.execute(
        """
        INSERT INTO employees (employee_id, employee_name, job_level, is_manager, manager_id, project_code) VALUES
        ('EMP001', 'Rajesh Iyer',        'L6', TRUE,  NULL,     NULL),
        ('EMP002', 'Meera Krishnan',     'L6', FALSE, NULL,     NULL),
        ('EMP003', 'Arvind Menon',       'L5', TRUE,  'EMP001', NULL),
        ('EMP004', 'Sunita Rao',         'L5', TRUE,  'EMP001', NULL),
        ('EMP005', 'Vikram Nair',        'L5', TRUE,  'EMP001', NULL),
        ('EMP006', 'Anita Desai',        'L4', TRUE,  'EMP003', 'PRJ001'),
        ('EMP007', 'Rohit Sharma',       'L4', TRUE,  'EMP003', 'PRJ002'),
        ('EMP008', 'Kavya Pillai',       'L4', TRUE,  'EMP003', 'PRJ004'),
        ('EMP009', 'Deepak Verma',       'L4', TRUE,  'EMP004', 'PRJ006'),
        ('EMP010', 'Priya Subramaniam',  'L4', TRUE,  'EMP004', 'PRJ008'),
        ('EMP011', 'Manoj Kumar',        'L4', TRUE,  'EMP005', 'PRJ010'),
        ('EMP012', 'Lakshmi Narayan',    'L4', TRUE,  'EMP005', 'PRJ012'),
        ('EMP013', 'Suresh Babu',        'L3', TRUE,  'EMP006', 'PRJ001'),
        ('EMP014', 'Divya Chandran',     'L3', FALSE, 'EMP007', 'PRJ002'),
        ('EMP015', 'Karthik Raghavan',   'L3', TRUE,  'EMP008', 'PRJ004'),
        ('EMP016', 'Nandini Rajan',      'L3', FALSE, 'EMP009', 'PRJ006'),
        ('EMP017', 'Faisal Ahmed',       'L3', TRUE,  'EMP010', 'PRJ008'),
        ('EMP018', 'Geetha Vijay',       'L3', FALSE, 'EMP011', 'PRJ010'),
        ('EMP019', 'Harish Chandra',     'L3', TRUE,  'EMP012', 'PRJ012'),
        ('EMP020', 'Swathi Menon',       'L2', FALSE, 'EMP013', 'PRJ001'),
        ('EMP021', 'Aditya Rao',         'L2', FALSE, 'EMP006', 'PRJ003'),
        ('EMP022', 'Naveen Krishnan',    'L3', TRUE,  'EMP008', 'PRJ005'),
        ('EMP023', 'Ramya Iyer',         'L3', TRUE,  'EMP009', 'PRJ007'),
        ('EMP024', 'Sandeep Joshi',      'L2', TRUE,  'EMP004', 'PRJ009'),
        ('EMP025', 'Pooja Reddy',        'L3', TRUE,  'EMP011', 'PRJ011'),
        ('EMP026', 'Arjun Menon',        'L3', TRUE,  'EMP012', 'PRJ013'),
        ('EMP027', 'Bhavana Nair',       'L3', TRUE,  'EMP012', 'PRJ014'),
        ('EMP028', 'Vishal Kumar',       'L1', FALSE, 'EMP020', 'PRJ001'),
        ('EMP029', 'Anjali Pillai',      'L1', FALSE, 'EMP014', 'PRJ002'),
        ('EMP030', 'Kiran Babu',         'L1', FALSE, 'EMP015', 'PRJ004'),
        ('EMP031', 'Sneha Kapoor',       'L1', FALSE, 'EMP003', NULL),
        ('EMP032', 'Ferdinand D''Souza', 'L2', FALSE, NULL,     'PRJ015')
        ON CONFLICT (employee_id) DO NOTHING
        """
    )

    # Backfill project leads now that the employees exist. PRJ015 stays
    # unassigned (intentionally).
    op.execute("UPDATE projects SET project_lead_id = 'EMP006' WHERE project_code = 'PRJ001'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP007' WHERE project_code = 'PRJ002'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP021' WHERE project_code = 'PRJ003'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP008' WHERE project_code = 'PRJ004'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP022' WHERE project_code = 'PRJ005'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP009' WHERE project_code = 'PRJ006'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP023' WHERE project_code = 'PRJ007'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP010' WHERE project_code = 'PRJ008'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP024' WHERE project_code = 'PRJ009'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP011' WHERE project_code = 'PRJ010'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP025' WHERE project_code = 'PRJ011'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP012' WHERE project_code = 'PRJ012'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP026' WHERE project_code = 'PRJ013'")
    op.execute("UPDATE projects SET project_lead_id = 'EMP027' WHERE project_code = 'PRJ014'")


def downgrade() -> None:
    # Delete only the seeded rows (children first). Foreign keys are
    # SET NULL / CASCADE so removing the master data cannot strand orphans.
    op.execute("DELETE FROM projects WHERE project_lead_id IS NOT NULL AND project_code LIKE 'PRJ%'")
    op.execute("DELETE FROM employees WHERE employee_id LIKE 'EMP%'")
    op.execute("DELETE FROM projects WHERE project_code LIKE 'PRJ%'")
    op.execute("DELETE FROM accounts WHERE account_id LIKE 'ACC%'")