"use client";

import { useState } from "react";
import { useDropzone } from "react-dropzone";

import {
  analyzeCsvUpload,
  importCsvToOpenMetadata,
  type CsvAnalyzeResponse,
  type CsvImportResponse,
} from "@/lib/api";

// This component renders CSV upload, AI review, and confirmed import flow.
export default function UploadPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [intent, setIntent] = useState("Analyze this CSV for governance and quality before import.");
  const [databaseSchemaFqn, setDatabaseSchemaFqn] = useState("guardian.guardian-db.guardian_demo");
  const [tableName, setTableName] = useState("");
  const [analysis, setAnalysis] = useState<CsvAnalyzeResponse | null>(null);
  const [importResult, setImportResult] = useState<CsvImportResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isImporting, setIsImporting] = useState(false);
  const [dropzoneMessage, setDropzoneMessage] = useState("");

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { "text/csv": [".csv"] },
    multiple: false,
    onDrop: (acceptedFiles, rejectedFiles) => {
      if (rejectedFiles.length > 0) {
        setSelectedFile(null);
        setDropzoneMessage("Only CSV files are supported.");
        return;
      }
      const file = acceptedFiles[0] ?? null;
      setSelectedFile(file);
      setDropzoneMessage(file ? `Selected file: ${file.name}` : "");
    },
  });

  // This function handles CSV upload and AI analysis call.
  async function handleAnalyzeUpload(): Promise<void> {
    if (!selectedFile) {
      setErrorMessage("Please choose a CSV file first.");
      return;
    }
    if (!intent.trim()) {
      setErrorMessage("Please provide your analysis intent.");
      return;
    }
    setIsAnalyzing(true);
    setErrorMessage("");
    setImportResult(null);
    try {
      const response = await analyzeCsvUpload(selectedFile, intent.trim());
      setAnalysis(response);
      setTableName(response.suggestedTableName);
    } catch (error) {
      const message = error instanceof Error ? error.message : "CSV analysis failed.";
      setErrorMessage(message);
    } finally {
      setIsAnalyzing(false);
    }
  }

  // This function confirms import into DB and OpenMetadata.
  async function handleImport(): Promise<void> {
    if (!analysis) {
      setErrorMessage("Please analyze the CSV before import.");
      return;
    }
    if (!databaseSchemaFqn.trim()) {
      setErrorMessage("Please provide database schema FQN.");
      return;
    }
    setIsImporting(true);
    setErrorMessage("");
    try {
      const response = await importCsvToOpenMetadata({
        analysisId: analysis.analysisId,
        tableName: tableName.trim() || analysis.suggestedTableName,
        databaseSchemaFqn: databaseSchemaFqn.trim(),
        overwriteExistingTable: true,
      });
      setImportResult(response);
    } catch (error) {
      const message = error instanceof Error ? error.message : "CSV import failed.";
      setErrorMessage(message);
    } finally {
      setIsImporting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-8">
      <h1 className="text-3xl font-semibold">CSV Upload + AI Review + Import</h1>
      <p className="text-sm text-zinc-600 dark:text-zinc-300">
        Upload one CSV, review AI comments, then confirm import into database and OpenMetadata metadata.
      </p>

      <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
        <h2 className="font-semibold">1) Upload CSV + Intent</h2>
        <div className="mt-3 space-y-3">
          <div
            {...getRootProps()}
            className={`cursor-pointer rounded border border-dashed px-4 py-6 text-sm transition ${
              isDragActive
                ? "border-indigo-500 bg-indigo-50/40 dark:bg-indigo-950/20"
                : "border-zinc-300 dark:border-zinc-700"
            }`}
          >
            <input {...getInputProps()} />
            <p>
              {isDragActive
                ? "Drop the CSV file here..."
                : "Drag and drop a CSV here, or click to select one"}
            </p>
            {selectedFile ? <p className="mt-2 text-zinc-500">Selected file: {selectedFile.name}</p> : null}
          </div>
          {dropzoneMessage ? <p className="text-xs text-amber-500">{dropzoneMessage}</p> : null}
          <textarea
            className="w-full rounded border border-zinc-300 bg-transparent px-3 py-2"
            value={intent}
            onChange={(event) => setIntent(event.target.value)}
            rows={4}
          />
          <button
            type="button"
            onClick={handleAnalyzeUpload}
            disabled={isAnalyzing || !selectedFile}
            className="rounded bg-indigo-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
          >
            {isAnalyzing ? "Analyzing..." : "Analyze CSV"}
          </button>
        </div>
      </section>

      {analysis ? (
        <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="font-semibold">2) AI Review</h2>
          <p className="mt-2 text-sm">{analysis.aiComment}</p>
          {analysis.aiWarnings.length ? (
            <ul className="mt-3 list-disc pl-5 text-sm text-amber-500">
              {analysis.aiWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          ) : null}
          <div className="mt-3 overflow-x-auto">
            <table className="min-w-full text-left text-sm">
              <thead>
                <tr className="border-b border-zinc-700">
                  <th className="py-1 pr-3">Column</th>
                  <th className="py-1 pr-3">Type</th>
                  <th className="py-1 pr-3">Null Ratio</th>
                </tr>
              </thead>
              <tbody>
                {analysis.columns.map((column) => (
                  <tr key={column.name} className="border-b border-zinc-800">
                    <td className="py-1 pr-3">{column.name}</td>
                    <td className="py-1 pr-3">{column.inferredType}</td>
                    <td className="py-1 pr-3">{column.nullRatio}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      ) : null}

      {analysis ? (
        <section className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm dark:border-zinc-800 dark:bg-zinc-950">
          <h2 className="font-semibold">3) Confirm Import</h2>
          <div className="mt-3 space-y-3">
            <input
              className="w-full rounded border border-zinc-300 bg-transparent px-3 py-2 text-sm"
              value={tableName}
              onChange={(event) => setTableName(event.target.value)}
              placeholder="Target table name"
            />
            <input
              className="w-full rounded border border-zinc-300 bg-transparent px-3 py-2 text-sm"
              value={databaseSchemaFqn}
              onChange={(event) => setDatabaseSchemaFqn(event.target.value)}
              placeholder="OpenMetadata database schema FQN"
            />
            <button
              type="button"
              onClick={handleImport}
              disabled={isImporting}
              className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            >
              {isImporting ? "Importing..." : "Import to DB + OpenMetadata"}
            </button>
          </div>
          {importResult ? (
            <div className="mt-4 rounded border border-emerald-400/30 bg-emerald-950/20 p-3 text-sm">
              <p>Rows imported: {importResult.rowsImported}</p>
              <p>Metadata status: {importResult.metadataImportStatus}</p>
              <p>Metadata FQN: {importResult.metadataTableFqn ?? "N/A"}</p>
            </div>
          ) : null}
        </section>
      ) : null}

      {errorMessage ? <p className="text-sm text-red-500">{errorMessage}</p> : null}
    </main>
  );
}
