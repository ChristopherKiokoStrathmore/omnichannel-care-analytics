/**
 * Slice metrics for the live demo.
 *
 * quantileCont matches DuckDB quantile_cont (linear), position q * (n - 1).
 * tests/test_demo_log.py locks that formula to the committed time-to-first-response
 * figures. Unfiltered counts are checked again when the demo log is loaded.
 */

export const CHANNELS = ["ussd", "app", "web", "social", "call"] as const;
export type Channel = (typeof CHANNELS)[number];

export const GROUPS = ["self_service_candidate", "assisted", "complaint"] as const;
export type GroupId = (typeof GROUPS)[number];

export type EndReason = "resolved" | "chose_abandon" | "max_contacts";

export const GROUP_LABEL: Record<GroupId, string> = {
  self_service_candidate: "Self-service candidate",
  assisted: "Assisted",
  complaint: "Complaint",
};

export type OutcomeFilter =
  | "all"
  | "resolved"
  | "abandoned"
  | "first_contact"
  | "later_contact"
  | "digital_to_call"
  | "repeat"
  | "switched";

export const OUTCOME_OPTIONS: { id: OutcomeFilter; label: string }[] = [
  { id: "all", label: "All outcomes" },
  { id: "resolved", label: "Resolved" },
  { id: "abandoned", label: "Abandoned" },
  { id: "first_contact", label: "Resolved on first contact" },
  { id: "later_contact", label: "Resolved after another contact" },
  { id: "digital_to_call", label: "Digital, then a call" },
  { id: "repeat", label: "Repeat contact" },
  { id: "switched", label: "Channel switch" },
];

export interface Journey {
  id: string;
  intent: string;
  category: string;
  group: GroupId;
  first: Channel;
  ttfr: number;
  contacts: number;
  path: Channel[];
  resolved: boolean;
  end: EndReason;
  repeat: boolean;
  switched: boolean;
  digitalFirst: boolean;
  digitalToCall: boolean;
  firstContact: boolean;
}

export interface Filters {
  groups: GroupId[];
  start: Channel[];
  touch: Channel[];
  category: string;
  intent: string;
  outcome: OutcomeFilter;
}

export interface TaxonomyIntent {
  category: string;
  group: GroupId;
  intent: string;
  medianInstructionChars: number;
  medianResponseChars: number;
  nExamples: number;
  weight: number;
}

export interface TaxonomyTag {
  tag: string;
  meaning: string;
  nExamples: number;
}

export interface TaxonomyCategory {
  category: string;
  nExamples: number;
  nIntents: number;
}

export interface DemoTaxonomy {
  source: string;
  licence: string;
  describedAs: string;
  nExamples: number;
  nIntents: number;
  nCategories: number;
  examplesPerIntent: number;
  categories: TaxonomyCategory[];
  intents: TaxonomyIntent[];
  tags: TaxonomyTag[];
}

export interface DemoLog {
  seed: number;
  label: string;
  nEvents: number;
  nJourneys: number;
  digitalChannels: Channel[];
  assistedChannel: Channel;
  journeys: Journey[];
  taxonomy: DemoTaxonomy;
}

export type RawJourney = [
  string,
  string,
  string,
  GroupId,
  Channel,
  number,
  number,
  Channel[],
  number,
  EndReason,
];

export interface RawDemoFile {
  assisted_channel: Channel;
  digital_channels: Channel[];
  journeys: RawJourney[];
  label: string;
  n_events: number;
  n_journeys: number;
  not_a_real_world_measurement: boolean;
  seed: number;
  taxonomy: {
    categories: { category: string; n_examples: number; n_intents: number }[];
    described_as: string;
    examples_per_intent: number;
    intents: {
      category: string;
      group: GroupId;
      intent: string;
      median_instruction_chars: number;
      median_response_chars: number;
      n_examples: number;
      weight: number;
    }[];
    licence: string;
    n_categories: number;
    n_examples: number;
    n_intents: number;
    source: string;
    tags: { meaning: string; n_examples: number; tag: string }[];
  };
}

