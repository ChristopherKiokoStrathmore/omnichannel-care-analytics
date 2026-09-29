# Design recommendations

This note is a human-centred design hypothesis for a telco care journey. No synthetic rate in this repository is a real-world measurement. Each recommendation says whether it rests on the public Bitext training set or on the SYNTHETIC event log.

## 1. Put lookup intents on a USSD menu and in the app

Basis: the public Bitext intent names, plus synthetic journey outputs.

Bitext publishes 26000 training examples, 26 intents, and 1000 examples of each intent. That balance is a property of the training set, so it does not say which intents are common in a contact centre. The self-service shortlist is a design rule in `config/synthetic.yaml` applied to those public names, not a Bitext column. The names on the shortlist are: check_cancellation_fee, check_excess_data_charges, check_mobile_payments, check_signal_coverage, check_usage, invoices, payment_methods.

On the synthetic log, self-service-candidate contacts resolve at base 0.82, realised 77.8% (420/540) on USSD and base 0.86, realised 85.5% (300/351) on the app. USSD first-contact time-to-first-response has median 1.0 minutes (n=1289). Those realised rates sit close to the base inputs. They are not independent evidence for the inputs.

What is not a single input is the spill to the call channel. Synthetic digital-to-call journeys in this group: 12.9% (144/1112) of its digital-first journeys. By intent:

- check_usage: 9.0% (42/467) digital-to-call
- invoices: 9.8% (31/317) digital-to-call
- check_excess_data_charges: 12.9% (24/186) digital-to-call
- check_mobile_payments: 9.1% (19/209) digital-to-call
- check_signal_coverage: 12.1% (17/141) digital-to-call
- payment_methods: 8.8% (8/91) digital-to-call
- check_cancellation_fee: 4.3% (3/69) digital-to-call

A design test should start with the intents at the top of that list, because under these assumptions they create the most call arrivals after a digital lookup attempt.

## 2. Keep a person available for complaint intents

Basis: synthetic outputs. The grouping of these intents is a config rule over the public names.

Complaint intents in the config: dispute_invoice, get_compensation, human_agent, report_poor_signal_coverage, report_problem.

Synthetic complaint contacts resolve at base 0.12, realised 11.4% (53/464) on USSD and base 0.60, realised 49.1% (422/859) on the call channel. Journey resolution for the group is 59.0% (579/982). Digital-to-call among its digital-first journeys is 53.3% (393/738). The low USSD base probability is an assumption. The digital-to-call share is an output of that assumption, the next-channel matrix, and the four-contact cap. Do not offer USSD as the only path for these intents. Use USSD to capture the symptom, then offer the call channel.

## 3. Treat social as acknowledgement, not resolution

Basis: synthetic clocks and synthetic resolution rates.

The social time-to-first-response distribution is an input (lognormal mu 3.40). On the simulated first contacts its median is 30.0 minutes and its 90th percentile is 69.9 minutes (n=325). That median reproduces the configured distribution. It is not an independent discovery that social is slow. The model multiplies resolution probability by 0.75 when a response is slower than 30.0 minutes. The lowest realised contact resolution is social, at 19.4% (102/526). Lookup intents on social are base 0.30, realised 34.5% (48/139). Complaint intents on social are base 0.15, realised 10.9% (20/184). Under these assumptions, keep social as acknowledgement and hand the customer to USSD, the app, or the call channel for the fix.

## 4. Make chat tolerate typos, and keep USSD as a menu

Basis: public Bitext language tags. Bitext calls this file a hybrid synthetic training set, so the tags describe generated training utterances.

Colloquial tag (Q): 49.5% (12862/26000). Typo tag (Z): 49.8% (12942/26000). Offensive-language tag (W): 35.7% (9271/26000). Keyword tag (K): 0.0% (0/26000). Negation tag (N): 0.0% (0/26000). The keyword and negation codes are documented by Bitext and are absent from this file's tag column. The utterances are full phrases, including colloquial wording and typos, not keyword strings. A USSD menu should be a structured choice, not a free-text copy of these utterances. A chat or app path trained only on clean phrases would miss the colloquial and typo variants this public set contains. This is a statement about the training set, not about customers in any country.

## What would change these recommendations

Replace the weights, base probabilities, and clocks in `config/synthetic.yaml` with operator measurements and rerun `python scripts/run_analysis.py`. The Twitter preview (93 data rows, 42 in-file reply pairs, median delay 50.8 minutes) is too small, too mixed across brands, and too incomplete as a thread sample to choose a channel. The full Customer Support on Twitter corpus was not downloaded, because that file was not available without a Kaggle login.
