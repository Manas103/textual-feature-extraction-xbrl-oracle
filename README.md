# Textual Feature Extraction Checked Against a Numeric Oracle

Two independent ways of reading the same real SEC filing, cross-checked against each
other. The text path reads a filing's own human-written presentation label (what a
reader sees on the income statement, balance sheet or cash flow statement); the oracle
path looks the same concept up by its standard XBRL tag name alone, never touching a
label. Python 3.12, DuckDB, pandas, pytest, over 22,387 real 10-Q and 10-K filings from
SEC EDGAR's own bulk Financial Statement Data Sets. Every number below was measured on
this machine by running the real code against real, downloaded SEC data, not targeted
in advance.

## Why this exists

A data scientist checking vendor data for a trading firm does not get to assume a
filer's prose and a filer's own structured tags agree. This project builds the
smallest honest version of that check: 9 financial concepts (revenue, cost of revenue,
net income, total assets, total liabilities, stockholders' equity, operating cash flow,
diluted EPS, diluted weighted-average shares), extracted two structurally independent
ways from the same real filings, with every disagreement attributed to a named cause
rather than silently averaged away.

## Honest framing, up front

- **Every filing is real.** Nothing here is simulated. The source is SEC's own
  quarterly "Financial Statement Data Sets"
  (`https://www.sec.gov/dera/data/financial-statement-data-sets.html`), four pipe-delimited
  files (`sub.txt`, `num.txt`, `pre.txt`, `tag.txt`) covering every XBRL-tagged
  submission that quarter. This project uses four real quarters (2025q3, 2025q4,
  2026q1, 2026q2), filtered to forms 10-Q and 10-K, 22,387 filings.
- **"Textual" means the filing's own presentation label, not OCR or free-form prose.**
  `pre.txt`'s `plabel` column is the literal text string the filer chose to print next
  to a number on its primary financial statements (`"Net (loss) income"`, `"Total
  Stockholder's Equity"`, `"COGS"`); this project matches that string by keyword rule,
  independent of the tag the filer also attached to the same line.
- **The oracle never reads a label.** `featurex/oracle.py` looks a concept up by a
  fixed, closed, pre-declared set of standard `us-gaap` tags only
  (`featurex/config.py::ORACLE_TAGS`), chosen from the tags' own published definitions
  before any disagreement was measured. A filing that tags revenue with a custom,
  non-standard concept simply has no oracle value for revenue, by design.
- **A declared simplification: one quarterly duration per 10-Q, not the year-to-date
  column too.** A 10-Q's income statement and cash flow figures often carry both a
  3-month and a year-to-date XBRL fact for the same line; this project always takes the
   3-month (quarterly) one (`featurex/resolve.py::expected_qtrs`).
- **A declared simplification: the consolidated figure only.** Every lookup requires
  `coreg IS NULL AND segments IS NULL`, the top-of-statement, non-segment, non-guarantor
  value. Segment and co-registrant breakdowns are real rows in the data and are
  deliberately excluded.
- **Machine and toolchain.** 8 physical / 16 logical cores, Windows 11 Home, Python
  3.12.10, DuckDB 1.5.6, pandas 3.0.6, pyarrow 26.0.0, pytest 9.1.1.
- **SEC's own fair-access policy was followed.** All downloads used a descriptive
  `User-Agent` with a real contact address, and the quarterly bulk zips (not a
  per-filing crawl) are the only files fetched, four HTTP requests total.

## Architecture

```
featurex/
  config.py       9 fields, oracle tag sets, text-match rules, tolerances
  download.py     fetch + cache the 4 real SEC quarterly bulk zips
  load.py         DuckDB schema; loads sub/num/pre filtered to 10-Q/10-K
  text_extract.py the text path: match a field's rule against pre.txt plabel
  resolve.py      turn a (adsh, tag) candidate into one real num.txt value
  oracle.py       the oracle path: look a field up by tag name alone
  reconcile.py    join both paths, classify every disagreement by cause
  pit.py          point-in-time acceptance-timestamp guard (and its leaky twin)
  measurements.py the 5 claim measurements
scripts/
  download_data.py   idempotent downloader
  build.py           builds data/featurex.duckdb from the raw files
  run_measurements.py runs the full reconciliation, prints every claim
tests/
  test_text_rules.py          unit tests on real plabel strings
  test_reconcile_synthetic.py one handcrafted filing per disagreement cause
  test_real_data.py           integration tests against the real database
```

**Why two separate resolution paths share one `resolve.py`, not two.** Both the text
path and the oracle path need the identical "pick the consolidated, correct-duration
value" logic; duplicating it would let the two paths silently drift on something that
has nothing to do with labels or tags (a duration bug, say) and call that a
"disagreement" when it is really the same bug counted twice. Sharing it means every
real disagreement traces back to the one thing that actually differs between the two
paths: how the field was identified, not how its value was looked up.

**Why `has_alt_duration` is computed inside the same query, not as a second pass.** The
`duration_mismatch` cause needs to know, for the specific candidate the text path
picked, whether a different `qtrs` value for that same tag would have agreed with the
oracle. Computing that as a correlated `EXISTS` subquery in the same DuckDB query that
resolves the primary value keeps the two facts (the value, and whether a better
duration existed) consistent by construction.

## Validation

### Unit tests: one handcrafted filing per disagreement cause

`tests/test_reconcile_synthetic.py` builds six synthetic filings in an in-memory
DuckDB database, one engineered to trigger each disagreement cause
(`label_not_matched`, `sign_mismatch`, `duration_mismatch`,
`custom_tag_different_concept`, `unexplained_value_mismatch`) plus one clean agreement,
and asserts the classifier names the cause correctly on each. See
`docs/test_output.txt`.

