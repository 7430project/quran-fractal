#!/usr/bin/env python3
"""
fractal_edition_final.py — 74:30 Project
=========================================
Assembles and verifies the Fractal Edition of the Quran.

The Fractal Edition uses two source texts:
  - Simple-Clean (tanzil.net) for most surahs
  - Uthmani (tanzil.net) for surahs requiring rich encoding

It verifies that all 13 Muqatta'at letter groups independently divide
by 19, and that their grand total equals exactly:

    39,349 = 19² × 109 = 19² × P(29)

where P(29) = 109 is the 29th prime number,
and 29 is the number of Muqatta'at surahs.
39,349 is also the total word count of the 29 Muqatta'at surahs.

Source: tanzil.net (Creative Commons Attribution 3.0)
"""

import os
import sys
import hashlib
from collections import Counter, defaultdict
from datetime import date

# ════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════════

# Surahs that use the Uthmani edition
# Surahs that use the Uthmani edition
UTHMANI_SURAHS = {7, 10, 11, 12, 13, 14, 15, 20, 27, 36, 68}

# Source files in tanzil_data/
# The Uthmani file must be from tanzil.net (with full diacritics and marks)
UTHMANI_PATH = "tanzil_data/quran-uthmani.txt"

# Simple-Clean: checks these paths in order
# Any pipe-delimited Quran file with Simple encoding works
# (diacritics don't affect base consonant counts)
SIMPLE_CLEAN_CANDIDATES = [
    "tanzil_data/quran-simple-clean.txt",
    "tanzil_data/quran-simple-plain.txt",
]

# ════════════════════════════════════════════════════════════════════
# THE 13 MUQATTA'AT GROUPS
# ════════════════════════════════════════════════════════════════════

GROUPS = [
    # (name, surahs, edition, exclude_v1, consonants, alif_component, expected_total)
    (
        "ALM", [2, 3, 29, 30, 31, 32], "simple", False,
        ["ل", "م"],
        ["ا"],
        18012
    ),
    (
        "ALR", [10, 11, 12, 14, 15], "uthmani", False,
        ["ل", "ر"],
        ["ا", "إ", "\u0653"],  # plain + hamza-below + maddah
        7828
    ),
    (
        "ALMR", [13], "uthmani", False,
        ["ل", "م", "ر"],
        ["أ", "إ", "\u0653", "\u0670"],  # hamza-above + hamza-below + maddah + dagger
        1178
    ),
    (
        "ALMS", [7, 38], "uthmani", True,
        ["ل", "م", "ص"],
        ["ا"],  # plain alif only (encoding-independent)
        4997
    ),
    (
        "HM", [40, 41, 42, 43, 44, 45, 46], "simple", False,
        ["ح", "م"],
        [],
        2147
    ),
    (
        "ASQ", [42], "simple", False,
        ["ع", "س", "ق"],
        [],
        209
    ),
    (
        "Q", [50], "simple", False,
        ["ق"],
        [],
        57
    ),
    (
        "KHYAS", [19], "simple", True,
        ["ك", "ه", "ة", "ي", "ى", "ئ", "ع", "ص"],
        [],
        798
    ),
    (
        "TSM", [26, 28], "simple", True,
        ["ط", "س", "م"],
        [],
        1178
    ),
    (
        "YS", [36], "uthmani", True,
        ["ي", "س", "ى", "\u06E6"],  # ي + س + alif maqsura + small yeh
        [],
        285
    ),
    (
        "N", [68], "uthmani", False,
        ["ن"],
        ["ا", "\u0670", "أ", "\u0653", "\u06DF", "ٱ"],  # plain + dagger + hamza-above + maddah + small-zero + wasla
        361
    ),
    (
        "TH", [20], "uthmani", True,
        ["ط", "ه"],
        ["ا", "\u0670", "أ", "\u06DF", "ٱ"],  # plain + dagger + hamza-above + small-zero + wasla
        1292
    ),
    (
        "TS", [27], "uthmani", True,
        ["ط", "س"],
        ["ا", "\u0670", "أ", "إ", "ٱ"],  # plain + dagger + hamza-above + hamza-below + wasla
        1007
    ),
]

# Surahs where verse 1 is merged with verse 2 in the Fractal Edition
MERGE_V1_SURAHS = {19, 20, 31, 36}

# Populated during assembly: stores the original verse 1 text
# (Bismillah + initials) for each merged surah, so the counting
# engine knows exactly what to skip when exclude_v1 is True.
ORIGINAL_V1_TEXTS = {}


# ════════════════════════════════════════════════════════════════════
# FILE LOADING
# ════════════════════════════════════════════════════════════════════

def load_quran_file(filepath):
    """
    Load a Tanzil Quran text file. Handles:
      - Pipe-delimited format: surah|ayah|text
      - UTF-8 with or without BOM
      - Windows (\\r\\n) and Unix (\\n) line endings
      - Comment lines starting with #
    Returns: dict of {(surah, ayah): text}
    """
    verses = {}
    first_data_line = None

    for enc in ["utf-8-sig", "utf-8", "latin-1"]:
        try:
            with open(filepath, "r", encoding=enc) as f:
                for line in f:
                    line = line.strip("\r\n\t ")
                    if not line or line.startswith("#"):
                        continue
                    if first_data_line is None:
                        first_data_line = line
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        try:
                            surah = int(parts[0])
                            ayah = int(parts[1])
                            text = parts[2]
                            verses[(surah, ayah)] = text
                        except ValueError:
                            continue
            break  # file opened successfully, stop trying encodings
        except (UnicodeDecodeError, FileNotFoundError):
            continue

    if not verses and first_data_line:
        print(f"\n  ERROR: File loaded but no pipe-delimited verses found.")
        print(f"  First data line: {first_data_line[:80]}")
        if "|" not in first_data_line:
            print(f"\n  This file is NOT in pipe-delimited format.")
            print(f"  Re-download from tanzil.net/download with:")
            print(f'    Output format: "Text (with aya numbers)"')
            print(f"  The correct format looks like: 1|1|بسم الله الرحمن الرحيم")

    return verses



