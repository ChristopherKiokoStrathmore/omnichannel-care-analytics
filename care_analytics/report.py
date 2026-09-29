"""Turn the KPI dictionary into the sentences the README and the design note use.

Every displayed rate is formatted from integer counts in that dictionary.
"""

from __future__ import annotations

CHANNEL_ORDER = ["ussd", "app", "web", "social", "call"]
GROUP_ORDER = ["self_service_candidate", "assisted", "complaint"]
GROUP_LABEL = {
    "self_service_candidate": "self-service candidate",
    "assisted": "assisted",
    "complaint": "complaint",
}


def share(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "undefined (0/0)"
    return f"{(int(numerator) / int(denominator)) * 100:.1f}% ({int(numerator)}/{int(denominator)})"


def one_decimal(value: float) -> str:
    return f"{float(value):.1f}"


def _match(rows: list[dict], **expected) -> dict:
    found = [row for row in rows if all(row[key] == value for key, value in expected.items())]
    if len(found) != 1:
        raise KeyError(expected)
    return found[0]


def _ordered(rows: list[dict], key: str, order: list[str]) -> list[dict]:
    position = {name: index for index, name in enumerate(order)}
    return sorted(rows, key=lambda row: position.get(row[key], len(order)))


def render_headlines(report: dict) -> str:
    public = report["public"]
    bitext = public["bitext"]
    twitter = public["twitter_sample"]
    synthetic = report["synthetic"]
    funnel = synthetic["funnel"]
    lines: list[str] = []

    lines.append("### Public inputs")
    lines.append("")
    lines.append(
        "Bitext training examples: "
        f"{bitext['n_examples']}. Intents: {bitext['n_intents']}. "
        f"Categories: {bitext['n_categories']}. "
        "Examples per intent: minimum "
        f"{bitext['examples_per_intent_min']}, maximum {bitext['examples_per_intent_max']}. "
        "The equal counts are how this training set was built. They are not customer demand."
    )
    lines.append("")
    category_bits = [
        f"{row['category']} {row['n_examples']} examples across {row['n_intents']} intents"
        for row in bitext["by_category"]
    ]
    lines.append("Bitext examples by category: " + "; ".join(category_bits) + ".")
    lines.append("")
    lines.append("Bitext language-tag shares:")
    lines.append("")
    for letter in ["Q", "Z", "W", "I", "K", "P", "E", "N"]:
        row = _match(bitext["by_tag"], tag=letter)
        lines.append(
            f"- {row['meaning']} ({letter}): {share(row['n_examples'], bitext['n_examples'])}"
        )
    lines.append("")
    length = bitext["instruction_length"]
    lines.append(
        "Shortest median instruction length in the Bitext training text: "
        f"{one_decimal(length['shortest_median_chars'])} characters "
        f"({length['shortest_intent']}). "
        "Longest median instruction length: "
        f"{one_decimal(length['longest_median_chars'])} characters "
        f"({length['longest_intent']}). "
        "These are lengths of published training utterances, not of field contacts."
    )
    lines.append("")
    lines.append(
        "Twitter preview data rows: "
        f"{twitter['n_rows']}. Physical newlines in the file: {twitter['physical_newlines']}. "
        f"Inbound tweets: {twitter['n_inbound']}. Outbound tweets: {twitter['n_outbound']}. "
        f"In-file reply links: {twitter['in_sample_reply_links']}. "
        "Inbound-to-company reply pairs with both tweets inside the preview: "
        f"{twitter['inbound_to_company_reply_pairs']}. "
        "Median reply delay on those pairs: "
        f"{one_decimal(twitter['reply_delay_minutes_median'])} minutes. "
        "90th percentile reply delay on those pairs: "
        f"{one_decimal(twitter['reply_delay_minutes_p90'])} minutes. "
        f"Negative delays in those pairs: {twitter['negative_reply_delays']}."
    )
    lines.append("")
    companies = sorted(
        twitter["company_account_counts"],
        key=lambda row: (-row["tweets"], row["author_id"]),
    )
    lines.append("Company-account tweets in the Twitter preview, by author_id:")
    lines.append("")
    for row in companies:
        lines.append(f"- {row['author_id']}: {row['tweets']}")
    lines.append("")
    telecom = twitter["telecom_or_cable_accounts"]
    if telecom:
        telecom_bits = [
            f"{row['author_id']} ({row['kind']}) {row['tweets']}" for row in telecom
        ]
        telecom_sentence = (
            "Preview tweets from the telecom and cable-ISP author allowlist: "
            + "; ".join(telecom_bits)
            + f". Combined tweets: {twitter['telecom_or_cable_tweets']}."
        )
    else:
        telecom_sentence = (
            "Preview tweets from the telecom and cable-ISP author allowlist: none. "
            f"Combined tweets: {twitter['telecom_or_cable_tweets']}."
        )
    lines.append(telecom_sentence)
    lines.append("")
    lines.append(
        "The full Kaggle dataset thoughtvector/customer-support-on-twitter was not "
        "downloaded. The preview is not a random sample and it is not a telco journey "
        "study. Do not generalise the reply delays above."
    )
    lines.append("")
    lines.append("### KPI definitions")
    lines.append("")
    lines.append(
        "The definitions below are for the synthetic log only. "
        "Public files in this repo have no journey outcomes to score."
    )
    lines.append("")
    for key in (
        "time_to_first_response",
        "repeat_contact",
        "channel_switch",
        "digital_to_call",
        "resolution_rate",
    ):
        lines.append(synthetic["definitions"][key])
        lines.append("")
    lines.append("### Synthetic journeys")
    lines.append("")
    lines.append(
        "These figures are synthetic. No synthetic rate in this repository is a "
        "real-world measurement. "
        f"Seed: {synthetic['seed']}. Journeys: {funnel['journeys']}. "
        f"Events: {funnel['events']}. Customers: {funnel['customers']} "
        "(one journey each)."
    )
    lines.append("")
    lines.append(
        "Synthetic journey resolution rate: "
        f"{share(funnel['resolved'], funnel['journeys'])}. "
        "Resolved on the first contact: "
        f"{share(funnel['resolved_on_first_contact'], funnel['journeys'])}. "
        "Repeat-contact rate: "
        f"{share(funnel['repeat_contact'], funnel['journeys'])}. "
        "Channel-switch rate: "
        f"{share(funnel['channel_switch'], funnel['journeys'])}. "
        "Digital-to-call rate among all journeys: "
        f"{share(funnel['digital_to_call'], funnel['journeys'])}. "
        "Digital-to-call rate among digital-first journeys: "
        f"{share(funnel['digital_to_call'], funnel['digital_first'])}. "
        "Digital-first journeys: "
        f"{share(funnel['digital_first'], funnel['journeys'])}. "
        "Abandoned journeys: "
        f"{share(funnel['abandoned'], funnel['journeys'])}. "
        "Of the abandoned journeys, chose-abandon ends: "
        f"{funnel['end_chose_abandon']}, and max-contact ends: {funnel['end_max_contacts']}."
    )
    lines.append("")
    lines.append("Synthetic time-to-first-response by first channel:")
    lines.append("")
    for row in _ordered(synthetic["ttfr_by_first_channel"], "channel", CHANNEL_ORDER):
        lines.append(
            f"- {row['channel']}: median {one_decimal(row['median_minutes'])} minutes, "
            f"90th percentile {one_decimal(row['p90_minutes'])} minutes "
            f"(n={row['journeys']})"
        )
    lines.append("")
    lines.append("Synthetic contact resolution rate by channel:")
    lines.append("")
    for row in _ordered(synthetic["resolution_by_channel"], "channel", CHANNEL_ORDER):
        lines.append(f"- {row['channel']}: {share(row['resolved_contacts'], row['contacts'])}")
    lines.append("")
    lines.append("Synthetic results by intent group:")
    lines.append("")
    for row in _ordered(synthetic["by_intent_group"], "intent_group", GROUP_ORDER):
        label = GROUP_LABEL[row["intent_group"]]
        lines.append(
            f"- {label}: journey resolution {share(row['resolved_journeys'], row['journeys'])}; "
            f"digital-to-call among its digital-first journeys "
            f"{share(row['digital_to_call'], row['digital_first'])}"
        )
    lines.append("")
    lines.append(
        "Synthetic contact resolution by intent group and channel. "
        "The base probability is the config input. The realised rate is the output:"
    )
    lines.append("")
    for group in GROUP_ORDER:
        for channel in CHANNEL_ORDER:
            row = _match(
                synthetic["resolution_by_group_channel"], intent_group=group, channel=channel
            )
            base = synthetic["assumptions"]["resolution_probability"][group][channel]
            lines.append(
                f"- {GROUP_LABEL[group]} on {channel}: base {base:.2f}, "
                f"realised {share(row['resolved_contacts'], row['contacts'])}"
            )
    lines.append("")
    flows = sorted(
        synthetic["directly_follows"],
        key=lambda row: (-row["n"], row["from_activity"], row["to_activity"]),
    )[:5]
    lines.append("Largest synthetic directly-follows flows:")
    lines.append("")
    for row in flows:
        lines.append(f"- {row['from_activity']} → {row['to_activity']}: {row['n']}")
    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _lookup_spill(report: dict) -> list[dict]:
    rows = [
        row
        for row in report["synthetic"]["resolution_by_intent"]
        if row["intent_group"] == "self_service_candidate"
    ]
    return sorted(rows, key=lambda row: (-row["digital_to_call"], row["intent"]))


def render_recommendations(report: dict) -> str:
    synthetic = report["synthetic"]
    bitext = report["public"]["bitext"]
    twitter = report["public"]["twitter_sample"]
    assumptions = synthetic["assumptions"]
    lookup_names = ", ".join(sorted(synthetic["config"]["intent_groups"]["self_service_candidate"]))
    complaint_names = ", ".join(sorted(synthetic["config"]["intent_groups"]["complaint"]))
    spills = _lookup_spill(report)
    spill_lines = [
        f"- {row['intent']}: {share(row['digital_to_call'], row['journeys'])} digital-to-call"
        for row in spills
    ]
    q_tag = _match(bitext["by_tag"], tag="Q")
    z_tag = _match(bitext["by_tag"], tag="Z")
    w_tag = _match(bitext["by_tag"], tag="W")
    k_tag = _match(bitext["by_tag"], tag="K")
    n_tag = _match(bitext["by_tag"], tag="N")
    social_mu = float(synthetic["config"]["ttfr_lognormal_minutes"]["social"]["mu"])
    lowest_channel = min(
        synthetic["resolution_by_channel"],
        key=lambda row: (row["resolved_contacts"] / row["contacts"], row["channel"]),
    )

    def cell(group: str, channel: str) -> str:
        row = _match(synthetic["resolution_by_group_channel"], intent_group=group, channel=channel)
        base = assumptions["resolution_probability"][group][channel]
        return (
            f"base {base:.2f}, realised {share(row['resolved_contacts'], row['contacts'])}"
        )

    lookup_group = _match(synthetic["by_intent_group"], intent_group="self_service_candidate")
    complaint_group = _match(synthetic["by_intent_group"], intent_group="complaint")
    social_ttfr = _match(synthetic["ttfr_by_first_channel"], channel="social")
    ussd_ttfr = _match(synthetic["ttfr_by_first_channel"], channel="ussd")
    paragraphs = [
        "# Design recommendations",
        "",
        "This note is a human-centred design hypothesis for a telco care journey. "
        "No synthetic rate in this repository is a real-world measurement. "
        "Each recommendation says whether it rests on the public Bitext training set "
        "or on the SYNTHETIC event log.",
        "",
        "## 1. Put lookup intents on a USSD menu and in the app",
        "",
        "Basis: the public Bitext intent names, plus synthetic journey outputs.",
        "",
        "Bitext publishes "
        f"{bitext['n_examples']} training examples, {bitext['n_intents']} intents, "
        f"and {bitext['examples_per_intent_min']} examples of each intent. "
        "That balance is a property of the training set, so it does not say which "
        "intents are common in a contact centre. The self-service shortlist is a "
        "design rule in `config/synthetic.yaml` applied to those public names, not a "
        f"Bitext column. The names on the shortlist are: {lookup_names}.",
        "",
        "On the synthetic log, self-service-candidate contacts resolve at "
        f"{cell('self_service_candidate', 'ussd')} on USSD and "
        f"{cell('self_service_candidate', 'app')} on the app. "
        "USSD first-contact time-to-first-response has median "
        f"{one_decimal(ussd_ttfr['median_minutes'])} minutes "
        f"(n={ussd_ttfr['journeys']}). "
        "Those realised rates sit close to the base inputs. They are not independent "
        "evidence for the inputs.",
        "",
        "What is not a single input is the spill to the call channel. "
        "Synthetic digital-to-call journeys in this group: "
        f"{share(lookup_group['digital_to_call'], lookup_group['digital_first'])} "
        "of its digital-first journeys. By intent:",
        "",
        *spill_lines,
        "",
        "A design test should start with the intents at the top of that list, "
        "because under these assumptions they create the most call arrivals after a "
        "digital lookup attempt.",
        "",
        "## 2. Keep a person available for complaint intents",
        "",
        "Basis: synthetic outputs. The grouping of these intents is a config rule "
        "over the public names.",
        "",
        f"Complaint intents in the config: {complaint_names}.",
        "",
        "Synthetic complaint contacts resolve at "
        f"{cell('complaint', 'ussd')} on USSD and "
        f"{cell('complaint', 'call')} on the call channel. "
        "Journey resolution for the group is "
        f"{share(complaint_group['resolved_journeys'], complaint_group['journeys'])}. "
        "Digital-to-call among its digital-first journeys is "
        f"{share(complaint_group['digital_to_call'], complaint_group['digital_first'])}. "
        "The low USSD base probability is an assumption. The digital-to-call share "
        "is an output of that assumption, the next-channel matrix, and the four-contact "
        "cap. Do not offer USSD as the only path for these intents. Use USSD to "
        "capture the symptom, then offer the call channel.",
        "",
        "## 3. Treat social as acknowledgement, not resolution",
        "",
        "Basis: synthetic clocks and synthetic resolution rates.",
        "",
        "The social time-to-first-response distribution is an input "
        f"(lognormal mu {social_mu:.2f}). On the simulated first contacts its median is "
        f"{one_decimal(social_ttfr['median_minutes'])} minutes and its 90th percentile "
        f"is {one_decimal(social_ttfr['p90_minutes'])} minutes "
        f"(n={social_ttfr['journeys']}). "
        "That median reproduces the configured distribution. It is not an independent "
        "discovery that social is slow. "
        "The model multiplies resolution probability by "
        f"{assumptions['slow_response_factor']:.2f} when a response is slower than "
        f"{one_decimal(assumptions['slow_response_minutes'])} minutes. "
        "The lowest realised contact resolution is "
        f"{lowest_channel['channel']}, at "
        f"{share(lowest_channel['resolved_contacts'], lowest_channel['contacts'])}. "
        "Lookup intents on social are "
        f"{cell('self_service_candidate', 'social')}. "
        "Complaint intents on social are "
        f"{cell('complaint', 'social')}. "
        "Under these assumptions, keep social as acknowledgement and hand the "
        "customer to USSD, the app, or the call channel for the fix.",
        "",
        "## 4. Make chat tolerate typos, and keep USSD as a menu",
        "",
        "Basis: public Bitext language tags. Bitext calls this file a hybrid "
        "synthetic training set, so the tags describe generated training utterances.",
        "",
        "Colloquial tag (Q): "
        f"{share(q_tag['n_examples'], bitext['n_examples'])}. "
        "Typo tag (Z): "
        f"{share(z_tag['n_examples'], bitext['n_examples'])}. "
        "Offensive-language tag (W): "
        f"{share(w_tag['n_examples'], bitext['n_examples'])}. "
        "Keyword tag (K): "
        f"{share(k_tag['n_examples'], bitext['n_examples'])}. "
        "Negation tag (N): "
        f"{share(n_tag['n_examples'], bitext['n_examples'])}. "
        "The keyword and negation codes are documented by Bitext and are absent from "
        "this file's tag column. The utterances are full phrases, including colloquial "
        "wording and typos, not keyword strings. A USSD menu should be a structured "
        "choice, not a free-text copy of these utterances. A chat or app path trained "
        "only on clean phrases would miss the colloquial and typo variants this public "
        "set contains. This is a statement about the training set, not about customers "
        "in any country.",
        "",
        "## What would change these recommendations",
        "",
        "Replace the weights, base probabilities, and clocks in "
        "`config/synthetic.yaml` with operator measurements and rerun "
        "`python scripts/run_analysis.py`. The Twitter preview "
        f"({twitter['n_rows']} data rows, "
        f"{twitter['inbound_to_company_reply_pairs']} in-file reply pairs, "
        f"median delay {one_decimal(twitter['reply_delay_minutes_median'])} minutes) "
        "is too small, too mixed across brands, and too incomplete as a thread "
        "sample to choose a channel. The full Customer Support on Twitter corpus "
        "was not downloaded, because that file was not available without a Kaggle login.",
        "",
    ]
    return "\n".join(paragraphs).rstrip() + "\n"
