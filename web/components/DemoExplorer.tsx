"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { OutcomeStack, RateBar, ResponseChart } from "@/components/charts";
import { demoLog, fullSlice } from "@/lib/demo-log";
import {
  CHANNELS,
  GROUPS,
  GROUP_LABEL,
  OUTCOME_OPTIONS,
  PRESETS,
  computeSlice,
  describeFilters,
  emptyFilters,
  filterJourneys,
  filtersEqual,
  filtersFromSearch,
  filtersToSearch,
  type Channel,
  type Filters,
  type GroupId,
  type IntentStat,
  type Journey,
} from "@/lib/demo-metrics";
import { definitions, rate, type CountRate } from "@/lib/figures";

type Panel = "performance" | "taxonomy" | "journeys";
type IntentSort = "journeys" | "resolution" | "name";

const PAGE_SIZE = 8;
const PANELS: { id: Panel; label: string }[] = [
  { id: "performance", label: "Performance" },
  { id: "taxonomy", label: "Intent taxonomy" },
  { id: "journeys", label: "Journeys" },
];

function isPanel(value: string | null): value is Panel {
  return value === "performance" || value === "taxonomy" || value === "journeys";
}

function copyFilters(filters: Filters): Filters {
  return {
    groups: [...filters.groups],
    start: [...filters.start],
    touch: [...filters.touch],
    category: filters.category,
    intent: filters.intent,
    outcome: filters.outcome,
  };
}

function endLabel(journey: Journey): string {
  if (journey.end === "resolved") return "resolved";
  if (journey.end === "max_contacts") return "max contacts";
  return "abandoned";
}

