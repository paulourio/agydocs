package gate

// ProfileConfig defines the tolerance bands and scoring thresholds for a specific prose style.
type ProfileConfig struct {
	Name                      string  `json:"name"`
	Description               string  `json:"description"`
	TargetBurstinessMin       float64 `json:"target_burstiness_min"`
	TargetBurstinessMax       float64 `json:"target_burstiness_max"`
	MaxSyntacticOverhead      float64 `json:"max_syntactic_overhead"`
	MaxZombieNominalsPct      float64 `json:"max_zombie_nominals_pct"`
	MaxEmDashesPer100w        float64 `json:"max_em_dashes_per_100w"`
	MinPunctuationBalance     float64 `json:"min_punctuation_balance"`
	MinDemonstrativeAnchoring float64 `json:"min_demonstrative_anchoring"`
	MaxConcreteAnchorLagWords *int    `json:"max_concrete_anchor_lag_words"`
	MinHVI                    float64 `json:"min_hvi"`
	MinTPI                    float64 `json:"min_tpi"`
}

// Violation represents an individual gate violation detected in prose.
type Violation struct {
	Stage          int    `json:"stage"`
	Rule           string `json:"rule"`
	Message        string `json:"message"`
	Line           *int   `json:"line"`
	Snippet        string `json:"snippet"`
	Recommendation string `json:"recommendation"`
}

// QualityMetrics contains all quantitative measurements computed during audit.
type QualityMetrics struct {
	TotalWords                  int     `json:"total_words"`
	TotalSentences              int     `json:"total_sentences"`
	MeanSentenceLength          float64 `json:"mean_sentence_length"`
	SentenceLengthStd           float64 `json:"sentence_length_std"`
	BurstinessCV                float64 `json:"burstiness_cv"`
	SyntacticOverhead           float64 `json:"syntactic_overhead"`
	ZombieNominalsCount         int     `json:"zombie_nominals_count"`
	ZombieNominalsPct           float64 `json:"zombie_nominals_pct"`
	EmDashesCount               int     `json:"em_dashes_count"`
	EmDashesPer100w             float64 `json:"em_dashes_per_100w"`
	ColonsCount                 int     `json:"colons_count"`
	SemicolonsCount             int     `json:"semicolons_count"`
	PunctuationBalanceRatio     float64 `json:"punctuation_balance_ratio"`
	SentenceInitialThisTotal    int     `json:"sentence_initial_this_total"`
	SentenceInitialThisAnchored int     `json:"sentence_initial_this_anchored"`
	DemonstrativeAnchoringIndex float64 `json:"demonstrative_anchoring_index"`
	ContrastiveReframesCount    int     `json:"contrastive_reframes_count"`
	ConcreteAnchorLagWords      *int    `json:"concrete_anchor_lag_words"`
	HumanVoiceIndex             float64 `json:"human_voice_index"`
	TechnicalPrecisionIndex     float64 `json:"technical_precision_index"`
}

// AuditReport aggregates profile configuration, pass/fail status, metrics, and violations.
type AuditReport struct {
	Profile    string         `json:"profile"`
	Passed     bool           `json:"passed"`
	Metrics    QualityMetrics `json:"metrics"`
	Violations []Violation    `json:"violations"`
}

func intPtr(i int) *int {
	return &i
}

// Profiles contains the pre-configured tolerance bands for all supported styles.
var Profiles = map[string]ProfileConfig{
	"rfc": {
		Name:                      "rfc",
		Description:               "Systems Specifications, RFCs, Architecture Decision Records (ADRs)",
		TargetBurstinessMin:       0.32,
		TargetBurstinessMax:       0.65,
		MaxSyntacticOverhead:      6.5,
		MaxZombieNominalsPct:      1.5,
		MaxEmDashesPer100w:        0.20,
		MinPunctuationBalance:     1.5,
		MinDemonstrativeAnchoring: 0.80,
		MaxConcreteAnchorLagWords: intPtr(200),
		MinHVI:                    80.0,
		MinTPI:                    85.0,
	},
	"paper": {
		Name:                      "paper",
		Description:               "Scientific Papers, Algorithmic Analysis, Formal Research",
		TargetBurstinessMin:       0.40,
		TargetBurstinessMax:       0.70,
		MaxSyntacticOverhead:      6.5,
		MaxZombieNominalsPct:      2.0,
		MaxEmDashesPer100w:        0.15,
		MinPunctuationBalance:     2.0,
		MinDemonstrativeAnchoring: 0.85,
		MaxConcreteAnchorLagWords: intPtr(300),
		MinHVI:                    85.0,
		MinTPI:                    85.0,
	},
	"essay": {
		Name:                      "essay",
		Description:               "Technical Architecture Essays & Deep Dives",
		TargetBurstinessMin:       0.38,
		TargetBurstinessMax:       0.70,
		MaxSyntacticOverhead:      5.5,
		MaxZombieNominalsPct:      1.0,
		MaxEmDashesPer100w:        0.25,
		MinPunctuationBalance:     1.5,
		MinDemonstrativeAnchoring: 0.80,
		MaxConcreteAnchorLagWords: intPtr(250),
		MinHVI:                    85.0,
		MinTPI:                    80.0,
	},
	"tutorial": {
		Name:                      "tutorial",
		Description:               "Developer Guides, Onboarding Walkthroughs & API Tutorials",
		TargetBurstinessMin:       0.30,
		TargetBurstinessMax:       0.60,
		MaxSyntacticOverhead:      4.5,
		MaxZombieNominalsPct:      0.8,
		MaxEmDashesPer100w:        0.15,
		MinPunctuationBalance:     1.0,
		MinDemonstrativeAnchoring: 0.75,
		MaxConcreteAnchorLagWords: intPtr(150),
		MinHVI:                    80.0,
		MinTPI:                    75.0,
	},
	"chat": {
		Name:                      "chat",
		Description:               "Interactive Agent Pairing, CLI Diagnostics & Code Reviews",
		TargetBurstinessMin:       0.30,
		TargetBurstinessMax:       0.75,
		MaxSyntacticOverhead:      4.0,
		MaxZombieNominalsPct:      1.0,
		MaxEmDashesPer100w:        0.10,
		MinPunctuationBalance:     1.0,
		MinDemonstrativeAnchoring: 0.85,
		MaxConcreteAnchorLagWords: nil,
		MinHVI:                    85.0,
		MinTPI:                    80.0,
	},
	"briefing": {
		Name:                      "briefing",
		Description:               "Executive Summaries & Technical Briefings",
		TargetBurstinessMin:       0.35,
		TargetBurstinessMax:       0.65,
		MaxSyntacticOverhead:      4.5,
		MaxZombieNominalsPct:      1.0,
		MaxEmDashesPer100w:        0.10,
		MinPunctuationBalance:     1.5,
		MinDemonstrativeAnchoring: 0.85,
		MaxConcreteAnchorLagWords: nil,
		MinHVI:                    80.0,
		MinTPI:                    80.0,
	},
}
