/**
 * TypeScript mirrors of the FastAPI contracts in `apps/api/app/schemas`.
 * Keep these in step with the Pydantic models; the backend is the source of truth.
 */

export type JobLevel = "L1" | "L2" | "L3" | "L4" | "L5" | "L6";

export type Currency = "INR" | "USD" | "EUR" | "GBP" | "AUD" | "CAD" | "JPY";

export type ExpenseCategory =
  | "FOOD_MEALS"
  | "TRAVEL"
  | "ACCOMMODATION"
  | "OTHER";

export type ClaimStatus =
  | "draft"
  | "submitted"
  | "in_audit"
  | "approved"
  | "rejected"
  | "needs_revision";

export type ClaimPriority = "low" | "medium" | "high" | "urgent";

export type AuditRecommendation =
  | "RECOMMEND_APPROVE"
  | "RECOMMEND_REJECT"
  | "FLAG_FOR_REVIEW";

export interface EmployeeProfile {
  employee_id: string;
  employee_name: string;
  email: string;
  job_level: JobLevel;
  is_manager: boolean;
  manager_id: string | null;
  project_code: string | null;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  profile: EmployeeProfile;
}

// --- category_data payloads, one per ExpenseCategory ------------------------

export interface FoodMealsData {
  meal_type: string;
  merchant_name: string;
  number_of_people: number;
}

export interface TravelData {
  travel_type: string;
  origin: string;
  destination: string;
  travel_date: string;
  travel_class?: string | null;
  ticket_number?: string | null;
}

export interface AccommodationData {
  hotel_name: string;
  location: string;
  check_in: string;
  check_out: string;
  number_of_nights: number;
  no_of_rooms: number;
  room_type?: string | null;
}

export interface OtherData {
  expense_type: string;
  merchant_name?: string | null;
  additional_details?: Record<string, unknown> | null;
}

export type CategoryData =
  | FoodMealsData
  | TravelData
  | AccommodationData
  | OtherData;

export interface ClaimCreatePayload {
  employee_id: string;
  business_purpose?: string | null;
  merchant_name?: string | null;
  project_code?: string | null;
  claim_amount: string;
  currency: Currency;
  receipt_url?: string | null;
  category: ExpenseCategory;
  category_data: CategoryData;
}

export interface Claim {
  claim_id: number;
  employee_id: string;
  auditer_id: string | null;
  auditer_notes: string | null;
  project_code: string | null;
  business_purpose: string | null;
  merchant_name: string | null;
  claim_amount: string;
  currency: Currency;
  status: ClaimStatus;
  priority: ClaimPriority;
  receipt_url: string | null;
  claim_created_at: string | null;
  claim_updated_at: string | null;
  receipt_created_at: string | null;
  category: ExpenseCategory;
  category_data: Record<string, unknown>;
}

export interface ClaimListItem extends Claim {
  employee_name: string | null;
  has_audit: boolean;
  audit_recommendation: AuditRecommendation | null;
  audit_confidence: string | null;
}

export type ClaimDecision = "approve" | "reject";

// --- agent output ----------------------------------------------------------

export type ValidationSeverity = "blocking" | "warning" | "info";
export type ValidationVerdict = "PASS" | "FAIL" | "FLAG_FOR_REVIEW";
export type PolicyDecision = "APPROVE" | "REJECT" | "FLAG_FOR_REVIEW";
export type CheckStatus = "passed" | "failed" | "not_applicable";

export interface ValidationFinding {
  rule_id: string;
  severity: ValidationSeverity;
  category: string;
  description: string;
  detail?: string | null;
  evidence?: Record<string, string>;
}

export interface ValidationCheck {
  check_name: string;
  status: CheckStatus;
  rule_id?: string | null;
}

export interface DuplicateCandidate {
  claim_id: number;
  score: number;
  match_reasons: string[];
}

export interface BudgetSnapshot {
  account_id: string;
  remaining_budget: string;
  claim_amount: string;
  currency?: string | null;
  within_budget: boolean;
}

export interface AuthenticityAssessment {
  is_suspicious: boolean;
  forged_likelihood: number;
  reasons: string[];
}

export interface ValidationAgentOutput {
  verdict: ValidationVerdict;
  confidence: number;
  findings: ValidationFinding[];
  checks: ValidationCheck[];
  warnings: string[];
  duplicate_candidates: DuplicateCandidate[];
  budget?: BudgetSnapshot | null;
  authenticity?: AuthenticityAssessment | null;
  summary?: string | null;
}

export interface PolicyViolation {
  policy_reference?: string | null;
  severity: ValidationSeverity;
  description: string;
  detail?: string | null;
  related_chunk_ids: number[];
}

export interface PolicyCheck {
  check_name: string;
  status: CheckStatus;
  policy_reference?: string | null;
  related_chunk_ids: number[];
}

export interface PolicyReference {
  chunk_id: number;
  policy_id: number;
  content: string;
  similarity_score?: number | null;
}

export interface PolicyAgentOutput {
  decision: PolicyDecision;
  confidence: number;
  violations: PolicyViolation[];
  checks: PolicyCheck[];
  reasons: string[];
  warnings: string[];
  references: PolicyReference[];
  summary?: string | null;
}

export interface AuditResult {
  claim_id: number;
  recommendation: AuditRecommendation;
  reasons: string[];
  validation?: ValidationAgentOutput | null;
  policy?: PolicyAgentOutput | null;
  references: PolicyReference[];
  warnings: string[];
  confidence: number;
  validation_violation?: string | null;
  policy_violation?: string | null;
  notes?: string | null;
}

export interface AuditRunResponse {
  status: "success" | "error";
  output: AuditResult | null;
  error: { code: string; message: string; agent: string } | null;
  agent_response_id: number | null;
  claim_status: ClaimStatus | null;
  validation_violation: string | null;
  policy_violation: string | null;
  notes: string | null;
  confidence_score: string | null;
  validation_response: ValidationAgentOutput | null;
  policy_response: PolicyAgentOutput | null;
  audit_response: AuditResult | null;
}

// --- display helpers -------------------------------------------------------

/** The four choices offered in the UI, mapped onto the backend enum. */
export const CATEGORY_OPTIONS: { value: ExpenseCategory; label: string }[] = [
  { value: "TRAVEL", label: "Travel" },
  { value: "FOOD_MEALS", label: "Food" },
  { value: "ACCOMMODATION", label: "Hotel" },
  { value: "OTHER", label: "Others" },
];

export const CATEGORY_LABELS: Record<ExpenseCategory, string> = {
  TRAVEL: "Travel",
  FOOD_MEALS: "Food",
  ACCOMMODATION: "Hotel",
  OTHER: "Others",
};

export const CURRENCY_OPTIONS: Currency[] = [
  "INR",
  "USD",
  "EUR",
  "GBP",
  "AUD",
  "CAD",
  "JPY",
];