### Integration tests against the real database

`tests/test_real_data.py` runs the actual pipeline against the real, downloaded SEC
data and checks all 5 claims. These skip (not fail) if the multi-gigabyte bulk files
have not been downloaded on the machine running the tests.

## Findings

**The text-match rules were wrong in specific, fixable ways on the first pass, and
right in a specific, not-fixable way on the last one.** The first version of
`TEXT_RULES` reached 75.5% field agreement. Inspecting the actual `label_not_matched`
rows (not the aggregate number) surfaced four real gaps: bare `"Revenue"` (singular,
no "s") was not matched by a rule that only looked for `"revenues"`; `"Net (loss)
income"` was not matched by a rule that looked for the literal substring `"net
income"`, because the parenthetical breaks it; `"Total Stockholder's Equity"` was not
matched by a rule looking for `"stockholders"` (plural, no apostrophe); and
`"Net cash provided from operating activities"` (the word "from", not "by" or "used
in") was missed entirely. Fixing these four, plus adding the real BDC/fund vocabulary
("Total Net Assets" for equity, "COGS" for cost of revenue), raised agreement to 85.7%
over three genuine passes. The remaining gap is not a rule bug: a real, recurring
pattern is a bare `"Diluted"` or `"Basic"` plabel with no other distinguishing word on
the line, used for both the EPS value and the share count elsewhere in the same
statement, distinguishable only by position in the table, not by the label text
itself. This project does not attempt that (it would stop being label-based text
extraction and start being statement-layout parsing), and discloses it as the largest
single remaining cause of `label_not_matched`.

**A real SEC data quirk: some `num.txt` rows have a present tag and a blank value.**
Early measurement showed oracle and text paths both resolving to the exact same tag for
a filing yet somehow disagreeing, which should be structurally impossible since they
share `resolve.py`. The cause was a handful of real `num.txt` rows (`adsh
0000001961-26-000014`'s `Revenues` fact, among others) where the tag, period and
duration are all present but `value` is blank in SEC's own bulk file. `resolve.py` now
filters `value IS NOT NULL` explicitly; those (filing, field) pairs correctly drop out
of the measured denominator instead of comparing `NaN` to `NaN`.

**The point-in-time guard mattered: the naive version really did leak.**
`pit.leaky_filed_date_as_of` (a deliberately wrong filter kept only to measure the leak
it causes) filters by a filing's `filed` date alone; the correct
`pit.features_as_of` filters by the real `accepted` timestamp. At a cutoff set to the
start of this dataset's single busiest filing day, the naive date-only filter leaked
623 filings' worth of features that were not actually public yet at that hour; the
timestamp-based filter leaked zero. See `measure_point_in_time` in
`docs/measurement_output.txt`.

## Measured results

Machine: 8 physical / 16 logical cores, Windows 11 Home, Python 3.12.10, DuckDB 1.5.6.

- **9 fields extracted from 22,387 real 10-Q/10-K filings** (claimed 14,000+, exceeded;
  `measure_scale`).
- **Point-in-time discipline holds: 0 rows leaked by the accepted-timestamp filter,
  623 leaked by the naive filed-date filter it replaced** (`measure_point_in_time`).
- **The oracle path is deterministic**: re-run twice on the same data, byte-identical
  output, 16,263 rows (`measure_oracle_determinism`).
- **Field agreement measured at 85.7% (136,583 of 159,395 in-scope fields), against a
  claimed 99.0%, after 3 genuine attempts at the text-match rules.** This is reported
  as measured, not adjusted to the claim; see Findings above and the per-field table in
  `docs/measurement_output.txt` for where the gap concentrates (`net_income` 72.0%,
  `eps_diluted` 73.0%, versus `total_assets` 98.7%, `total_liabilities` 98.9%).
- **Every one of the 22,812 measured disagreements is classified by a named cause, 0
  unclassified**: `label_not_matched` 15,725, `duration_mismatch` 3,263,
  `custom_tag_different_concept` 1,920, `unexplained_value_mismatch` 1,879,
  `sign_mismatch` 25 (`measure_disagreement_classification`).

The scope of "agreement" is deliberately narrow: a (filing, field) pair only enters the
denominator when the oracle itself has a value, so the 99.0%-vs-85.7% gap is not
inflated by filings that never reported a concept at all.

## Building and running

```
python -m venv venv
venv\Scripts\python -m pip install -r requirements.txt

python scripts/download_data.py      # 4 real SEC quarterly zips, ~340 MB combined
python scripts/build.py              # builds data/featurex.duckdb, ~1-2 minutes
python scripts/run_measurements.py > docs/measurement_output.txt
venv\Scripts\python -m pytest tests -v > docs/test_output.txt
```

## Limitations

- The text-match rules are keyword-based, not a general NLP model; they were revised
  against this dataset's actual vocabulary and will miss filer-specific phrasing not
  seen in that process (see Findings).
- A bare `"Diluted"`/`"Basic"` plabel with no other word is not resolved; this is the
  largest remaining component of `label_not_matched` and is a label-only-extraction
  limitation stated deliberately rather than worked around with statement-position
  heuristics.
- 10-Q year-to-date XBRL facts are not considered, only the single-quarter duration
  (declared above).
- `net_income`'s oracle priority (`NetIncomeLoss` over `ProfitLoss`) picks the
  parent-attributable figure when a filing reports both that and the
  including-noncontrolling-interest figure; a text match that lands on the other one is
  real and currently falls into `unexplained_value_mismatch` rather than a more
  specific cause.
