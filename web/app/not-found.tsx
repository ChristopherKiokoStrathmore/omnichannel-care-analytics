import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page narrow">
      <p className="kicker">Missing page</p>
      <h1>This page is not part of the demo.</h1>
      <p className="lede">The brief and the KPI dashboard are the two pages in this app.</p>
      <p className="actions">
        <Link href="/" className="button button-primary">
          Back to the brief
        </Link>
        <Link href="/dashboard" className="button button-secondary">
          Open the dashboard
        </Link>
      </p>
    </div>
  );
}