export function emptyFilters(): Filters {
  return {
    groups: [],
    start: [],
    touch: [],
    category: "",
    intent: "",
    outcome: "all",
  };
}

export const PRESETS: { id: string; label: string; detail: string; filters: Filters }[] = [
  {
    id: "all",
    label: "All journeys",
    detail: "The committed baseline for seed 20260929.",
    filters: emptyFilters(),
  },
  {
    id: "complaints",
    label: "Complaints",
    detail: "Complaint intents. Resolution falls and more digital journeys reach a call.",
    filters: { ...emptyFilters(), groups: ["complaint"] },
  },
  {
    id: "lookups",
    label: "Lookup intents",
    detail: "Self-service candidates: status checks such as usage, invoices, and coverage.",
    filters: { ...emptyFilters(), groups: ["self_service_candidate"] },
  },
  {
    id: "ussd",
    label: "Started on USSD",
    detail: "Journeys whose first contact is USSD.",
    filters: { ...emptyFilters(), start: ["ussd"] },
  },
  {
    id: "ussd-call",
    label: "USSD, then a call",
    detail: "USSD first, and a later contact on the call channel.",
    filters: { ...emptyFilters(), start: ["ussd"], outcome: "digital_to_call" },
  },
  {
    id: "social",
    label: "Started on social",
    detail: "The slow clock. Social first-response times sit far above USSD.",
    filters: { ...emptyFilters(), start: ["social"] },
  },
];

export function quantileCont(values: number[], q: number): number {
  if (values.length === 0) {
    throw new Error("quantile of an empty slice");
  }
  const ordered = [...values].sort((left, right) => left - right);
  if (ordered.length === 1) {
    return ordered[0];
  }
  const pos = q * (ordered.length - 1);
  const index = Math.floor(pos);
  const frac = pos - index;
  if (index >= ordered.length - 1) {
    return ordered[ordered.length - 1];
  }
  return ordered[index] * (1 - frac) + ordered[index + 1] * frac;
}

function isChannel(value: string): value is Channel {
  return (CHANNELS as readonly string[]).includes(value);
}

function isGroup(value: string): value is GroupId {
  return (GROUPS as readonly string[]).includes(value);
}

function isOutcome(value: string): value is OutcomeFilter {
  return OUTCOME_OPTIONS.some((option) => option.id === value);
}

export function hydrate(raw: RawDemoFile): DemoLog {
  if (!raw.not_a_real_world_measurement) {
    throw new Error("demo log is missing the synthetic flag");
  }
  const digital = new Set(raw.digital_channels);
  const journeys: Journey[] = raw.journeys.map((item) => {
    const path = item[7];
    const contacts = item[6];
    const resolved = item[8] === 1;
    const first = item[4];
    const end = item[9];
    if (path.length !== contacts || path[0] !== first) {
      throw new Error(`${item[0]} path does not match the journey header`);
    }
    if ((end === "resolved") !== resolved) {
      throw new Error(`${item[0]} end reason disagrees with resolved`);
    }
    if (!path.every(isChannel) || !isChannel(first) || !isGroup(item[3])) {
      throw new Error(`${item[0]} has an unknown channel or group`);
    }
    const digitalFirst = digital.has(first);
    return {
      id: item[0],
      intent: item[1],
      category: item[2],
      group: item[3],
      first,
      ttfr: item[5],
      contacts,
      path,
      resolved,
      end,
      repeat: contacts >= 2,
      switched: new Set(path).size > 1,
      digitalFirst,
      digitalToCall: digitalFirst && path.slice(1).includes("call"),
      firstContact: resolved && contacts === 1,
    };
  });
  const nEvents = journeys.reduce((sum, journey) => sum + journey.contacts, 0);
  if (journeys.length !== raw.n_journeys || nEvents !== raw.n_events) {
    throw new Error("demo log header does not match the journey rows");
  }
  return {
    seed: raw.seed,
    label: raw.label,
    nEvents,
    nJourneys: journeys.length,
    digitalChannels: raw.digital_channels,
    assistedChannel: raw.assisted_channel,
    journeys,
    taxonomy: {
      source: raw.taxonomy.source,
      licence: raw.taxonomy.licence,
      describedAs: raw.taxonomy.described_as,
      nExamples: raw.taxonomy.n_examples,
      nIntents: raw.taxonomy.n_intents,
      nCategories: raw.taxonomy.n_categories,
      examplesPerIntent: raw.taxonomy.examples_per_intent,
      categories: raw.taxonomy.categories.map((row) => ({
        category: row.category,
        nExamples: row.n_examples,
        nIntents: row.n_intents,
      })),
      intents: raw.taxonomy.intents.map((row) => ({
        category: row.category,
        group: row.group,
        intent: row.intent,
        medianInstructionChars: row.median_instruction_chars,
        medianResponseChars: row.median_response_chars,
        nExamples: row.n_examples,
        weight: row.weight,
      })),
      tags: raw.taxonomy.tags.map((row) => ({
        tag: row.tag,
        meaning: row.meaning,
        nExamples: row.n_examples,
      })),
    },
  };
}

