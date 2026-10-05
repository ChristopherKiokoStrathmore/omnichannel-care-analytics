import rawReport from "../data/kpis.json";

/**
 * Every displayed figure is an integer count from data/kpis.json
 * (a copy of reports/kpis.json) or the one-decimal string reports/headlines.md
 * already prints from those counts. Seed 20260929.
 */

type IntentGroup = "self_service_candidate" | "assisted" | "complaint";
type Channel = "ussd" | "app" | "web" | "social" | "call";

export interface CountRate {
  percent: string;
  fraction: string;
  text: string;
  numerator: number;
  denominator: number;
}

interface Report {
  public: {
    bitext: {
      n_examples: number;
      n_intents: number;
      n_categories: number;
      examples_per_intent_min: number;
      examples_per_intent_max: number;
      by_category: { category: string; n_examples: number; n_intents: number }[];
      by_tag: { tag: string; meaning: string; n_examples: number }[];
      instruction_length: {
        shortest_intent: string;
        shortest_median_chars: number;
        longest_intent: string;
        longest_median_chars: number;
      };
    };
    twitter_sample: {
      n_rows: number;
      n_inbound: number;
      n_outbound: number;
      inbound_to_company_reply_pairs: number;
      reply_delay_minutes_median: number;
      reply_delay_minutes_p90: number;
      telecom_or_cable_tweets: number;
    };
  };
  synthetic: {
    seed: number;
    definitions: {
      time_to_first_response: string;
      repeat_contact: string;
      channel_switch: string;
      digital_to_call: string;
      resolution_rate: string;
    };
    assumptions: {
      slow_response_minutes: number;
      slow_response_factor: number;
      resolution_probability: Record<IntentGroup, Record<Channel, number>>;
    };
    config: {
      ttfr_lognormal_minutes: Record<Channel, { mu: number; sigma: number }>;
    };
    funnel: {
      journeys: number;
      events: number;
      customers: number;
      resolved_on_first_contact: number;
      repeat_contact: number;
      channel_switch: number;
      digital_first: number;
      digital_to_call: number;
      resolved: number;
      abandoned: number;
      end_chose_abandon: number;
      end_max_contacts: number;
    };
    ttfr_by_first_channel: {
      channel: Channel;
      journeys: number;
      median_minutes: number;
      p90_minutes: number;
    }[];
    resolution_by_channel: {
      channel: Channel;
      contacts: number;
      resolved_contacts: number;
    }[];
    resolution_by_group_channel: {
      intent_group: IntentGroup;
      channel: Channel;
      contacts: number;
      resolved_contacts: number;
    }[];
    resolution_by_intent: {
      category: string;
      intent: string;
      intent_group: IntentGroup;
      journeys: number;
      resolved_journeys: number;
      digital_first: number;
      digital_to_call: number;
    }[];
    by_intent_group: {
      intent_group: IntentGroup;
      journeys: number;
      resolved_journeys: number;
      digital_first: number;
      digital_to_call: number;
      resolved_on_first_contact: number;
    }[];
    directly_follows: { from_activity: string; to_activity: string; n: number }[];
    sankey: { first_channel: Channel; outcome: string; n: number }[];
  };
}

const report = rawReport as Report;

export const CHANNELS = ["ussd", "app", "web", "social", "call"] as const;
export const GROUP_ORDER = ["self_service_candidate", "assisted", "complaint"] as const;
export const FOLLOW_COLUMNS = [
  "ussd",
  "app",
  "web",
  "social",
  "call",
  "resolved",
  "abandoned",
] as const;
export const OUTCOMES = [
  "Resolved on first contact",
  "Resolved after another contact",
  "Abandoned",
] as const;

const GROUP_LABEL: Record<IntentGroup, string> = {
  self_service_candidate: "self-service candidate",
  assisted: "assisted",
  complaint: "complaint",
};

const TAG_ORDER = ["Q", "Z", "W", "I", "K", "P", "E", "N"] as const;

