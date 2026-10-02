export type OnboardingStatus =
  | "RECEIVED"
  | "IN_PROGRESS"
  | "AWAITING_CUSTOMER"
  | "APPROVED"
  | "APPROVED_PENDING_PROVISIONING"
  | "REJECTED"
  | "ESCALATED"
  | "ERROR";

export type NextActionType =
  | "LOGIN"
  | "VISIT_BRANCH"
  | "PROVIDE_INFO"
  | "RETRY_LATER"
  | "FIX_INPUT"
  | "NONE";

export type RequiredDocument = {
  code: string;
  name: string;
  mandatory: boolean;
  policy_ref: string | null;
  source?: string;
};

export type PendingQuestion = {
  field: string;
  label: string;
  type: "text" | "number" | "select";
  options?: string[] | null;
  required: boolean;
};

export type AgentTraceStep = {
  node: string;
  agent: string | null;
  status: "ok" | "failed" | "escalated" | "skipped";
  summary: string;
  started_at: string;
  duration_ms: number | null;
};

export type Provisioning = {
  username: string;
  provider: "local_mock" | "cognito";
  status: "created" | "failed";
  temporary_password?: string | null;
};

export type ConversationMessage = {
  role: "customer" | "assistant" | "system" | string;
  content: string;
  created_at: string;
};

export type OnboardingResult = {
  onboarding_id: string;
  status: OnboardingStatus;
  reason_code: string | null;
  customer_message: string | null;
  proposed_solution: string | null;
  next_action: { type: NextActionType; detail?: string | null };
  required_documents: RequiredDocument[];
  pending_questions: PendingQuestion[];
  agents_trace: AgentTraceStep[];
  provisioning: Provisioning | null;
  error: { code: string; message: string } | null;
  prospect_name?: string;
  document_id_masked?: string;
  product?: string;
  created_at: string;
  messages?: ConversationMessage[];
};

export type Product = {
  code: string;
  name: string;
  description: string;
};

export type StartRequest = {
  prospect_name: string;
  document_id: string;
  product: string;
  email?: string;
};

export type Answers = Record<string, string | number>;