export function matches(journey: Journey, filters: Filters): boolean {
  if (filters.groups.length > 0 && !filters.groups.includes(journey.group)) {
    return false;
  }
  if (filters.start.length > 0 && !filters.start.includes(journey.first)) {
    return false;
  }
  if (filters.touch.length > 0 && !journey.path.some((channel) => filters.touch.includes(channel))) {
    return false;
  }
  if (filters.category && journey.category !== filters.category) {
    return false;
  }
  if (filters.intent && journey.intent !== filters.intent) {
    return false;
  }
  switch (filters.outcome) {
    case "all":
      return true;
    case "resolved":
      return journey.resolved;
    case "abandoned":
      return !journey.resolved;
    case "first_contact":
      return journey.firstContact;
    case "later_contact":
      return journey.resolved && !journey.firstContact;
    case "digital_to_call":
      return journey.digitalToCall;
    case "repeat":
      return journey.repeat;
    case "switched":
      return journey.switched;
    default:
      return true;
  }
}

export function filterJourneys(journeys: Journey[], filters: Filters): Journey[] {
  return journeys.filter((journey) => matches(journey, filters));
}

export interface TtfrRow {
  channel: Channel;
  journeys: number;
  median: number;
  p90: number;
}

export interface ChannelResolution {
  channel: Channel;
  contacts: number;
  resolvedContacts: number;
}

export interface SankeyRow {
  channel: Channel;
  first: number;
  later: number;
  abandoned: number;
  journeys: number;
}

export interface IntentStat {
  intent: string;
  category: string;
  group: GroupId;
  journeys: number;
  resolved: number;
  digitalFirst: number;
  digitalToCall: number;
}

export interface Flow {
  from: string;
  to: string;
  n: number;
}

export interface SliceMetrics {
  journeys: number;
  events: number;
  resolved: number;
  abandoned: number;
  firstContact: number;
  repeat: number;
  switched: number;
  digitalFirst: number;
  digitalToCall: number;
  choseAbandon: number;
  maxContacts: number;
  ttfr: TtfrRow[];
  resolutionByChannel: ChannelResolution[];
  sankey: SankeyRow[];
  byIntent: IntentStat[];
  flows: Flow[];
}

const FLOW_ORDER = ["ussd", "app", "web", "social", "call", "resolved", "abandoned"];

