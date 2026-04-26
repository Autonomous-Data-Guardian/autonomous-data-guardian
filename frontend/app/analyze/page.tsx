"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import {
  analyzeChange,
  type AnalyzeChangeRequest,
  searchAssets,
  type SearchAssetItem,
} from "@/lib/api";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

// This component renders table selection + intent input and submits impact analysis.
export default function AnalyzePage() {
  const router = useRouter();
  const [query, setQuery] = useState("customer");
  const [assets, setAssets] = useState<SearchAssetItem[]>([]);
  const [isSearching, setIsSearching] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [searchNotice, setSearchNotice] = useState("");
  const [selectedFqn, setSelectedFqn] = useState("");
  const [intent, setIntent] = useState(
    "I want to delete the email column because we no longer use it."
  );

  // This function executes asset search request.
  async function handleSearch(searchText: string): Promise<void> {
    setIsSearching(true);
    setErrorMessage("");
    setSearchNotice("");
    try {
      const foundAssets = await searchAssets(searchText);
      setAssets(foundAssets);
      if (foundAssets.length > 0) {
        if (!selectedFqn) setSelectedFqn(foundAssets[0].fqn);
      } else {
        setSelectedFqn("");
        setSearchNotice(`Table "${searchText}" does not exist. Try another table name.`);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Unable to load tables from OpenMetadata backend.";
      setErrorMessage(message);
    } finally {
      setIsSearching(false);
    }
  }

  // This function loads initial table options so the demo starts ready.
  useEffect(() => {
    let isActive = true;
    void searchAssets("customer")
      .then((foundAssets) => {
        if (!isActive) return;
        setAssets(foundAssets);
        if (foundAssets.length > 0) setSelectedFqn(foundAssets[0].fqn);
      })
      .catch((error) => {
        if (!isActive) return;
        const message = error instanceof Error ? error.message : "Unable to load tables from OpenMetadata backend.";
        setErrorMessage(message);
      })
      .finally(() => {
        if (!isActive) return;
        setIsSearching(false);
      });
    return () => {
      isActive = false;
    };
  }, []);

  // This function submits the change request and navigates to report page.
  async function handleAnalyze(): Promise<void> {
    if (!selectedFqn) {
      setErrorMessage("Please select a table first.");
      return;
    }
    if (!intent.trim()) {
      setErrorMessage("Please describe your intent before analysis.");
      return;
    }
    setIsSubmitting(true);
    setErrorMessage("");
    try {
      const payload: AnalyzeChangeRequest = {
        assetType: "table",
        assetFqn: selectedFqn,
        description: intent,
        intent,
      };
      const report = await analyzeChange(payload);
      router.push(`/report/${report.reportId}`);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Analysis failed. Check backend logs.";
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-6 md:p-10">
      <h1 className="text-3xl font-semibold text-slate-950">Analyze Metadata Impact</h1>
      <p className="text-sm text-slate-600">
        Select a table from OpenMetadata, describe your intent, and get downstream impact + safety guidance.
      </p>
      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>1) Select Table</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2">
            <Input
              className="bg-white/80"
              placeholder="Search table by keyword"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <Button
              className="h-8 bg-slate-950 text-white hover:bg-slate-800"
              disabled={isSearching || !query}
              onClick={() => handleSearch(query)}
              type="button"
            >
              <Search className="size-4" />
              {isSearching ? "Searching..." : "Search"}
            </Button>
          </div>
          <ul className="mt-3 space-y-2">
            {assets.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  onClick={() => setSelectedFqn(item.fqn)}
                  className={`w-full rounded-xl border px-3 py-2 text-left text-sm transition ${
                    selectedFqn === item.fqn
                      ? "border-sky-300 bg-sky-50/80"
                      : "border-slate-200 bg-white/80 hover:border-slate-300"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <div className="font-medium text-slate-900">{item.fqn || item.name}</div>
                    {selectedFqn === item.fqn ? (
                      <Badge className="bg-sky-600 text-white">Selected</Badge>
                    ) : null}
                  </div>
                  <div className="text-slate-500">{item.description || "No description available."}</div>
                </button>
              </li>
            ))}
          </ul>
          {searchNotice ? (
            <Alert className="mt-3">
              <AlertTitle>Table not found</AlertTitle>
              <AlertDescription>{searchNotice}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>2) Enter Intent</CardTitle>
        </CardHeader>
        <CardContent>
          <label className="block text-sm font-medium text-slate-700">
            What are you trying to do?
            <Textarea
              className="mt-2 min-h-28 bg-white/80"
              value={intent}
              onChange={(event) => setIntent(event.target.value)}
              placeholder="Example: Remove email column from dim_customer because no product depends on it."
              rows={4}
            />
          </label>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>3) Analyze Impact</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Button
            type="button"
            onClick={handleAnalyze}
            disabled={isSubmitting || !selectedFqn}
            className="h-9 bg-sky-600 px-4 font-medium text-white hover:bg-sky-500 disabled:opacity-60"
          >
            {isSubmitting ? "Analyzing..." : "Analyze Intent"}
          </Button>
          {errorMessage ? (
            <Alert variant="destructive">
              <AlertTitle>Unable to analyze</AlertTitle>
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          ) : null}
        </CardContent>
      </Card>
    </main>
  );
}
