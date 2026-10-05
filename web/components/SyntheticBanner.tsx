import { digitalFirstLaterCall, resolution, seed } from "@/lib/figures";

export function SyntheticBanner() {
  return (
    <div className="synthetic-banner" role="note">
      <p>
        <strong>SYNTHETIC</strong> data, seed {seed}. Not a real-world measurement.
      </p>
      <p>
        Journey resolution {resolution.text}. Digital-first journeys that later reach a call:{" "}
        {digitalFirstLaterCall.text}.
      </p>
    </div>
  );
}