function assertEqual(actual: string, expected: string, label: string): void {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

export function rate(numerator: number, denominator: number): CountRate {
  const percent = `${((numerator / denominator) * 100).toFixed(1)}%`;
  const fraction = `${numerator}/${denominator}`;
  return {
    percent,
    fraction,
    text: `${percent} (${fraction})`,
    numerator,
    denominator,
  };
}

function expectRate(numerator: number, denominator: number, expected: string, label: string): CountRate {
  const value = rate(numerator, denominator);
  assertEqual(value.text, expected, label);
  return value;
}

const funnel = report.synthetic.funnel;

export const seed = report.synthetic.seed;
export const journeys = funnel.journeys;
export const events = funnel.events;
export const customers = funnel.customers;

export const resolution = expectRate(funnel.resolved, funnel.journeys, "81.4% (3256/4000)", "resolution");
export const firstContact = expectRate(
  funnel.resolved_on_first_contact,
  funnel.journeys,
  "55.6% (2223/4000)",
  "first contact",
);
export const repeatContact = expectRate(
  funnel.repeat_contact,
  funnel.journeys,
  "36.5% (1462/4000)",
  "repeat contact",
);
export const channelSwitch = expectRate(
  funnel.channel_switch,
  funnel.journeys,
  "30.9% (1235/4000)",
  "channel switch",
);
export const digitalToCallAll = expectRate(
  funnel.digital_to_call,
  funnel.journeys,
  "24.3% (971/4000)",
  "digital-to-call all",
);
export const digitalFirstLaterCall = expectRate(
  funnel.digital_to_call,
  funnel.digital_first,
  "32.0% (971/3035)",
  "digital-first later call",
);
export const digitalFirst = expectRate(
  funnel.digital_first,
  funnel.journeys,
  "75.9% (3035/4000)",
  "digital-first",
);
export const abandoned = expectRate(funnel.abandoned, funnel.journeys, "18.6% (744/4000)", "abandoned");

export const abandonedEnds = {
  choseAbandon: funnel.end_chose_abandon,
  maxContacts: funnel.end_max_contacts,
};

export const funnelRates: {
  id: string;
  label: string;
  rate: CountRate;
  note?: string;
  emphasis?: boolean;
}[] = [
  {
    id: "resolution",
    label: "Journey resolution",
    rate: resolution,
    note: "Journeys whose end reason is resolved.",
    emphasis: true,
  },
  {
    id: "first",
    label: "Resolved on the first contact",
    rate: firstContact,
  },
  {
    id: "repeat",
    label: "Repeat contact",
    rate: repeatContact,
    note: "Two or more contacts in the same journey.",
  },
  {
    id: "switch",
    label: "Channel switch",
    rate: channelSwitch,
    note: "More than one distinct channel. A second contact on the same channel is not a switch.",
  },
  {
    id: "digital-first",
    label: "Digital-first",
    rate: digitalFirst,
    note: "First contact on ussd, app, web, or social.",
  },
  {
    id: "d2c-all",
    label: "Digital-to-call, all journeys",
    rate: digitalToCallAll,
    note: `Numerator is the ${digitalToCallAll.numerator} journeys that start digital and later reach a call.`,
  },
  {
    id: "d2c-digital",
    label: "Digital-to-call, digital-first journeys",
    rate: digitalFirstLaterCall,
    note: `Same ${digitalFirstLaterCall.numerator} journeys, divided by the ${digitalFirstLaterCall.denominator} digital-first journeys.`,
    emphasis: true,
  },
  {
    id: "abandoned",
    label: "Abandoned",
    rate: abandoned,
    note: `Of the abandoned journeys, chose-abandon ends: ${abandonedEnds.choseAbandon}, and max-contact ends: ${abandonedEnds.maxContacts}.`,
  },
];

const TTFR_TEXT: Record<Channel, { median: string; p90: string }> = {
  ussd: { median: "1.0", p90: "1.7" },
  app: { median: "2.0", p90: "4.0" },
  web: { median: "4.8", p90: "10.5" },
  social: { median: "30.0", p90: "69.9" },
  call: { median: "5.9", p90: "11.2" },
};

export const ttfr = CHANNELS.map((channel) => {
  const row = report.synthetic.ttfr_by_first_channel.find((item) => item.channel === channel);
  if (!row) {
    throw new Error(`missing ttfr ${channel}`);
  }
  const median = row.median_minutes.toFixed(1);
  const p90 = row.p90_minutes.toFixed(1);
  assertEqual(median, TTFR_TEXT[channel].median, `${channel} median`);
  assertEqual(p90, TTFR_TEXT[channel].p90, `${channel} p90`);
  return {
    channel,
    journeys: row.journeys,
    median,
    p90,
    medianMinutes: row.median_minutes,
    p90Minutes: row.p90_minutes,
  };
});

const CHANNEL_RESOLUTION_TEXT: Record<Channel, string> = {
  ussd: "43.4% (699/1611)",
  app: "50.8% (582/1145)",
  web: "43.9% (317/722)",
  social: "19.4% (102/526)",
  call: "65.6% (1556/2372)",
};

export const resolutionByChannel = CHANNELS.map((channel) => {
  const row = report.synthetic.resolution_by_channel.find((item) => item.channel === channel);
  if (!row) {
    throw new Error(`missing channel resolution ${channel}`);
  }
  return {
    channel,
    contacts: row.contacts,
    resolvedContacts: row.resolved_contacts,
    rate: expectRate(
      row.resolved_contacts,
      row.contacts,
      CHANNEL_RESOLUTION_TEXT[channel],
      `${channel} resolution`,
    ),
  };
});

const GROUP_TEXT: Record<IntentGroup, { resolution: string; digitalToCall: string }> = {
  self_service_candidate: {
    resolution: "94.7% (1401/1480)",
    digitalToCall: "12.9% (144/1112)",
  },
  assisted: {
    resolution: "83.0% (1276/1538)",
    digitalToCall: "36.6% (434/1185)",
  },
  complaint: {
    resolution: "59.0% (579/982)",
    digitalToCall: "53.3% (393/738)",
  },
};

export const intentGroups = GROUP_ORDER.map((group) => {
  const row = report.synthetic.by_intent_group.find((item) => item.intent_group === group);
  if (!row) {
    throw new Error(`missing group ${group}`);
  }
  return {
    group,
    label: GROUP_LABEL[group],
    journeys: row.journeys,
    resolvedJourneys: row.resolved_journeys,
    digitalFirst: row.digital_first,
    digitalToCall: row.digital_to_call,
    resolvedOnFirstContact: row.resolved_on_first_contact,
    resolution: expectRate(
      row.resolved_journeys,
      row.journeys,
      GROUP_TEXT[group].resolution,
      `${group} resolution`,
    ),
    digitalToCallRate: expectRate(
      row.digital_to_call,
      row.digital_first,
      GROUP_TEXT[group].digitalToCall,
      `${group} digital-to-call`,
    ),
  };
});

const GROUP_CHANNEL_TEXT: Record<IntentGroup, Record<Channel, { base: string; realised: string }>> = {
  self_service_candidate: {
    ussd: { base: "0.82", realised: "77.8% (420/540)" },
    app: { base: "0.86", realised: "85.5% (300/351)" },
    web: { base: "0.74", realised: "75.5% (160/212)" },
    social: { base: "0.30", realised: "34.5% (48/139)" },
    call: { base: "0.90", realised: "85.4% (473/554)" },
  },
  assisted: {
    ussd: { base: "0.38", realised: "37.2% (226/607)" },
    app: { base: "0.52", realised: "48.9% (227/464)" },
    web: { base: "0.45", realised: "44.0% (128/291)" },
    social: { base: "0.20", realised: "16.7% (34/203)" },
    call: { base: "0.78", realised: "68.9% (661/959)" },
  },
  complaint: {
    ussd: { base: "0.12", realised: "11.4% (53/464)" },
    app: { base: "0.22", realised: "16.7% (55/330)" },
    web: { base: "0.18", realised: "13.2% (29/219)" },
    social: { base: "0.15", realised: "10.9% (20/184)" },
    call: { base: "0.60", realised: "49.1% (422/859)" },
  },
};

export const groupChannel = GROUP_ORDER.flatMap((group) =>
  CHANNELS.map((channel) => {
    const row = report.synthetic.resolution_by_group_channel.find(
      (item) => item.intent_group === group && item.channel === channel,
    );
    if (!row) {
      throw new Error(`missing ${group} ${channel}`);
    }
    const expected = GROUP_CHANNEL_TEXT[group][channel];
    const base = report.synthetic.assumptions.resolution_probability[group][channel].toFixed(2);
    assertEqual(base, expected.base, `${group} ${channel} base`);
    return {
      group,
      label: GROUP_LABEL[group],
      channel,
      base,
      contacts: row.contacts,
      resolvedContacts: row.resolved_contacts,
      realised: expectRate(row.resolved_contacts, row.contacts, expected.realised, `${group} ${channel}`),
    };
  }),
);

export const sankey = CHANNELS.map((channel) => {
  const pick = (outcome: (typeof OUTCOMES)[number]) => {
    const found = report.synthetic.sankey.find(
      (row) => row.first_channel === channel && row.outcome === outcome,
    );
    if (!found) {
      throw new Error(`missing sankey ${channel} ${outcome}`);
    }
    return found.n;
  };
  const first = pick("Resolved on first contact");
  const later = pick("Resolved after another contact");
  const abandonedCount = pick("Abandoned");
  const total = first + later + abandonedCount;
  const sample = ttfr.find((row) => row.channel === channel);
  if (!sample || sample.journeys !== total) {
    throw new Error(`sankey sum ${channel} is ${total}`);
  }
  return { channel, first, later, abandoned: abandonedCount, journeys: total };
});

export const followMatrix = CHANNELS.map((from) => ({
  from,
  cells: FOLLOW_COLUMNS.map((to) => {
    const found = report.synthetic.directly_follows.find(
      (row) => row.from_activity === from && row.to_activity === to,
    );
    if (!found) {
      throw new Error(`missing flow ${from} -> ${to}`);
    }
    return { to, n: found.n };
  }),
}));

export const largestFollows = [...report.synthetic.directly_follows]
  .sort((left, right) => right.n - left.n || left.from_activity.localeCompare(right.from_activity))
  .slice(0, 5)
  .map((row) => ({ from: row.from_activity, to: row.to_activity, n: row.n }));

const LARGEST_EXPECTED = [
  ["call", "resolved", "1556"],
  ["ussd", "resolved", "699"],
  ["app", "resolved", "582"],
  ["ussd", "call", "385"],
  ["call", "call", "382"],
];
largestFollows.forEach((row, index) => {
  const expected = LARGEST_EXPECTED[index];
  assertEqual(`${row.from}|${row.to}|${row.n}`, expected.join("|"), `largest flow ${index}`);
});

const LOOKUP_EXPECTED = [
  ["check_usage", "9.0% (42/467)"],
  ["invoices", "9.8% (31/317)"],
  ["check_excess_data_charges", "12.9% (24/186)"],
  ["check_mobile_payments", "9.1% (19/209)"],
  ["check_signal_coverage", "12.1% (17/141)"],
  ["payment_methods", "8.8% (8/91)"],
  ["check_cancellation_fee", "4.3% (3/69)"],
] as const;

export const lookupSpill = LOOKUP_EXPECTED.map(([intent, expected]) => {
  const row = report.synthetic.resolution_by_intent.find((item) => item.intent === intent);
  if (!row) {
    throw new Error(`missing intent ${intent}`);
  }
  return {
    intent,
    journeys: row.journeys,
    digitalFirst: row.digital_first,
    digitalToCall: row.digital_to_call,
    rate: expectRate(row.digital_to_call, row.journeys, expected, intent),
  };
});

export const intents = report.synthetic.resolution_by_intent.map((row) => ({
  category: row.category,
  intent: row.intent,
  group: GROUP_LABEL[row.intent_group],
  journeys: row.journeys,
  resolvedJourneys: row.resolved_journeys,
  digitalFirst: row.digital_first,
  digitalToCall: row.digital_to_call,
}));

export const definitions = [
  { title: "Time to first response", text: report.synthetic.definitions.time_to_first_response },
  { title: "Repeat contact", text: report.synthetic.definitions.repeat_contact },
  { title: "Channel switch", text: report.synthetic.definitions.channel_switch },
  { title: "Digital-to-call", text: report.synthetic.definitions.digital_to_call },
  { title: "Resolution rate", text: report.synthetic.definitions.resolution_rate },
];

export const socialClock = {
  mu: report.synthetic.config.ttfr_lognormal_minutes.social.mu.toFixed(2),
  slowMinutes: report.synthetic.assumptions.slow_response_minutes.toFixed(1),
  slowFactor: report.synthetic.assumptions.slow_response_factor.toFixed(2),
};

const bitext = report.public.bitext;
const twitter = report.public.twitter_sample;

const TAG_TEXT: Record<(typeof TAG_ORDER)[number], string> = {
  Q: "49.5% (12862/26000)",
  Z: "49.8% (12942/26000)",
  W: "35.7% (9271/26000)",
  I: "72.7% (18899/26000)",
  K: "0.0% (0/26000)",
  P: "47.3% (12310/26000)",
  E: "4.7% (1228/26000)",
  N: "0.0% (0/26000)",
};

export const publicProfile = {
  examples: bitext.n_examples,
  intents: bitext.n_intents,
  categories: bitext.n_categories,
  perIntent: bitext.examples_per_intent_min,
  categoriesRows: bitext.by_category,
  tags: TAG_ORDER.map((tag) => {
    const row = bitext.by_tag.find((item) => item.tag === tag);
    if (!row) {
      throw new Error(`missing tag ${tag}`);
    }
    return {
      tag,
      meaning: row.meaning,
      rate: expectRate(row.n_examples, bitext.n_examples, TAG_TEXT[tag], `tag ${tag}`),
    };
  }),
  shortestIntent: bitext.instruction_length.shortest_intent,
  shortestMedian: bitext.instruction_length.shortest_median_chars.toFixed(1),
  longestIntent: bitext.instruction_length.longest_intent,
  longestMedian: bitext.instruction_length.longest_median_chars.toFixed(1),
  twitterRows: twitter.n_rows,
  twitterInbound: twitter.n_inbound,
  twitterOutbound: twitter.n_outbound,
  twitterPairs: twitter.inbound_to_company_reply_pairs,
  twitterMedian: twitter.reply_delay_minutes_median.toFixed(1),
  twitterP90: twitter.reply_delay_minutes_p90.toFixed(1),
  telecomTweets: twitter.telecom_or_cable_tweets,
};

assertEqual(String(seed), "20260929", "seed");
assertEqual(String(journeys), "4000", "journeys");
assertEqual(String(events), "6376", "events");
assertEqual(String(customers), "4000", "customers");
assertEqual(String(abandonedEnds.choseAbandon), "542", "chose abandon");
assertEqual(String(abandonedEnds.maxContacts), "202", "max contacts");
assertEqual(String(abandonedEnds.choseAbandon + abandonedEnds.maxContacts), "744", "abandon split");
assertEqual(String(publicProfile.examples), "26000", "bitext examples");
assertEqual(String(publicProfile.intents), "26", "bitext intents");
assertEqual(String(publicProfile.categories), "7", "bitext categories");
assertEqual(String(publicProfile.perIntent), "1000", "examples per intent");
assertEqual(String(bitext.examples_per_intent_max), "1000", "examples per intent max");
assertEqual(publicProfile.shortestIntent, "pay", "shortest intent");
assertEqual(publicProfile.shortestMedian, "42.0", "shortest median");
assertEqual(publicProfile.longestIntent, "check_excess_data_charges", "longest intent");
assertEqual(publicProfile.longestMedian, "62.0", "longest median");
assertEqual(String(publicProfile.twitterRows), "93", "twitter rows");
assertEqual(String(publicProfile.twitterInbound), "49", "twitter inbound");
assertEqual(String(publicProfile.twitterOutbound), "44", "twitter outbound");
assertEqual(String(publicProfile.twitterPairs), "42", "twitter pairs");
assertEqual(publicProfile.twitterMedian, "50.8", "twitter median");
assertEqual(publicProfile.twitterP90, "385.7", "twitter p90");
assertEqual(String(publicProfile.telecomTweets), "4", "telecom tweets");
assertEqual(socialClock.mu, "3.40", "social mu");
assertEqual(socialClock.slowMinutes, "30.0", "slow minutes");
assertEqual(socialClock.slowFactor, "0.75", "slow factor");
assertEqual(String(intents.length), "26", "intent rows");
