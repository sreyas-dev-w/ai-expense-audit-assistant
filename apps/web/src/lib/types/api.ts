/**
 * Hand-written mirrors of the FastAPI Pydantic contracts in `apps/api/app/schemas`.
 *
 * Casing is deliberately inconsistent in the backend and must not be normalised here:
 * `ClaimStatus` / `ClaimPriority` / `AIDecision` are lowercase, while `PolicyDecision`
 * and `ValidationVerdict` are UPPERCASE. Both appear in the same `AuditResult` payload.
 */

// ============================================================
// Enums
// ============================================================

export type Currency = "INR" | "USD" | "EUR" | "GBP" | "AUD" | "CAD" | "JPY"

export type JobLevel = "L1" | "L2" | "L3" | "L4" | "L5" | "L6"

export type ExpenseCategory = "FOOD_MEALS" | "TRAVEL" | "ACCOMMODATION" | "OTHER"

export type ClaimStatus =
  | "draft"
  | "submitted"
  | "in_audit"
  | "approved"
  | "rejected"
  | "needs_revision"

export type ClaimPriority = "low" | "medium" | "high" | "urgent"

export type AIRunStatus = "pending" | "running" | "completed" | "failed"

export type AIDecision = "approve" | "reject" | "review"

export type PolicySeverity = "blocking" | "warning" | "info"

export type PolicyDecision = "APPROVE" | "REJECT" | "FLAG_FOR_REVIEW"

export type PolicyCheckStatus = "passed" | "failed" | "not_applicable"

export type ValidationSeverity = "blocking" | "warning" | "info"

export type ValidationFindingCategory =
  | "amount"
  | "date"
  | "field"
  | "mismatch"
  | "authenticity"
  | "budget"
  | "duplicate"

export type ValidationCheckStatus = "passed" | "failed" | "not_applicable"

export type ValidationVerdict = "PASS" | "FAIL" | "FLAG_FOR_REVIEW"

// ============================================================
// Auth
// ============================================================

export interface AuthRequest {
  username: string
  password: string
}

export interface AuthResponse {
  authenticated: boolean
  employee_id: string | null
}

// ============================================================
// Employees / Projects / Accounts
// ============================================================

export interface EmployeeResponse {
  employee_id: string
  employee_name: string
  job_level: JobLevel
  is_manager: boolean
  manager_id: string | null
  project_code: string | null
  username: string | null
}

export interface EmployeeDetailsEmployee {
  employee_id: string
  employee_name: string
  job_level: string
  manager_id: string | null
  project_code: string | null
}

export interface EmployeeDetailsProject {
  project_code: string
  project_name: string
  account_id: string
  project_lead_id: string | null
}

export interface EmployeeDetailsAccount {
  account_id: string
  account_name: string
  fiscal_year: number
  budget_allocated: string
  remaining_budget: string
  currency: string
}

export interface EmployeeDetailsResponse {
  employee: EmployeeDetailsEmployee
  project: EmployeeDetailsProject | null
  account: EmployeeDetailsAccount | null
}

export interface ProjectDetailsResponse {
  project_code: string
  project_name: string
  account_id: string
  project_lead_id: string | null
  lead_name: string | null
}

// ============================================================
// Policy documents — /api/v1/policies/documents
// ============================================================