export function computeSlice(journeys: Journey[]): SliceMetrics {
  const ttfrValues: Record<Channel, number[]> = {
    ussd: [],
    app: [],
    web: [],
    social: [],
    call: [],
  };
  const contacts: Record<Channel, number> = { ussd: 0, app: 0, web: 0, social: 0, call: 0 };
  const resolvedContacts: Record<Channel, number> = { ussd: 0, app: 0, web: 0, social: 0, call: 0 };
  const sankeyMap: Record<Channel, { first: number; later: number; abandoned: number }> = {
    ussd: { first: 0, later: 0, abandoned: 0 },
    app: { first: 0, later: 0, abandoned: 0 },
    web: { first: 0, later: 0, abandoned: 0 },
    social: { first: 0, later: 0, abandoned: 0 },
    call: { first: 0, later: 0, abandoned: 0 },
  };
  const intentMap = new Map<string, IntentStat>();
  const flowMap = new Map<string, number>();

  let events = 0;
  let resolved = 0;
  let firstContact = 0;
  let repeat = 0;
  let switched = 0;
  let digitalFirst = 0;
  let digitalToCall = 0;
  let choseAbandon = 0;
  let maxContacts = 0;

  for (const journey of journeys) {
    events += journey.contacts;
    if (journey.resolved) resolved += 1;
    if (journey.firstContact) firstContact += 1;
    if (journey.repeat) repeat += 1;
    if (journey.switched) switched += 1;
    if (journey.digitalFirst) digitalFirst += 1;
    if (journey.digitalToCall) digitalToCall += 1;
    if (journey.end === "chose_abandon") choseAbandon += 1;
    if (journey.end === "max_contacts") maxContacts += 1;
    ttfrValues[journey.first].push(journey.ttfr);
    if (journey.firstContact) sankeyMap[journey.first].first += 1;
    else if (journey.resolved) sankeyMap[journey.first].later += 1;
    else sankeyMap[journey.first].abandoned += 1;

    journey.path.forEach((channel, index) => {
      contacts[channel] += 1;
      if (index === journey.path.length - 1 && journey.resolved) {
        resolvedContacts[channel] += 1;
      }
      const target =
        index === journey.path.length - 1
          ? journey.resolved
            ? "resolved"
            : "abandoned"
          : journey.path[index + 1];
      const key = `${channel}|${target}`;
      flowMap.set(key, (flowMap.get(key) ?? 0) + 1);
    });

    const existing = intentMap.get(journey.intent);
    if (existing) {
      existing.journeys += 1;
      if (journey.resolved) existing.resolved += 1;
      if (journey.digitalFirst) existing.digitalFirst += 1;
      if (journey.digitalToCall) existing.digitalToCall += 1;
    } else {
      intentMap.set(journey.intent, {
        intent: journey.intent,
        category: journey.category,
        group: journey.group,
        journeys: 1,
        resolved: journey.resolved ? 1 : 0,
        digitalFirst: journey.digitalFirst ? 1 : 0,
        digitalToCall: journey.digitalToCall ? 1 : 0,
      });
    }
  }

  const flows = [...flowMap.entries()]
    .map(([key, n]) => {
      const [from, to] = key.split("|");
      return { from, to, n };
    })
    .sort(
      (left, right) =>
        right.n - left.n ||
        FLOW_ORDER.indexOf(left.from) - FLOW_ORDER.indexOf(right.from) ||
        FLOW_ORDER.indexOf(left.to) - FLOW_ORDER.indexOf(right.to),
    );

  return {
    journeys: journeys.length,
    events,
    resolved,
    abandoned: journeys.length - resolved,
    firstContact,
    repeat,
    switched,
    digitalFirst,
    digitalToCall,
    choseAbandon,
    maxContacts,
    ttfr: CHANNELS.flatMap((channel) => {
      const values = ttfrValues[channel];
      if (values.length === 0) return [];
      return [
        {
          channel,
          journeys: values.length,
          median: quantileCont(values, 0.5),
          p90: quantileCont(values, 0.9),
        },
      ];
    }),
    resolutionByChannel: CHANNELS.map((channel) => ({
      channel,
      contacts: contacts[channel],
      resolvedContacts: resolvedContacts[channel],
    })),
    sankey: CHANNELS.flatMap((channel) => {
      const row = sankeyMap[channel];
      const total = row.first + row.later + row.abandoned;
      if (total === 0) return [];
      return [{ channel, first: row.first, later: row.later, abandoned: row.abandoned, journeys: total }];
    }),
    byIntent: [...intentMap.values()].sort(
      (left, right) => right.journeys - left.journeys || left.intent.localeCompare(right.intent),
    ),
    flows,
  };
}

