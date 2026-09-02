"""Text normalization and recognition metrics for OCR analysis."""

import unicodedata


def normalize_ocr_text(text: str) -> str:
    """Normalize Unicode form, case, and whitespace for OCR comparison."""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(character for character in normalized if not character.isspace())


def levenshtein_distance(reference: str, hypothesis: str) -> int:
    """Return character-level Levenshtein edit distance."""
    if len(reference) < len(hypothesis):
        reference, hypothesis = hypothesis, reference
    previous = list(range(len(hypothesis) + 1))

    for reference_index, reference_character in enumerate(reference, start=1):
        current = [reference_index]
        for hypothesis_index, hypothesis_character in enumerate(hypothesis, start=1):
            insertion = current[hypothesis_index - 1] + 1
            deletion = previous[hypothesis_index] + 1
            substitution = previous[hypothesis_index - 1] + (
                reference_character != hypothesis_character
            )
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def character_error_rate(reference: str, hypothesis: str) -> float:
    """Return CER after OCR text normalization."""
    normalized_reference = normalize_ocr_text(reference)
    normalized_hypothesis = normalize_ocr_text(hypothesis)
    if not normalized_reference:
        return 0.0 if not normalized_hypothesis else 1.0
    return levenshtein_distance(normalized_reference, normalized_hypothesis) / len(
        normalized_reference
    )


def text_similarity(reference: str, hypothesis: str) -> float:
    """Return normalized edit similarity in the inclusive range [0, 1]."""
    normalized_reference = normalize_ocr_text(reference)
    normalized_hypothesis = normalize_ocr_text(hypothesis)
    length = max(len(normalized_reference), len(normalized_hypothesis))
    if length == 0:
        return 1.0
    return 1.0 - (
        levenshtein_distance(normalized_reference, normalized_hypothesis) / length
    )


def normalized_texts_match(reference: str, hypothesis: str) -> bool:
    """Return whether two texts are exact after OCR normalization."""
    return normalize_ocr_text(reference) == normalize_ocr_text(hypothesis)
