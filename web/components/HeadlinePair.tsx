import { digitalFirstLaterCall, resolution } from "@/lib/figures";

export function HeadlinePair() {
  return (
    <div className="headline-pair">
      <article>
        <p>Journey resolution</p>
        <strong>{resolution.percent}</strong>
        <span>{resolution.fraction}</span>
      </article>
      <article>
        <p>Digital-first journeys that later reach a call</p>
        <strong>{digitalFirstLaterCall.percent}</strong>
        <span>{digitalFirstLaterCall.fraction}</span>
      </article>
    </div>
  );
}
