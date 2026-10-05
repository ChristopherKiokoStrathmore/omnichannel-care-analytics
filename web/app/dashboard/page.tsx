import type { Metadata } from "next";
import { ChartFrame, OutcomeStack, RateBar, ResponseChart } from "@/components/charts";
import { HeadlinePair } from "@/components/HeadlinePair";
import {
  CHANNELS,
  definitions,
  events,
  FOLLOW_COLUMNS,
  followMatrix,
  funnelRates,
  groupChannel,
  intentGroups,
  intents,
  journeys,
  largestFollows,
  lookupSpill,
  resolutionByChannel,
  sankey,
  seed,
  socialClock,
  ttfr,
} from "@/lib/figures";
import { REPO_HEATMAP_HTML, REPO_RECOMMENDATIONS, REPO_SANKEY_HTML } from "@/lib/site";

export const metadata: Metadata = {
  title: "Dashboard",
  description:
    "SYNTHETIC KPI dashboard, seed 20260929. Resolution rate 81.4% (3256/4000). Digital-first journeys that later reach a call: 32.0% (971/3035).",
};

const SECTIONS = [
  { href: "#funnel", label: "Funnel" },
  { href: "#outcome", label: "Outcomes" },
  { href: "#response", label: "Response" },
  { href: "#channel", label: "Channel" },
  { href: "#intent", label: "Intent" },
  { href: "#flows", label: "Flows" },
  { href: "#friction", label: "Friction" },
  { href: "#notes", label: "Notes" },
] as const;

const maxFlow = Math.max(...followMatrix.flatMap((row) => row.cells.map((cell) => cell.n)));

