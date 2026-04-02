# quran-fractal

**39,349 = 19² × P(29)**

Verification script and assembled Quran text for the [74:30 Project](https://7430project.com).

## What This Is

The Quran contains 29 chapters marked with combinations of Arabic letters called the Muqatta'at. Chapter 74, verse 30 states: *"Over it are nineteen."*

When you count the named letters across their chapters, grouped by their shared initials, you get 13 totals. All 13 divide by 19. Their sum — 39,349 — equals 19² × 109, where 109 is the 29th prime and 29 is the number of marked chapters. That same number is also the total word count of those 29 chapters.

This repository contains everything needed to verify this independently.

## Quick Start

```
git clone https://github.com/7430project/quran-fractal.git
cd quran-fractal
python3 verify.py
```

The script outputs `fractal_edition.txt` — the assembled Quran text with the complete verification proof appended.

Upload `fractal_edition.txt` to any AI and ask it to verify the claims.

## What's In the Repo

| File | Description |
|------|-------------|
| `verify.py` | Assembles the Fractal Edition, counts every letter, verifies all 13 groups |
| `tanzil_data/quran-simple-plain.txt` | Tanzil Simple-Plain edition (source) |
| `tanzil_data/quran-uthmani.txt` | Tanzil Uthmani edition (source) |

## What the Script Does

1. Loads both Quran source texts from tanzil.net
2. Assembles the Fractal Edition (correct edition per surah)
3. Applies verse merges (surahs 19, 20, 31, 36) and word corrections
4. Counts every Muqatta'at letter in every group from the assembled text
5. Verifies all 13 groups divide by 19
6. Verifies the grand total = 39,349 = 19² × P(29)
7. Writes `fractal_edition.txt` with the Quran text and verification proof

## The 13 Groups

| # | Group | Surahs | Total | ÷19 | Tier |
|---|-------|--------|------:|----:|------|
| 1 | ALM | 2,3,29,30,31,32 | 18,012 | 948 | 1 |
| 2 | ALR | 10,11,12,14,15 | 7,828 | 412 | 2 |
| 3 | ALMR | 13 | 1,178 | 62 | 2 |
| 4 | ALMS | 7,38 | 4,997 | 263 | 1 |
| 5 | HM | 40-46 | 2,147 | 113 | 1 |
| 6 | ASQ | 42 | 209 | 11 | 1 |
| 7 | Q | 50 | 57 | 3 | 1 |
| 8 | KHYAS | 19 | 798 | 42 | 1 |
| 9 | TSM | 26,28 | 1,178 | 62 | 1 |
| 10 | YS | 36 | 285 | 15 | 1 |
| 11 | N | 68 | 361 | 19 | 2 |
| 12 | TH | 20 | 1,292 | 68 | 2 |
| 13 | TS | 27 | 1,007 | 53 | 2 |
| | **Total** | | **39,349** | **2,071** | |

**Tier 1** (8 groups): Zero parameters. Consonants + plain alif only. Encoding-independent. (1/19)⁸ ≈ 10⁻¹⁰.

**Tier 2** (5 groups): Constrained. Require specific Uthmani alif variants. Not load-bearing — reject all five and the core result is unchanged.

## Requirements

- Python 3.6+
- No external dependencies (standard library only)

## Source Data

Quran text from [tanzil.net](https://tanzil.net) under [Creative Commons Attribution 3.0](https://creativecommons.org/licenses/by/3.0/).

SHA-256 hashes of source files are included in the output for verification.

## Project

- Website: [7430project.com](https://7430project.com)
- Download: [unzip.zip](https://7430project.com/unzip.zip)

*Don't believe me. Count.*