export function DemoExplorer() {
  const params = useSearchParams();
  const [filters, setFilters] = useState<Filters>(() => filtersFromSearch(params));
  const [query, setQuery] = useState(() => params.get("q") ?? "");
  const [panel, setPanel] = useState<Panel>(() => (isPanel(params.get("view")) ? params.get("view") as Panel : "performance"));
  const [page, setPage] = useState(0);
  const [intentSort, setIntentSort] = useState<IntentSort>("journeys");

  const queryString = filtersToSearch(filters, { q: query.trim(), view: panel });

  useEffect(() => {
    const next = queryString ? `/demo?${queryString}` : "/demo";
    const current = `${window.location.pathname}${window.location.search}`;
    if (current !== next) {
      window.history.replaceState(null, "", next);
    }
  }, [queryString]);

  const broadFilters = useMemo(() => ({ ...filters, intent: "" }), [filters]);
  const broadJourneys = useMemo(
    () => filterJourneys(demoLog.journeys, broadFilters),
    [broadFilters],
  );
  const focusedJourneys = useMemo(
    () => (filters.intent ? broadJourneys.filter((journey) => journey.intent === filters.intent) : broadJourneys),
    [broadJourneys, filters.intent],
  );
  const metrics = useMemo(() => computeSlice(focusedJourneys), [focusedJourneys]);
  const broadMetrics = useMemo(() => computeSlice(broadJourneys), [broadJourneys]);
  const intentStats = useMemo(
    () => new Map(broadMetrics.byIntent.map((row) => [row.intent, row])),
    [broadMetrics],
  );

  const activePreset = PRESETS.find((preset) => filtersEqual(preset.filters, filters));
  const sliceText = describeFilters(filters, metrics.journeys);
  const resolutionText =
    metrics.journeys === 0 ? "no journeys" : rate(metrics.resolved, metrics.journeys).text;
  const isFull = filtersEqual(filters, emptyFilters());

  function apply(next: Filters) {
    setFilters(copyFilters(next));
    setPage(0);
  }

  function toggleValue<T extends string>(list: T[], value: T): T[] {
    return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
  }

  function intentRecord(intent: string) {
    return demoLog.taxonomy.intents.find((item) => item.intent === intent);
  }

  function toggleGroup(group: GroupId) {
    const groups = toggleValue(filters.groups, group);
    const current = filters.intent ? intentRecord(filters.intent) : undefined;
    const intentOk = !current || groups.length === 0 || groups.includes(current.group);
    apply({ ...filters, groups, intent: intentOk ? filters.intent : "" });
  }

  function toggleChannel(key: "start" | "touch", channel: Channel) {
    apply({ ...filters, [key]: toggleValue(filters[key], channel) });
  }

  function setCategory(category: string) {
    const current = filters.intent ? intentRecord(filters.intent) : undefined;
    const intentOk = !current || category === "" || current.category === category;
    apply({ ...filters, category, intent: intentOk ? filters.intent : "" });
  }

  function focusIntent(intent: string) {
    if (filters.intent === intent) {
      apply({ ...filters, intent: "" });
      return;
    }
    const record = intentRecord(intent);
    if (!record) return;
    const groups =
      filters.groups.length > 0 && !filters.groups.includes(record.group) ? [] : filters.groups;
    const category = filters.category && filters.category !== record.category ? "" : filters.category;
    apply({ ...filters, intent, category, groups });
  }

  const intentChoices = demoLog.taxonomy.intents.filter((item) => {
    if (filters.category && item.category !== filters.category) return false;
    if (filters.groups.length > 0 && !filters.groups.includes(item.group)) return false;
    return true;
  });

  const sortedIntents = [...broadMetrics.byIntent].sort((left, right) => {
    if (intentSort === "name") return left.intent.localeCompare(right.intent);
    if (intentSort === "resolution") {
      const leftRate = left.resolved / left.journeys;
      const rightRate = right.resolved / right.journeys;
      return rightRate - leftRate || right.journeys - left.journeys;
    }
    return right.journeys - left.journeys || left.intent.localeCompare(right.intent);
  });

  const visibleTaxonomy = demoLog.taxonomy.categories.filter(
    (category) => filters.category === "" || category.category === filters.category,
  );

  const journeyQuery = query.trim().toLowerCase();
  const listed = focusedJourneys.filter((journey) => {
    if (!journeyQuery) return true;
    return (
      journey.id.toLowerCase().includes(journeyQuery) ||
      journey.intent.toLowerCase().includes(journeyQuery)
    );
  });
  const pageCount = Math.max(1, Math.ceil(listed.length / PAGE_SIZE));
  const safePage = Math.min(page, pageCount - 1);
  const pageRows = listed.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const switches = metrics.flows.filter(
    (flow) => flow.from !== flow.to && flow.to !== "resolved" && flow.to !== "abandoned",
  );

  return (
    <div className="page demo-page">
      <header className="dash-intro">
        <p className="kicker">Live demo · synthetic seed {demoLog.seed}</p>
        <h1>Filter journeys, read the rates</h1>
        <p className="lede">
          {demoLog.nJourneys.toLocaleString("en-US")} synthetic journeys and{" "}
          {demoLog.nEvents.toLocaleString("en-US")} events. Choose a channel, an intent, or a
          preset. Every rate is recomputed from the journeys still in the slice. The Bitext list
          is a public training taxonomy, not demand.
        </p>
        <p className="actions">
          <Link href="/" className="button button-secondary">
            Read the article
          </Link>
          <Link href="/dashboard" className="button button-secondary">
            KPI report
          </Link>
        </p>
      </header>

      <div className="demo-presets" role="group" aria-label="Preset slices">
        {PRESETS.map((preset) => {
          const selected = activePreset?.id === preset.id;
          return (
            <button
              key={preset.id}
              type="button"
              className={selected ? "chip chip-on" : "chip"}
              aria-pressed={selected}
              onClick={() => apply(preset.filters)}
            >
              {preset.label}
            </button>
          );
        })}
      </div>
      {activePreset ? <p className="section-lead">{activePreset.detail}</p> : null}
      <p className="slice-line" aria-live="polite">
        {sliceText}. Resolution {resolutionText}.
        {isFull ? " This is the full synthetic log." : " Full log resolution is 81.4% (3256/4000)."}
      </p>

      <div className="demo-layout">
        <form className="demo-filters" onSubmit={(event) => event.preventDefault()}>
          <h2>Filters</h2>
          <fieldset>
            <legend>Intent group</legend>
            <div className="chip-row">
              {GROUPS.map((group) => (
                <button
                  key={group}
                  type="button"
                  className={filters.groups.includes(group) ? "chip chip-on" : "chip"}
                  aria-pressed={filters.groups.includes(group)}
                  onClick={() => toggleGroup(group)}
                >
                  {GROUP_LABEL[group]}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Started on</legend>
            <p className="filter-hint">First contact only.</p>
            <div className="chip-row">
              {CHANNELS.map((channel) => (
                <button
                  key={channel}
                  type="button"
                  className={filters.start.includes(channel) ? "chip chip-on" : "chip"}
                  aria-pressed={filters.start.includes(channel)}
                  onClick={() => toggleChannel("start", channel)}
                >
                  {channel}
                </button>
              ))}
            </div>
          </fieldset>
          <fieldset>
            <legend>Path includes</legend>
            <p className="filter-hint">Any contact on the path, including the first.</p>
            <div className="chip-row">
              {CHANNELS.map((channel) => (
                <button
                  key={channel}
                  type="button"
                  className={filters.touch.includes(channel) ? "chip chip-on" : "chip"}
                  aria-pressed={filters.touch.includes(channel)}
                  onClick={() => toggleChannel("touch", channel)}
                >
                  {channel}
                </button>
              ))}
            </div>
          </fieldset>
          <label className="field">
            <span>Category</span>
            <select value={filters.category} onChange={(event) => setCategory(event.target.value)}>
              <option value="">All categories</option>
              {demoLog.taxonomy.categories.map((category) => (
                <option key={category.category} value={category.category}>
                  {category.category}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Intent</span>
            <select
              value={filters.intent}
              onChange={(event) => {
                const intent = event.target.value;
                if (!intent) apply({ ...filters, intent: "" });
                else focusIntent(intent);
              }}
            >
              <option value="">All intents in this slice</option>
              {intentChoices.map((item) => (
                <option key={item.intent} value={item.intent}>
                  {item.intent}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Outcome</span>
            <select
              value={filters.outcome}
              onChange={(event) =>
                apply({
                  ...filters,
                  outcome: OUTCOME_OPTIONS.find((option) => option.id === event.target.value)?.id ?? "all",
                })
              }
            >
              {OUTCOME_OPTIONS.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <button type="button" className="button button-secondary" onClick={() => apply(emptyFilters())}>
            Reset filters
          </button>
        </form>

        <div className="demo-main">
          <div className="kpi-grid">
            <article className="kpi">
              <p>Journeys in this slice</p>
              <strong>{metrics.journeys.toLocaleString("en-US")}</strong>
              <span>{metrics.events.toLocaleString("en-US")} contacts</span>
              {isFull ? null : <span className="kpi-base">Full log 4,000 journeys</span>}
            </article>
            <KpiRate
              label="Journey resolution"
              numerator={metrics.resolved}
              denominator={metrics.journeys}
              baseline={rate(fullSlice.resolved, fullSlice.journeys)}
              showBaseline={!isFull}
            />
            <KpiRate
              label="Resolved on first contact"
              numerator={metrics.firstContact}
              denominator={metrics.journeys}
              baseline={rate(fullSlice.firstContact, fullSlice.journeys)}
              showBaseline={!isFull}
            />
            <KpiRate
              label="Repeat contact"
              numerator={metrics.repeat}
              denominator={metrics.journeys}
              baseline={rate(fullSlice.repeat, fullSlice.journeys)}
              showBaseline={!isFull}
            />
            <KpiRate
              label="Channel switch"
              numerator={metrics.switched}
              denominator={metrics.journeys}
              baseline={rate(fullSlice.switched, fullSlice.journeys)}
              showBaseline={!isFull}
            />
            <KpiRate
              label="Digital-to-call among digital-first"
              numerator={metrics.digitalToCall}
              denominator={metrics.digitalFirst}
              baseline={rate(fullSlice.digitalToCall, fullSlice.digitalFirst)}
              showBaseline={!isFull}
            />
          </div>

          <div className="view-tabs" role="tablist" aria-label="Demo views">
            {PANELS.map((item) => {
              const selected = panel === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  role="tab"
                  id={`tab-${item.id}`}
                  aria-selected={selected}
                  aria-controls={`panel-${item.id}`}
                  onClick={() => setPanel(item.id)}
                >
                  {item.label}
                </button>
              );
            })}
          </div>

          {panel === "performance" ? (
            <div role="tabpanel" id="panel-performance" aria-labelledby="tab-performance">
              {metrics.journeys === 0 ? (
                <EmptySlice onReset={() => apply(emptyFilters())} />
              ) : (
                <>
                  <section className="band">
                    <header className="section-head">
                      <p>01</p>
                      <h2>Funnel</h2>
                    </header>
                    <p className="section-lead">
                      Each bar divides a count in this slice by its own denominator.
                    </p>
                    <div className="rate-list">
                      <RateOrEmpty
                        label="Journey resolution"
                        numerator={metrics.resolved}
                        denominator={metrics.journeys}
                        note="End reason is resolved."
                        emphasis
                      />
                      <RateOrEmpty
                        label="Resolved on the first contact"
                        numerator={metrics.firstContact}
                        denominator={metrics.journeys}
                      />
                      <RateOrEmpty
                        label="Repeat contact"
                        numerator={metrics.repeat}
                        denominator={metrics.journeys}
                        note="Two or more contacts in the same journey."
                      />
                      <RateOrEmpty
                        label="Channel switch"
                        numerator={metrics.switched}
                        denominator={metrics.journeys}
                        note="More than one distinct channel. A second contact on the same channel is not a switch."
                      />
                      <RateOrEmpty
                        label="Digital-first"
                        numerator={metrics.digitalFirst}
                        denominator={metrics.journeys}
                        note="First contact on ussd, app, web, or social."
                      />
                      <RateOrEmpty
                        label="Digital-to-call, journeys in this slice"
                        numerator={metrics.digitalToCall}
                        denominator={metrics.journeys}
                      />
                      <RateOrEmpty
                        label="Digital-to-call, digital-first journeys"
                        numerator={metrics.digitalToCall}
                        denominator={metrics.digitalFirst}
                        note="Same numerator, divided only by journeys that started on a digital channel."
                        emphasis
                      />
                      <RateOrEmpty
                        label="Abandoned"
                        numerator={metrics.abandoned}
                        denominator={metrics.journeys}
                        note={`Chose abandon ${metrics.choseAbandon}. Max contacts ${metrics.maxContacts}.`}
                      />
                    </div>
                  </section>

                  <section className="band">
                    <header className="section-head">
                      <p>02</p>
                      <h2>First channel to outcome</h2>
                    </header>
                    <OutcomeStack
                      rows={metrics.sankey}
                      caption="Counts are the journeys in this slice. A channel with no journeys is omitted."
                    />
                  </section>

                  <section className="band">
                    <header className="section-head">
                      <p>03</p>
                      <h2>Time to first response</h2>
                    </header>
                    <p className="section-lead">
                      Minutes from the first inbound timestamp to the response on that same first
                      contact. Median and the 90th percentile use linear interpolation.
                    </p>
                    <ResponseChart
                      rows={metrics.ttfr.map((row) => ({
                        channel: row.channel,
                        journeys: row.journeys,
                        median: row.median.toFixed(1),
                        p90: row.p90.toFixed(1),
                        medianMinutes: row.median,
                        p90Minutes: row.p90,
                      }))}
                    />
                  </section>

                  <section className="band">
                    <header className="section-head">
                      <p>04</p>
                      <h2>Contact resolution by channel</h2>
                    </header>
                    <p className="section-lead">
                      Resolved contacts divided by contacts on that channel. A journey has at most
                      one resolved contact, the one that closes it.
                    </p>
                    <div className="rate-list">
                      {metrics.resolutionByChannel.map((row) =>
                        row.contacts === 0 ? (
                          <p key={row.channel} className="section-lead">
                            {row.channel}: no contacts in this slice.
                          </p>
                        ) : (
                          <RateBar
                            key={row.channel}
                            label={row.channel}
                            value={rate(row.resolvedContacts, row.contacts)}
                          />
                        ),
                      )}
                    </div>
                  </section>

                  <section className="band">
                    <header className="section-head">
                      <p>05</p>
                      <h2>Directly-follows</h2>
                    </header>
                    <p className="section-lead">
                      {switches[0]
                        ? `Largest channel change in this slice: ${switches[0].from} followed by ${switches[0].to} (${switches[0].n}).`
                        : "No step in this slice changes channel."}{" "}
                      A second contact on the same channel is a repeat, not a switch.
                    </p>
                    <ol className="flow-list">
                      {metrics.flows.slice(0, 5).map((flow) => (
                        <li key={`${flow.from}-${flow.to}`}>
                          <span>
                            {flow.from} → {flow.to}
                          </span>
                          <strong>{flow.n}</strong>
                        </li>
                      ))}
                    </ol>
                  </section>

                  <section className="band">
                    <header className="section-head">
                      <p>06</p>
                      <h2>Intents in this slice</h2>
                    </header>
                    <p className="section-lead">
                      Choose an intent to narrow the rates above. The table ignores the intent
                      filter so the other intents stay visible.
                    </p>
                    <div className="chip-row sort-row">
                      {(
                        [
                          ["journeys", "Sort by journeys"],
                          ["resolution", "Sort by resolution"],
                          ["name", "Sort by name"],
                        ] as const
                      ).map(([id, label]) => (
                        <button
                          key={id}
                          type="button"
                          className={intentSort === id ? "chip chip-on" : "chip"}
                          aria-pressed={intentSort === id}
                          onClick={() => setIntentSort(id)}
                        >
                          {label}
                        </button>
                      ))}
                    </div>
                    <IntentTable
                      rows={sortedIntents}
                      selected={filters.intent}
                      onSelect={focusIntent}
                    />
                  </section>

                  <section className="band">
                    <header className="section-head">
                      <p>07</p>
                      <h2>Definitions</h2>
                    </header>
                    <div className="definitions">
                      {definitions.map((item) => (
                        <details key={item.title}>
                          <summary>{item.title}</summary>
                          <p>{item.text}</p>
                        </details>
                      ))}
                    </div>
                  </section>
                </>
              )}
            </div>
          ) : null}

          {panel === "taxonomy" ? (
            <div role="tabpanel" id="panel-taxonomy" aria-labelledby="tab-taxonomy">
              <section className="band">
                <header className="section-head">
                  <p>Public</p>
                  <h2>Bitext telco intents</h2>
                </header>
                <p className="section-lead">
                  {demoLog.taxonomy.source}. {demoLog.taxonomy.nExamples.toLocaleString("en-US")}{" "}
                  training examples, {demoLog.taxonomy.nIntents} intents,{" "}
                  {demoLog.taxonomy.nCategories} categories, {demoLog.taxonomy.examplesPerIntent}{" "}
                  examples of each intent. Bitext describes the file as a {demoLog.taxonomy.describedAs}.
                  Licence {demoLog.taxonomy.licence}. Equal counts are how the file was built. They
                  are not demand. Simulator weights are assumptions in the synthetic config.
                </p>
                <div className="chip-row">
                  <button
                    type="button"
                    className={filters.category === "" ? "chip chip-on" : "chip"}
                    aria-pressed={filters.category === ""}
                    onClick={() => setCategory("")}
                  >
                    All categories
                  </button>
                  {demoLog.taxonomy.categories.map((category) => (
                    <button
                      key={category.category}
                      type="button"
                      className={filters.category === category.category ? "chip chip-on" : "chip"}
                      aria-pressed={filters.category === category.category}
                      onClick={() => setCategory(category.category)}
                    >
                      {category.category}
                    </button>
                  ))}
                </div>
                {visibleTaxonomy.map((category) => {
                  const intents = demoLog.taxonomy.intents.filter(
                    (item) => item.category === category.category,
                  );
                  const inSlice = intents.reduce(
                    (sum, item) => sum + (intentStats.get(item.intent)?.journeys ?? 0),
                    0,
                  );
                  return (
                    <section key={category.category} className="taxonomy-block">
                      <h3>
                        {category.category}
                        <span>
                          {category.nExamples.toLocaleString("en-US")} training examples ·{" "}
                          {inSlice.toLocaleString("en-US")} journeys in the current channel and group
                          filters
                        </span>
                      </h3>
                      <div className="intent-grid">
                        {intents.map((item) => {
                          const stat = intentStats.get(item.intent);
                          const selected = filters.intent === item.intent;
                          return (
                            <article
                              key={item.intent}
                              className={selected ? "intent-card intent-card-on" : "intent-card"}
                            >
                              <h4>
                                <button
                                  type="button"
                                  aria-pressed={selected}
                                  onClick={() => focusIntent(item.intent)}
                                >
                                  {item.intent}
                                </button>
                              </h4>
                              <p>{GROUP_LABEL[item.group]}</p>
                              <p>
                                {item.nExamples.toLocaleString("en-US")} training examples. Median
                                instruction {item.medianInstructionChars.toFixed(1)} characters.
                                Median response {item.medianResponseChars.toFixed(1)} characters.
                              </p>
                              <p>Simulator weight {item.weight}. Not measured demand.</p>
                              {stat && stat.journeys > 0 ? (
                                <>
                                  <RateBar
                                    label="Journey resolution in the other filters"
                                    value={rate(stat.resolved, stat.journeys)}
                                  />
                                  {stat.digitalFirst > 0 ? (
                                    <RateBar
                                      label="Digital-to-call among digital-first"
                                      value={rate(stat.digitalToCall, stat.digitalFirst)}
                                    />
                                  ) : (
                                    <p className="section-lead">No digital-first journeys in the other filters.</p>
                                  )}
                                </>
                              ) : (
                                <p className="section-lead">No journeys in the other filters.</p>
                              )}
                            </article>
                          );
                        })}
                      </div>
                    </section>
                  );
                })}
              </section>

              <section className="band">
                <header className="section-head">
                  <p>Public</p>
                  <h2>Language tags</h2>
                </header>
                <p className="section-lead">
                  Shares of the {demoLog.taxonomy.nExamples.toLocaleString("en-US")} training
                  examples. These tags describe the Bitext wording. They do not change when you
                  filter journeys.
                </p>
                <div className="rate-list">
                  {[...demoLog.taxonomy.tags]
                    .sort(
                      (left, right) =>
                        right.nExamples - left.nExamples || left.tag.localeCompare(right.tag),
                    )
                    .map((tag) => (
                      <RateBar
                        key={tag.tag}
                        label={`${tag.meaning} (${tag.tag})`}
                        value={rate(tag.nExamples, demoLog.taxonomy.nExamples)}
                      />
                    ))}
                </div>
              </section>
            </div>
          ) : null}

          {panel === "journeys" ? (
            <div role="tabpanel" id="panel-journeys" aria-labelledby="tab-journeys">
              <section className="band">
                <header className="section-head">
                  <p>Log</p>
                  <h2>Journeys in this slice</h2>
                </header>
                <p className="section-lead">
                  One customer, one intent, one path. Search looks through this slice only. It does
                  not change the rates.
                </p>
                <label className="field">
                  <span>Find a journey</span>
                  <input
                    type="search"
                    value={query}
                    placeholder="J00012 or check_usage"
                    onChange={(event) => {
                      setQuery(event.target.value);
                      setPage(0);
                    }}
                  />
                </label>
                {listed.length === 0 ? (
                  <p className="section-lead">No journey id or intent in this slice matches.</p>
                ) : (
                  <>
                    <p className="section-lead">
                      Showing {safePage * PAGE_SIZE + 1}–{safePage * PAGE_SIZE + pageRows.length} of{" "}
                      {listed.length.toLocaleString("en-US")}.
                    </p>
                    <div className="journey-list">
                      {pageRows.map((journey) => (
                        <article key={journey.id} className="journey-card">
                          <header>
                            <strong>{journey.id}</strong>
                            <span>{journey.intent}</span>
                            <span className={journey.resolved ? "end-pill" : "end-pill end-pill-stop"}>
                              {endLabel(journey)}
                            </span>
                          </header>
                          <ol className="path">
                            {journey.path.map((channel, index) => (
                              <li key={`${journey.id}-${index}`}>{channel}</li>
                            ))}
                            <li className={journey.resolved ? "path-end" : "path-end path-stop"}>
                              {endLabel(journey)}
                            </li>
                          </ol>
                          <p>
                            First response {journey.ttfr.toFixed(1)} min · {journey.contacts}{" "}
                            {journey.contacts === 1 ? "contact" : "contacts"} · {journey.category} ·{" "}
                            {GROUP_LABEL[journey.group]}
                          </p>
                          <button type="button" className="text-button" onClick={() => focusIntent(journey.intent)}>
                            {filters.intent === journey.intent ? "Clear this intent" : "Filter to this intent"}
                          </button>
                        </article>
                      ))}
                    </div>
                    {pageCount > 1 ? (
                      <div className="pager">
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() => setPage(Math.max(0, safePage - 1))}
                          disabled={safePage === 0}
                        >
                          Previous
                        </button>
                        <span>
                          Page {safePage + 1} of {pageCount}
                        </span>
                        <button
                          type="button"
                          className="button button-secondary"
                          onClick={() => setPage(Math.min(pageCount - 1, safePage + 1))}
                          disabled={safePage >= pageCount - 1}
                        >
                          Next
                        </button>
                      </div>
                    ) : null}
                  </>
                )}
              </section>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function KpiRate({
  label,
  numerator,
  denominator,
  baseline,
  showBaseline,
}: {
  label: string;
  numerator: number;
  denominator: number;
  baseline: CountRate;
  showBaseline: boolean;
}) {
  const value = denominator === 0 ? null : rate(numerator, denominator);
  return (
    <article className="kpi">
      <p>{label}</p>
      <strong>{value ? value.percent : "—"}</strong>
      <span>{value ? value.fraction : "No journeys in the denominator"}</span>
      {showBaseline ? <span className="kpi-base">Full log {baseline.percent}</span> : null}
    </article>
  );
}

function RateOrEmpty({
  label,
  numerator,
  denominator,
  note,
  emphasis = false,
}: {
  label: string;
  numerator: number;
  denominator: number;
  note?: string;
  emphasis?: boolean;
}) {
  if (denominator === 0) {
    return (
      <p className="section-lead">
        {label}: no journeys in the denominator.
      </p>
    );
  }
  return <RateBar label={label} value={rate(numerator, denominator)} note={note} emphasis={emphasis} />;
}

function IntentTable({
  rows,
  selected,
  onSelect,
}: {
  rows: IntentStat[];
  selected: string;
  onSelect: (intent: string) => void;
}) {
  return (
    <div className="table-scroll" tabIndex={0} role="region" aria-label="Intents in this slice">
      <table className="intent-table">
        <caption>Synthetic journeys by intent for the current filters, before the intent pick.</caption>
        <thead>
          <tr>
            <th scope="col">Intent</th>
            <th scope="col">Group</th>
            <th scope="col">Journeys</th>
            <th scope="col">Resolution</th>
            <th scope="col">Digital-to-call</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.intent} className={selected === row.intent ? "row-on" : undefined}>
              <th scope="row">
                <button
                  type="button"
                  className="text-button"
                  aria-pressed={selected === row.intent}
                  onClick={() => onSelect(row.intent)}
                >
                  {row.intent}
                </button>
              </th>
              <td>{GROUP_LABEL[row.group]}</td>
              <td>{row.journeys}</td>
              <td>{rate(row.resolved, row.journeys).text}</td>
              <td>
                {row.digitalFirst === 0 ? "—" : rate(row.digitalToCall, row.digitalFirst).text}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function EmptySlice({ onReset }: { onReset: () => void }) {
  return (
    <section className="band">
      <h2>No journeys in this slice</h2>
      <p className="section-lead">
        The filters exclude every synthetic journey. The taxonomy tab still lists the public
        intents.
      </p>
      <button type="button" className="button button-primary" onClick={onReset}>
        Reset filters
      </button>
    </section>
  );
}
