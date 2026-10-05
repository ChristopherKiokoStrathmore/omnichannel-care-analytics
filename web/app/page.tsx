import Link from "next/link";
import { ChartFrame, RateBar } from "@/components/charts";
import { HeadlinePair } from "@/components/HeadlinePair";
import {
  digitalFirstLaterCall,
  events,
  firstContact,
  journeys,
  publicProfile,
  resolution,
  resolutionByChannel,
  seed,
  ttfr,
} from "@/lib/figures";
import { REPO_URL } from "@/lib/site";

const ussd = ttfr.find((row) => row.channel === "ussd");
const social = ttfr.find((row) => row.channel === "social");
const callResolution = resolutionByChannel.find((row) => row.channel === "call");
const socialResolution = resolutionByChannel.find((row) => row.channel === "social");

export default function HomePage() {
  if (!ussd || !social || !callResolution || !socialResolution) {
    throw new Error("missing home-page figures");
  }

  return (
    <div className="page">
      <section className="hero">
        <p className="kicker">Omnichannel care analytics · seed {seed}</p>
        <h1>
          <span className="display-percent">{digitalFirstLaterCall.percent}</span>
          of digital-first journeys later reach a call
        </h1>
        <p className="lede">
          {digitalFirstLaterCall.text}. {journeys} synthetic journeys, {events} events, one journey
          per customer. Journey resolution is {resolution.text}.
        </p>
        <HeadlinePair />
        <p className="actions">
          <Link href="/dashboard" className="button button-primary">
            Open the dashboard
          </Link>
          <a href={REPO_URL} className="button button-secondary" rel="noopener noreferrer">
            Pipeline on GitHub
          </a>
        </p>
      </section>

      <ChartFrame
        src="/charts/hero.png"
        alt="Diagram labelled SYNTHETIC data, seed 20260929. A customer moves from USSD to the app to social to a call. The pipeline scores 4,000 journeys and 6,376 events. The outcome shown is 32.0 percent of digital-first journeys later reaching a call, 971 of 3,035."
        width={1600}
        height={800}
        priority
        caption="Committed story chart. The 32.0% outcome is 971 of 3035 digital-first journeys."
      />

      <section className="index" aria-label="Dashboard entry points">
        <Link href="/dashboard#funnel" className="index-card">
          <span>01</span>
          <h2>Funnel</h2>
          <p>
            Resolution {resolution.text}. Resolved on the first contact {firstContact.text}.
          </p>
        </Link>
        <Link href="/dashboard#response" className="index-card">
          <span>02</span>
          <h2>Time to first response</h2>
          <p>
            ussd median {ussd.median} minutes (n={ussd.journeys}). social median {social.median}{" "}
            minutes (n={social.journeys}).
          </p>
        </Link>
        <Link href="/dashboard#channel" className="index-card">
          <span>03</span>
          <h2>Resolution by channel and intent</h2>
          <p>
            call {callResolution.rate.text}. social {socialResolution.rate.text}.
          </p>
        </Link>
      </section>

      <section className="band">
        <header className="section-head">
          <p>Scope</p>
          <h2>Three inputs, kept apart</h2>
        </header>
        <div className="scope-grid">
          <article>
            <h3>Synthetic journeys</h3>
            <p>
              Seed {seed}. {journeys} journeys. {events} events. All journey rates on the dashboard
              come from this log.
            </p>
          </article>
          <article>
            <h3>Bitext training set</h3>
            <p>
              {publicProfile.examples} examples, {publicProfile.intents} intents,{" "}
              {publicProfile.categories} categories, {publicProfile.perIntent} examples of each
              intent. Equal counts are how the file was built. They are not demand.
            </p>
          </article>
          <article>
            <h3>Twitter preview</h3>
            <p>
              {publicProfile.twitterRows} data rows ({publicProfile.twitterInbound} inbound,{" "}
              {publicProfile.twitterOutbound} outbound). Not a telco journey study. The reply delay
              below is not the synthetic time-to-first-response.
            </p>
          </article>
        </div>
      </section>

      <section className="band">
        <header className="section-head">
          <p>Public · Bitext</p>
          <h2>Training examples by category</h2>
        </header>
        <ChartFrame
          src="/charts/bitext_categories.png"
          alt="Bar chart of the public Bitext training set. Example counts by category: SERVICES 7000, SUBSCRIPTION 5000, PAYMENT 4000, COMPLAINTS 3000, CONSUMPTION 3000, BILLING 2000, CONTACT 2000. The chart says the equal counts are how the file was built, not demand."
          width={1440}
          height={720}
          caption="Public Bitext training set. Example counts by category."
        />
        <div className="table-scroll" tabIndex={0} role="region" aria-label="Bitext examples by category">
          <table>
            <caption>Bitext examples by category. Counts from reports/headlines.md.</caption>
            <thead>
              <tr>
                <th scope="col">Category</th>
                <th scope="col">Examples</th>
                <th scope="col">Intents</th>
              </tr>
            </thead>
            <tbody>
              {publicProfile.categoriesRows.map((row) => (
                <tr key={row.category}>
                  <th scope="row">{row.category}</th>
                  <td>{row.n_examples}</td>
                  <td>{row.n_intents}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <h3 className="subhead">Language-tag shares</h3>
        <p className="section-lead">
          Shares of the {publicProfile.examples} training examples. Shortest median instruction
          length: {publicProfile.shortestMedian} characters ({publicProfile.shortestIntent}).
          Longest: {publicProfile.longestMedian} characters ({publicProfile.longestIntent}).
        </p>
        <div className="rate-list">
          {publicProfile.tags.map((tag) => (
            <RateBar key={tag.tag} label={`${tag.meaning} (${tag.tag})`} value={tag.rate} />
          ))}
        </div>
      </section>

      <section className="band">
        <header className="section-head">
          <p>Public · Twitter preview</p>
          <h2>Not a journey sample</h2>
        </header>
        <p className="section-lead">
          {publicProfile.twitterPairs} inbound-to-company reply pairs sit inside the preview. Median
          reply delay on those pairs: {publicProfile.twitterMedian} minutes. 90th percentile:{" "}
          {publicProfile.twitterP90} minutes. Preview tweets from the telecom and cable-ISP
          allowlist, combined: {publicProfile.telecomTweets}. Do not generalise these delays.
        </p>
        <p className="actions">
          <a href={REPO_URL} className="button button-secondary" rel="noopener noreferrer">
            Read the study on GitHub
          </a>
        </p>
      </section>
    </div>
  );
}
