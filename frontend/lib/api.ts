export interface SearchAssetItem {
  id: string;
  name: string;
  fqn: string;
  entityType: string;
  description?: string | null;
}

export interface AnalyzeChangeResponse {
  reportId: string;
  riskLevel: "Low" | "Medium" | "High" | "Critical";
  riskScore: number;
  summary: string;
  affectedAssets: string[];
  sensitiveDataWarning?: string | null;
  ownerGovernanceGaps: string[];
  triggeredFactors: string[];
  recommendations: string[];
  createdAt: string;
}

export interface AnalyzeChangeRequest {
  assetType: "table";
  assetFqn: string;
  changeType?:
    | "DELETE_COLUMN"
    | "RENAME_COLUMN"
    | "DELETE_TABLE"
    | "CHANGE_COLUMN_TYPE";
  columnName?: string;
  newColumnName?: string;
  newColumnType?: string;
  description: string;
  intent: string;
}

export interface CsvColumnProfile {
  name: string;
  inferredType: string;
  nullRatio: number;
  sampleValues: string[];
}

export interface CsvAnalyzeResponse {
  analysisId: string;
  fileName: string;
  rowCount: number;
  columns: CsvColumnProfile[];
  aiComment: string;
  aiWarnings: string[];
  suggestedTableName: string;
  suggestedDescription: string;
  createdAt: string;
}

export interface CsvImportRequest {
  analysisId: string;
  tableName?: string;
  databaseSchemaFqn?: string;
  overwriteExistingTable: boolean;
}

export interface CsvImportResponse {
  analysisId: string;
  tableName: string;
  rowsImported: number;
  databaseImportStatus: string;
  metadataImportStatus: string;
  metadataTableFqn?: string | null;
  metadataEntityId?: string | null;
  warnings: string[];
}

const backendUrl = process.env.NEXT_PUBLIC_GUARDIAN_API_URL ?? "http://localhost:8000";

// This function performs asset search against the backend API.
export async function searchAssets(query: string): Promise<SearchAssetItem[]> {
  const response = await fetch(
    `${backendUrl}/assets/search?q=${encodeURIComponent(query)}`,
    { cache: "no-store" }
  );
  if (!response.ok) {
    let detail = "Unable to search assets";
    try {
      const payload = await response.json();
      if (payload?.detail) detail = String(payload.detail);
    } catch {
      // Keep default message when backend does not return JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

// This function submits a change analysis request and returns the report payload.
export async function analyzeChange(
  payload: AnalyzeChangeRequest
): Promise<AnalyzeChangeResponse> {
  const response = await fetch(`${backendUrl}/analyze-change`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail = "Unable to analyze change";
    try {
      const errorPayload = await response.json();
      if (errorPayload?.detail) detail = String(errorPayload.detail);
    } catch {
      // Keep default message when backend does not return JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

// This function retrieves one stored report by id from backend API.
export async function getReport(reportId: string): Promise<AnalyzeChangeResponse> {
  const response = await fetch(`${backendUrl}/reports/${reportId}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("Unable to load report");
  return response.json();
}

// This function uploads one CSV file and returns AI review output.
export async function analyzeCsvUpload(file: File, intent: string): Promise<CsvAnalyzeResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("intent", intent);
  const response = await fetch(`${backendUrl}/csv/analyze`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    let detail = "Unable to analyze uploaded CSV";
    try {
      const payload = await response.json();
      if (payload?.detail) detail = String(payload.detail);
    } catch {
      // Keep default message when backend does not return JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}

// This function confirms import for a previously analyzed CSV session.
export async function importCsvToOpenMetadata(payload: CsvImportRequest): Promise<CsvImportResponse> {
  const response = await fetch(`${backendUrl}/csv/import`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    let detail = "Unable to import CSV";
    try {
      const errorPayload = await response.json();
      if (errorPayload?.detail) detail = String(errorPayload.detail);
    } catch {
      // Keep default message when backend does not return JSON.
    }
    throw new Error(detail);
  }
  return response.json();
}
