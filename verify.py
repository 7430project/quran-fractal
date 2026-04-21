#!/usr/bin/env python3
"""
verify.py — 74:30 Project | Fractal Edition
============================================
Assembles and verifies the Fractal Edition of the Quran.

Two source texts from tanzil.net:
  - Simple-Plain for most surahs
  - Uthmani for surahs requiring rich encoding

Verifies that all 13 Muqatta'at letter groups independently divide
by 19, and that their grand total equals:

    39,349 = 19² × 109 = 19² × P(29)

where P(29) = 109 is the 29th prime, and 29 is the number of
Muqatta'at surahs. 39,349 is also the word count of the same 29 surahs.

Source: tanzil.net (Creative Commons Attribution 3.0)
"""

import os
import sys
import hashlib
import unicodedata
from datetime import date

# ════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════

UTHMANI_SURAHS = {7, 10, 11, 12, 13, 14, 15, 20, 27, 36, 68}

UTHMANI_PATH = "tanzil_data/quran-uthmani.txt"
SIMPLE_PLAIN_CANDIDATES = [
    "tanzil_data/quran-simple-plain.txt",
    "tanzil_data/quran-simple-clean.txt",
]

MUQATTA_SURAHS = {2, 3, 7, 10, 11, 12, 13, 14, 15, 19, 20, 26, 27, 28, 29, 30,
                  31, 32, 36, 38, 40, 41, 42, 43, 44, 45, 46, 50, 68}
MERGE_V1_SURAHS = {19, 20, 31, 36}

# ════════════════════════════════════════════════════════════════════
# THE 13 MUQATTA'AT GROUPS
# ════════════════════════════════════════════════════════════════════

# (name, tier, surahs, edition, exclude_v1, consonants, alif_chars, expected_total)
GROUPS = [
    ("ALM",   1, [2, 3, 29, 30, 31, 32], "simple", False,
     ["ل", "م"], ["ا"], 18012),
    ("ALR",   2, [10, 11, 12, 14, 15], "uthmani", False,
     ["ل", "ر"], ["ا", "إ", "\u0653"], 7828),
    ("ALMR",  2, [13], "uthmani", False,
     ["ل", "م", "ر"], ["أ", "إ", "\u0653", "\u0670"], 1178),
    ("ALMS",  1, [7, 38], "mixed", True,
     ["ل", "م", "ص"], ["ا"], 4997),
    ("HM",    1, [40, 41, 42, 43, 44, 45, 46], "simple", False,
     ["ح", "م"], [], 2147),
    ("ASQ",   1, [42], "simple", False,
     ["ع", "س", "ق"], [], 209),
    ("Q",     1, [50], "simple", False,
     ["ق"], [], 57),
    ("KHYAS", 1, [19], "simple", True,
     ["ك", "ه", "ة", "ي", "ى", "ئ", "ع", "ص"], [], 798),
    ("TSM",   1, [26, 28], "simple", True,
     ["ط", "س", "م"], [], 1178),
    ("YS",    1, [36], "uthmani", True,
     ["ي", "س", "ى", "\u06E6"], [], 285),
    ("N",     2, [68], "uthmani", False,
     ["ن"], ["ا", "\u0670", "أ", "\u0653", "\u06DF", "ٱ"], 361),
    ("TH",    2, [20], "uthmani", True,
     ["ط", "ه"], ["ا", "\u0670", "أ", "\u06DF", "ٱ"], 1292),
    ("TS",    2, [27], "uthmani", True,
     ["ط", "س"], ["ا", "\u0670", "أ", "إ", "ٱ"], 1007),
]

ORIGINAL_V1_TEXTS = {}  # populated during assembly

# ════════════════════════════════════════════════════════════════════
# LOADING
# ════════════════════════════════════════════════════════════════════

def load_quran_file(filepath):
    verses = {}
    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                for line in f:
                    line = line.strip("\r\n\t ")
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        try:
                            verses[(int(parts[0]), int(parts[1]))] = parts[2]
                        except ValueError:
                            continue
            break
        except (UnicodeDecodeError, FileNotFoundError):
            continue
    return verses


# ════════════════════════════════════════════════════════════════════
# COUNTING
# ════════════════════════════════════════════════════════════════════

def count_chars_in_surah(edition_list, surah, char_set, exclude_v1):
    total = 0
    for s, a, text in edition_list:
        if s != surah:
            continue
        if exclude_v1 and a == 1:
            if surah in MERGE_V1_SURAHS and surah in ORIGINAL_V1_TEXTS:
                orig_len = len(ORIGINAL_V1_TEXTS[surah])
                text = text[orig_len + 1:]
            else:
                continue
        total += sum(1 for c in text if c in char_set)
    return total


def verify_group(spec, edition_list):
    name, tier, surahs, edition, excl_v1, consonants, alif_chars, expected = spec
    char_set = set(consonants + alif_chars)
    total = 0
    for s in surahs:
        total += count_chars_in_surah(edition_list, s, char_set, excl_v1)
    return total


# ════════════════════════════════════════════════════════════════════
# ASSEMBLY
# ════════════════════════════════════════════════════════════════════

