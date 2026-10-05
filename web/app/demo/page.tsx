import type { Metadata } from "next";
import { Suspense } from "react";
import { DemoExplorer } from "@/components/DemoExplorer";

export const metadata: Metadata = {
  title: "Live demo",
  description:
    "Filter 4,000 synthetic care journeys by channel and intent. Rates recompute on the slice. Seed 20260929. Not a real-world measurement.",
};

export default function DemoPage() {
  return (
    <Suspense
      fallback={
        <div className="page">
          <p className="kicker">Live demo</p>
          <h1>Filter journeys, read the rates</h1>
          <p className="lede">Loading the synthetic log.</p>
        </div>
      }
    >
      <DemoExplorer />
    </Suspense>
  );
}
