import Link from "next/link";
import { AlertCircle, GitBranch, ShieldAlert } from "lucide-react";

import { getReport } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

interface ReportPageProps {
  params: Promise<{ id: string }>;
}

// This component renders one saved risk report result.
export default async function ReportPage({ params }: ReportPageProps) {
  const { id } = await params;
  const report = await getReport(id);

  return (
    <main className="mx-auto flex w-full max-w-5xl flex-1 flex-col gap-6 p-6 md:p-10">
      <header className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold text-slate-950">Risk Report</h1>
        <Link
          href="/analyze"
          className="inline-flex h-8 items-center rounded-lg bg-slate-950 px-3 text-sm font-medium text-white transition hover:bg-slate-800"
        >
          Analyze another change
        </Link>
      </header>

      <section className="grid gap-4 md:grid-cols-3">
        <Card className="glass-panel border-sky-100/80">
          <CardHeader>
            <CardTitle>Risk Score</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-5xl font-semibold text-slate-950">{report.riskScore}</p>
            <Badge className="mt-2 bg-sky-100 text-sky-700" variant="secondary">
              {report.riskLevel}
            </Badge>
          </CardContent>
        </Card>
        <Card className="glass-panel border-sky-100/80">
          <CardHeader>
            <CardTitle>Impacted Assets</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-5xl font-semibold text-slate-950">{report.affectedAssets.length}</p>
            <p className="mt-2 text-sm text-slate-600">Downstream dependencies detected</p>
          </CardContent>
        </Card>
        <Card className="glass-panel border-sky-100/80">
          <CardHeader>
            <CardTitle>Governance Gaps</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-5xl font-semibold text-slate-950">{report.ownerGovernanceGaps.length}</p>
            <p className="mt-2 text-sm text-slate-600">Ownership and quality blind spots</p>
          </CardContent>
        </Card>
      </section>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>AI Explanation</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-700">{report.summary}</p>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader className="flex-row items-center gap-2">
          <AlertCircle className="size-4 text-slate-700" />
          <CardTitle>Why This Score</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="flex flex-wrap gap-2 text-xs">
          {report.triggeredFactors.map((factor) => (
              <li key={factor}>
                <Badge className="bg-slate-100 text-slate-700" variant="secondary">
                  {factor}
                </Badge>
              </li>
          ))}
          </ul>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader className="flex-row items-center gap-2">
          <GitBranch className="size-4 text-slate-700" />
          <CardTitle>Affected Assets</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {report.affectedAssets.map((asset) => (
            <li key={asset}>{asset}</li>
          ))}
          </ul>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader className="flex-row items-center gap-2">
          <ShieldAlert className="size-4 text-slate-700" />
          <CardTitle>Sensitive Data Warning</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-slate-700">
          {report.sensitiveDataWarning ?? "No sensitive data warning detected."}
          </p>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>Owner / Governance Gaps</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
          {report.ownerGovernanceGaps.length ? (
            report.ownerGovernanceGaps.map((gap) => <li key={gap}>{gap}</li>)
          ) : (
            <li>No governance gaps detected.</li>
          )}
          </ul>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>Safe Migration Plan</CardTitle>
        </CardHeader>
        <CardContent>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-slate-700">
          {report.recommendations.map((item) => (
            <li key={item}>{item}</li>
          ))}
          </ol>
        </CardContent>
      </Card>

      <Card className="glass-panel border-sky-100/80">
        <CardHeader>
          <CardTitle>Impact Graph</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="rounded-xl border border-dashed border-sky-200 bg-white/60 p-4">
            <div className="rounded bg-sky-100 px-3 py-2 text-sm font-medium text-slate-800">
              selected.table
            </div>
            <Separator className="my-3" />
            <div className="ml-4 grid gap-2">
            {report.affectedAssets.map((asset) => (
                <div key={asset} className="flex items-center gap-2 text-sm text-slate-700">
                <span className="text-zinc-400">└──</span>
                  <span className="rounded bg-slate-100 px-2 py-1">{asset}</span>
                </div>
            ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </main>
  );
}