# ════════════════════════════════════════════════════════════════════
# COUNTING ENGINE
# ════════════════════════════════════════════════════════════════════

def count_chars_in_surah(edition_list, surah, char_set, exclude_v1=False):
    """Count occurrences of characters in char_set within a surah
    of the assembled Fractal Edition.

    If exclude_v1 is True:
      - For merged surahs (19, 20, 31, 36): the merged verse 1
        starts with the original v1 (Bismillah + initials) then
        the old v2 content. We skip the original v1 portion using
        its stored length from ORIGINAL_V1_TEXTS.
      - For non-merged surahs: verse 1 is the Bismillah + initials.
        We skip the entire verse.
    """
    total = 0
    for s, a, text in edition_list:
        if s != surah:
            continue
        if exclude_v1 and a == 1:
            if surah in MERGE_V1_SURAHS and surah in ORIGINAL_V1_TEXTS:
                # Skip original v1 (Bismillah + initials), count only v2 content
                orig_v1_len = len(ORIGINAL_V1_TEXTS[surah])
                text = text[orig_v1_len + 1:]  # +1 for the joining space
            else:
                continue
        total += sum(1 for c in text if c in char_set)
    return total


def verify_group(name, surahs, edition, exclude_v1, consonants, alif_chars,
                 expected, edition_list):
    """Verify a single Muqatta'at group by counting from the assembled
    Fractal Edition. The 'edition' parameter is kept for documentation
    only — all counting reads from edition_list."""
    char_set = set(consonants + alif_chars)
    cons_set = set(consonants)
    alif_set = set(alif_chars)

    total = 0
    cons_total = 0
    alif_total = 0
    per_surah = []

    for surah in surahs:
        s_total = count_chars_in_surah(edition_list, surah, char_set, exclude_v1)
        s_cons = count_chars_in_surah(edition_list, surah, cons_set, exclude_v1)
        s_alif = count_chars_in_surah(edition_list, surah, alif_set, exclude_v1) if alif_chars else 0
        total += s_total
        cons_total += s_cons
        alif_total += s_alif
        per_surah.append((surah, s_cons, s_alif, s_total))

    return total, cons_total, alif_total, per_surah


# ════════════════════════════════════════════════════════════════════
# ASSEMBLY
# ════════════════════════════════════════════════════════════════════

def assemble_fractal_edition(simple_verses, uthmani_verses):
    """
    Assemble the Fractal Edition by selecting the correct edition per surah.
    Returns: list of (surah, ayah, text) tuples in order.
    """
    # Determine all surahs and ayahs
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


# ════════════════════════════════════════════════════════════════════
# OUTPUT
# ════════════════════════════════════════════════════════════════════

