export type ClaimStatus = "Draft" | "Under Review" | "Approved" | "Failed";

export interface Employee {
  employee_id: string;
  employee_name: string;
  job_level: string;
  manager_id: string | null;
  project_code: string;
  is_manager: boolean;
}

export interface OcrExtractedText {
  merchant: string;
  date: string;
  total_amount: number;
}

export interface Claim {
  claim_id: number;
  employee_id: string;
  claim_name: string;
  estimated_amount: number;
  status: ClaimStatus;
  violations: string | null;
  requires_human_review: boolean;
  document_path: string | null;
  ocr_text: OcrExtractedText | null;
  created_at: string;
}

export interface SubmitResponse {
  claim_id: number;
  status: ClaimStatus;
  violations: string[];
  requires_human_review: boolean;
  ocr_text: OcrExtractedText;
  message: string;
}

export interface TeamClaimResponse {
  claim_id: number;
  claim_name: string;
  estimated_amount: number;
  status: ClaimStatus;
  violations: string | null;
  requires_human_review: boolean;
  document_path: string | null;
  ocr_text: OcrExtractedText | null;
  created_at: string;
  employee_id: string;
  employee_name: string;
  job_level: string;
}

export interface ApprovalActionResponse {
  claim_id: number;
  status: ClaimStatus;
  message: string;
}

export interface AppNavigationItem {
  label: string;
  href: string;
  description: string;
  visible: boolean;
  badge?: number;
}