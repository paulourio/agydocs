#!/usr/bin/env python3
"""quality_gate.py - Deterministic 3-Stage NLP Quality Gate for Technical Prose.

Enforces authentic human voice, syntactic burstiness, demonstrative anchoring,
and information density while eradicating AI slop, Claude-ese, and formulaic motifs.

Usage:
    python3 quality_gate.py [--profile {rfc,paper,essay,tutorial,chat,briefing}]
                            [--json] [--fix-hints] [--verbose] [FILE]
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# ==============================================================================
# 1. Lexical Dictionaries & Patterns
# ==============================================================================

CLAUDISMS: list[tuple[str, str, str]] = [
    # (Pattern, Label, Fix Recommendation)
    (
        r"\bsit with (?:this|that|these|the realization|the fact|the idea)\b",
        "Reflective Posing ('sit with this')",
        "Cut phrase; state the technical conclusion directly.",
    ),
    (
        r"\bthe physics of (?:the problem|software|code|systems?|engineering|the cluster)\b",
        "Metaphorical Physics ('the physics of...')",
        "Replace with concrete constraints: 'hardware limits', 'network boundaries', 'kernel invariants'.",
    ),
    (
        r"\b(?:does|doing)\s+(?:the|real)\s+work\b",
        "Epistemic Fluff ('doing real work')",
        "Specify the exact mechanism: 'enforces state replication', 'indexes foreign keys'.",
    ),
    (
        r"\b(?:an?|the)\s+honest\s+(?:take|assessment|look|conversation)\b|\bhonestly\s+speaking\b",
        "Performative Candor ('honest take')",
        "Cut entirely; state the finding directly.",
    ),
    (
        r"\bexact grain\b",
        "Claudish Dialect ('exact grain')",
        "Use 'granularity', 'byte offset', or 'resolution'.",
    ),
    (
        r"\bcompounds? over time\b",
        "Metaphorical Compounding ('compounds over time')",
        "Specify the exact mechanical accumulation, such as lock contention or unmaintained code paths.",
    ),
]

# Contextual Claudism: 'load-bearing'
# Allowed ONLY when followed by physical/concrete systems nouns
LOAD_BEARING_PATTERN = r"\bload[- ]bearing\b"
ALLOWED_LOAD_BEARING_NOUNS = {
    "beam",
    "beams",
    "cable",
    "cables",
    "column",
    "columns",
    "database",
    "databases",
    "endpoint",
    "endpoints",
    "girder",
    "girders",
    "index",
    "indices",
    "infrastructure",
    "member",
    "members",
    "node",
    "nodes",
    "partition",
    "partitions",
    "pillar",
    "pillars",
    "pipe",
    "pipes",
    "schema",
    "schemas",
    "service",
    "services",
    "shard",
    "shards",
    "structure",
    "structures",
    "substrate",
    "substrates",
    "table",
    "tables",
    "truss",
    "trusses",
    "wall",
    "walls",
    "wire",
    "wires",
}

AI_TELLS: list[tuple[str, str, str]] = [
    (
        r"\bdelv(?:e|es|ed|ing)\b",
        "Generic AI Tell ('delve')",
        "Replace with 'inspect', 'analyze', 'examine', or 'profile'.",
    ),
    (
        r"\btapestry\b",
        "Generic AI Tell ('tapestry')",
        "Cut or replace with concrete architecture description.",
    ),
    (
        r"\bbeacon\b",
        "Generic AI Tell ('beacon')",
        "Cut theatrical metaphor; state system purpose.",
    ),
    (
        r"\b(?:serves?|stands?|is|are)\s+as\s+a\s+testament\s+to\b|\btestament\s+to\b",
        "Copular Inflation ('testament to')",
        "Replace with 'proves', 'shows', or 'demonstrates'.",
    ),
    (
        r"\bparamount\b",
        "Generic AI Tell ('paramount')",
        "Use 'critical', 'mandatory', or explain consequence of omission.",
    ),
    (
        r"\bmultifaceted\b",
        "Generic AI Tell ('multifaceted')",
        "Detail the specific components or dimensions.",
    ),
    (
        r"\bintertwined\b",
        "Generic AI Tell ('intertwined')",
        "Specify the coupling or dependency relationship.",
    ),
    (
        r"\bparsimoniously\b",
        "Lexical Register Intrusion ('parsimoniously')",
        "Use 'sparingly', 'minimally', or state the exact limit.",
    ),
    (
        r"\bnuanced\s+(?:landscape|realm|interplay|tapestry)\b",
        "Generic AI Tell ('nuanced landscape')",
        "Describe the specific architectural trade-offs.",
    ),
    (
        r"\bseamless(?:ly)?\b",
        "Generic AI Tell ('seamless')",
        "Specify latency, integration protocol, or error boundaries.",
    ),
    (
        r"\bcrucial foundation\b",
        "Generic AI Tell ('crucial foundation')",
        "State the exact prerequisite dependency.",
    ),
    (
        r"\b(?:formal\s+)?axiomatic\s+compression\s+operators?\b",
        "Pseudo-Intellectual AI Tell ('axiomatic compression operator')",
        "Use 'precise technical terms' or 'exact behavioral guarantees'.",
    ),
]

PERFORMATIVE_WINKS: list[tuple[str, str, str]] = [
    (
        r"\bsee what i did (?:there|here)\b",
        "Conversational Wink",
        "Cut performative humor.",
    ),
    (
        r"\bhere'?s the kicker\b",
        "Conversational Wink ('Here's the kicker')",
        "State the finding directly.",
    ),
    (
        r"\blet(?:'s|\s+us)\s+dive\s+in\b",
        "Performative Banter ('Let's dive in')",
        "Begin immediately with technical substance.",
    ),
    (r"\bbuckle up\b", "Performative Banter ('Buckle up')", "Cut theatrical banter."),
    (
        r"\bat the end of the day\b",
        "Performative Cliché ('At the end of the day')",
        "State conclusion directly.",
    ),
    (
        r"\bjourney worth taking\b",
        "Performative Banter ('journey worth taking')",
        "Cut literary melodrama.",
    ),
    (
        r"\blet(?:'s|\s+us)\s+unpack\b",
        "Meta-Padding ('Let's unpack')",
        "Explain the mechanism directly without announcing it.",
    ),
    (
        r"\blet(?:'s|\s+us)\s+take\s+a\s+step\s+back\b",
        "Meta-Padding ('Let's take a step back')",
        "Address the topic directly.",
    ),
    (
        r"\bok,?\s*i'?m becoming almost meta\b",
        "Performative Meta-Commentary",
        "Cut self-referential commentary.",
    ),
]

SYCOPHANCY_PATTERNS: list[tuple[str, str, str]] = [
    (
        r"\byou(?:'re| are) (?:completely|absolutely|totally) right\b",
        "Sycophantic Validation",
        "Cut agreement; deliver analysis directly.",
    ),
    (
        r"(?:\bthat(?:'s|\s+is)\s+a\s+|\b)(?:great|profound|fantastic|wonderful|excellent|good)\s+(?:point|question|catch|observation)\b",
        "Sycophantic Flattery",
        "Answer the prompt directly without evaluating the user's intelligence.",
    ),
    (
        r"\bi(?:'d| would) (?:be delighted|be happy|love) to (?:help|assist)\b",
        "Sycophantic Preambles",
        "Start directly with code, diff, or diagnostics.",
    ),
    (
        r"^\s*(?:certainly|sure thing|of course|gladly)[!,.]?\s*",
        "Sycophantic Opening ('Certainly!')",
        "Start directly with the answer.",
    ),
    (
        r"\bi hope this helps\b",
        "Customer-Support Sign-Off",
        "End at the technical verification step.",
    ),
    (
        r"\bhappy coding!?\b",
        "Customer-Support Sign-Off",
        "End cleanly at the technical step.",
    ),
    (
        r"\b(?:let me know if|feel free to|don'?t hesitate to)\s+(?:you\s+have\s+any\s+questions|reach\s+out|ask|there'?s\s+anything\s+else)\b",
        "Customer-Support Sign-Off",
        "End cleanly at the technical verification step.",
    ),
]

TAILING_CLAUSES: list[tuple[str, str, str]] = [
    (
        r",\s*(?:highlighting|underscoring|fostering|ensuring|paving the way|showcasing|embodying|exemplifying|bolstering|underpinning)\b",
        "Tailing Participial Clause (-ing appendage)",
        "End sentence at the period. Avoid moralizing or teleological appendages.",
    ),
]

LIGHT_VERB_NOMINALS: list[tuple[str, str, str]] = [
    (
        r"\bperform an? allocation\b",
        "Light Verb Nominal ('perform an allocation')",
        "Use 'allocate'.",
    ),
    (
        r"\bfacilitate the optimization of\b",
        "Light Verb Nominal ('facilitate optimization')",
        "Use 'optimize'.",
    ),
    (
        r"\bmake an? adjustment to\b",
        "Light Verb Nominal ('make an adjustment')",
        "Use 'adjust'.",
    ),
    (
        r"\bconduct an evaluation of\b",
        "Light Verb Nominal ('conduct evaluation')",
        "Use 'evaluate'.",
    ),
    (
        r"\bachieve the mitigation of\b",
        "Light Verb Nominal ('achieve mitigation')",
        "Use 'mitigate'.",
    ),
    (
        r"\bprovide an explanation of\b",
        "Light Verb Nominal ('provide an explanation')",
        "Use 'explain'.",
    ),
    (
        r"\bexecute a termination of\b",
        "Light Verb Nominal ('execute a termination of')",
        "Use 'terminate'.",
    ),
    (
        r"\breach a determination regarding\b",
        "Light Verb Nominal ('reach a determination regarding')",
        "Use 'determine'.",
    ),
    (
        r"\bperform an execution of\b",
        "Light Verb Nominal ('perform an execution of')",
        "Use 'execute'.",
    ),
]

# Canonical technical nouns ending in -tion/-ment/-ance that are NOT zombie nominals
VALID_DOMAIN_TECHNICAL_NOUNS = {
    # Formal computing, systems, and mathematical primitives (-ity, -tion, -sion, -ment, -ance, -ence)
    "abstraction",
    "abstractions",
    "absurdity",
    "absurdities",
    "achievement",
    "achievements",
    "acknowledgement",
    "acknowledgment",
    "acquisition",
    "action",
    "adherence",
    "affinity",
    "aggregation",
    "algorithm",
    "alignment",
    "allocation",
    "antigravity",
    "authority",
    "authorities",
    "cadence",
    "cadences",
    "circumlocution",
    "circumlocutions",
    "clarification",
    "clarifications",
    "comment",
    "comments",
    "community",
    "communities",
    "competition",
    "competitions",
    "confirmation",
    "confirmations",
    "conjunction",
    "conjunctions",
    "convention",
    "conventions",
    "criticality",
    "criticalities",
    "decomposition",
    "decompositions",
    "decoupling",
    "decouplings",
    "development",
    "developments",
    "disambiguation",
    "disambiguations",
    "dominance",
    "dominances",
    "entanglement",
    "entanglements",
    "entities",
    "entity",
    "eradication",
    "formation",
    "formations",
    "foundation",
    "foundations",
    "friction",
    "frictions",
    "frustration",
    "frustrations",
    "functionality",
    "functionalities",
    "idempotence",
    "inflation",
    "inflations",
    "interrogation",
    "interrogations",
    "intuition",
    "intuitions",
    "lucidity",
    "mention",
    "mentions",
    "misconception",
    "misconceptions",
    "misprediction",
    "mispredictions",
    "motion",
    "motions",
    "nominalization",
    "nominalizations",
    "ornamentation",
    "ornamentations",
    "paradigm",
    "paradigms",
    "possibility",
    "possibilities",
    "presence",
    "presences",
    "profundity",
    "profundities",
    "prohibition",
    "prohibitions",
    "proposition",
    "propositions",
    "punctuation",
    "punctuations",
    "quantity",
    "quantities",
    "readability",
    "reality",
    "realities",
    "reception",
    "receptions",
    "rejection",
    "rejections",
    "remediation",
    "remediations",
    "sentence",
    "sentences",
    "sentience",
    "simplification",
    "simplifications",
    "speculation",
    "speculations",
    "telemetry",
    "telemetries",
    "terminology",
    "terminologies",
    "tradition",
    "traditions",
    "uniformity",
    "uniformities",
    "violation",
    "violations",
    "ambiguity",
    "animation",
    "appearance",
    "application",
    "argument",
    "assertion",
    "assignment",
    "assistance",
    "associativity",
    "atomicity",
    "attachment",
    "authentication",
    "authorization",
    "availability",
    "balance",
    "calculation",
    "calibration",
    "cancellation",
    "capacitance",
    "capacity",
    "cardinality",
    "chance",
    "circumstance",
    "classification",
    "clearance",
    "coherence",
    "commitment",
    "communication",
    "commutativity",
    "compartment",
    "compatibility",
    "compensation",
    "competence",
    "compliance",
    "complexity",
    "computability",
    "computation",
    "concavity",
    "concurrency",
    "concurrence",
    "condition",
    "configuration",
    "conference",
    "confidence",
    "conformance",
    "connection",
    "connectivity",
    "consequence",
    "consistency",
    "construction",
    "consumption",
    "containment",
    "contention",
    "continuation",
    "continuity",
    "convergence",
    "convexity",
    "convolution",
    "correction",
    "deallocation",
    "decidability",
    "decompression",
    "decrement",
    "decryption",
    "deduplication",
    "definition",
    "demonstration",
    "density",
    "deployment",
    "derivation",
    "description",
    "deserialization",
    "destination",
    "difference",
    "differentiability",
    "dimension",
    "distance",
    "distribution",
    "distributivity",
    "divergence",
    "document",
    "documentation",
    "durability",
    "duration",
    "elasticity",
    "element",
    "emission",
    "encryption",
    "entitlement",
    "environment",
    "equation",
    "equipment",
    "equality",
    "evidence",
    "eviction",
    "evolution",
    "exception",
    "execution",
    "existence",
    "expectation",
    "experiment",
    "explanation",
    "expressivity",
    "extensibility",
    "fence",
    "fraction",
    "fragment",
    "fragmentation",
    "frequency",
    "function",
    "generalization",
    "generation",
    "glance",
    "granularity",
    "guidance",
    "heterogeneity",
    "hierarchy",
    "homogeneity",
    "identity",
    "idempotency",
    "immutability",
    "impedance",
    "implementation",
    "impossibility",
    "increment",
    "inequality",
    "inference",
    "information",
    "ingestion",
    "inheritance",
    "initialization",
    "instance",
    "instantiation",
    "instruction",
    "instrument",
    "integrability",
    "integrity",
    "interaction",
    "interference",
    "interoperability",
    "interpretation",
    "interruption",
    "intersection",
    "invariance",
    "invalidation",
    "iteration",
    "latency",
    "linearizability",
    "linearization",
    "linearity",
    "locality",
    "location",
    "maintainability",
    "maintenance",
    "majority",
    "management",
    "manipulation",
    "measurement",
    "migration",
    "minority",
    "modification",
    "modularity",
    "monotonicity",
    "multiplicity",
    "mutability",
    "mutation",
    "nonlinearity",
    "normalization",
    "observability",
    "occurrence",
    "operation",
    "optimization",
    "orientation",
    "pagination",
    "parameterization",
    "parity",
    "partition",
    "performance",
    "permission",
    "permutation",
    "persistence",
    "placement",
    "population",
    "position",
    "precision",
    "priority",
    "probability",
    "production",
    "programmability",
    "projection",
    "propagation",
    "proportion",
    "provenance",
    "quality",
    "quantization",
    "reachability",
    "reaction",
    "reallocation",
    "reconciliation",
    "recoverability",
    "recurrence",
    "redirection",
    "reducibility",
    "reduction",
    "reference",
    "refinement",
    "reflection",
    "reflexivity",
    "registration",
    "regression",
    "regularity",
    "relation",
    "reliability",
    "reluctance",
    "replacement",
    "replication",
    "representation",
    "reproducibility",
    "requirement",
    "residence",
    "resistance",
    "resolution",
    "resonance",
    "rotation",
    "saturation",
    "scalability",
    "science",
    "section",
    "segment",
    "segmentation",
    "sensitivity",
    "separation",
    "sequence",
    "serializability",
    "serialization",
    "session",
    "significance",
    "silence",
    "simulation",
    "singularity",
    "solution",
    "specialization",
    "specification",
    "stability",
    "stance",
    "statement",
    "substance",
    "substitution",
    "synchronicity",
    "synchronization",
    "termination",
    "tolerance",
    "topology",
    "traceability",
    "tractability",
    "transaction",
    "transformation",
    "transition",
    "translation",
    "transmission",
    "transitivity",
    "truncation",
    "utility",
    "validation",
    "validity",
    "variance",
    "verbosity",
    "verification",
    "version",
    "visibility",
}

# Verbs, adverbs, and particles indicating unanchored demonstrative pronouns ("This/These")
UNANCHORED_THIS_FOLLOWERS: set[str] = {
    # Auxiliaries & modals
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "do",
    "does",
    "did",
    "done",
    "doing",
    "have",
    "has",
    "had",
    "having",
    "can",
    "could",
    "will",
    "would",
    "shall",
    "should",
    "may",
    "might",
    "must",
    # Copular & linking verbs
    "seems",
    "seemed",
    "seem",
    "appears",
    "appeared",
    "appear",
    "remains",
    "remained",
    "remain",
    "becomes",
    "became",
    "become",
    "looks",
    "looked",
    "look",
    "feels",
    "felt",
    "feel",
    # Common action / reporting verbs used with abstract "This"
    "means",
    "meant",
    "mean",
    "shows",
    "showed",
    "shown",
    "show",
    "proves",
    "proved",
    "proven",
    "prove",
    "demonstrates",
    "demonstrated",
    "demonstrate",
    "ensures",
    "ensured",
    "ensure",
    "guarantees",
    "guaranteed",
    "guarantee",
    "provides",
    "provided",
    "provide",
    "allows",
    "allowed",
    "allow",
    "causes",
    "caused",
    "cause",
    "leads",
    "led",
    "lead",
    "creates",
    "created",
    "create",
    "requires",
    "required",
    "require",
    "suggests",
    "suggested",
    "suggest",
    "implies",
    "implied",
    "imply",
    "indicates",
    "indicated",
    "indicate",
    "gives",
    "gave",
    "given",
    "give",
    "yields",
    "yielded",
    "yield",
    "results",
    "resulted",
    "result",
    "serves",
    "served",
    "serve",
    "stands",
    "stood",
    "stand",
    "helps",
    "helped",
    "help",
    "makes",
    "made",
    "make",
    "protects",
    "protected",
    "protect",
    "prevents",
    "prevented",
    "prevent",
    "handles",
    "handled",
    "handle",
    "works",
    "worked",
    "work",
    "fails",
    "failed",
    "fail",
    "breaks",
    "broke",
    "broken",
    "break",
    "holds",
    "held",
    "hold",
    "applies",
    "applied",
    "apply",
    "occurs",
    "occurred",
    "occur",
    "happens",
    "happened",
    "happen",
    "depends",
    "depended",
    "depend",
    "consists",
    "consisted",
    "consist",
    "represents",
    "represented",
    "represent",
    "includes",
    "included",
    "include",
    "contains",
    "contained",
    "contain",
    "differs",
    "differed",
    "differ",
    "eliminates",
    "eliminated",
    "eliminate",
    "reduces",
    "reduced",
    "reduce",
    "increases",
    "increased",
    "increase",
    "introduces",
    "introduced",
    "introduce",
    "simplifies",
    "simplified",
    "simplify",
    "triggers",
    "triggered",
    "trigger",
    "initiates",
    "initiated",
    "initiate",
    "forces",
    "forced",
    "force",
    "demands",
    "demanded",
    "demand",
    "leaves",
    "left",
    "leave",
    "violates",
    "violated",
    "violate",
    "exposes",
    "exposed",
    "expose",
    "reveals",
    "revealed",
    "reveal",
    "generates",
    "generated",
    "generate",
    "induces",
    "induced",
    "induce",
    "mitigates",
    "mitigated",
    "mitigate",
    "manifests",
    "manifested",
    "manifest",
    # Adverbs / particles intervening before verbs
    "also",
    "only",
    "just",
    "simply",
    "directly",
    "actually",
    "essentially",
    "effectively",
    "clearly",
    "not",
    "however",
    "therefore",
    "thus",
    "instead",
    "again",
    "already",
    "still",
    "even",
    "often",
    "always",
    "rarely",
    "seldom",
    "never",
    "in",
    "to",
    "for",
    "with",
    "at",
    "by",
    "from",
}


def is_valid_domain_noun(word: str) -> bool:
    """Checks if a word or its singular form is an accepted domain technical primitive."""
    w_lower = word.lower()
    if w_lower in VALID_DOMAIN_TECHNICAL_NOUNS:
        return True
    if (
        w_lower.endswith("ities")
        and (w_lower[:-5] + "ity") in VALID_DOMAIN_TECHNICAL_NOUNS
    ):
        return True
    if w_lower.endswith("s") and w_lower[:-1] in VALID_DOMAIN_TECHNICAL_NOUNS:
        return True
    return bool(w_lower.endswith("es") and w_lower[:-2] in VALID_DOMAIN_TECHNICAL_NOUNS)


def is_zombie_nominal(word: str) -> bool:
    """Detects bureaucratic action-obscuring nominalizations in singular and plural forms."""
    w_lower = word.lower()
    if "-" in w_lower:
        return is_zombie_nominal(w_lower.split("-")[-1])
    if "_" in w_lower:
        return is_zombie_nominal(w_lower.split("_")[-1])
    if len(w_lower) < 6 or is_valid_domain_noun(w_lower):
        return False
    return bool(
        re.search(
            r"(?:tions?|ments?|ances?|ences?|ities|ity|izations?|olog(?:y|ies))$",
            w_lower,
        )
    )


# ==============================================================================
# 2. Profile Tolerance Configuration
# ==============================================================================


@dataclass
class ProfileConfig:
    name: str
    description: str
    target_burstiness_min: float
    target_burstiness_max: float
    max_syntactic_overhead: float
    max_zombie_nominals_pct: float
    max_em_dashes_per_100w: float
    min_punctuation_balance: float
    min_demonstrative_anchoring: float
    max_concrete_anchor_lag_words: int | None
    min_hvi: float
    min_tpi: float


PROFILES: dict[str, ProfileConfig] = {
    "rfc": ProfileConfig(
        name="rfc",
        description="Systems Specifications, RFCs, Architecture Decision Records (ADRs)",
        target_burstiness_min=0.32,
        target_burstiness_max=0.65,
        max_syntactic_overhead=6.5,
        max_zombie_nominals_pct=1.5,
        max_em_dashes_per_100w=0.20,
        min_punctuation_balance=1.5,
        min_demonstrative_anchoring=0.80,
        max_concrete_anchor_lag_words=200,
        min_hvi=80.0,
        min_tpi=85.0,
    ),
    "paper": ProfileConfig(
        name="paper",
        description="Scientific Papers, Algorithmic Analysis, Formal Research",
        target_burstiness_min=0.40,
        target_burstiness_max=0.70,
        max_syntactic_overhead=6.5,
        max_zombie_nominals_pct=2.0,
        max_em_dashes_per_100w=0.15,
        min_punctuation_balance=2.0,
        min_demonstrative_anchoring=0.85,
        max_concrete_anchor_lag_words=300,
        min_hvi=85.0,
        min_tpi=85.0,
    ),
    "essay": ProfileConfig(
        name="essay",
        description="Technical Architecture Essays & Deep Dives",
        target_burstiness_min=0.38,
        target_burstiness_max=0.70,
        max_syntactic_overhead=5.5,
        max_zombie_nominals_pct=1.0,
        max_em_dashes_per_100w=0.25,
        min_punctuation_balance=1.5,
        min_demonstrative_anchoring=0.80,
        max_concrete_anchor_lag_words=250,
        min_hvi=85.0,
        min_tpi=80.0,
    ),
    "tutorial": ProfileConfig(
        name="tutorial",
        description="Developer Guides, Onboarding Walkthroughs & API Tutorials",
        target_burstiness_min=0.30,
        target_burstiness_max=0.60,
        max_syntactic_overhead=4.5,
        max_zombie_nominals_pct=0.8,
        max_em_dashes_per_100w=0.15,
        min_punctuation_balance=1.0,
        min_demonstrative_anchoring=0.75,
        max_concrete_anchor_lag_words=150,
        min_hvi=80.0,
        min_tpi=75.0,
    ),
    "chat": ProfileConfig(
        name="chat",
        description="Interactive Agent Pairing, CLI Diagnostics & Code Reviews",
        target_burstiness_min=0.30,
        target_burstiness_max=0.75,
        max_syntactic_overhead=4.0,
        max_zombie_nominals_pct=1.0,
        max_em_dashes_per_100w=0.10,
        min_punctuation_balance=1.0,
        min_demonstrative_anchoring=0.85,
        max_concrete_anchor_lag_words=None,
        min_hvi=85.0,
        min_tpi=80.0,
    ),
    "briefing": ProfileConfig(
        name="briefing",
        description="Executive Summaries & Technical Briefings",
        target_burstiness_min=0.35,
        target_burstiness_max=0.65,
        max_syntactic_overhead=4.5,
        max_zombie_nominals_pct=1.0,
        max_em_dashes_per_100w=0.10,
        min_punctuation_balance=1.5,
        min_demonstrative_anchoring=0.85,
        max_concrete_anchor_lag_words=None,
        min_hvi=80.0,
        min_tpi=80.0,
    ),
}

# ==============================================================================
# 3. Data Structures for Findings
# ==============================================================================


@dataclass
class Violation:
    stage: int
    rule: str
    message: str
    line: int | None
    snippet: str
    recommendation: str


@dataclass
class QualityMetrics:
    total_words: int = 0
    total_sentences: int = 0
    mean_sentence_length: float = 0.0
    sentence_length_std: float = 0.0
    burstiness_cv: float = 0.0
    syntactic_overhead: float = 0.0
    zombie_nominals_count: int = 0
    zombie_nominals_pct: float = 0.0
    em_dashes_count: int = 0
    em_dashes_per_100w: float = 0.0
    colons_count: int = 0
    semicolons_count: int = 0
    punctuation_balance_ratio: float = 0.0
    sentence_initial_this_total: int = 0
    sentence_initial_this_anchored: int = 0
    demonstrative_anchoring_index: float = 1.0
    contrastive_reframes_count: int = 0
    concrete_anchor_lag_words: int | None = None
    human_voice_index: float = 100.0
    technical_precision_index: float = 100.0


@dataclass
class AuditReport:
    profile: str
    passed: bool
    metrics: QualityMetrics = field(default_factory=QualityMetrics)
    violations: list[Violation] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile": self.profile,
            "passed": self.passed,
            "metrics": asdict(self.metrics),
            "violations": [asdict(v) for v in self.violations],
        }


# ==============================================================================
# 4. Text Processing Utilities
# ==============================================================================


def split_into_lines_and_prose(
    text: str,
) -> tuple[list[str], str, list[tuple[int, str]]]:
    """Separates raw text into lines and prose blocks, removing code fences, math blocks, frontmatter, and tables.

    Excludes educational negative example quotes, rejected variants, and list headers
    from narrative prose evaluation.
    """
    lines = text.splitlines()
    prose_lines: list[tuple[int, str]] = []
    body_lines: list[str] = []
    in_math_block = False
    in_frontmatter = False
    code_fence_len = 0

    in_negative_context = False
    in_banned_list = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        # Handle YAML frontmatter at start of file
        if idx == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue

        # CommonMark code fences with backtick counts (including nested inside blockquotes)
        m_fence = re.match(r"^(`{3,})", stripped.lstrip("> "))
        if m_fence:
            fl = len(m_fence.group(1))
            if code_fence_len == 0:
                code_fence_len = fl
                continue
            elif fl >= code_fence_len:
                code_fence_len = 0
                continue
        if code_fence_len > 0:
            continue

        # Handle LaTeX display math blocks ($$ ... $$ and \begin{equation} ... \end{equation})
        if stripped.startswith("$$"):
            if stripped.endswith("$$") and len(stripped) > 2:
                continue
            in_math_block = not in_math_block
            continue
        if re.match(
            r"^\\begin\{(?:equation|align|gather|multline|displaymath)\*?\}",
            stripped,
        ):
            in_math_block = True
            continue
        if re.match(
            r"^\\end\{(?:equation|align|gather|multline|displaymath)\*?\}",
            stripped,
        ):
            in_math_block = False
            continue
        if in_math_block:
            continue

        # Skip horizontal rules
        if stripped in ("---", "___", "***"):
            in_negative_context = False
            in_banned_list = False
            continue

        # Skip markdown table rows
        if stripped.startswith("|") and stripped.endswith("|"):
            continue

        # Heading detection
        m_head = re.match(r"^(#{1,6})\s+(.*)", line)
        if m_head:
            head_hashes, head_text = m_head.group(1), m_head.group(2).strip()
            if re.search(
                r"\b(?:After|PASSED|Master|Authentic|Positive|Canonical)\b",
                head_text,
                re.IGNORECASE,
            ):
                in_negative_context = False
            elif re.search(
                r"\b(?:Before|Negative|Banned|REJECTED|Slop|Anti-Pattern|Bad|Defect|Strawman|Infantilized|Prohibited|Bourbaki|Fluff)\b",
                head_text,
                re.IGNORECASE,
            ):
                in_negative_context = True
            elif len(head_hashes) <= 2:
                in_negative_context = False
            in_banned_list = False
            continue

        # Check for list heading introducing banned / negative items
        if re.search(
            r"^[-*+]?\s*\*\*(?:Prohibited|Banned|Anti-Patterns?|Violation(?:\s+Example)?)[^*:]*[:*]+",
            stripped,
            re.IGNORECASE,
        ):
            in_banned_list = True
            continue
        elif (
            stripped.startswith("- **")
            and not re.search(
                r"^[-*+]?\s*\*\*(?:Prohibited|Banned|Anti-Patterns?|Violation(?:\s+Example)?)[^*:]*[:*]+",
                stripped,
                re.IGNORECASE,
            )
        ) or not stripped.startswith(("-", "*", "+", " ")):
            in_banned_list = False

        # Educational quote / Negative example detection
        is_neg_example = False

        # 1. Blockquotes demonstrating negative examples under negative context or explicit markers
        if stripped.startswith(">") and (
            in_negative_context
            or re.search(
                r"^\s*(?:>\s*)+(?:[\*\"`])*(?:Bad|Defect|Negative(?:\s+Example)?|Anti-Pattern|Banned|Strawman|Infantilized|Before|REJECTED)\b",
                line,
                re.IGNORECASE,
            )
        ):
            is_neg_example = True

        # 2. Bullet lines explicitly marked as Bad / Defect / Negative Example / Avoid / Strawman or diagnostic metadata
        if re.match(
            r"^\s*[-*+]?\s*\**\s*(?:"
            r"Bad|Defect|Negative(?:\s+Example)?|Anti-Pattern|Banned|Strawman[^*:]*|"
            r"Infantilized|Avoid|Trivial\s+Reframe|Claudisms?\s+Detected|Violations?|"
            r"Fatal\s+Defect|AI\s+Tells|Tailing\s+Clauses|Quality\s+Gate|Shannon\s+Information\s+Loss|"
            r"Zombie\s+Nominals?|Human\s+Voice\s+Index|Technical\s+Precision\s+Index|"
            r"Linguistic\s+Virtues|Dependency\s+Locality|Burstiness|Demonstrative\s+Anchoring|"
            r"Status|Root\s+Cause|Action|Result"
            r")\s*[:*]+\s*",
            line,
            re.IGNORECASE,
        ):
            is_neg_example = True

        # 3. Sub-items under banned/prohibited lists quoting bad phrases
        if in_banned_list and re.match(r"^\s*[-*+]?\s*(?:\*[\"']|[\"'])", line):
            is_neg_example = True

        if is_neg_example:
            continue

        # Clean line of parenthetical negative quotes and annotations like (*"..."*) or (*e.g. "..."*)
        cleaned = re.sub(r"\(\*.*?\*\)", " ", line)

        # Strip blockquote prefix (including multi-level nested blockquotes)
        cleaned = re.sub(r"^(?:\s*>\s*)+", "", cleaned)

        # Remove list markers
        cleaned = re.sub(r"^\s*[-*+]\s+", "", cleaned)
        cleaned = re.sub(r"^\s*\d+\.\s+", "", cleaned)
        if cleaned.strip():
            prose_lines.append((idx, cleaned))
            body_lines.append(cleaned)

    full_prose = " ".join(body_lines)
    return lines, full_prose, prose_lines


def extract_sentences(prose: str) -> list[str]:
    """Splits prose into distinct sentences, respecting abbreviations, inline math, and markdown formatting."""
    pat = r"(?:(?<=[.!?])|(?<=[.!?][\"\'”’*_.)])|(?<=[.!?][\"\'”’*_.)]{2}))\s+(?=[A-Za-z0-9\"\'‘“`$*\[(-])"
    raw_sentences = re.split(pat, prose)
    cleaned = []
    for s in raw_sentences:
        st = s.strip()
        if st and len(st) > 2:
            cleaned.append(st)
    return cleaned


def tokenize_words(text: str) -> list[str]:
    """Extracts words from text, preserving alphanumeric tokens."""
    return re.findall(r"\b[A-Za-z0-9_-]+\b", text)


def compute_anchor_lag(lines: list[str]) -> int | None:
    """Computes words from start of document or first header until first code block, table, or display equation."""
    word_count = 0
    in_frontmatter = False

    for idx, line in enumerate(lines, start=1):
        stripped = line.strip()
        if idx == 1 and stripped == "---":
            in_frontmatter = True
            continue
        if in_frontmatter:
            if stripped == "---":
                in_frontmatter = False
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith("```"):
            return word_count
        if stripped.startswith("|") and stripped.endswith("|") and "-" in stripped:
            return word_count
        if stripped.startswith("$$") or re.match(
            r"^\\begin\{(?:equation|align|gather|multline|displaymath)\*?\}",
            stripped,
        ):
            return word_count

        words = tokenize_words(line)
        word_count += len(words)

    return word_count if word_count > 0 else None


# ==============================================================================
# 5. Diagnostic Engine: Stages 1, 2, and 3
# ==============================================================================


def audit_stage1_hard_invariants(
    text: str,
    lines: list[str],
    prose_lines: list[tuple[int, str]],
    violations: list[Violation],
) -> None:
    """Audits Stage 1: Fast-fail hard invariants (regex tokens, Claudisms, tailing participial clauses)."""
    # 1. Check Claudisms with line numbers
    for line_idx, line in prose_lines:
        line_clean = re.sub(r"`[^`]+`", " ", line)

        for pattern, label, fix in CLAUDISMS:
            matches = list(re.finditer(pattern, line_clean, re.IGNORECASE))
            for m in matches:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Claudism",
                        message=f"Detected {label}: '{m.group(0)}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation=fix,
                    )
                )

        # Contextual check for 'load-bearing'
        for m in re.finditer(LOAD_BEARING_PATTERN, line_clean, re.IGNORECASE):
            post_text = line_clean[m.end() :].strip()
            next_words = tokenize_words(post_text)
            first_noun = next_words[0].lower() if next_words else ""
            if first_noun not in ALLOWED_LOAD_BEARING_NOUNS:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Claudism (Contextual)",
                        message=f"Abstract usage of 'load-bearing' before non-physical noun '{first_noun}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation="Allow 'load-bearing' only before concrete systems nouns (table, column, partition, service, wire).",
                    )
                )

        # 2. Performative Winks
        for pattern, label, fix in PERFORMATIVE_WINKS:
            matches = list(re.finditer(pattern, line_clean, re.IGNORECASE))
            for m in matches:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Performative Wink",
                        message=f"Detected {label}: '{m.group(0)}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation=fix,
                    )
                )

        # 3. Sycophantic Flares
        for pattern, label, fix in SYCOPHANCY_PATTERNS:
            matches = list(re.finditer(pattern, line_clean, re.IGNORECASE))
            for m in matches:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Sycophancy",
                        message=f"Detected {label}: '{m.group(0)}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation=fix,
                    )
                )

        # 4. AI Tells
        for pattern, label, fix in AI_TELLS:
            matches = list(re.finditer(pattern, line_clean, re.IGNORECASE))
            for m in matches:
                violations.append(
                    Violation(
                        stage=1,
                        rule="AI Tell",
                        message=f"Detected {label}: '{m.group(0)}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation=fix,
                    )
                )

        # 4b. Domain Laundry List Throat-Clearing (e.g. "In computing, architecture, mathematics, and engineering...")
        m_domain = re.search(
            r"^\s*In\s+([a-zA-Z\s]{3,25}),\s+([a-zA-Z\s]{3,25}),\s+(?:[a-zA-Z\s]{3,25},\s+)*and\s+([a-zA-Z\s]{3,25}),",
            line_clean,
            re.IGNORECASE,
        )
        if m_domain:
            domain_keywords = {
                "computing",
                "software",
                "systems",
                "architecture",
                "engineering",
                "mathematics",
                "math",
                "computer science",
                "hardware",
                "networking",
                "data science",
                "machine learning",
                "distributed systems",
                "database systems",
            }
            matched_text = m_domain.group(0).lower()
            found_domains = sum(1 for kw in domain_keywords if kw in matched_text)
            if found_domains >= 2:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Domain Laundry List (Throat-Clearing)",
                        message=f"Domain laundry list used to manufacture scope: '{m_domain.group(0).strip()}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation="Cut the domain list; state the technical fact directly in its relevant context.",
                    )
                )

        # 5. Tailing Clauses
        for pattern, label, fix in TAILING_CLAUSES:
            matches = list(re.finditer(pattern, line_clean, re.IGNORECASE))
            for m in matches:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Tailing Participial Clause",
                        message=f"Detected dangling {label}: '{m.group(0)}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation=fix,
                    )
                )

        # 6. Light-Verb Nominals
        for pattern, label, fix in LIGHT_VERB_NOMINALS:
            matches = list(re.finditer(pattern, line_clean, re.IGNORECASE))
            for m in matches:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Light Verb Nominal",
                        message=f"Smothered verb in {label}: '{m.group(0)}'",
                        line=line_idx,
                        snippet=line.strip(),
                        recommendation=fix,
                    )
                )

        # 7. Knuth Micro-Syntax: Sentence-initial math/variable/code symbols
        line_sentences = extract_sentences(line)
        for s_idx, s in enumerate(line_sentences):
            st = s.strip()
            # Skip bullet list glossary/parameter definitions like "- `param`: description" on first item
            if s_idx == 0 and line.strip().startswith(
                ("-", "*", "+", "1.", "2.", "3.", "4.", ">", "#", "|")
            ):
                continue
            m_math = re.match(r"^(\$[^\$]+\$)(?:\s+|$)", st)
            m_code = re.match(r"^(`[^`]+`)(?:\s+|$)", st)
            sym = m_math.group(1) if m_math else (m_code.group(1) if m_code else None)
            if sym:
                violations.append(
                    Violation(
                        stage=1,
                        rule="Knuth Micro-Syntax (Initial Symbol)",
                        message=f"Sentence begins with raw mathematical symbol or code token: '{sym}'.",
                        line=line_idx,
                        snippet=st[:60] + ("..." if len(st) > 60 else ""),
                        recommendation="Prefix with governing noun: 'The variable x...', 'The function `foo()`...'",
                    )
                )

        # 8. Knuth Micro-Syntax: Adjacent formulas without intervening words
        adj_formula = re.search(
            r"\$[^\$]+\$(?:,\s*|\s+)\$[^\$]+\$(?!\s*,\s*(?:and|or)\b|\s+(?:and|or)\b)",
            line,
        )
        if adj_formula:
            violations.append(
                Violation(
                    stage=1,
                    rule="Knuth Micro-Syntax (Formula Clumping)",
                    message=f"Adjacent mathematical formulas without intervening words: '{adj_formula.group(0)}'",
                    line=line_idx,
                    snippet=line.strip(),
                    recommendation="Separate with English words: 'where q < p', not '$S_q, q < p$'.",
                )
            )

        # 9. Logic symbols in prose text
        logic_symbol = re.search(
            r"(?:\\forall|\\exists|\\Rightarrow|\\therefore|\\iff|\\implies)\b|[∀∃⇒∴⇔]",
            line_clean,
        )
        if logic_symbol:
            violations.append(
                Violation(
                    stage=1,
                    rule="Knuth Micro-Syntax (Logic Symbol in Prose)",
                    message=f"Logic symbol '{logic_symbol.group(0)}' used directly in running text.",
                    line=line_idx,
                    snippet=line.strip(),
                    recommendation="Use English words ('for all', 'there exists', 'implies', 'therefore').",
                )
            )


def audit_stage2_tolerance_bands(
    text: str,
    prose: str,
    sentences: list[str],
    words: list[str],
    profile: ProfileConfig,
    metrics: QualityMetrics,
    violations: list[Violation],
) -> None:
    """Audits Stage 2: Multi-metric tolerance bands (burstiness, overhead, nominals, anchoring)."""
    metrics.total_words = len(words)
    metrics.total_sentences = len(sentences)

    if metrics.total_words == 0 or metrics.total_sentences == 0:
        return

    # 1. Burstiness (Sentence Length Coefficient of Variation)
    sentence_lens = [
        len(tokenize_words(s)) for s in sentences if len(tokenize_words(s)) > 0
    ]
    if sentence_lens:
        metrics.mean_sentence_length = statistics.mean(sentence_lens)
        metrics.sentence_length_std = (
            statistics.stdev(sentence_lens) if len(sentence_lens) > 1 else 0.0
        )
        if metrics.mean_sentence_length > 0:
            metrics.burstiness_cv = (
                metrics.sentence_length_std / metrics.mean_sentence_length
            )

    if len(sentences) >= 4:
        if metrics.burstiness_cv < profile.target_burstiness_min:
            violations.append(
                Violation(
                    stage=2,
                    rule="Low Burstiness (Metronomic Uniformity)",
                    message=f"Sentence length CV ({metrics.burstiness_cv:.3f}) is below minimum {profile.target_burstiness_min}.",
                    line=None,
                    snippet=f"Mean sentence length: {metrics.mean_sentence_length:.1f} words (std: {metrics.sentence_length_std:.1f})",
                    recommendation="Vary sentence length aggressively. Mix short punchy statements (3-6 words) with compound sentences.",
                )
            )
        elif metrics.burstiness_cv > profile.target_burstiness_max:
            violations.append(
                Violation(
                    stage=2,
                    rule="Excessive Burstiness (Fragmented / Run-On)",
                    message=f"Sentence length CV ({metrics.burstiness_cv:.3f}) exceeds maximum {profile.target_burstiness_max}.",
                    line=None,
                    snippet=f"Mean sentence length: {metrics.mean_sentence_length:.1f} words (std: {metrics.sentence_length_std:.1f})",
                    recommendation="Rebalance sentences; break run-on sentences and unify fragmented dependent clauses.",
                )
            )

    # 2. Syntactic Overhead (Subject-Verb Distance & Prepositional Depth)
    # Estimate SVD & PPD from clausal structure
    svd_estimates = []
    ppd_max = 0
    for s in sentences:
        # Prepositional chaining count: of, in, to, for, with, on, at, by, from
        prep_matches = re.findall(
            r"\b(?:of|in|to|for|with|on|at|by|from)\s+[a-z0-9_-]+(?:\s+[a-z0-9_-]+){0,3}",
            s,
            re.IGNORECASE,
        )
        if prep_matches:
            ppd_max = max(ppd_max, len(prep_matches))
        # Estimate SVD from words between subject head and verb
        sub_verb = re.search(
            r"^[A-Z][a-z0-9_-]+\s+(?:(?:of|in|for|with)\s+[a-z0-9_-]+\s+)*([a-z0-9_-]+)\s+(?:is|are|was|were|has|have|had|[a-z]+s)\b",
            s,
        )
        if sub_verb:
            svd_estimates.append(len(sub_verb.group(0).split()))
        else:
            svd_estimates.append(2.0)

    mean_svd = statistics.mean(svd_estimates) if svd_estimates else 2.0
    metrics.syntactic_overhead = round(0.6 * mean_svd + 0.8 * min(ppd_max, 6) + 1.0, 2)

    if (
        metrics.syntactic_overhead > profile.max_syntactic_overhead
        and len(sentences) >= 3
    ):
        violations.append(
            Violation(
                stage=2,
                rule="Syntactic Memory Overhead (DLT Violation)",
                message=f"Syntactic overhead ({metrics.syntactic_overhead:.2f}) exceeds profile limit ({profile.max_syntactic_overhead}).",
                line=None,
                snippet=f"Mean SVD: {mean_svd:.1f}, Max PPD: {ppd_max}",
                recommendation="Shorten distance between grammatical subject and finite verb. Eliminate prepositional chains.",
            )
        )

    # 3. Zombie Nominalizations (excluding valid domain nouns)
    nominals = [w for w in words if is_zombie_nominal(w)]

    metrics.zombie_nominals_count = len(nominals)
    metrics.zombie_nominals_pct = round((len(nominals) / metrics.total_words) * 100, 2)

    if metrics.zombie_nominals_pct > profile.max_zombie_nominals_pct:
        sample_noms = list(set(nominals))[:5]
        violations.append(
            Violation(
                stage=2,
                rule="Excessive Zombie Nominals",
                message=f"Zombie nominal density ({metrics.zombie_nominals_pct:.2f}%) exceeds profile limit ({profile.max_zombie_nominals_pct}%). Found: {sample_noms}",
                line=None,
                snippet=f"{len(nominals)} nominals across {metrics.total_words} words",
                recommendation="Convert bureaucratic nouns into active verbs and concrete actors.",
            )
        )

    # 4. Em-Dash Overuse & Punctuation Balance
    cleaned_prose = re.sub(r"https?://\S+", " ", prose)
    cleaned_prose = re.sub(r"`[^`]+`", " ", cleaned_prose)
    unicode_em = len(re.findall(r"—", prose))
    ascii_em = len(
        re.findall(
            r"(?<=[a-zA-Z0-9,;\"'])\s*--\s*(?=[a-zA-Z0-9\"'])|\s+--\s+",
            prose,
        )
    )
    em_dashes = unicode_em + ascii_em
    colons = len(re.findall(r"(?<!:):(?!:)", cleaned_prose))
    semicolons = len(re.findall(r";", cleaned_prose))
    metrics.em_dashes_count = em_dashes
    metrics.colons_count = colons
    metrics.semicolons_count = semicolons
    metrics.em_dashes_per_100w = round((em_dashes / metrics.total_words) * 100, 2)
    metrics.punctuation_balance_ratio = round(
        (colons + semicolons) / (em_dashes + 1), 2
    )

    if metrics.em_dashes_per_100w > profile.max_em_dashes_per_100w and (
        metrics.total_words >= 50 or em_dashes >= 2
    ):
        violations.append(
            Violation(
                stage=2,
                rule="Em-Dash Saturation",
                message=f"Em-dash rate ({metrics.em_dashes_per_100w:.2f}/100w) exceeds limit ({profile.max_em_dashes_per_100w}/100w).",
                line=None,
                snippet=f"{em_dashes} em-dashes found",
                recommendation="Replace em-dashes with semicolons, parentheses, or periods.",
            )
        )

    if (
        metrics.punctuation_balance_ratio < profile.min_punctuation_balance
        and em_dashes >= 3
    ):
        violations.append(
            Violation(
                stage=2,
                rule="Punctuation Imbalance",
                message=f"Punctuation balance ratio ({metrics.punctuation_balance_ratio:.2f}) is below minimum ({profile.min_punctuation_balance}).",
                line=None,
                snippet=f"{colons} colons, {semicolons} semicolons vs {em_dashes} em-dashes",
                recommendation="Meter complex clauses with colons and semicolons rather than breathy em-dashes.",
            )
        )

    # 5. Demonstrative Anchoring Index (DAI)
    this_total = 0
    this_anchored = 0
    # Search for sentence-initial This/These
    for s in sentences:
        m = re.match(
            r"^\s*([Tt]his|[Tt]hese)\b(?:\s+([a-zA-Z0-9_-]+)|([,\.;:—–-]))?", s
        )
        if m:
            this_total += 1
            follower = m.group(2)
            punct = m.group(3)
            # If punctuation follows immediately (e.g. "This, in turn..."), it is unanchored
            if punct:
                pass
            elif follower and follower.lower() not in UNANCHORED_THIS_FOLLOWERS:
                this_anchored += 1

    metrics.sentence_initial_this_total = this_total
    metrics.sentence_initial_this_anchored = this_anchored
    if this_total > 0:
        metrics.demonstrative_anchoring_index = round(this_anchored / this_total, 2)
    else:
        metrics.demonstrative_anchoring_index = 1.0

    if (
        this_total >= 2
        and metrics.demonstrative_anchoring_index < profile.min_demonstrative_anchoring
    ):
        violations.append(
            Violation(
                stage=2,
                rule="Unanchored Demonstrative Pronouns",
                message=f"Demonstrative Anchoring Index ({metrics.demonstrative_anchoring_index:.2f}) is below target ({profile.min_demonstrative_anchoring}).",
                line=None,
                snippet=f"{this_anchored}/{this_total} sentence-initial 'This/These' are anchored to explicit nouns.",
                recommendation="Always attach a concrete governing noun: 'This invariant...', 'This latency...', 'This result...'",
            )
        )

    # 6. Contrastive Reframes Analysis (Information Gain)
    prose_clean = re.sub(r"`[^`]+`", " ", prose)
    reframes = re.findall(
        r"\b(?:it(?:'s|\s+is)?\s+not\s+(?:just|merely|simply|only|about)?|are\s+not\s+(?:just|merely|simply|only|about)?|is\s+not\s+(?:just|merely|simply|only|about)?|not\s+(?:just|merely|simply|only|about)|does\s+not\s+guarantee|doesn't\s+guarantee)\b(.*?)\b(?:but\s+(?:also|rather|instead)?|rather|instead|it(?:'s|\s+is)\s+about|it\s+guarantees|;\s*(?:they\s+are|it\s+is|rather|instead))\b(.*?)(?:[.;\n]|$)",
        prose_clean,
        re.IGNORECASE,
    )
    metrics.contrastive_reframes_count = len(reframes)
    for x_clause, y_clause in reframes:
        # Check if X is a trivial strawman
        trivial_patterns = [
            r"\btyping\b",
            r"\bstaring\b",
            r"\bsimple\b",
            r"\bjust\b",
            r"\braw speed\b",
            r"\bluck\b",
            r"\bmagic\b",
            r"\bdrawing boxes\b",
            r"\bmemorizing\b",
            r"\bwriting lines of code\b",
            r"\bdecorative\b",
            r"\bornament(?:ation)?\b",
            r"\bdecoration\b",
            r"\bfancy\b",
            r"\bfluff\b",
        ]
        is_trivial = any(
            re.search(pat, x_clause, re.IGNORECASE) for pat in trivial_patterns
        )
        if is_trivial:
            violations.append(
                Violation(
                    stage=2,
                    rule="Low-Information Contrastive Strawman",
                    message="Detected trivial contrastive reframe ('Not X, but Y') with zero information gain.",
                    line=None,
                    snippet=f"Clause X: '{x_clause.strip()}' -> Clause Y: '{y_clause.strip()}'",
                    recommendation="Cut the 'Not X' strawman and state assertion Y directly.",
                )
            )

    # 7. Concrete Anchor Lag (Tutorial profile)
    if profile.max_concrete_anchor_lag_words is not None:
        metrics.concrete_anchor_lag_words = compute_anchor_lag(text.splitlines())
        if (
            metrics.concrete_anchor_lag_words is not None
            and metrics.concrete_anchor_lag_words
            > profile.max_concrete_anchor_lag_words
        ):
            violations.append(
                Violation(
                    stage=2,
                    rule="Delayed Concrete Anchor",
                    message=f"Concrete anchor lag ({metrics.concrete_anchor_lag_words} words) exceeds profile limit ({profile.max_concrete_anchor_lag_words} words).",
                    line=None,
                    snippet="Preamble length before first code fence or table",
                    recommendation=f"Introduce a concrete code example or data schema within the first {profile.max_concrete_anchor_lag_words} words.",
                )
            )


def audit_stage3_composite_scoring(
    profile: ProfileConfig, metrics: QualityMetrics, violations: list[Violation]
) -> None:
    """Audits Stage 3: Composite Index (HVI & TPI) and overall pass/fail determination."""
    hvi = 100.0
    tpi = 100.0

    # Stage 1 penalty
    stage1_count = sum(1 for v in violations if v.stage == 1)
    if stage1_count > 0:
        hvi -= stage1_count * 15.0

    # Stage 2 penalties
    # Burstiness penalty
    if metrics.burstiness_cv < profile.target_burstiness_min:
        delta = profile.target_burstiness_min - metrics.burstiness_cv
        hvi -= min(25.0, delta * 80.0)

    # Zombie nominal penalty
    if metrics.zombie_nominals_pct > profile.max_zombie_nominals_pct:
        delta_nom = metrics.zombie_nominals_pct - profile.max_zombie_nominals_pct
        hvi -= min(20.0, delta_nom * 10.0)
        tpi -= min(15.0, delta_nom * 5.0)

    # Em-dash penalty
    if metrics.em_dashes_per_100w > profile.max_em_dashes_per_100w:
        hvi -= 10.0

    # Demonstrative anchoring penalty
    if metrics.demonstrative_anchoring_index < profile.min_demonstrative_anchoring:
        delta_dai = (
            profile.min_demonstrative_anchoring - metrics.demonstrative_anchoring_index
        )
        hvi -= delta_dai * 30.0

    # Syntactic overhead penalty
    if metrics.syntactic_overhead > profile.max_syntactic_overhead:
        tpi -= 15.0

    metrics.human_voice_index = max(0.0, round(hvi, 1))
    metrics.technical_precision_index = max(0.0, round(tpi, 1))

    if metrics.human_voice_index < profile.min_hvi:
        violations.append(
            Violation(
                stage=3,
                rule="Low Human Voice Index",
                message=f"Human Voice Index ({metrics.human_voice_index:.1f}) is below minimum {profile.min_hvi}.",
                line=None,
                snippet="Composite voice score failed",
                recommendation="Address Stage 1 and Stage 2 violations to recover authentic human cadence.",
            )
        )

    if metrics.technical_precision_index < profile.min_tpi:
        violations.append(
            Violation(
                stage=3,
                rule="Low Technical Precision Index",
                message=f"Technical Precision Index ({metrics.technical_precision_index:.1f}) is below minimum {profile.min_tpi}.",
                line=None,
                snippet="Composite precision score failed",
                recommendation="Ground assertions in exact domain primitives and concrete physical referents.",
            )
        )


def audit_document(text: str, profile_name: str = "essay") -> AuditReport:
    """Executes the complete 3-stage audit on the target text."""
    if profile_name not in PROFILES:
        raise ValueError(
            f"Unknown profile '{profile_name}'. Available: {list(PROFILES.keys())}"
        )

    profile = PROFILES[profile_name]
    lines, prose, prose_lines = split_into_lines_and_prose(text)
    words = tokenize_words(prose)
    sentences = extract_sentences(prose)

    violations: list[Violation] = []
    metrics = QualityMetrics()

    # Stage 1: Fast-fail hard invariants
    audit_stage1_hard_invariants(text, lines, prose_lines, violations)

    # Stage 2: Multi-metric tolerance bands
    audit_stage2_tolerance_bands(
        text, prose, sentences, words, profile, metrics, violations
    )

    # Stage 3: Composite scoring
    audit_stage3_composite_scoring(profile, metrics, violations)

    passed = len(violations) == 0
    return AuditReport(
        profile=profile_name, passed=passed, metrics=metrics, violations=violations
    )


# ==============================================================================
# 6. Terminal Presentation & CLI Interface
# ==============================================================================


def format_terminal_report(
    report: AuditReport, show_fix_hints: bool = True, verbose: bool = False
) -> str:
    """Formats the audit report for human terminal inspection with ANSI colors."""
    lines: list[str] = []
    status_icon = "🟢" if report.passed else "🔴"
    status_text = "PASSED" if report.passed else "FAILED"

    lines.append("=" * 76)
    lines.append(
        f"  NLP QUALITY GATE: {status_icon} {status_text} (Profile: {report.profile.upper()})"
    )
    lines.append("=" * 76)

    m = report.metrics
    lines.append(
        f"• Words: {m.total_words} | Sentences: {m.total_sentences} | Mean Sentence Length: {m.mean_sentence_length:.1f}w"
    )
    lines.append(
        f"• Burstiness CV: {m.burstiness_cv:.3f} | Syntactic Overhead: {m.syntactic_overhead:.2f}"
    )
    lines.append(
        f"• Zombie Nominals: {m.zombie_nominals_pct:.2f}% ({m.zombie_nominals_count} words)"
    )
    lines.append(
        f"• Demonstrative Anchoring (DAI): {m.demonstrative_anchoring_index:.2f} ({m.sentence_initial_this_anchored}/{m.sentence_initial_this_total})"
    )
    lines.append(
        f"• Em-Dashes: {m.em_dashes_per_100w:.2f}/100w | Punctuation Balance (PBR): {m.punctuation_balance_ratio:.2f}"
    )
    if m.concrete_anchor_lag_words is not None:
        lines.append(f"• Concrete Anchor Lag: {m.concrete_anchor_lag_words} words")
    lines.append(
        f"• Composite Scores: Human Voice Index (HVI) = {m.human_voice_index:.1f} | Technical Precision (TPI) = {m.technical_precision_index:.1f}"
    )
    lines.append("-" * 76)

    if report.violations:
        lines.append(f"VIOLATIONS DETECTED ({len(report.violations)}):")
        for idx, v in enumerate(report.violations, start=1):
            loc = f"Line {v.line}" if v.line else "Document Scope"
            lines.append(f"\n[{idx}] Stage {v.stage} - {v.rule} ({loc})")
            lines.append(f"    Message: {v.message}")
            if v.snippet:
                lines.append(f'    Context: "{v.snippet}"')
            if show_fix_hints and v.recommendation:
                lines.append(f"    💡 Fix:  {v.recommendation}")
    else:
        lines.append(
            "✨ All Stage 1, Stage 2, and Stage 3 quality gates satisfied cleanly."
        )

    lines.append("=" * 76)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Deterministic 3-Stage NLP Quality Gate for Technical Prose.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "file",
        nargs="?",
        default="-",
        help="Path to markdown/text file to audit (defaults to stdin).",
    )
    parser.add_argument(
        "--profile",
        "-p",
        choices=list(PROFILES.keys()),
        default="essay",
        help="Target writing profile band (default: essay).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON for automated agent loops and CI pipelines.",
    )
    parser.add_argument(
        "--fix-hints",
        action="store_true",
        default=True,
        help="Show actionable fix recommendations for each violation (default: true).",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Display extended diagnostic details.",
    )

    args = parser.parse_args()

    # Read content from file or stdin
    if args.file == "-":
        content = sys.stdin.read()
    else:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}", file=sys.stderr)
            return 2
        content = file_path.read_text(encoding="utf-8")

    report = audit_document(content, profile_name=args.profile)

    if args.json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print(
            format_terminal_report(
                report, show_fix_hints=args.fix_hints, verbose=args.verbose
            )
        )

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
