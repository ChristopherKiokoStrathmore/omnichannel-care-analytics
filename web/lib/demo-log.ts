import rawJson from "../data/demo-log.json";
import { computeSlice, hydrate, type RawDemoFile } from "./demo-metrics";

export const demoLog = hydrate(rawJson as RawDemoFile);
export const fullSlice = computeSlice(demoLog.journeys);

function assertEqual(actual: string | number, expected: string | number, label: string): void {
  if (actual !== expected) {
    throw new Error(`${label}: expected ${expected}, got ${actual}`);
  }
}

assertEqual(demoLog.seed, 20260929, "seed");
assertEqual(demoLog.label, "SYNTHETIC", "label");
assertEqual(demoLog.nJourneys, 4000, "header journeys");
assertEqual(demoLog.nEvents, 6376, "header events");
assertEqual(demoLog.taxonomy.nExamples, 26000, "bitext examples");
assertEqual(demoLog.taxonomy.nIntents, 26, "bitext intents");
assertEqual(demoLog.taxonomy.nCategories, 7, "bitext categories");
assertEqual(demoLog.taxonomy.examplesPerIntent, 1000, "examples per intent");
assertEqual(fullSlice.journeys, 4000, "journeys");
assertEqual(fullSlice.events, 6376, "events");
assertEqual(fullSlice.resolved, 3256, "resolved");
assertEqual(fullSlice.firstContact, 2223, "first contact");
assertEqual(fullSlice.repeat, 1462, "repeat");
assertEqual(fullSlice.switched, 1235, "switch");
assertEqual(fullSlice.digitalFirst, 3035, "digital first");
assertEqual(fullSlice.digitalToCall, 971, "digital to call");
assertEqual(fullSlice.abandoned, 744, "abandoned");
assertEqual(fullSlice.choseAbandon, 542, "chose abandon");
assertEqual(fullSlice.maxContacts, 202, "max contacts");

const EXPECTED_RESOLUTION: Record<string, [number, number]> = {
  ussd: [1611, 699],
  app: [1145, 582],
  web: [722, 317],
  social: [526, 102],
  call: [2372, 1556],
};

for (const row of fullSlice.resolutionByChannel) {
  const expected = EXPECTED_RESOLUTION[row.channel];
  assertEqual(row.contacts, expected[0], `${row.channel} contacts`);
  assertEqual(row.resolvedContacts, expected[1], `${row.channel} resolved contacts`);
}

const EXPECTED_TTFR: Record<string, [string, string, number]> = {
  ussd: ["1.0", "1.7", 1289],
  app: ["2.0", "4.0", 873],
  web: ["4.8", "10.5", 548],
  social: ["30.0", "69.9", 325],
  call: ["5.9", "11.2", 965],
};

for (const row of fullSlice.ttfr) {
  const expected = EXPECTED_TTFR[row.channel];
  assertEqual(row.journeys, expected[2], `${row.channel} ttfr n`);
  assertEqual(row.median.toFixed(1), expected[0], `${row.channel} median`);
  assertEqual(row.p90.toFixed(1), expected[1], `${row.channel} p90`);
}

const ussdToCall = fullSlice.flows.find((flow) => flow.from === "ussd" && flow.to === "call");
if (!ussdToCall) {
  throw new Error("missing ussd to call flow");
}
assertEqual(ussdToCall.n, 385, "ussd to call");

const complaint = computeSlice(demoLog.journeys.filter((journey) => journey.group === "complaint"));
assertEqual(complaint.journeys, 982, "complaint journeys");
assertEqual(complaint.resolved, 579, "complaint resolved");
assertEqual(complaint.digitalFirst, 738, "complaint digital");
assertEqual(complaint.digitalToCall, 393, "complaint digital to call");

const lookup = computeSlice(
  demoLog.journeys.filter((journey) => journey.group === "self_service_candidate"),
);
assertEqual(lookup.journeys, 1480, "lookup journeys");
assertEqual(lookup.resolved, 1401, "lookup resolved");
assertEqual(lookup.digitalFirst, 1112, "lookup digital");
assertEqual(lookup.digitalToCall, 144, "lookup digital to call");

const dispute = computeSlice(demoLog.journeys.filter((journey) => journey.intent === "dispute_invoice"));
assertEqual(dispute.journeys, 212, "dispute journeys");
assertEqual(dispute.resolved, 125, "dispute resolved");
assertEqual(dispute.digitalFirst, 158, "dispute digital");
assertEqual(dispute.digitalToCall, 78, "dispute digital to call");
