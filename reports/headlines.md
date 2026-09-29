### Public inputs

Bitext training examples: 26000. Intents: 26. Categories: 7. Examples per intent: minimum 1000, maximum 1000. The equal counts are how this training set was built. They are not customer demand.

Bitext examples by category: BILLING 2000 examples across 2 intents; COMPLAINTS 3000 examples across 3 intents; CONSUMPTION 3000 examples across 3 intents; CONTACT 2000 examples across 2 intents; PAYMENT 4000 examples across 4 intents; SERVICES 7000 examples across 7 intents; SUBSCRIPTION 5000 examples across 5 intents.

Bitext language-tag shares:

- colloquial (Q): 49.5% (12862/26000)
- errors and typos (Z): 49.8% (12942/26000)
- offensive language (W): 35.7% (9271/26000)
- interrogative structure (I): 72.7% (18899/26000)
- keyword mode (K): 0.0% (0/26000)
- politeness (P): 47.3% (12310/26000)
- abbreviations (E): 4.7% (1228/26000)
- negation (N): 0.0% (0/26000)

Shortest median instruction length in the Bitext training text: 42.0 characters (pay). Longest median instruction length: 62.0 characters (check_excess_data_charges). These are lengths of published training utterances, not of field contacts.

Twitter preview data rows: 93. Physical newlines in the file: 100. Inbound tweets: 49. Outbound tweets: 44. In-file reply links: 66. Inbound-to-company reply pairs with both tweets inside the preview: 42. Median reply delay on those pairs: 50.8 minutes. 90th percentile reply delay on those pairs: 385.7 minutes. Negative delays in those pairs: 0.

Company-account tweets in the Twitter preview, by author_id:

- AppleSupport: 13
- SpotifyCares: 8
- Tesco: 8
- VirginTrains: 4
- British_Airways: 3
- Ask_Spectrum: 1
- ChaseSupport: 1
- HPSupport: 1
- O2: 1
- SouthwestAir: 1
- UPSHelp: 1
- comcastcares: 1
- sprintcare: 1

Preview tweets from the telecom and cable-ISP author allowlist: Ask_Spectrum (cable_isp) 1; O2 (mobile) 1; comcastcares (cable_isp) 1; sprintcare (mobile) 1. Combined tweets: 4.

The full Kaggle dataset thoughtvector/customer-support-on-twitter was not downloaded. The preview is not a random sample and it is not a telco journey study. Do not generalise the reply delays above.

### KPI definitions

The definitions below are for the synthetic log only. Public files in this repo have no journey outcomes to score.

Time-to-first-response is the delay, in minutes, between a journey's first inbound timestamp and the response timestamp on that same first contact. Median and the 90th percentile use DuckDB quantile_cont (linear). The synthetic generator draws each delay from the channel lognormal in config/synthetic.yaml and then clips it. Every synthetic contact has a response, so there are no censored non-responses.

Repeat-contact rate is the share of synthetic journeys with two or more contacts. A repeat contact is a later contact in the same journey after an unresolved contact. The synthetic log has one journey per customer, so this is not a later, separate issue from the same person.

Channel-switch rate is the share of synthetic journeys whose contacts use more than one distinct channel. A second contact on the same channel is a repeat contact and is not a channel switch.

A synthetic digital-to-call journey starts on a digital channel (ussd, app, web, or social) and has a later contact on the call channel. That is the operational definition of a failed digital attempt that ends in a call. The rate is reported for all journeys and again among digital-first journeys only.

On the synthetic log, contact resolution rate for a channel, or for an intent group on a channel, is resolved contacts divided by contacts on that slice. A journey has at most one resolved contact, the one that closes it. Journey resolution rate is journeys whose end reason is resolved, divided by journeys. Realised rates are outputs. They are not the base probabilities in the config: each contact multiplies that base by attempt decay and, when the response is slower than the configured threshold, by the slow-response factor.

### Synthetic journeys

These figures are synthetic. No synthetic rate in this repository is a real-world measurement. Seed: 20260929. Journeys: 4000. Events: 6376. Customers: 4000 (one journey each).

Synthetic journey resolution rate: 81.4% (3256/4000). Resolved on the first contact: 55.6% (2223/4000). Repeat-contact rate: 36.5% (1462/4000). Channel-switch rate: 30.9% (1235/4000). Digital-to-call rate among all journeys: 24.3% (971/4000). Digital-to-call rate among digital-first journeys: 32.0% (971/3035). Digital-first journeys: 75.9% (3035/4000). Abandoned journeys: 18.6% (744/4000). Of the abandoned journeys, chose-abandon ends: 542, and max-contact ends: 202.

Synthetic time-to-first-response by first channel:

- ussd: median 1.0 minutes, 90th percentile 1.7 minutes (n=1289)
- app: median 2.0 minutes, 90th percentile 4.0 minutes (n=873)
- web: median 4.8 minutes, 90th percentile 10.5 minutes (n=548)
- social: median 30.0 minutes, 90th percentile 69.9 minutes (n=325)
- call: median 5.9 minutes, 90th percentile 11.2 minutes (n=965)

Synthetic contact resolution rate by channel:

- ussd: 43.4% (699/1611)
- app: 50.8% (582/1145)
- web: 43.9% (317/722)
- social: 19.4% (102/526)
- call: 65.6% (1556/2372)

Synthetic results by intent group:

- self-service candidate: journey resolution 94.7% (1401/1480); digital-to-call among its digital-first journeys 12.9% (144/1112)
- assisted: journey resolution 83.0% (1276/1538); digital-to-call among its digital-first journeys 36.6% (434/1185)
- complaint: journey resolution 59.0% (579/982); digital-to-call among its digital-first journeys 53.3% (393/738)

Synthetic contact resolution by intent group and channel. The base probability is the config input. The realised rate is the output:

- self-service candidate on ussd: base 0.82, realised 77.8% (420/540)
- self-service candidate on app: base 0.86, realised 85.5% (300/351)
- self-service candidate on web: base 0.74, realised 75.5% (160/212)
- self-service candidate on social: base 0.30, realised 34.5% (48/139)
- self-service candidate on call: base 0.90, realised 85.4% (473/554)
- assisted on ussd: base 0.38, realised 37.2% (226/607)
- assisted on app: base 0.52, realised 48.9% (227/464)
- assisted on web: base 0.45, realised 44.0% (128/291)
- assisted on social: base 0.20, realised 16.7% (34/203)
- assisted on call: base 0.78, realised 68.9% (661/959)
- complaint on ussd: base 0.12, realised 11.4% (53/464)
- complaint on app: base 0.22, realised 16.7% (55/330)
- complaint on web: base 0.18, realised 13.2% (29/219)
- complaint on social: base 0.15, realised 10.9% (20/184)
- complaint on call: base 0.60, realised 49.1% (422/859)

Largest synthetic directly-follows flows:

- call → resolved: 1556
- ussd → resolved: 699
- app → resolved: 582
- ussd → call: 385
- call → call: 382
