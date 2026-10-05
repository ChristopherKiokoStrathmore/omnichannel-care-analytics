import { REPO_HEADLINES, REPO_KPIS, REPO_LICENSE, REPO_URL } from "@/lib/site";
import { seed } from "@/lib/figures";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <p>
        Seed {seed}. The article and the KPI report show the committed totals. The live demo
        recomputes those definitions on the journeys you select. Source files:{" "}
        <a href={REPO_HEADLINES} rel="noopener noreferrer">
          reports/headlines.md
        </a>{" "}
        and{" "}
        <a href={REPO_KPIS} rel="noopener noreferrer">
          reports/kpis.json
        </a>
        .
      </p>
      <p>
        <a href={REPO_URL} rel="noopener noreferrer">
          Omnichannel care analytics on GitHub
        </a>
        {" · "}
        <a href={REPO_LICENSE} rel="noopener noreferrer">
          MIT License
        </a>
        {" · Christopher Nguu"}
      </p>
    </footer>
  );
}
