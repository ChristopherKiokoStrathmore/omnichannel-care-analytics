import Image from "next/image";
import type { CountRate } from "@/lib/figures";

export function RateBar({
  label,
  value,
  note,
  emphasis = false,
}: {
  label: string;
  value: CountRate;
  note?: string;
  emphasis?: boolean;
}) {
  const width = value.denominator === 0 ? 0 : (value.numerator / value.denominator) * 100;

  return (
    <div className={emphasis ? "rate rate-emphasis" : "rate"}>
      <div className="rate-head">
        <span>{label}</span>
        <strong>{value.percent}</strong>
      </div>
      <div className="track" role="img" aria-label={`${label}: ${value.text}`}>
        <span style={{ width: `${width}%` }} />
      </div>
      <p className="rate-meta">
        {value.fraction}
        {note ? ` · ${note}` : ""}
      </p>
    </div>
  );
}

export function ResponseChart({
  rows,
}: {
  rows: {
    channel: string;
    journeys: number;
    median: string;
    p90: string;
    medianMinutes: number;
    p90Minutes: number;
  }[];
}) {
  const longest = rows.reduce((best, row) => (row.p90Minutes > best.p90Minutes ? row : best));

  return (
    <figure className="minutes">
      <div className="legend">
        <span>
          <i className="swatch swatch-median" aria-hidden="true" /> Median
        </span>
        <span>
          <i className="swatch swatch-p90" aria-hidden="true" /> 90th percentile
        </span>
      </div>
      <div className="minutes-list">
        {rows.map((row) => (
          <div key={row.channel} className="minutes-row">
            <div className="minutes-label">
              <span>{row.channel}</span>
              <span>n={row.journeys}</span>
            </div>
            <div
              className="minutes-track"
              role="img"
              aria-label={`${row.channel}: median ${row.median} minutes, 90th percentile ${row.p90} minutes, n=${row.journeys}`}
            >
              <span
                className="p90"
                style={{ width: `${(row.p90Minutes / longest.p90Minutes) * 100}%` }}
              />
              <span
                className="median"
                style={{ width: `${(row.medianMinutes / longest.p90Minutes) * 100}%` }}
              />
            </div>
            <p className="minutes-nums">
              median {row.median} min · p90 {row.p90} min
            </p>
          </div>
        ))}
      </div>
      <figcaption>
        Scale ends at the longest 90th percentile in this table ({longest.channel}, {longest.p90}{" "}
        minutes).
      </figcaption>
    </figure>
  );
}

export function OutcomeStack({
  rows,
}: {
  rows: { channel: string; first: number; later: number; abandoned: number; journeys: number }[];
}) {
  return (
    <figure className="stacks">
      <div className="legend">
        <span>
          <i className="swatch swatch-first" aria-hidden="true" /> Resolved on first contact
        </span>
        <span>
          <i className="swatch swatch-later" aria-hidden="true" /> Resolved after another contact
        </span>
        <span>
          <i className="swatch swatch-abandoned" aria-hidden="true" /> Abandoned
        </span>
      </div>
      <div className="stack-list">
        {rows.map((row) => (
          <div key={row.channel} className="stack-row">
            <span className="stack-name">{row.channel}</span>
            <div
              className="stack"
              role="img"
              aria-label={`${row.channel}: resolved on first contact ${row.first}, resolved after another contact ${row.later}, abandoned ${row.abandoned}, n=${row.journeys}`}
            >
              <span className="seg-first" style={{ flexGrow: row.first }} />
              <span className="seg-later" style={{ flexGrow: row.later }} />
              <span className="seg-abandoned" style={{ flexGrow: row.abandoned }} />
            </div>
            <span className="stack-n">n={row.journeys}</span>
          </div>
        ))}
      </div>
      <figcaption>Bar length follows the committed Sankey counts. Exact counts are in the table.</figcaption>
    </figure>
  );
}

export function ChartFrame({
  src,
  alt,
  width,
  height,
  caption,
  priority = false,
  sourceHref,
  sourceLabel,
}: {
  src: string;
  alt: string;
  width: number;
  height: number;
  caption: string;
  priority?: boolean;
  sourceHref?: string;
  sourceLabel?: string;
}) {
  return (
    <figure className="chart">
      <Image
        src={src}
        alt={alt}
        width={width}
        height={height}
        sizes="(max-width: 72rem) 100vw, 72rem"
        priority={priority}
        style={{ width: "100%", height: "auto" }}
      />
      <figcaption>
        <span>{caption}</span>
        {sourceHref && sourceLabel ? (
          <a href={sourceHref} rel="noopener noreferrer">
            {sourceLabel}
          </a>
        ) : null}
      </figcaption>
    </figure>
  );
}