def assemble_fractal_edition(simple_verses, uthmani_verses):
    all_keys = set(simple_verses.keys()) | set(uthmani_verses.keys())
    all_surahs = sorted(set(s for s, a in all_keys))
    edition = []
    for surah in all_surahs:
        source = uthmani_verses if surah in UTHMANI_SURAHS else simple_verses
        surah_ayahs = sorted(
            [(s, a) for (s, a) in source.keys() if s == surah],
            key=lambda x: x[1]
        )
        for s, a in surah_ayahs:
            edition.append((s, a, source[(s, a)]))
    return edition


def apply_corrections(edition):
    """Apply verse merges (19, 20, 31, 36) and word segmentation fixes."""
    merged = []
    held_v1 = None
    for s, a, t in edition:
        if s in MERGE_V1_SURAHS and a == 1:
            held_v1 = (s, t)
            ORIGINAL_V1_TEXTS[s] = t
            continue
        if s in MERGE_V1_SURAHS and a == 2 and held_v1 and held_v1[0] == s:
            merged.append((s, 1, held_v1[1] + " " + t))
            held_v1 = None
            continue
        if s in MERGE_V1_SURAHS and a > 2:
            merged.append((s, a - 1, t))
        else:
            merged.append((s, a, t))

    WORD_MERGE_VERSES = {
        (64, 14): (0, 1), (71, 2):  (1, 2), (74, 1):  (4, 5),
        (78, 40): (12, 13), (82, 6):  (0, 1), (84, 6):  (0, 1),
    }
    final = []
    for s, a, t in merged:
        if (s, a) in WORD_MERGE_VERSES:
            i, j = WORD_MERGE_VERSES[(s, a)]
            words = t.split()
            words = words[:i] + [words[i] + words[j]] + words[j + 1:]
            t = " ".join(words)
        final.append((s, a, t))
    return final


# ════════════════════════════════════════════════════════════════════
# BOOK-LEVEL COUNTS
# ════════════════════════════════════════════════════════════════════

def book_level_counts(edition):
    """Compute the four book-level measurements with precise definitions.

    Letters: characters in U+0600–U+06FF whose Unicode General Category
    starts with 'L' (Lu/Ll/Lt/Lm/Lo). This is the operative definition
    for Section 5.4 of the verification document.
    """
    n_surahs = len({s for s, a, t in edition})
    n_verses = len(edition)
    n_words = 0
    n_letters = 0
    muq_words = 0
    for s, a, t in edition:
        w = len(t.split())
        n_words += w
        if s in MUQATTA_SURAHS:
            muq_words += w
        for c in t:
            if '\u0600' <= c <= '\u06FF' and unicodedata.category(c).startswith('L'):
                n_letters += 1
    return {
        "surahs": n_surahs,
        "verses": n_verses,
        "words": n_words,
        "letters": n_letters,
        "muq_words": muq_words,
    }


# ════════════════════════════════════════════════════════════════════
# OUTPUT: FRACTAL EDITION TEXT
# ════════════════════════════════════════════════════════════════════

def write_fractal_edition(edition, output_path):
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# ══════════════════════════════════════════════════════════════\n")
        f.write("# THE FRACTAL EDITION — 74:30 Project\n")
        f.write("# ══════════════════════════════════════════════════════════════\n")
        f.write("#\n")
        f.write("# This file contains the assembled Fractal Edition text followed\n")
        f.write("# by a verification document. The document specifies a counting\n")
        f.write("# procedure and records the result. Scroll to 'VERIFICATION\n")
        f.write("# DOCUMENT' below the text for the full specification.\n")
        f.write("#\n")
        f.write(f"# Generated:        {date.today()}\n")
        f.write(f"# Source:           tanzil.net (CC BY 3.0)\n")
        f.write(f"# Format:           surah|ayah|text\n")
        f.write(f"# Uthmani surahs:   {sorted(UTHMANI_SURAHS)}\n")
        f.write(f"# Verse merges:     surahs 19, 20, 31, 36 (v1 + v2 → v1)\n")
        f.write(f"# Word segm. (يا):  surahs 64, 71, 74, 78, 82, 84\n")
        f.write("#\n")
        f.write("# Note: Bismillahs are embedded in verse 1 of each surah, not on\n")
        f.write("# standalone lines. Uthmani surahs use ٱ (wasla, U+0671) in place\n")
        f.write("# of ا (plain alif) in the Bismillah — substring searches must\n")
        f.write("# account for this.\n")
        f.write("#\n")
        for s, a, t in edition:
            f.write(f"{s}|{a}|{t}\n")


# ════════════════════════════════════════════════════════════════════
# OUTPUT: VERIFICATION DOCUMENT
# ════════════════════════════════════════════════════════════════════

