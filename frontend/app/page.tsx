import Link from "next/link";
import { ArrowRight, ShieldCheck } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

// This component renders the dashboard overview page for the MVP.
export default function Home() {
  return (
    <div className="flex flex-1 items-center justify-center p-6 md:p-10">
      <main className="glass-panel w-full max-w-4xl space-y-8 rounded-3xl p-8 md:p-10">
        <div className="space-y-3">
          <Badge className="bg-sky-100 text-sky-700" variant="secondary">
            <ShieldCheck className="size-3.5" />
            Safe Metadata Changes
          </Badge>
          <h1 className="text-3xl font-semibold text-slate-950 md:text-4xl">
            Autonomous Data Guardian
          </h1>
          <p className="max-w-2xl text-sm text-slate-600 md:text-base">
          Simulate risky OpenMetadata changes before they break dashboards, pipelines, or governance rules.
          </p>
        </div>
        <section className="grid gap-4 sm:grid-cols-2">
          <Card className="glass-subtle border-sky-100/80">
            <CardHeader>
              <CardTitle>Dashboard Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
              Track reports and quickly start a new impact simulation.
              </CardDescription>
            </CardContent>
          </Card>
          <Card className="glass-subtle border-sky-100/80">
            <CardHeader>
              <CardTitle>One Killer Flow</CardTitle>
            </CardHeader>
            <CardContent>
              <CardDescription>
              What happens if I rename, delete, or change a table/column?
              </CardDescription>
            </CardContent>
          </Card>
        </section>
        <div className="flex gap-3">
          <Link
            href="/analyze"
            className="inline-flex h-10 items-center gap-2 rounded-lg bg-slate-950 px-5 text-sm font-medium text-white transition hover:bg-slate-800"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "0.5rem",
              backgroundColor: "#020617",
              color: "#ffffff",
              padding: "0.65rem 1.25rem",
              borderRadius: "0.75rem",
            }}
          >
            Start Analysis
            <ArrowRight className="size-4" />
          </Link>
          <Link
            href="/upload"
            className="inline-flex h-10 items-center gap-2 rounded-lg border border-slate-300 px-5 text-sm font-medium text-slate-700 transition hover:bg-slate-100"
          >
            CSV Upload Flow
            <ArrowRight className="size-4" />
          </Link>
        </div>
      </main>
    </div>
  );
}