export default function DashboardPage() {
  const ussd = ttfr.find((row) => row.channel === "ussd");
  const social = ttfr.find((row) => row.channel === "social");
  const selfService = intentGroups.find((row) => row.group === "self_service_candidate");
  const complaint = intentGroups.find((row) => row.group === "complaint");
  const ussdSelf = groupChannel.find(
    (row) => row.group === "self_service_candidate" && row.channel === "ussd",
  );
  const appSelf = groupChannel.find(
    (row) => row.group === "self_service_candidate" && row.channel === "app",
  );
  const ussdComplaint = groupChannel.find((row) => row.group === "complaint" && row.channel === "ussd");
  const callComplaint = groupChannel.find((row) => row.group === "complaint" && row.channel === "call");
  const socialResolution = resolutionByChannel.find((row) => row.channel === "social");
  const ussdToCall = largestFollows.find((row) => row.from === "ussd" && row.to === "call");

  if (
    !ussd ||
    !social ||
    !selfService ||
    !complaint ||
    !ussdSelf ||
    !appSelf ||
    !ussdComplaint ||
    !callComplaint ||
    !socialResolution ||
    !ussdToCall
  ) {
    throw new Error("missing dashboard figures");
  }

  return (
    <div className="page">
      <header className="dash-intro">
        <p className="kicker">KPI dashboard · seed {seed}</p>
        <h1>Funnel, first response, and resolution</h1>
        <p className="lede">
          {journeys} synthetic journeys and {events} events. A journey is one customer, one intent,
          and one or more contacts. Digital channels are ussd, app, web, and social. The assisted
          channel is call.
        </p>
        <HeadlinePair />
      </header>

      <nav className="section-nav" aria-label="Dashboard sections">
        {SECTIONS.map((section) => (
          <a key={section.href} href={section.href}>
            {section.label}
          </a>
        ))}
      </nav>

      <section id="funnel" className="band">
        <header className="section-head">
          <p>01</p>
          <h2>Funnel</h2>
        </header>
        <p className="section-lead">
          Each bar is a committed count divided by its own denominator. The two digital-to-call
          rows share a numerator and use different denominators.
        </p>
        <div className="rate-list">
          {funnelRates.map((item) => (
            <RateBar
              key={item.id}
              label={item.label}
              value={item.rate}
              note={item.note}
              emphasis={item.emphasis}
            />
          ))}
        </div>
      </section>

      <section id="outcome" className="band">
        <header className="section-head">
          <p>02</p>
          <h2>First channel to journey outcome</h2>
        </header>
        <p className="section-lead">
          The Sankey splits the same {journeys} journeys into resolved on the first contact,
          resolved after another contact, or abandoned.
        </p>
        <OutcomeStack rows={sankey} />
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Sankey counts by first channel">
          <table>
            <caption>Committed Sankey counts by first channel. Source: reports/kpis.json.</caption>
            <thead>
              <tr>
                <th scope="col">First channel</th>
                <th scope="col">Resolved on first contact</th>
                <th scope="col">Resolved after another contact</th>
                <th scope="col">Abandoned</th>
                <th scope="col">Journeys</th>
              </tr>
            </thead>
            <tbody>
              {sankey.map((row) => (
                <tr key={row.channel}>
                  <th scope="row">{row.channel}</th>
                  <td>{row.first}</td>
                  <td>{row.later}</td>
                  <td>{row.abandoned}</td>
                  <td>{row.journeys}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <ChartFrame
          src="/charts/SYNTHETIC_sankey.png"
          alt="SYNTHETIC Sankey chart. First channel, ussd, app, web, social, or call, flows to resolved on first contact, resolved after another contact, or abandoned."
          width={1567}
          height={898}
          caption="Static copy of the committed Sankey. SYNTHETIC data."
          sourceHref={REPO_SANKEY_HTML}
          sourceLabel="Interactive HTML on GitHub"
        />
      </section>

      <section id="response" className="band">
        <header className="section-head">
          <p>03</p>
          <h2>Time to first response</h2>
        </header>
        <p className="section-lead">
          Delay, in minutes, between a journey&apos;s first inbound timestamp and the response on
          that same first contact. Every synthetic contact has a response. Median and the 90th
          percentile use DuckDB quantile_cont (linear), shown to one decimal as in
          reports/headlines.md.
        </p>
        <ResponseChart rows={ttfr} />
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Time to first response by first channel">
          <table>
            <caption>Synthetic time-to-first-response by first channel.</caption>
            <thead>
              <tr>
                <th scope="col">First channel</th>
                <th scope="col">Journeys</th>
                <th scope="col">Median minutes</th>
                <th scope="col">90th percentile minutes</th>
              </tr>
            </thead>
            <tbody>
              {ttfr.map((row) => (
                <tr key={row.channel}>
                  <th scope="row">{row.channel}</th>
                  <td>{row.journeys}</td>
                  <td>{row.median}</td>
                  <td>{row.p90}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="channel" className="band">
        <header className="section-head">
          <p>04</p>
          <h2>Contact resolution by channel</h2>
        </header>
        <p className="section-lead">
          Resolved contacts divided by contacts on that channel. A journey has at most one resolved
          contact, the one that closes it.
        </p>
        <div className="rate-list">
          {resolutionByChannel.map((row) => (
            <RateBar key={row.channel} label={row.channel} value={row.rate} />
          ))}
        </div>
        <ChartFrame
          src="/charts/resolution_by_channel.png"
          alt="SYNTHETIC bar chart of contact resolution by channel: ussd 43.4 percent (699 of 1611), app 50.8 percent (582 of 1145), web 43.9 percent (317 of 722), social 19.4 percent (102 of 526), call 65.6 percent (1556 of 2372)."
          width={1440}
          height={720}
          caption="Static copy of the committed channel chart. SYNTHETIC data."
        />
      </section>

      <section id="intent" className="band">
        <header className="section-head">
          <p>05</p>
          <h2>Resolution by intent</h2>
        </header>
        <p className="section-lead">
          Complaint journeys move on to the call channel more often than lookup journeys. The rates
          below are the group totals printed in reports/headlines.md.
        </p>
        <div className="group-grid">
          {intentGroups.map((group) => (
            <article key={group.group} className="group-card">
              <h3>{group.label}</h3>
              <RateBar label="Journey resolution" value={group.resolution} />
              <RateBar
                label="Digital-to-call among digital-first"
                value={group.digitalToCallRate}
              />
            </article>
          ))}
        </div>
        <ChartFrame
          src="/charts/intent_group_outcomes.png"
          alt="SYNTHETIC grouped bars. Self-service candidate: journey resolution 94.7 percent (1401 of 1480) and digital-to-call 12.9 percent (144 of 1112). Assisted: 83.0 percent (1276 of 1538) and 36.6 percent (434 of 1185). Complaint: 59.0 percent (579 of 982) and 53.3 percent (393 of 738)."
          width={1440}
          height={760}
          caption="Static copy of the committed intent-group chart. SYNTHETIC data."
        />
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Intent group totals">
          <table>
            <caption>Synthetic results by intent group. Rates match reports/headlines.md.</caption>
            <thead>
              <tr>
                <th scope="col">Intent group</th>
                <th scope="col">Journeys</th>
                <th scope="col">Resolved</th>
                <th scope="col">Journey resolution</th>
                <th scope="col">Resolved on first contact</th>
                <th scope="col">Digital-first</th>
                <th scope="col">Digital-to-call</th>
                <th scope="col">Digital-to-call among digital-first</th>
              </tr>
            </thead>
            <tbody>
              {intentGroups.map((group) => (
                <tr key={group.group}>
                  <th scope="row">{group.label}</th>
                  <td>{group.journeys}</td>
                  <td>{group.resolvedJourneys}</td>
                  <td>{group.resolution.text}</td>
                  <td>{group.resolvedOnFirstContact}</td>
                  <td>{group.digitalFirst}</td>
                  <td>{group.digitalToCall}</td>
                  <td>{group.digitalToCallRate.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="subhead">Contact resolution by intent group and channel</h3>
        <p className="section-lead">
          The base probability is the config input. The realised rate is the output. Realised rates
          sit near the base inputs because of sampling and the two adjustments for later attempts
          and slow responses.
        </p>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Resolution by intent group and channel">
          <table>
            <caption>Base probability and realised contact resolution. Source: reports/headlines.md.</caption>
            <thead>
              <tr>
                <th scope="col">Intent group</th>
                <th scope="col">Channel</th>
                <th scope="col">Config base</th>
                <th scope="col">Contacts</th>
                <th scope="col">Resolved contacts</th>
                <th scope="col">Realised rate</th>
              </tr>
            </thead>
            <tbody>
              {groupChannel.map((row) => (
                <tr key={`${row.group}-${row.channel}`}>
                  <th scope="row">{row.label}</th>
                  <td>{row.channel}</td>
                  <td>{row.base}</td>
                  <td>{row.contacts}</td>
                  <td>{row.resolvedContacts}</td>
                  <td>{row.realised.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <h3 className="subhead">Counts by intent</h3>
        <p className="section-lead">
          reports/headlines.md prints rates for the three groups, not a rate for every intent. This
          table stays in counts from reports/kpis.json.
        </p>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Counts by intent">
          <table>
            <caption>Synthetic journey counts by intent. No rate is added here.</caption>
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col">Intent</th>
                <th scope="col">Group</th>
                <th scope="col">Journeys</th>
                <th scope="col">Resolved journeys</th>
                <th scope="col">Digital-first</th>
                <th scope="col">Digital-to-call</th>
              </tr>
            </thead>
            <tbody>
              {intents.map((row) => (
                <tr key={row.intent}>
                  <td>{row.category}</td>
                  <th scope="row">{row.intent}</th>
                  <td>{row.group}</td>
                  <td>{row.journeys}</td>
                  <td>{row.resolvedJourneys}</td>
                  <td>{row.digitalFirst}</td>
                  <td>{row.digitalToCall}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section id="flows" className="band">
        <header className="section-head">
          <p>06</p>
          <h2>Directly-follows</h2>
        </header>
        <p className="section-lead">
          Among steps that change channel, the largest flow is ussd followed by call ({ussdToCall.n}
          ). A second contact on the same channel counts as a repeat contact and does not count as a
          channel switch.
        </p>
        <ol className="flow-list">
          {largestFollows.map((row) => (
            <li key={`${row.from}-${row.to}`}>
              <span>
                {row.from} → {row.to}
              </span>
              <strong>{row.n}</strong>
            </li>
          ))}
        </ol>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Directly-follows counts">
          <table className="matrix">
            <caption>All committed directly-follows counts. Rows are the preceding activity.</caption>
            <thead>
              <tr>
                <th scope="col">From</th>
                {FOLLOW_COLUMNS.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {followMatrix.map((row) => (
                <tr key={row.from}>
                  <th scope="row">{row.from}</th>
                  {row.cells.map((cell) => (
                    <td key={cell.to} className={cell.n === maxFlow ? "peak" : undefined}>
                      {cell.n}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section-lead">
          <a href="/charts/SYNTHETIC_directly_follows.csv">Download the committed CSV</a>
        </p>
      </section>

      <section id="friction" className="band">
        <header className="section-head">
          <p>07</p>
          <h2>Friction heatmap</h2>
        </header>
        <p className="section-lead">
          Realised friction is one minus the contact resolution rate. Cells sit near the base
          probabilities in the config, moved by the attempt penalty and the slow-response penalty.
        </p>
        <ChartFrame
          src="/charts/SYNTHETIC_friction_heatmap.png"
          alt="SYNTHETIC friction heatmap. Rows are intents and columns are channels ussd, app, web, social, and call. Friction is one minus the contact resolution rate. The chart is labelled SYNTHETIC DATA."
          width={1427}
          height={1762}
          caption="Static copy of the committed heatmap. SYNTHETIC data."
          sourceHref={REPO_HEATMAP_HTML}
          sourceLabel="Interactive HTML on GitHub"
        />
        <p className="section-lead">
          <a href="/charts/SYNTHETIC_friction_matrix.csv">Download the committed friction matrix</a>
        </p>
      </section>

      <section id="notes" className="band">
        <header className="section-head">
          <p>08</p>
          <h2>How to read the rates</h2>
        </header>
        <div className="definitions">
          {definitions.map((item) => (
            <details key={item.title}>
              <summary>{item.title}</summary>
              <p>{item.text}</p>
            </details>
          ))}
        </div>

        <h3 className="subhead">Design notes from the recommendations file</h3>
        <p className="section-lead">
          These are hypotheses for a care journey. Each one names whether it rests on the public
          Bitext training set or on the synthetic log.{" "}
          <a href={REPO_RECOMMENDATIONS} rel="noopener noreferrer">
            docs/recommendations.md
          </a>
        </p>
        <div className="note-grid">
          <article>
            <h3>Lookup intents on USSD and in the app</h3>
            <p>
              Self-service contacts resolve at base {ussdSelf.base}, realised {ussdSelf.realised.text}{" "}
              on ussd, and base {appSelf.base}, realised {appSelf.realised.text} on the app. USSD
              first-contact time-to-first-response has median {ussd.median} minutes (n={ussd.journeys}
              ). Digital-to-call in this group: {selfService.digitalToCallRate.text} of its
              digital-first journeys.
            </p>
          </article>
          <article>
            <h3>Keep a person available for complaints</h3>
            <p>
              Complaint contacts resolve at base {ussdComplaint.base}, realised{" "}
              {ussdComplaint.realised.text} on ussd, and base {callComplaint.base}, realised{" "}
              {callComplaint.realised.text} on call. Journey resolution is {complaint.resolution.text}.
              Digital-to-call among its digital-first journeys is {complaint.digitalToCallRate.text}.
            </p>
          </article>
          <article>
            <h3>Treat social as acknowledgement</h3>
            <p>
              The social clock is an input (lognormal mu {socialClock.mu}). On simulated first
              contacts the median is {social.median} minutes and the 90th percentile is {social.p90}{" "}
              minutes (n={social.journeys}). The model multiplies resolution probability by{" "}
              {socialClock.slowFactor} when a response is slower than {socialClock.slowMinutes}{" "}
              minutes. Lowest realised contact resolution: social, {socialResolution.rate.text}.
            </p>
          </article>
        </div>

        <h3 className="subhead">Lookup intents, digital-to-call over journeys</h3>
        <p className="section-lead">
          The fraction in docs/recommendations.md divides digital-to-call by journeys for that
          intent. It does not use the digital-first denominator behind the 32.0% headline.
        </p>
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Lookup intent digital-to-call">
          <table>
            <caption>
              Self-service intents ordered as in docs/recommendations.md. The rate is digital-to-call
              over journeys.
            </caption>
            <thead>
              <tr>
                <th scope="col">Intent</th>
                <th scope="col">Journeys</th>
                <th scope="col">Digital-first</th>
                <th scope="col">Digital-to-call</th>
                <th scope="col">Digital-to-call / journeys</th>
              </tr>
            </thead>
            <tbody>
              {lookupSpill.map((row) => (
                <tr key={row.intent}>
                  <th scope="row">{row.intent}</th>
                  <td>{row.journeys}</td>
                  <td>{row.digitalFirst}</td>
                  <td>{row.digitalToCall}</td>
                  <td>{row.rate.text}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="section-lead">
          Channels in the generator, in report order: {CHANNELS.join(", ")}.
        </p>
      </section>
    </div>
  );
}