export interface PolicyDocumentSummary {
  policy_id: number
  filename: string
  policy_version: string | null
  status: string
  error: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface PolicyIngestResult {
  policy_id: number
  filename: string
  doc_hash: string
  chunk_count: number
  reingested: boolean
}

// ============================================================
// Claim submission (category_data is a discriminated union)
// ============================================================

export interface LineItem {
  item_header: string
  item_amount: string
}

export interface FoodMealsData {
  meal_type: string
  merchant_name: string
  number_of_people: number
  line_items: LineItem[]
}

export interface TravelData {
  travel_type: string
  origin: string
  destination: string
  travel_date: string
  travel_class?: string | null
  ticket_number?: string | null
  line_items: LineItem[]
}

export interface AccommodationData {
  hotel_name: string
  location: string
  check_in: string
  check_out: string
  number_of_nights: number
  no_of_rooms: number
  room_type?: string | null
  line_items: LineItem[]
}

export interface OtherData {
  expense_type: string
  merchant_name?: string | null
  additional_details?: Record<string, unknown> | null
  line_items: LineItem[]
}

interface ClaimCreateBase {
  employee_id: string
  business_purpose?: string | null
  merchant_name?: string | null
  project_code?: string | null
  claim_amount: string
  currency: Currency
  receipt_url?: string | null
}

export type ClaimCreate =
  | (ClaimCreateBase & { category: "FOOD_MEALS"; category_data: FoodMealsData })
  | (ClaimCreateBase & { category: "TRAVEL"; category_data: TravelData })
  | (ClaimCreateBase & { category: "ACCOMMODATION"; category_data: AccommodationData })
  | (ClaimCreateBase & { category: "OTHER"; category_data: OtherData })

export interface ClaimSubmissionResponse {
  message: string
  claim_id: number
  status: ClaimStatus
  ai_run_status: AIRunStatus
  receipt_url: string | null
}

/** `ClaimDetailsResponse` — used by both the manager and employee claim-list endpoints. */
export interface ClaimDetailsResponse {
  claim_id: number
  business_purpose: string | null
  merchant_name: string | null
  category: string
  category_data: Record<string, unknown>
  employee_id: string
  auditer_id: string | null
  auditer_notes: string | null
  project_code: string | null
  claim_amount: string
  tax_amount: string
  currency: string
  status: string
  priority: string
  ai_run_status: string
  ai_decision: string | null
  receipt_url: string | null
  claim_created_at: string | null
  claim_updated_at: string | null
  receipt_created_at: string | null
}

export interface ClaimAuditUpdate {
  status: ClaimStatus
  priority: ClaimPriority
  auditer_id: string
  auditer_notes?: string | null
}

// ============================================================
// Agent response (persisted AI record) — /claims/{id}/agent-response
// ============================================================

export interface AgentResponseDetails {
  id: number
  claim_id: number
  validation_response: Record<string, unknown> | null
  policy_response: Record<string, unknown> | null
  notes: string | null
  confidence_score: string | null
}

// ============================================================
// Audit result — POST /audits/{claim_id}/run
// ============================================================

export interface ExtractionSummary {
  is_receipt: boolean | null
  merchant_name: string | null
  claim_amount: string | null
  currency: Currency | null
  expense_date: string | null
  receipt_no: string | null
  payment_status: string | null
}

export interface AuditAgentError {
  agent: string
  code: string
  message: string
  retryable: boolean
}

export interface PolicyReference {
  chunk_id: number
  policy_id: number
  policy_filename: string | null
  content: string
  similarity_score: number | null
}

export interface PolicyViolation {
  policy_reference: string | null
  severity: PolicySeverity
  description: string
  detail: string | null
  related_chunk_ids: number[]
}

export interface PolicyCheck {
  check_name: string
  status: PolicyCheckStatus
  policy_reference: string | null
  related_chunk_ids: number[]
}

export interface PolicyAgentOutput {
  decision: PolicyDecision
  confidence: number
  violations: PolicyViolation[]
  checks: PolicyCheck[]
  reasons: string[]
  warnings: string[]
  references: PolicyReference[]
  summary: string | null
}

export interface ValidationFinding {
  rule_id: string
  severity: ValidationSeverity
  category: ValidationFindingCategory
  description: string
  detail: string | null
  evidence: Record<string, string>
}

export interface ValidationCheck {
  check_name: string
  status: ValidationCheckStatus
  rule_id: string | null
}

export interface DuplicateCandidate {
  claim_id: number
  score: number
  match_reasons: string[]
}

export interface BudgetSnapshot {
  account_id: string
  remaining_budget: string
  claim_amount: string
  currency: string | null
  within_budget: boolean
}

export interface AuthenticityAssessment {
  is_suspicious: boolean
  forged_likelihood: number
  reasons: string[]
}

export interface ValidationAgentOutput {
  verdict: ValidationVerdict
  confidence: number
  findings: ValidationFinding[]
  checks: ValidationCheck[]
  warnings: string[]
  duplicate_candidates: DuplicateCandidate[]
  budget: BudgetSnapshot | null
  authenticity: AuthenticityAssessment | null
  summary: string | null
}

export interface AuditResult {
  claim_id: number
  status: ClaimStatus
  ai_run_status: AIRunStatus
  ai_decision: AIDecision | null
  priority: ClaimPriority | null
  confidence: number | null
  reasons: string[]
  warnings: string[]
  notes: string | null
  extraction_summary: ExtractionSummary | null
  category_data: Record<string, unknown> | null
  policy: PolicyAgentOutput | null
  grounding_references: PolicyReference[]
  validation: ValidationAgentOutput | null
  errors: AuditAgentError[]
}

// ============================================================
// Error envelope
// ============================================================

export interface ValidationErrorDetail {
  loc: (string | number)[]
  msg: string
  type: string
}

export interface ApiErrorBody {
  detail: string | ValidationErrorDetail[]
}