function sameMembers(left: string[], right: string[]): boolean {
  if (left.length !== right.length) return false;
  const bag = new Set(left);
  return right.every((item) => bag.has(item));
}

export function filtersEqual(left: Filters, right: Filters): boolean {
  return (
    left.outcome === right.outcome &&
    left.category === right.category &&
    left.intent === right.intent &&
    sameMembers(left.groups, right.groups) &&
    sameMembers(left.start, right.start) &&
    sameMembers(left.touch, right.touch)
  );
}

export function describeFilters(filters: Filters, count: number): string {
  const noun = count === 1 ? "journey" : "journeys";
  const who: string[] = [];
  if (filters.groups.length === 1) {
    who.push(GROUP_LABEL[filters.groups[0]].toLowerCase());
  } else if (filters.groups.length > 1) {
    who.push(filters.groups.map((group) => GROUP_LABEL[group].toLowerCase()).join(" or "));
  }
  if (filters.category) who.push(filters.category);
  if (filters.intent) who.push(filters.intent.replace(/_/g, " "));
  const subject = who.length > 0 ? `${who.join(", ")} ${noun}` : noun;
  let sentence = `${count.toLocaleString("en-US")} ${subject}`;
  if (filters.start.length > 0) {
    sentence += ` starting on ${filters.start.join(", ")}`;
  }
  if (filters.touch.length > 0) {
    sentence += ` whose path includes ${filters.touch.join(" or ")}`;
  }
  if (filters.outcome !== "all") {
    const outcomeLabel: Record<Exclude<OutcomeFilter, "all">, string> = {
      resolved: "that resolve",
      abandoned: "that are abandoned",
      first_contact: "resolved on the first contact",
      later_contact: "resolved after another contact",
      digital_to_call: "that start digital and later reach a call",
      repeat: "with a repeat contact",
      switched: "that switch channel",
    };
    sentence += ` ${outcomeLabel[filters.outcome]}`;
  }
  return sentence;
}

function readList(params: URLSearchParams, key: string): string[] {
  const value = params.get(key);
  if (!value) return [];
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

export function filtersFromSearch(params: URLSearchParams): Filters {
  const outcomeRaw = params.get("outcome") ?? "all";
  return {
    groups: readList(params, "group").filter(isGroup),
    start: readList(params, "start").filter(isChannel),
    touch: readList(params, "touch").filter(isChannel),
    category: params.get("category") ?? "",
    intent: params.get("intent") ?? "",
    outcome: isOutcome(outcomeRaw) ? outcomeRaw : "all",
  };
}

export function filtersToSearch(
  filters: Filters,
  extra: { q?: string; view?: string },
): string {
  const params = new URLSearchParams();
  if (filters.groups.length > 0) params.set("group", filters.groups.join(","));
  if (filters.start.length > 0) params.set("start", filters.start.join(","));
  if (filters.touch.length > 0) params.set("touch", filters.touch.join(","));
  if (filters.category) params.set("category", filters.category);
  if (filters.intent) params.set("intent", filters.intent);
  if (filters.outcome !== "all") params.set("outcome", filters.outcome);
  if (extra.q) params.set("q", extra.q);
  if (extra.view && extra.view !== "performance") params.set("view", extra.view);
  return params.toString();
}
