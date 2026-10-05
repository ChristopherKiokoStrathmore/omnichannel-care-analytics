import Link from "next/link";

export default function NotFound() {
  return (
    <div className="page narrow">
      <p className="kicker">Missing page</p>
      <h1>This page is not in the app.</h1>
      <p className="lede">The article, the live demo, and the KPI report are the three pages.</p>
      <p className="actions">
        <Link href="/demo" className="button button-primary">
          Open the live demo
        </Link>
        <Link href="/" className="button button-secondary">
          Read the article
        </Link>
      </p>
    </div>
  );
}