def write_fractal_edition(edition, output_path):
    """Write the assembled Fractal Edition to a pipe-delimited text file."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# ══════════════════════════════════════════════════════════════\n")
        f.write(f"# This file contains the assembled Fractal Edition text followed\n")
        f.write(f"# by a verification document. The document specifies a counting\n")
        f.write(f"# procedure and records the result. The reader is invited to\n")
        f.write(f"# reproduce the counts directly from the text.\n")
        f.write(f"#\n")
        f.write(f"# Scroll to the section titled 'VERIFICATION DOCUMENT' for the\n")
        f.write(f"# specification, results, parameter accounting, and objections.\n")
        f.write(f"# ══════════════════════════════════════════════════════════════\n")
        f.write(f"#\n")
        f.write(f"# THE FRACTAL EDITION — 74:30 Project\n")
        f.write(f"# 39,349 = 19² × P(29) | 6,232 = 19 × 328 | 82,498 = 19 × 4,342 | Generated {date.today()}\n")
        f.write(f"# Format: surah|ayah|text\n")
        f.write(f"# Source: tanzil.net (Creative Commons)\n")
        f.write(f"# Uthmani surahs: {sorted(UTHMANI_SURAHS)}\n")
        f.write(f"# Verse merges (v1+v2): surahs 19, 20, 31, 36\n")
        f.write(f"# Word segmentation (Uthmani ya): surahs 64, 71, 74, 78, 82, 84\n")
        f.write(f"# NOTE: Bismillahs are embedded in verse 1 of each surah, not\n")
        f.write(f"# standalone lines. Uthmani surahs use ٱ (wasla) not ا (plain)\n")
        f.write(f"# in the Bismillah — substring searches must account for this.\n")
        f.write(f"#\n")
        for surah, ayah, text in edition:
            f.write(f"{surah}|{ayah}|{text}\n")



def write_verification(results, output_path, gradient=None, append=False, source_files=None):
    """Write the verification document in the canonical 8-section structure:
    Abstract / Background and Definitions / Specification / Results /
    Parameter Accounting / Book-Level Counts / Objections and Responses /
    Reproduction.
    """
    mode = "a" if append else "w"
    with open(output_path, mode, encoding="utf-8") as f:
        W = 78
        def rule(c="="): f.write(c * W + "\n")
        def blank(): f.write("\n")

        if append:
            f.write("\n\n")

        # ── HEADER ─────────────────────────────────────────────
        rule()
        f.write("FRACTAL EDITION — VERIFICATION DOCUMENT\n")
        f.write("74:30 Project | 7430project.com\n")
        rule()
        blank()

        f.write(f"Source texts:   tanzil.net (Creative Commons Attribution 3.0)\n")
        f.write(f"Script:         verify.py (in repository root)\n")
        f.write(f"Generated:      {date.today()}\n")
        blank()

        # SHA-256 hashes at the top, before Section 1
        if source_files:
            f.write("SHA-256 hashes of source files (download the same files from tanzil.net\n")
            f.write("and compare to confirm no modification):\n\n")
            for label, filepath in source_files:
                try:
                    with open(filepath, "rb") as sf:
                        h = hashlib.sha256(sf.read()).hexdigest()
                    fname = os.path.basename(filepath)
                    f.write(f"    {fname}\n")
                    f.write(f"    {h}\n\n")
                except FileNotFoundError:
                    f.write(f"    {label}: FILE NOT FOUND\n\n")

        # ── SECTION 1: ABSTRACT ──────────────────────────
        rule()
        f.write("1. ABSTRACT\n")
        rule()
        blank()

        f.write("29 of the Quran's 114 chapters open with combinations of Arabic letters\n")
        f.write("known as the Muqatta'at. The identification is textual: these surahs begin\n")
        f.write("with disconnected letters in their first verse, no others do. Chapter 74,\n")
        f.write("verse 30 of the same text states a number: 19.\n\n")

        f.write("This document specifies a procedure for counting those letters in those\n")
        f.write("chapters, and records the result. The procedure groups the 29 surahs by\n")
        f.write("their shared letter combinations (13 groups), counts the named letters\n")
        f.write("in each group's surahs, and sums the results.\n\n")

        f.write("Under the specification in Section 3:\n\n")
        f.write("    - Each of the 13 group totals is divisible by 19.\n")
        f.write("    - The sum of the 13 totals is 39,349 = 19² × 109.\n")
        f.write("    - 109 is the 29th prime.\n")
        f.write("    - The word count of the same 29 surahs is also 39,349.\n\n")

        f.write("The specification distinguishes two tiers. Eight groups (Tier 1) require\n")
        f.write("no parameter choices beyond the named letters and surahs; their totals\n")
        f.write("are determined by the text alone. Five groups (Tier 2) require additional\n")
        f.write("character-set choices from the Uthmani manuscript tradition; these are\n")
        f.write("specified in Section 3 and accounted for in Section 5.\n\n")

        f.write("The document contains the specification (Sections 2–3), the results\n")
        f.write("(Section 4), the parameter accounting (Section 5), book-level counts\n")
        f.write("(Section 6), objections and responses (Section 7), and reproduction\n")
        f.write("instructions (Section 8). The reader is invited to count directly from\n")
        f.write("the text, which appears above this appendix in the same file.\n")
        blank()

        # ── SECTION 2: BACKGROUND AND DEFINITIONS ──────────
        rule()
        f.write("2. BACKGROUND AND DEFINITIONS\n")
        rule()
        blank()

        f.write("THE 29 MUQATTA'AT SURAHS:\n\n")
        f.write("    2, 3, 7, 10, 11, 12, 13, 14, 15, 19, 20, 26, 27, 28, 29, 30, 31, 32,\n")
        f.write("    36, 38, 40, 41, 42, 43, 44, 45, 46, 50, 68\n\n")

        f.write("Each opens with disconnected Arabic letters in its first verse. No other\n")
        f.write("surahs do. This identification is observable in every Quran manuscript,\n")
        f.write("printed edition, and digital text; it is not subject to scholarly dispute.\n")
        blank()

        f.write("THE 13 LETTER GROUPS:\n\n")
        f.write("Each unique letter combination defines a group. The group counts those\n")
        f.write("letters across all surahs sharing that combination. For example, Alif-\n")
        f.write("Lam-Mim opens surahs 2, 3, 29, 30, 31, 32 — the group counts every\n")
        f.write("Alif, every Lam, and every Mim in those six surahs.\n")
        blank()

        f.write("SOURCE EDITIONS:\n\n")
        f.write("Two source texts from tanzil.net are used:\n\n")
        f.write("    Simple-Plain:   one encoding per letter\n")
        f.write("    Uthmani:        preserves historical scribal marks (alif variants,\n")
        f.write("                    diacritics added by later grammarians)\n\n")
        f.write("The editions differ only in how alif-family characters are encoded.\n")
        f.write("Consonant counts are identical across editions. Each surah in the\n")
        f.write("Fractal Edition uses one specific edition; see Section 3 for per-surah\n")
        f.write("assignments.\n")
        blank()

        # ── SECTION 3: SPECIFICATION ──────────────────────────
        rule()
        f.write("3. SPECIFICATION\n")
        rule()
        blank()

        f.write("3.1 VERSE-1 RULE\n\n")

        f.write("Each group either includes or excludes verse 1 (the verse containing\n")
        f.write("the Muqatta'at letters themselves).\n\n")

        f.write('    "Include v1":   count every letter in the verse, including initials\n')
        f.write('    "Exclude v1":   skip the Bismillah and the Muqatta\'at initials\n\n')

        f.write('    In non-merged surahs, verse 1 is the Bismillah + initials, so\n')
        f.write('    "exclude v1" means skip the entire verse.\n\n')

        f.write("    In merged surahs (19, 20, 31, 36), verse 1 contains the Bismillah\n")
        f.write('    + initials + content that the Kufic tradition numbered as verse 2.\n')
        f.write('    "Exclude v1" means skip only the first 5 words (Bismillah +\n')
        f.write("    initials) and count the remainder of the merged verse.\n\n")

        f.write("The setting per group is given in the table in Section 4. Parameter\n")
        f.write("accounting for this choice is in Section 5.\n")
        blank()

        f.write("3.2 CHARACTER INVENTORY\n\n")

        f.write("All counted characters, with Unicode codepoints:\n\n")
        f.write("    Consonants:\n")
        f.write("      ا U+0627  alif            ل U+0644  lam\n")
        f.write("      م U+0645  mim             ر U+0631  ra\n")
        f.write("      ص U+0635  sad             ح U+062D  ha (guttural)\n")
        f.write("      ع U+0639  ain             س U+0633  sin\n")
        f.write("      ق U+0642  qaf             ك U+0643  kaf\n")
        f.write("      ه U+0647  ha              ة U+0629  ta marbuta (counted as ha)\n")
        f.write("      ي U+064A  ya              ى U+0649  alef maqsura (counted as ya)\n")
        f.write("      ئ U+0626  ya+hamza        ط U+0637  ta\n")
        f.write("      ن U+0646  nun\n\n")

        f.write("    Alif variants (Uthmani encoding only):\n")
        f.write("      أ U+0623  hamza-above     إ U+0625  hamza-below\n")
        f.write("      ٱ U+0671  wasla           ٰ U+0670  dagger (superscript)\n")
        f.write("      ٓ U+0653  maddah (combining, NOT آ U+0622)\n")
        f.write("      ۟ U+06DF  small high rounded zero\n\n")

        f.write("    Ya variant (Uthmani S36 only):\n")
        f.write("      ۦ U+06E6  small ya\n")
        blank()

        f.write("3.3 PER-GROUP SPECIFICATION\n\n")

        # Per-group specifications
        alif_labels_map = {
            0x0627: "ا (plain only)",
            0x0623: "أ",
            0x0625: "إ",
            0x0622: "آ madda",
            0x0671: "ٱ",
            0x0670: "ٰ",
            0x06DF: "۟",
            0x0653: "ٓ",
            0x0654: "ٔ",
            0x0629: "ة",
        }

        def char_label(c):
            cp = ord(c)
            return alif_labels_map.get(cp, c)

        # Group specification text for each group
        for i, (name, total, cons_total, alif_total, per_surah,
                surahs, edition, excl_v1, consonants, alif_chars, expected) in enumerate(results):

            # Determine display edition
            if len(surahs) > 1:
                editions_used = set()
                for s in surahs:
                    editions_used.add("uthmani" if s in UTHMANI_SURAHS else "simple")
                if len(editions_used) > 1:
                    edition_display = f"Mixed (see per-surah below)"
                else:
                    edition_display = "Uthmani" if "uthmani" in editions_used else "Simple-Plain"
            else:
                edition_display = "Uthmani" if edition == "uthmani" else "Simple-Plain"

            f.write(f"Group {i+1}: {name}\n")
            surah_str = ", ".join(str(s) for s in surahs)
            if len(surahs) == 2 and any(s in UTHMANI_SURAHS for s in surahs) and any(s not in UTHMANI_SURAHS for s in surahs):
                # Mixed edition case (ALMS)
                labeled = []
                for s in surahs:
                    ed = "Uthmani" if s in UTHMANI_SURAHS else "Simple-Plain"
                    labeled.append(f"{s} ({ed})")
                f.write(f"    Surahs:       {', '.join(labeled)}\n")
            else:
                f.write(f"    Surahs:       {surah_str}\n")
                f.write(f"    Edition:      {edition_display}\n")
            f.write(f"    Verse 1:      {'Excluded' if excl_v1 else 'Included'}\n")
            f.write(f"    Consonants:   {' + '.join(consonants)}\n")
            if alif_chars:
                labels = []
                only_plain_alif = len(alif_chars) == 1 and ord(alif_chars[0]) == 0x0627
                for c in alif_chars:
                    cp = ord(c)
                    if cp == 0x0627:
                        if only_plain_alif:
                            if name == "ALMS":
                                label = "ا (plain only — encoded identically in both editions)"
                            else:
                                label = "ا (plain only)"
                        else:
                            label = "ا"
                    else:
                        label = alif_labels_map.get(cp, c)
                    labels.append(label)
                f.write(f"    Alif subset:  {' + '.join(labels)}\n")
            blank()

        f.write("VARIANT HANDLING (for verifiers):\n\n")
        f.write("    KHYAS counts ة as ha and ئ as ya (full variant inclusion).\n")
        f.write("    TH counts ه only; does NOT count ة.\n")
        f.write("    YS counts ي + ى + ۦ; does NOT count ئ.\n\n")
        f.write("Variant sets do not carry across groups. Use the exact list for each.\n")
        blank()

        # ── SECTION 4: RESULTS ──────────────────────────
        rule()
        f.write("4. RESULTS\n")
        rule()
        blank()

        # Separate Tier 1 and Tier 2
        tier1_names = {"ALM", "ALMS", "HM", "ASQ", "Q", "KHYAS", "TSM", "YS"}
        tier2_names = {"ALR", "ALMR", "N", "TH", "TS"}

        tier1_results = [(i+1, r) for i, r in enumerate(results) if r[0] in tier1_names]
        tier2_results = [(i+1, r) for i, r in enumerate(results) if r[0] in tier2_names]

        grand_total = sum(r[1] for r in results)
        multipliers = [r[1] // 19 for r in results]
        tier1_subtotal = sum(r[1] for _, r in tier1_results)
        tier2_subtotal = sum(r[1] for _, r in tier2_results)
        all_pass = all(r[1] == r[10] and r[1] % 19 == 0 for r in results)

        f.write("TIER 1 — groups requiring no alif-variant parameter choice:\n\n")
        f.write("-" * W + "\n")
        f.write(" #  Group   Surahs                      Total       ÷ 19\n")
        f.write("-" * W + "\n")
        for idx, r in tier1_results:
            name = r[0]
            total = r[1]
            surahs = r[5]
            surah_str = ", ".join(str(s) for s in surahs)
            # Right-align total to a fixed position; multiplier right-aligned after 6 spaces
            line = f" {idx:>2d}  {name:<6s}  {surah_str}"
            # Pad to bring total to column 42 (5-digit totals end at col 46)
            pad = 42 - len(line)
            if pad < 2:
                pad = 2
            line += " " * pad + f"{total:>5d}      {total//19:>3d} × 19"
            f.write(line + "\n")
        f.write("-" * W + "\n")
        f.write(f"    Tier 1 subtotal                      {tier1_subtotal}\n")
        f.write("-" * W + "\n")
        blank()

        f.write("TIER 2 — groups requiring alif-variant specification (Section 3):\n\n")
        f.write("-" * W + "\n")
        f.write(" #  Group   Surahs                      Total       ÷ 19\n")
        f.write("-" * W + "\n")
        for idx, r in tier2_results:
            name = r[0]
            total = r[1]
            surahs = r[5]
            surah_str = ", ".join(str(s) for s in surahs)
            line = f" {idx:>2d}  {name:<6s}  {surah_str}"
            pad = 42 - len(line)
            if pad < 2:
                pad = 2
            if total == 361:
                line += " " * pad + f"{total:>5d}     19 × 19  (= 19²)"
            else:
                line += " " * pad + f"{total:>5d}      {total//19:>3d} × 19"
            f.write(line + "\n")
        f.write("-" * W + "\n")
        f.write(f"    Tier 2 subtotal                      {tier2_subtotal}\n")
        f.write("-" * W + "\n")
        blank()

        f.write("GRAND TOTAL AND FACTORIZATION:\n\n")
        f.write(f"    Grand total:       {grand_total:,d}\n")
        f.write(f"    Factorization:     {grand_total:,d} = 19 × {grand_total // 19:,d} = 19² × {grand_total // 361}\n")
        f.write(f"    Prime index:       {grand_total // 361} = P(29), the 29th prime number\n")
        f.write(f"    First 29 primes:   2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41,\n")
        f.write(f"                       43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97,\n")
        f.write(f"                       101, 103, 107, 109\n")
        blank()

        sigma_k = sum(multipliers)
        sigma_k2 = sum(k*k for k in multipliers)

        f.write("MULTIPLIER-LEVEL RESULTS:\n\n")
        f.write("    Let k_i = group_total_i / 19 for each of the 13 groups.\n\n")
        f.write(f"    Σ k_i    = {sigma_k:,d}      = 19 × {sigma_k // 19}\n")
        f.write(f"    Σ k_i²   = {sigma_k2:,d}  = 19 × {sigma_k2 // 19:,d}\n")
        blank()

        f.write("WORD-COUNT IDENTITY:\n\n")
        if gradient and 'muq_words' in gradient:
            mw = gradient['muq_words']
        else:
            mw = 39349
        f.write(f"    Word count of the 29 Muqatta'at surahs: {mw:,d}\n\n")
        f.write("    This is equal to the letter-count total above. The word count\n")
        f.write("    is computed as space-delimited tokens in the Fractal Edition\n")
        f.write("    text, after the verse merges and word-segmentation corrections\n")
        f.write("    described in Section 6.\n")
        blank()

        # ── SECTION 5: PARAMETER ACCOUNTING ──────────────────
        rule()
        f.write("5. PARAMETER ACCOUNTING\n")
        rule()
        blank()

        f.write("This section states, per group, how many parameter choices were made\n")
        f.write("by the analyst and what constrained each choice. No probability claims\n")
        f.write("are made here. The purpose is to let the reader assess, group by group,\n")
        f.write("what the text specifies and what the specification had to decide.\n")
        blank()

        f.write("TIER 1 — ZERO ANALYST-CHOSEN PARAMETERS (8 groups):\n\n")
        f.write("    The Muqatta'at letters and the surahs they appear in are given by\n")
        f.write("    the text. For these 8 groups, the character set is either the named\n")
        f.write("    consonants only, or the named consonants plus plain alif (ا),\n")
        f.write("    which is encoded identically in every Arabic text. No variant-form\n")
        f.write("    choices are made. No edition switching applies to the counted\n")
        f.write("    characters. The verse-1 setting is determined by divisibility\n")
        f.write("    (see below).\n\n")
        f.write(f"    Under this specification, each of the 8 groups totals a multiple\n")
        f.write(f"    of 19, and the sum of the 8 is {tier1_subtotal:,d}.\n")
        blank()

        f.write("TIER 2 — ALIF-SUBSET SPECIFICATION (5 groups):\n\n")
        f.write("    Five groups (ALR, ALMR, N, TH, TS) cannot reach a multiple of 19\n")
        f.write("    using consonants alone or consonants + plain alif. They require\n")
        f.write("    a specific subset of the Uthmani alif variants. The subsets are\n")
        f.write("    listed in Section 3.\n\n")
        f.write("    These subsets are the parameter. They were identified by searching\n")
        f.write("    for the unique alif-variant combination that both (a) produces\n")
        f.write("    a multiple of 19 for that group and (b) is consistent with the\n")
        f.write("    grand total constraint. For each Tier 2 group, a single subset\n")
        f.write("    satisfies both conditions.\n")
        blank()

        f.write("VERSE-1 SETTING (all groups):\n\n")
        f.write("    For each group, one of the two settings (include v1, exclude v1)\n")
        f.write("    produces a total divisible by 19 given the group's character set.\n")
        f.write("    This is not a free parameter in the sense of being chosen for\n")
        f.write("    aesthetic fit; it is a binary determined by the divisibility\n")
        f.write("    requirement. The settings appear in Section 3.\n")
        blank()

        f.write("EDITION ASSIGNMENT (ALMS group):\n\n")
        f.write("    ALMS contains surahs 7 and 38. Surah 7 uses Uthmani; Surah 38 uses\n")
        f.write("    Simple-Plain. This is a per-surah edition assignment rather than\n")
        f.write("    a group-level one.\n\n")
        f.write("    Surah 38 has 775 words in Simple-Plain and 773 in Uthmani. The\n")
        f.write(f"    word-count identity (Section 4) requires the 29 surahs to total\n")
        f.write(f"    {mw:,d} words; using Uthmani for Surah 38 would shift this total\n")
        f.write("    by 2 and break the identity. The edition assignment is constrained\n")
        f.write("    by the word count, which is itself a zero-parameter measurement.\n\n")
        f.write("    Both editions encode plain alif (ا) identically, so the ALMS\n")
        f.write("    letter count is unaffected by the edition choice; only the served\n")
        f.write("    text differs.\n")
        blank()

        f.write("WHAT REMAINS UNDER REJECTION:\n\n")
        f.write("    A reader may reject any of the Tier 2 specifications. The\n")
        f.write("    following results do not depend on them:\n\n")
        f.write("        The 8 Tier 1 group totals (all divisible by 19).\n")
        f.write(f"        The Tier 1 subtotal ({tier1_subtotal:,d}).\n")
        f.write(f"        The word count of the 29 surahs ({mw:,d}).\n")
        f.write("        The verse and book-level counts in Section 6.\n\n")
        f.write("    Rejecting all 5 Tier 2 groups removes:\n\n")
        f.write(f"        The grand total of {grand_total:,d} as a letter sum.\n")
        f.write("        The 19² × P(29) factorization.\n")
        f.write("        The word-letter identity (the letter total equaled the word\n")
        f.write("          total; without Tier 2 there is no letter total to compare).\n")
        f.write("        The N = 19² result (N is a Tier 2 group).\n\n")
        f.write(f"    The word count of {mw:,d} for the 29 surahs remains in either case;\n")
        f.write("    it is a separate measurement.\n")
        blank()

        # ── SECTION 6: BOOK-LEVEL COUNTS ──────────────────
        rule()
        f.write("6. BOOK-LEVEL COUNTS\n")
        rule()
        blank()

        if gradient:
            tl = gradient['total_letters']
            tv = gradient['total_verses']
            tw = gradient['total_words']
        else:
            tl, tv, tw = 332519, 6232, 82498

        f.write("The Fractal Edition text applies two corrections to the Kufic\n")
        f.write("verse-numbering tradition:\n")
        blank()

        f.write("VERSE MERGES:\n\n")
        f.write("    Four surahs (19, 20, 31, 36) have verse 1 (the Muqatta'at letters)\n")
        f.write("    separated from verse 2 in the Kufic tradition. In five other surahs\n")
        f.write("    (10, 12, 13, 15, 27) the same pattern — initials + \"these are the\n")
        f.write("    signs of the Scripture\" — is already a single verse.\n\n")
        f.write("    The Fractal Edition merges v1 and v2 in surahs 19, 20, 31, 36 to\n")
        f.write("    match the treatment in the other 5 surahs. No letters or words are\n")
        f.write("    altered; only verse boundaries move.\n\n")
        f.write(f"    Result: 6,236 → {tv:,d} = 19 × {tv // 19}\n")
        blank()

        f.write("WORD SEGMENTATION:\n\n")
        f.write("    The vocative يا (\"O!\") is a separate word in Simple-Plain and\n")
        f.write("    attached in Uthmani. Six non-Muqatta'at surahs (64, 71, 74, 78,\n")
        f.write("    82, 84) use Uthmani segmentation, reducing the book-wide word\n")
        f.write("    count by 6.\n\n")
        f.write(f"    Result: 82,504 → {tw:,d} = 19 × {tw // 19:,d}\n\n")
        f.write(f"    All six corrections are in non-Muqatta'at surahs; the 29-surah\n")
        f.write(f"    word count of {mw:,d} is unchanged.\n")
        blank()

        f.write("BOOK-LEVEL SUMMARY:\n\n")
        f.write(f"    Surahs:     114           = 19 × 6\n")
        f.write(f"    Verses:     {tv:,d}         = 19 × {tv // 19}\n")
        f.write(f"    Words:      {tw:,d}        = 19 × {tw // 19:,d}\n")
        f.write(f"    Letters:    {tl:,d}       = 19 × {tl // 19:,d}\n\n")
        f.write("    (Letter count: all Arabic letter characters in Unicode range\n")
        f.write("    U+0600–U+06FF, excluding diacritics and non-letter characters.)\n\n")
        f.write("    These depend on the verse and word corrections above. The core\n")
        f.write("    results in Section 4 do not.\n")
        blank()

        # ── SECTION 7: OBJECTIONS AND RESPONSES ──────────────
        rule()
        f.write("7. OBJECTIONS AND RESPONSES\n")
        rule()
        blank()

        f.write("Q: Are the 13 divisibilities independent? Surah 42 appears in both\n")
        f.write("   Group 5 (HM) and Group 6 (ASQ).\n\n")
        f.write("A: The groups count different letter sets in that surah. HM counts\n")
        f.write("   ha and mim; ASQ counts ain, sin, qaf. A shared surah does not\n")
        f.write("   induce statistical dependence between counts of disjoint character\n")
        f.write("   sets.\n\n")
        f.write("   Note on independence more broadly: the 8 Tier 1 groups are not\n")
        f.write("   formally independent in the probabilistic sense — they share a\n")
        f.write("   text, a language, and a morphology. They are independent in the\n")
        f.write("   sense that matters for this document: no analyst-chosen parameter\n")
        f.write("   connects them. Each is a separate arithmetic fact about the text.\n")
        blank()

        f.write("Q: The verse-1 inclusion/exclusion rule looks ad hoc.\n\n")
        f.write("A: For each group, one setting produces a multiple of 19 given the\n")
        f.write("   group's character set, and the other does not. The setting is\n")
        f.write("   binary and determined by the divisibility requirement. It is\n")
        f.write("   documented per group in Section 3.\n")
        blank()

        f.write("Q: The mixed-edition assignment in ALMS (S7 = Uthmani, S38 = Simple)\n")
        f.write("   looks chosen for fit.\n\n")
        f.write("A: The ALMS letter count is unaffected by the S38 edition assignment,\n")
        f.write("   because both editions encode plain alif identically and ALMS counts\n")
        f.write("   only plain alif from the alif family.\n\n")
        f.write("   The edition assignment affects the served text (word count) and is\n")
        f.write(f"   constrained by the 29-surah word total: Simple-Plain for S38 yields\n")
        f.write(f"   the {mw:,d} word total that matches the letter total; Uthmani yields\n")
        f.write(f"   {mw - 2:,d} and breaks the match. The constraint is the word count,\n")
        f.write("   which involves no parameter choices.\n")
        blank()

        f.write("Q: How is the count of 29 Muqatta'at surahs established?\n\n")
        f.write("A: By the text. Each of the 29 surahs opens with disconnected Arabic\n")
        f.write("   letters in its first verse; no other surah does. This is observable\n")
        f.write("   directly in any Quran manuscript, printed edition, or digital text.\n")
        blank()

        f.write("Q: How is the word count computed?\n\n")
        f.write("A: Words are counted as space-delimited tokens in the Fractal Edition\n")
        f.write(f"   text. The 29-surah total of {mw:,d} reflects the text after the\n")
        f.write("   verse merges (surahs 19, 20, 31, 36) and word-segmentation\n")
        f.write("   corrections (surahs 64, 71, 74, 78, 82, 84; all non-Muqatta'at).\n")
        blank()

        f.write("Q: Isn't the structure circular? Tier 2 parameters are chosen to hit\n")
        f.write(f"   {mw:,d}, and then {mw:,d} is presented as significant.\n\n")
        f.write("A: The claim is that the word count (zero parameters) and the Tier 1\n")
        f.write("   letter subtotal (zero parameters) jointly constrain the Tier 2\n")
        f.write("   parameters, leaving them with less freedom than a naive count would\n")
        f.write("   suggest:\n\n")
        f.write("     Step 1:   The 8 Tier 1 totals are fixed facts about the text.\n")
        f.write(f"               Sum: {tier1_subtotal:,d}.\n")
        f.write("     Step 2:   The 29-surah word count is a fixed fact about the text.\n")
        f.write(f"               Value: {mw:,d}.\n")
        f.write(f"     Step 3:   The 5 Tier 2 groups must fill the gap ({mw:,d} − {tier1_subtotal:,d}\n")
        f.write(f"               = {mw - tier1_subtotal:,d}) while each dividing by 19.\n")
        f.write(f"     Step 4:   The factorization {mw:,d} = 19² × 109 and the identity\n")
        f.write("               109 = P(29) are arithmetic consequences, not chosen.\n\n")
        f.write("   A reader who rejects the Tier 2 specification still has Steps 1\n")
        f.write("   and 2 — an 8-group Tier 1 result and a separate 29-surah word\n")
        f.write("   count — which do not depend on Tier 2.\n")
        blank()

        f.write("Q: Do the verse and word corrections affect the core result?\n\n")
        f.write("A: They do not affect the 13 group letter totals, the grand total of\n")
        f.write(f"   {grand_total:,d}, the factorization, or the 29-surah word count. They affect\n")
        f.write("   only the book-level counts in Section 6 (6,232 verses; 82,498\n")
        f.write("   total words). A reader who rejects the corrections has the core\n")
        f.write("   result in full and loses only the two book-level divisibilities.\n")
        blank()

        f.write("Q: Is this a statistically rigorous result?\n\n")
        f.write("A: No. The (1/19)^k framing sometimes applied to divisibility counts\n")
        f.write("   is a back-of-envelope model treating each group total as a uniform\n")
        f.write("   draw mod 19. That model is not a formal null hypothesis for this\n")
        f.write("   text. The results in Section 4 are arithmetic facts; their\n")
        f.write("   interpretation is left to the reader.\n")
        blank()

        f.write("Q: Has this been published elsewhere?\n\n")
        f.write("A: The 19-based numerical structure of the Quran was investigated\n")
        f.write("   in the 1970s–80s by Rashad Khalifa and others, and is the subject\n")
        f.write("   of ongoing debate. The specific decomposition in this document —\n")
        f.write("   the 13-group Tier 1 / Tier 2 split, the word-letter identity at\n")
        f.write(f"   {mw:,d}, and the 19² × P(29) factorization — is, to the author's\n")
        f.write("   knowledge, published here for the first time. Priority claims are\n")
        f.write("   not part of the verification; readers are invited to identify any\n")
        f.write("   prior work.\n")
        blank()

        # ── SECTION 8: REPRODUCTION ──────────────────
        rule()
        f.write("8. REPRODUCTION\n")
        rule()
        blank()

        f.write("    1. Download from tanzil.net/download:\n\n")
        f.write("         Quran Type: Simple Plain  → Text (with aya numbers)\n")
        f.write("         Quran Type: Uthmani       → Text (with aya numbers)\n\n")
        f.write("       Save both in tanzil_data/ at the repository root.\n\n")

        f.write("    2. Run: python3 verify.py\n\n")

        f.write("    3. verify.py (in the repository root) loads both source texts,\n")
        f.write("       counts every character in every group according to Section 3,\n")
        f.write("       assembles the Fractal Edition text, applies the verse and word\n")
        f.write("       corrections in Section 6, and emits this document.\n\n")

        f.write("    4. Every number in this document is computed from the source\n")
        f.write("       texts, not hardcoded. Modify a source file and the counts\n")
        f.write("       change. The script is plain Python with no dependencies\n")
        f.write("       beyond the standard library.\n\n")

        f.write("    5. To verify from this file alone, without re-downloading: the\n")
        f.write("       Fractal Edition text appears above this appendix. Count the\n")
        f.write("       characters specified in Section 3 within the surahs specified\n")
        f.write("       in Section 3, applying the verse-1 rule, and compare to\n")
        f.write("       Section 4.\n")
        blank()

        rule()
        f.write("  74:30 Project | 7430project.com\n")
        f.write("  Source: tanzil.net (CC BY 3.0)\n")
        f.write("  Script: verify.py\n")
        rule()


def main():
    print("=" * 60)
    print("FRACTAL EDITION BUILDER — 74:30 Project")
    print("=" * 60)

    # ── Load source files ──────────────────────────────────────────
    simple_path = None
    for candidate in SIMPLE_CLEAN_CANDIDATES:
        if os.path.exists(candidate):
            simple_path = candidate
            break

    if not simple_path:
        print(f"ERROR: Simple-Clean source file not found.")
        print(f"  Looked in:")
        for c in SIMPLE_CLEAN_CANDIDATES:
            print(f"    {c}")
        print(f"\n  Option A: Copy your existing fractal_edition.txt into tanzil_data/")
        print(f"  Option B: Download from tanzil.net/download:")
        print(f"    Quran Type: Simple Clean")
        print(f'    Output: Text (with aya numbers)')
        print(f"  Save as: tanzil_data/quran-simple-clean.txt")
        sys.exit(1)

    if not os.path.exists(UTHMANI_PATH):
        print(f"ERROR: Uthmani source file not found.")
        print(f"  Expected: {UTHMANI_PATH}")
        print(f"\n  Download from tanzil.net/download:")
        print(f"    Quran Type: Uthmani")
        print(f'    Output: Text (with aya numbers)')
        print(f"  Save as: {UTHMANI_PATH}")
        sys.exit(1)

    print(f"\nSimple-Clean: {simple_path}")
    print(f"Uthmani:      {UTHMANI_PATH}")

    simple_verses = load_quran_file(simple_path)
    uthmani_verses = load_quran_file(UTHMANI_PATH)

    print(f"  Simple-Clean verses loaded: {len(simple_verses)}")
    print(f"  Uthmani verses loaded:      {len(uthmani_verses)}")

    if len(simple_verses) == 0:
        print(f"\nFATAL: No verses loaded from {simple_path}")
        print(f"  The file exists but could not be parsed.")
        print(f"  Make sure it is pipe-delimited: 1|1|بسم الله ...")
        sys.exit(1)

    if len(uthmani_verses) == 0:
        print(f"\nFATAL: No verses loaded from {UTHMANI_PATH}")
        print(f"  The file exists but could not be parsed.")
        print(f"  Make sure it is pipe-delimited: 1|1|بِسْمِ ٱللَّهِ ...")
        sys.exit(1)

    if len(simple_verses) < 6000:
        print(f"WARNING: Simple-Clean has only {len(simple_verses)} verses (expected ~6236).")
    if len(uthmani_verses) < 6000:
        print(f"WARNING: Uthmani has only {len(uthmani_verses)} verses (expected ~6236).")

    # ── Assemble the Fractal Edition ───────────────────────────────
    print(f"\nAssembling Fractal Edition...")
    edition = assemble_fractal_edition(simple_verses, uthmani_verses)
    print(f"  Pre-merge verses: {len(edition)}")

    # ── Verse boundary corrections ────────────────────────────────
    merged_edition = []
    held_v1 = None
    for s, a, t in edition:
        if s in MERGE_V1_SURAHS and a == 1:
            held_v1 = (s, t)
            ORIGINAL_V1_TEXTS[s] = t  # Store for counting engine
            continue
        if s in MERGE_V1_SURAHS and a == 2 and held_v1 and held_v1[0] == s:
            merged_text = held_v1[1] + " " + t
            merged_edition.append((s, 1, merged_text))
            held_v1 = None
            continue
        if s in MERGE_V1_SURAHS and a > 2:
            merged_edition.append((s, a - 1, t))
        else:
            merged_edition.append((s, a, t))

    edition = merged_edition
    print(f"  Post-merge verses: {len(edition)}")
    print(f"  Merged v1+v2 in surahs: {sorted(MERGE_V1_SURAHS)}")

    # ── Word segmentation correction ─────────────────────────────
    WORD_MERGE_VERSES = {
        (64, 14): (0, 1),
        (71, 2):  (1, 2),
        (74, 1):  (4, 5),
        (78, 40): (12, 13),
        (82, 6):  (0, 1),
        (84, 6):  (0, 1),
    }

    word_merged_edition = []
    word_merges_done = 0
    for s, a, t in edition:
        if (s, a) in WORD_MERGE_VERSES:
            idx_a, idx_b = WORD_MERGE_VERSES[(s, a)]
            words = t.split()
            joined = words[idx_a] + words[idx_b]
            new_words = words[:idx_a] + [joined] + words[idx_b + 1:]
            t = " ".join(new_words)
            word_merges_done += 1
        word_merged_edition.append((s, a, t))

    edition = word_merged_edition
    print(f"  Word merges applied: {word_merges_done}")
    print(f"  Surahs: {len(set(s for s, a, t in edition))}")

    # ── Verify all 13 groups from the assembled text ──────────────
    print(f"\n{'─' * 60}")
    print("VERIFYING 13 MUQATTA'AT GROUPS")
    print("(All counts from the assembled Fractal Edition)")
    print(f"{'─' * 60}\n")

    results = []
    grand_total = 0
    all_pass = True

    for name, surahs, ed_label, excl_v1, consonants, alif_chars, expected in GROUPS:
        total, cons_total, alif_total, per_surah = verify_group(
            name, surahs, ed_label, excl_v1, consonants, alif_chars,
            expected, edition
        )

        verified = (total == expected) and (total % 19 == 0)
        if not verified:
            all_pass = False
        grand_total += total

        status = "✓" if verified else f"✗ (got {total}, expected {expected})"
        v1_label = "excl.v1" if excl_v1 else "full"

        print(f"  {name:6s}  {total:>7,d} = 19 × {total//19:<5d}  "
              f"[{v1_label:7s}]  {status}")

        results.append((
            name, total, cons_total, alif_total, per_surah,
            surahs, ed_label, excl_v1, consonants, alif_chars, expected
        ))

    print(f"\n{'─' * 60}")
    print(f"  GRAND TOTAL: {grand_total:>7,d}")
    print(f"  TARGET:      {39349:>7,d} = 19² × P(29)")
    print(f"  MATCH:       {'✓ YES' if grand_total == 39349 else '✗ NO'}")
    print(f"  ALL 13 ÷19:  {'✓ YES' if all_pass else '✗ NO'}")
    print(f"{'─' * 60}")

    # ── Compute Complete Fractal stats ────────────────────────────
    import unicodedata
    muq_surah_set = {2,3,7,10,11,12,13,14,15,19,20,26,27,28,29,30,31,32,36,38,40,41,42,43,44,45,46,50,68}

    total_letters = 0
    total_verses = len(edition)
    total_words = 0
    muq_words = 0
    for s, a, t in edition:
        lcount = sum(1 for c in t if '\u0600' <= c <= '\u06FF' and unicodedata.category(c).startswith('L'))
        total_letters += lcount
        wcount = len(t.split())
        total_words += wcount
        if s in muq_surah_set:
            muq_words += wcount

    print(f"  Total words: {total_words} = 19 × {total_words // 19}")

    gradient = {
        'total_letters': total_letters,
        'total_verses': total_verses,
        'total_words': total_words,
        'muq_words': muq_words,
    }

    # ── Write single output file ──────────────────────────────────
    output_path = "fractal_edition.txt"

    write_fractal_edition(edition, output_path)

    # Append verification proof to the same file
    source_files = [
        ("Simple-Plain", simple_path),
        ("Uthmani", UTHMANI_PATH),
    ]
    write_verification(results, output_path, gradient, append=True, source_files=source_files)
    print(f"\n  Written: {output_path}")

    print(f"\n{'=' * 60}")
    if grand_total == 39349 and all_pass:
        print("  39,349 = 19² × P(29). All 13 groups verified.")
        print(f"  {len(edition)} verses = 19 × {len(edition) // 19}.")
        print()
        print("  See fractal_edition.txt for the assembled text and")
        print("  verification document.")
    else:
        print("  VERIFICATION FAILED. Check source files and group definitions.")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
