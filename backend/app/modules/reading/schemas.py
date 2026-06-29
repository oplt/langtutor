from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.app.modules.translation.schemas import TranslationOut

InterestArea = Literal[
    "news",
    "sports",
    "technology",
    "science",
    "business",
    "arts",
    "culture",
    "travel",
    "health",
    "environment",
    "history",
    "daily_life",
]

SourceMode = Literal["online", "generated"]
Strictness = Literal["strict", "balanced", "natural"]
AdaptationMode = Literal["llm", "rules", "raw"]
TranslationMode = Literal["none", "full", "sentence_by_sentence"]

LEVEL_MAX_RANK: dict[int, int] = {
    1: 500,
    2: 1000,
    3: 2000,
    4: 3000,
    5: 4000,
    6: 5000,
}


class ReadingGenerateIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    language: Literal["nl"] = "nl"
    level: int = Field(ge=1, le=6)
    max_frequency_rank: int = Field(default=2000, ge=500, le=5000, alias="maxFrequencyRank")
    interest_area: InterestArea = Field(alias="interestArea")
    word_count: int = Field(default=500, ge=100, le=1500, alias="wordCount")
    source_mode: SourceMode = Field(default="online", alias="sourceMode")
    strictness: Strictness = "balanced"
    translation_mode: TranslationMode = Field(default="full", alias="translationMode")

    @model_validator(mode="after")
    def normalize_rank_for_level(self):
        # The frequency rank is derived from level. Keeping the field in the API
        # is useful for clients, but the backend must not trust mismatched input.
        self.max_frequency_rank = LEVEL_MAX_RANK[self.level]
        return self


class ReadingSourceOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str = ""
    url: str = ""
    publisher: str = ""
    published_at: str = Field(default="", alias="publishedAt")


class ReadingCoverageOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    total_words: int = Field(alias="totalWords")
    allowed_words: int = Field(alias="allowedWords")
    unknown_words: int = Field(alias="unknownWords")
    coverage_percent: float = Field(alias="coveragePercent")
    unknown_word_list: list[str] = Field(default_factory=list, alias="unknownWordList")
    proper_nouns: list[str] = Field(default_factory=list, alias="properNouns")
    acronyms: list[str] = Field(default_factory=list)


class ReadingReplacementOut(BaseModel):
    original: str
    replacement: str
    reason: str = ""


class ReadingGlossaryEntryOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    word: str
    meaning: str = ""
    definition: str = ""
    example_sentence: str = Field(default="", alias="exampleSentence")
    reason_kept: str = Field(default="", alias="reasonKept")


class ReadingQuizQuestionOut(BaseModel):
    type: str = "multiple_choice"
    question: str
    options: list[str] = Field(default_factory=list)
    answer: str


class SentenceTranslationOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_sentence: str = Field(alias="sourceSentence")
    translated_sentence: str = Field(alias="translatedSentence")


class ReadingGenerateOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    adapted_text: str = Field(alias="adaptedText")
    translated_text: str | None = Field(default=None, alias="translatedText")
    translation: TranslationOut | None = None
    sentence_translations: list[SentenceTranslationOut] = Field(default_factory=list, alias="sentenceTranslations")
    summary: str = ""
    source: ReadingSourceOut
    level: int
    max_frequency_rank: int = Field(alias="maxFrequencyRank")
    word_count_requested: int = Field(alias="wordCountRequested")
    word_count_actual: int = Field(alias="wordCountActual")
    coverage: ReadingCoverageOut
    pre_coverage: ReadingCoverageOut | None = Field(default=None, alias="preCoverage")
    replacements: list[ReadingReplacementOut] = Field(default_factory=list)
    glossary: list[ReadingGlossaryEntryOut] = Field(default_factory=list)
    quiz: list[ReadingQuizQuestionOut] = Field(default_factory=list)
    source_mode: SourceMode = Field(alias="sourceMode")
    strictness: Strictness
    interest_area: InterestArea = Field(alias="interestArea")
    translation_mode: TranslationMode = Field(default="none", alias="translationMode")
    adaptation_mode: AdaptationMode = Field(default="raw", alias="adaptationMode")
    warnings: list[str] = Field(default_factory=list)
    target_coverage_percent: float = Field(default=0, alias="targetCoveragePercent")
    unknown_words: list[str] = Field(default_factory=list, alias="unknownWords")
    attempts: int = 1
    warning: str | None = None


class ReadingSaveIn(BaseModel):
    reading: ReadingGenerateOut


class ReadingSaveOut(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    saved_at: str = Field(alias="savedAt")