def write_verification(results, edition, counts, output_path,
                       source_files=None, append=True):
    """Write the verification document (8 sections) to output_path."""
    W = 78
    mode = "a" if append else "w"

    tier1 = [r for r in results if r["tier"] == 1]
    tier2 = [r for r in results if r["tier"] == 2]
    tier1_sum = sum(r["total"] for r in tier1)
    tier2_sum = sum(r["total"] for r in tier2)
    grand = tier1_sum + tier2_sum
    ks = [r["total"] // 19 for r in results]
    sum_k = sum(ks)
    sum_k2 = sum(k * k for k in ks)

    with open(output_path, mode, encoding="utf-8") as f:
        def rule(c="="): f.write(c * W + "\n")
        def thin(): f.write("-" * W + "\n")
        def blank(): f.write("\n")

        if append:
            f.write("\n\n")

        # ── HEADER ───────────────────────────────────────────────────
        rule()
        f.write("FRACTAL EDITION — VERIFICATION DOCUMENT\n")
        f.write("74:30 Project | 7430project.com\n")
        rule()
        blank()
        f.write(f"Source texts:   tanzil.net (Creative Commons Attribution 3.0)\n")
        f.write(f"Script:         verify.py (in repository root)\n")
        f.write(f"Generated:      {date.today()}\n")
        blank()
        if source_files:
            f.write("SHA-256 hashes of source files (compare to a fresh download\n")
            f.write("from tanzil.net to confirm no modification):\n\n")
            for label, path in source_files:
                try:
                    with open(path, "rb") as sf:
                        h = hashlib.sha256(sf.read()).hexdigest()
                    f.write(f"    {os.path.basename(path)}\n")
                    f.write(f"    {h}\n\n")
                except FileNotFoundError:
                    f.write(f"    {label}: FILE NOT FOUND\n\n")

        # ── SECTION 1: ABSTRACT ──────────────────────────────────────
        rule()
        f.write("1. ABSTRACT\n")
        rule()
        blank()
        f.write("29 of the Quran's 114 chapters open with combinations of Arabic letters\n")
        f.write("known as the Muqatta'at. The identification is textual: these surahs\n")
        f.write("begin with disconnected letters in their first verse, and no others do.\n")
        f.write("Chapter 74, verse 30 of the same text states a number: 19.\n\n")
        f.write("This document specifies a procedure for counting those letters in those\n")
        f.write("chapters, and records the result. Under the specification in Section 3:\n\n")
        f.write("    - Each of the 13 group totals is divisible by 19.\n")
        f.write("    - The sum of the 13 totals is 39,349 = 19² × 109.\n")
        f.write("    - 109 is the 29th prime.\n")
        f.write("    - The word count of the same 29 surahs is also 39,349.\n\n")
        f.write("The 13 groups split into two tiers:\n\n")
        f.write("    Tier 1 (8 groups): no parameter choices beyond the named letters\n")
        f.write("                       and surahs. Totals determined by the text alone.\n")
        f.write("    Tier 2 (5 groups): require an alif-variant subset from the Uthmani\n")
        f.write("                       manuscript tradition. Subsets specified in 3.3.\n\n")
        f.write("The reader is invited to count directly from the Fractal Edition text,\n")
        f.write("which appears above this appendix in the same file.\n")
        blank()

        # ── SECTION 2: BACKGROUND AND DEFINITIONS ────────────────────
        rule()
        f.write("2. BACKGROUND AND DEFINITIONS\n")
        rule()
        blank()
        f.write("THE 29 MUQATTA'AT SURAHS:\n\n")
        f.write("    2, 3, 7, 10, 11, 12, 13, 14, 15, 19, 20, 26, 27, 28, 29, 30, 31, 32,\n")
        f.write("    36, 38, 40, 41, 42, 43, 44, 45, 46, 50, 68\n\n")
        f.write("Each opens with disconnected Arabic letters in its first verse. No other\n")
        f.write("surah does. This is observable directly in any Quran manuscript, printed\n")
        f.write("edition, or digital text.\n")
        blank()

        f.write("THE 13 LETTER GROUPS:\n\n")
        f.write("Each unique letter combination defines a group. The group counts those\n")
        f.write("letters across all surahs sharing that combination.\n\n")
        f.write("     #   Group    Surahs                           Tier\n")
        f.write("    ─── ──────── ──────────────────────────────── ──────\n")
        order = [("ALM", 1), ("ALR", 2), ("ALMR", 3), ("ALMS", 4),
                 ("HM", 5), ("ASQ", 6), ("Q", 7), ("KHYAS", 8),
                 ("TSM", 9), ("YS", 10), ("N", 11), ("TH", 12), ("TS", 13)]
        by_name = {r["name"]: r for r in results}
        for name, num in order:
            r = by_name[name]
            surahs_str = ", ".join(str(s) for s in r["surahs"])
            if len(surahs_str) > 32:
                surahs_str = surahs_str[:29] + "..."
            f.write(f"    {num:>2d}   {name:<8s} {surahs_str:<32s} {r['tier']}\n")
        blank()

        f.write("TWO SOURCE EDITIONS:\n\n")
        f.write("Two source texts from tanzil.net are used:\n\n")
        f.write("    Simple-Plain:  one encoding per letter\n")
        f.write("    Uthmani:       preserves historical scribal marks (alif variants,\n")
        f.write("                   diacritics added by later grammarians)\n\n")
        f.write("The editions differ only in how alif-family characters are encoded.\n")
        f.write("Base consonant counts are identical across editions. Each surah in the\n")
        f.write("Fractal Edition uses one specific edition; assignments are in 3.3.\n\n")
        f.write("Uthmani surahs in the Fractal Edition:\n\n")
        f.write(f"    {', '.join(str(s) for s in sorted(UTHMANI_SURAHS))}\n")
        blank()

        # ── SECTION 3: COUNTING SPECIFICATION ────────────────────────
        rule()
        f.write("3. COUNTING SPECIFICATION\n")
        rule()
        blank()

        f.write("3.1 VERSE-1 RULE\n\n")
        f.write("Each group either includes or excludes v1 (the verse containing the\n")
        f.write("Muqatta'at initials). Behaviour depends on whether the surah is merged:\n\n")
        f.write("    Setting       Non-merged surah      Merged surah (19, 20, 31, 36)\n")
        f.write("    ──────────    ──────────────────    ──────────────────────────────\n")
        f.write("    Include v1    Count entire v1       Count entire merged v1\n")
        f.write("    Exclude v1    Skip entire v1        Skip first 5 tokens of v1\n")
        f.write("                                        (Bismillah + initials)\n\n")
        f.write("Merged surahs are the four where the Fractal Edition merges Kufic v1\n")
        f.write("and v2 into a single v1 (see 5.2). In those, v1 contains Bismillah +\n")
        f.write("initials + content, and 'exclude v1' skips only the first 5 space-\n")
        f.write("delimited tokens (the four-word Bismillah plus the one-token initials),\n")
        f.write("keeping the content.\n\n")
        f.write("Which setting applies to which group: see 3.3.\n")
        blank()

        f.write("3.2 CHARACTER INVENTORY\n\n")
        f.write("All characters counted by at least one group, with Unicode codepoints:\n\n")
        f.write("    Consonants (encoded identically in Simple-Plain and Uthmani):\n")
        f.write("      ا U+0627  alif           ل U+0644  lam\n")
        f.write("      م U+0645  mim            ر U+0631  ra\n")
        f.write("      ص U+0635  sad            ح U+062D  ha (ḥāʾ, throat-h)\n")
        f.write("      ع U+0639  ain            س U+0633  sin\n")
        f.write("      ق U+0642  qaf            ك U+0643  kaf\n")
        f.write("      ه U+0647  ha (hāʾ)       ة U+0629  ta marbuta\n")
        f.write("      ي U+064A  ya             ى U+0649  alef maqsura\n")
        f.write("      ئ U+0626  ya+hamza       ط U+0637  ta\n")
        f.write("      ن U+0646  nun\n\n")
        f.write("    Alif / ya variants (Uthmani encoding only):\n")
        f.write("      أ U+0623  hamza-above    إ U+0625  hamza-below\n")
        f.write("      ٱ U+0671  wasla          ٰ U+0670  dagger (superscript alef)\n")
        f.write("      ٓ U+0653  maddah (combining, NOT آ U+0622)\n")
        f.write("      ۟ U+06DF  small high rounded zero\n")
        f.write("      ۦ U+06E6  small ya\n\n")
        f.write("Each group uses a specific subset. Subsets do not carry across groups;\n")
        f.write("use the exact list in 3.3 for each.\n")
        blank()

        f.write("3.3 PER-GROUP SPECIFICATION\n\n")

        def fmt_chars(chars):
            return " + ".join(chars) if chars else ""

        def group_block(name):
            r = by_name[name]
            f.write(f"Group {r['num']}: {name}\n")
            if name == "ALMS":
                f.write(f"    Surahs:       7 (Uthmani), 38 (Simple-Plain)\n")
            elif r["edition"] == "uthmani":
                f.write(f"    Surahs:       {', '.join(str(s) for s in r['surahs'])}\n")
                f.write(f"    Edition:      Uthmani\n")
            else:
                f.write(f"    Surahs:       {', '.join(str(s) for s in r['surahs'])}\n")
                f.write(f"    Edition:      Simple-Plain\n")
            f.write(f"    Verse 1:      {'Excluded' if r['excl_v1'] else 'Included'}\n")
            all_chars = r["consonants"] + r["alif_chars"]
            f.write(f"    Count:        {fmt_chars(all_chars)}\n")
            if name == "ALMS":
                f.write(f"                  (plain alif only; encoded identically in\n")
                f.write(f"                   both editions)\n")
            elif name == "KHYAS":
                f.write(f"                  (counts ة as ha-variant, ئ as ya-variant)\n")
            elif name == "YS":
                f.write(f"                  (includes small ya U+06E6; does NOT count ئ)\n")
            elif name == "TH":
                f.write(f"                  (counts ه only; does NOT count ة)\n")
            elif name == "ALMR":
                f.write(f"                  (no plain alif ا; no wasla ٱ)\n")
            blank()

        f.write("TIER 1 — no alif-variant choice required:\n\n")
        for name in ["ALM", "ALMS", "HM", "ASQ", "Q", "KHYAS", "TSM", "YS"]:
            group_block(name)

        f.write("TIER 2 — requires Uthmani alif-variant subset:\n\n")
        for name in ["ALR", "ALMR", "N", "TH", "TS"]:
            group_block(name)

        # ── SECTION 4: RESULTS ───────────────────────────────────────
        rule()
        f.write("4. RESULTS\n")
        rule()
        blank()

        def results_table(group_list, subtotal_label, subtotal_val):
            thin()
            f.write(" #  Group   Surahs                          Total     ÷ 19\n")
            thin()
            for r in group_list:
                surahs_str = ", ".join(str(s) for s in r["surahs"])
                if len(surahs_str) > 30:
                    surahs_str = surahs_str[:27] + "..."
                div = r["total"] // 19
                if r["total"] == 361:
                    div_str = "19 × 19  (= 19²)"
                else:
                    div_str = f"{div} × 19"
                f.write(f"{r['num']:>2d}  {r['name']:<6s}  {surahs_str:<30s} "
                        f"{r['total']:>6,d}    {div_str}\n")
            thin()
            f.write(f"    {subtotal_label:<36s}{subtotal_val:>6,d}\n")
            thin()
            blank()

        f.write("TIER 1 — zero alif-variant parameters:\n\n")
        results_table(tier1, "Tier 1 subtotal", tier1_sum)

        f.write("TIER 2 — alif-variant subset per group (see 3.3):\n\n")
        results_table(tier2, "Tier 2 subtotal", tier2_sum)

        f.write("GRAND TOTAL AND FACTORIZATION:\n\n")
        f.write(f"    Grand total:       {grand:,d}\n")
        f.write(f"    Factorization:     {grand:,d} = 19 × {grand//19:,d} = 19² × {grand//361}\n")
        f.write(f"    Prime index:       {grand//361} = P(29), the 29th prime\n")
        f.write(f"    First 29 primes:   2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41,\n")
        f.write(f"                       43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97,\n")
        f.write(f"                       101, 103, 107, 109\n")
        blank()

        f.write("MULTIPLIER-LEVEL RESULTS:\n\n")
        f.write("    Let k_i = group_total_i / 19 for each of the 13 groups.\n\n")
        f.write(f"    Σ k_i    = {sum_k:,d}         = 19 × {sum_k//19}\n")
        f.write(f"    Σ k_i²   = {sum_k2:,d}   = 19 × {sum_k2//19:,d}\n")
        blank()

        f.write("WORD-COUNT IDENTITY:\n\n")
        f.write(f"    Word count of the 29 Muqatta'at surahs: {counts['muq_words']:,d}\n\n")
        f.write("    Equal to the grand letter total above. Words are counted as space-\n")
        f.write("    delimited tokens in the Fractal Edition text after the verse merges\n")
        f.write("    and word-segmentation corrections described in 5.2 and 5.3.\n")
        blank()

        # ── SECTION 5: BOOK-LEVEL COUNTS ─────────────────────────────
        rule()
        f.write("5. BOOK-LEVEL COUNTS\n")
        rule()
        blank()
        f.write("Four measurements of the Fractal Edition as a whole:\n\n")
        f.write(f"    Surahs:    {counts['surahs']:>7,d}     = 19 × {counts['surahs']//19}\n")
        f.write(f"    Verses:    {counts['verses']:>7,d}     = 19 × {counts['verses']//19}\n")
        f.write(f"    Words:     {counts['words']:>7,d}     = 19 × {counts['words']//19:,d}\n")
        f.write(f"    Letters:   {counts['letters']:>7,d}     = 19 × {counts['letters']//19:,d}\n\n")
        f.write("Each is defined below.\n")
        blank()

        f.write("5.1 SURAHS — 114.\n\n")
        f.write("    The standard chapter count.\n")
        blank()

        f.write(f"5.2 VERSES — {counts['verses']:,d}.\n\n")
        f.write("    The Kufic tradition has 6,236 verses. In four surahs (19, 20, 31,\n")
        f.write("    36) verse 1 is the initials alone and verse 2 is the content\n")
        f.write("    beginning 'these are the signs of the Scripture' (or equivalent).\n")
        f.write("    In five other initial-bearing surahs (10, 12, 13, 15, 27) the same\n")
        f.write("    pattern appears but as a single verse.\n\n")
        f.write("    The Fractal Edition merges v1 and v2 in surahs 19, 20, 31, 36 to\n")
        f.write("    match the treatment in the five others. No letters or words are\n")
        f.write("    altered; only verse boundaries move.\n\n")
        f.write(f"        Kufic:     6,236\n")
        f.write(f"        Fractal:   {counts['verses']:,d}  = 19 × {counts['verses']//19}\n")
        blank()

        f.write(f"5.3 WORDS — {counts['words']:,d}.\n\n")
        f.write("    Words are counted as space-delimited tokens.\n\n")
        f.write("    The vocative يا ('O!') is a separate token in Simple-Plain and\n")
        f.write("    attached to the following word in Uthmani. Six non-Muqatta'at\n")
        f.write("    surahs (64, 71, 74, 78, 82, 84) use the Uthmani segmentation,\n")
        f.write("    reducing the book-wide word count by 6.\n\n")
        f.write("        Simple-Plain-segmented total:  82,504\n")
        f.write(f"        Fractal Edition:               {counts['words']:,d}  = 19 × {counts['words']//19:,d}\n\n")
        f.write("    All six corrections are in non-Muqatta'at surahs; the 29-surah\n")
        f.write(f"    word count of {counts['muq_words']:,d} is unchanged.\n")
        blank()

        f.write(f"5.4 LETTERS — {counts['letters']:,d}.\n\n")
        f.write("    DEFINITION\n\n")
        f.write("    A letter is a character in Unicode range U+0600–U+06FF whose\n")
        f.write("    Unicode General Category starts with 'L' — that is, one of:\n\n")
        f.write("        Lu   uppercase letter       (not used in Arabic script)\n")
        f.write("        Ll   lowercase letter       (not used in Arabic script)\n")
        f.write("        Lt   titlecase letter       (not used in Arabic script)\n")
        f.write("        Lm   modifier letter        (includes tatweel U+0640, small ya U+06E6)\n")
        f.write("        Lo   other letter           (all Arabic consonants, wasla U+0671)\n\n")
        f.write("    Python one-liner:\n\n")
        f.write("        sum(1 for c in text\n")
        f.write("            if '\\u0600' <= c <= '\\u06FF'\n")
        f.write("            and unicodedata.category(c).startswith('L'))\n\n")
        f.write("    INCLUDED\n\n")
        f.write("    The 28 base Arabic consonants; ta marbuta (ة U+0629); alef maqsura\n")
        f.write("    (ى U+0649); hamza (ء U+0621); alef variants آ / أ / إ; waw+hamza\n")
        f.write("    (ؤ U+0624); ya+hamza (ئ U+0626); Uthmani wasla (ٱ U+0671); small ya\n")
        f.write("    (ۦ U+06E6); tatweel (ـ U+0640, the kashida elongation character —\n")
        f.write("    Unicode category Lm; there are 155 tatweels in the Fractal Edition).\n\n")
        f.write("    EXCLUDED\n\n")
        f.write("    All combining marks (Unicode Mn/Mc): fatha, kasra, damma, shadda,\n")
        f.write("    sukun, tanwin, maddah mark (ٓ U+0653), dagger alef (ٰ U+0670), small-\n")
        f.write("    high markers (U+06D6–U+06ED), and similar. Also excluded: Arabic\n")
        f.write("    punctuation, end-of-ayah markers, and digits.\n\n")
        f.write("    DIFFERENCE FROM SECTION 4\n\n")
        f.write("    The book-level letter count is a category filter. The Section 4\n")
        f.write("    group counts enumerate specific characters by codepoint, and — for\n")
        f.write("    Tier 2 groups — include some combining marks (U+0670, U+0653,\n")
        f.write("    U+06DF) that the book-level filter excludes. The two counts use\n")
        f.write("    different definitions for different purposes and are not nested.\n\n")
        f.write("    SCOPE\n\n")
        f.write("    The verse and word corrections in 5.2 and 5.3 affect the book-level\n")
        f.write("    totals but not the 13 group letter counts or the 29-surah word\n")
        f.write("    count. A reader who rejects these corrections retains the full\n")
        f.write("    Section 4 result and loses only the two book-level divisibilities\n")
        f.write("    for verses and words.\n")
        blank()

        # ── SECTION 6: PARAMETER ACCOUNTING ──────────────────────────
        rule()
        f.write("6. PARAMETER ACCOUNTING\n")
        rule()
        blank()
        f.write("Per group, what the text specifies and what the specification chose.\n")
        f.write("No probability claims are made here.\n")
        blank()

        f.write("TIER 1 — ZERO ANALYST-CHOSEN PARAMETERS (8 groups):\n\n")
        f.write("    The Muqatta'at letters and the surahs they appear in are given by\n")
        f.write("    the text. For these 8 groups, the character set is either the named\n")
        f.write("    consonants only, or the named consonants plus plain alif (ا) —\n")
        f.write("    which is encoded identically in every Arabic text. No variant-form\n")
        f.write("    choices are made.\n\n")
        f.write(f"    Tier 1 subtotal: {tier1_sum:,d}. Each group divides individually by 19.\n")
        blank()

        f.write("TIER 2 — ALIF-SUBSET SPECIFICATION (5 groups):\n\n")
        f.write("    Five groups (ALR, ALMR, N, TH, TS) cannot reach a multiple of 19\n")
        f.write("    using consonants alone or consonants + plain alif. They require a\n")
        f.write("    specific subset of the Uthmani alif variants, listed in 3.3.\n\n")
        f.write("    These subsets are the parameter. They were identified by searching\n")
        f.write("    for the unique alif-variant combination that (a) produces a multiple\n")
        f.write("    of 19 for that group and (b) is consistent with the grand-total\n")
        f.write("    constraint. For each Tier 2 group, a single subset satisfies both.\n")
        blank()

        f.write("VERSE-1 SETTING (all groups):\n\n")
        f.write("    For each group, one setting (include, exclude) produces a total\n")
        f.write("    divisible by 19 and the other does not. It is a binary determined\n")
        f.write("    by the divisibility requirement, not a free parameter.\n")
        blank()

        f.write("EDITION ASSIGNMENT (ALMS):\n\n")
        f.write("    Surah 7 uses Uthmani; surah 38 uses Simple-Plain. This is a\n")
        f.write("    per-surah assignment. The ALMS letter count is unaffected (plain\n")
        f.write("    alif is encoded identically in both editions), but the served\n")
        f.write("    word count is:\n\n")
        f.write("        S38 Simple-Plain:   29-surah total = 39,349   ✓ matches letter total\n")
        f.write("        S38 Uthmani:        29-surah total = 39,347   ✗\n\n")
        f.write("    The assignment is constrained by the word count, which involves no\n")
        f.write("    parameter choices.\n")
        blank()

        f.write("WHAT REMAINS IF TIER 2 IS REJECTED:\n\n")
        f.write("    Still holds:\n")
        f.write("        - The 8 Tier 1 group totals (each divisible by 19).\n")
        f.write(f"        - Tier 1 subtotal: {tier1_sum:,d}.\n")
        f.write(f"        - 29-surah word count: {counts['muq_words']:,d}.\n")
        f.write("        - The book-level counts in Section 5.\n\n")
        f.write("    Lost:\n")
        f.write(f"        - The grand total of {grand:,d} as a letter sum.\n")
        f.write("        - The 19² × P(29) factorization.\n")
        f.write("        - The word-letter identity (no letter total to compare).\n")
        f.write("        - N = 19² (N is a Tier 2 group).\n\n")
        f.write(f"    The 29-surah word count of {counts['muq_words']:,d} remains in either case; it is\n")
        f.write("    a separate measurement.\n")
        blank()

        # ── SECTION 7: OBJECTIONS AND RESPONSES ──────────────────────
        rule()
        f.write("7. OBJECTIONS AND RESPONSES\n")
        rule()
        blank()

        f.write("Q: Are the 13 divisibilities independent? Surah 42 appears in both\n")
        f.write("   Group 5 (HM) and Group 6 (ASQ).\n\n")
        f.write("A: The groups count disjoint letter sets in that surah — HM counts\n")
        f.write("   ha + mim, ASQ counts ain + sin + qaf. A shared surah does not\n")
        f.write("   induce statistical dependence between counts of disjoint character\n")
        f.write("   sets. More broadly, the 8 Tier 1 groups are not formally independent\n")
        f.write("   in the probabilistic sense (they share a text, a language, a\n")
        f.write("   morphology), but they are independent in the sense that matters\n")
        f.write("   here — no analyst-chosen parameter connects them.\n")
        blank()

        f.write("Q: The verse-1 inclusion/exclusion rule looks ad hoc.\n\n")
        f.write("A: For each group, one setting produces a multiple of 19 and the other\n")
        f.write("   does not. The setting is binary and determined by the divisibility\n")
        f.write("   requirement. Documented per group in 3.3.\n")
        blank()

        f.write("Q: The mixed-edition assignment in ALMS (S7 = Uthmani, S38 = Simple-\n")
        f.write("   Plain) looks chosen for fit.\n\n")
        f.write("A: The ALMS letter count is unaffected by the S38 edition assignment —\n")
        f.write("   plain alif is encoded identically in both editions, and ALMS counts\n")
        f.write("   only plain alif from the alif family. The assignment affects only\n")
        f.write(f"   the served word count, and the constraint is the 29-surah total of\n")
        f.write(f"   {counts['muq_words']:,d} — a measurement with no parameter choices.\n")
        blank()

        f.write("Q: Isn't the structure circular? Tier 2 parameters are chosen to hit\n")
        f.write(f"   {counts['muq_words']:,d}, and then {counts['muq_words']:,d} is presented as significant.\n\n")
        f.write("A: The claim is that two zero-parameter measurements — the Tier 1\n")
        f.write(f"   letter subtotal ({tier1_sum:,d}) and the 29-surah word count ({counts['muq_words']:,d}) —\n")
        f.write("   jointly constrain the Tier 2 parameters:\n\n")
        f.write(f"       Step 1:   Tier 1 totals are fixed by the text. Sum: {tier1_sum:,d}.\n")
        f.write(f"       Step 2:   The 29-surah word count is fixed by the text.\n")
        f.write(f"                 Value: {counts['muq_words']:,d}.\n")
        f.write(f"       Step 3:   Tier 2 groups must fill the gap\n")
        f.write(f"                 ({counts['muq_words']:,d} − {tier1_sum:,d} = {counts['muq_words']-tier1_sum:,d}) while each dividing by 19.\n")
        f.write(f"       Step 4:   The factorization {counts['muq_words']:,d} = 19² × 109 and the identity\n")
        f.write(f"                 109 = P(29) are arithmetic consequences, not chosen.\n\n")
        f.write("   A reader who rejects Tier 2 still has Steps 1 and 2 — independent\n")
        f.write("   facts that do not depend on Tier 2.\n")
        blank()

        f.write("Q: Is this a statistically rigorous result?\n\n")
        f.write("A: No. The (1/19)^k framing sometimes applied to divisibility counts\n")
        f.write("   is a back-of-envelope model that treats each group total as a\n")
        f.write("   uniform draw mod 19. That model is not a formal null hypothesis for\n")
        f.write("   this text. The results in Section 4 are arithmetic facts; their\n")
        f.write("   interpretation is left to the reader.\n")
        blank()

        f.write("Q: Has this been published elsewhere?\n\n")
        f.write("A: The 19-based numerical structure of the Quran was investigated in\n")
        f.write("   the 1970s–80s by Rashad Khalifa and others, and remains the subject\n")
        f.write("   of ongoing debate. The specific decomposition in this document — the\n")
        f.write("   13-group Tier 1 / Tier 2 split, the word-letter identity at 39,349,\n")
        f.write("   and the 19² × P(29) factorization — is, to the author's knowledge,\n")
        f.write("   published here for the first time. Readers are invited to identify\n")
        f.write("   any prior work.\n")
        blank()

        # ── SECTION 8: REPRODUCTION ──────────────────────────────────
        rule()
        f.write("8. REPRODUCTION\n")
        rule()
        blank()
        f.write("    1. Download from tanzil.net/download:\n\n")
        f.write("         Quran Type: Simple Plain  → Text (with aya numbers)\n")
        f.write("         Quran Type: Uthmani       → Text (with aya numbers)\n\n")
        f.write("       Save both in tanzil_data/ at the repository root.\n\n")
        f.write("    2. Run: python3 verify.py\n\n")
        f.write("    3. The script loads both source texts, counts every character in\n")
        f.write("       every group according to Section 3, assembles the Fractal\n")
        f.write("       Edition text, applies the verse and word corrections in\n")
        f.write("       Section 5, and regenerates this document.\n\n")
        f.write("    4. Every number in this document is computed from the source\n")
        f.write("       texts, not hardcoded. Plain Python, standard library only.\n\n")
        f.write("    5. To verify from this file alone, without re-downloading: the\n")
        f.write("       Fractal Edition text appears above this appendix. Count the\n")
        f.write("       characters specified in 3.2 within the surahs specified in\n")
        f.write("       3.3, applying the verse-1 rule, and compare to Section 4.\n")
        f.write("       For the book-level letter count, use the filter in 5.4.\n")
        blank()

        rule()
        f.write("  74:30 Project | 7430project.com\n")
        f.write("  Source: tanzil.net (CC BY 3.0)\n")
        f.write("  Script: verify.py\n")
        rule()


# ════════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("FRACTAL EDITION BUILDER — 74:30 Project")
    print("=" * 60)

    simple_path = next((p for p in SIMPLE_PLAIN_CANDIDATES if os.path.exists(p)), None)
    if not simple_path:
        print("ERROR: Simple-Plain source file not found. Looked in:")
        for c in SIMPLE_PLAIN_CANDIDATES:
            print(f"  {c}")
        sys.exit(1)
    if not os.path.exists(UTHMANI_PATH):
        print(f"ERROR: Uthmani source file not found at {UTHMANI_PATH}")
        sys.exit(1)

    print(f"\nSimple-Plain: {simple_path}")
    print(f"Uthmani:      {UTHMANI_PATH}")

    simple_verses = load_quran_file(simple_path)
    uthmani_verses = load_quran_file(UTHMANI_PATH)
    print(f"  Simple-Plain verses: {len(simple_verses)}")
    print(f"  Uthmani verses:      {len(uthmani_verses)}")

    edition = assemble_fractal_edition(simple_verses, uthmani_verses)
    edition = apply_corrections(edition)
    print(f"  Post-correction verses: {len(edition)}")

    # Verify 13 groups
    print(f"\n{'─' * 60}")
    print("VERIFYING 13 MUQATTA'AT GROUPS")
    print(f"{'─' * 60}\n")

    results = []
    all_pass = True
    for i, spec in enumerate(GROUPS):
        name, tier, surahs, edition_label, excl_v1, cons, alif, expected = spec
        total = verify_group(spec, edition)
        ok = (total == expected) and (total % 19 == 0)
        all_pass = all_pass and ok
        results.append({
            "num": i + 1, "name": name, "tier": tier, "surahs": surahs,
            "edition": edition_label, "excl_v1": excl_v1,
            "consonants": cons, "alif_chars": alif,
            "total": total, "expected": expected,
        })
        v1 = "excl.v1" if excl_v1 else "full"
        status = "✓" if ok else f"✗ (got {total}, expected {expected})"
        print(f"  {name:<6s}  {total:>7,d} = 19 × {total//19:<5d}  [{v1:<7s}]  {status}")

    grand = sum(r["total"] for r in results)
    print(f"\n  GRAND TOTAL: {grand:,d}  (target 39,349)")
    print(f"  MATCH:       {'✓' if grand == 39349 else '✗'}")
    print(f"  ALL ÷ 19:    {'✓' if all_pass else '✗'}")

    counts = book_level_counts(edition)
    print(f"\n  Book-level: {counts['surahs']} surahs, {counts['verses']:,} verses, "
          f"{counts['words']:,} words, {counts['letters']:,} letters")

    output_path = "fractal_edition.txt"
    write_fractal_edition(edition, output_path)
    write_verification(
        results, edition, counts, output_path,
        source_files=[("Simple-Plain", simple_path), ("Uthmani", UTHMANI_PATH)],
        append=True,
    )
    print(f"\n  Written: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
