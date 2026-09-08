# Search contract

## Venue scope

Primary core: NeurIPS, ICML, ICLR, AAAI, IJCAI.

MAS-required: AAMAS.

For LLM/NLP-agent topics, add ACL Main and EMNLP Main. Add ACL Findings and
EMNLP Findings as secondary proceedings. Include arXiv-only preprints as a
common secondary lane for every topic.

## Inclusion and exclusion

Include main technical or research tracks, including long, short, oral,
spotlight, and poster papers. Label Findings explicitly.

Exclude workshops, tutorials, demos, student research workshops, doctoral
consortia, and extended abstracts unless the user expands the scope.

An official proceedings page is formal evidence. An official accepted list is
provisional accepted evidence. A submission page without an acceptance signal
does not establish acceptance.

## Version graph

Each result preserves all manifestations:

- `canonical_citation_url`: official proceedings when verified;
- `reading_copy_url`: arXiv when available, otherwise the citation version;
- `acceptance_evidence_url`: the official page establishing status;
- `versions[]`: source-specific metadata without destructive collapse.

Status values:

- `verified_proceedings`
- `verified_accepted`
- `candidate_unverified`
- `preprint_only`

## Coverage

Every requested venue-year pair must produce one coverage row with official
source, status, enumerated count, direct keyword matches, and error if any.
When the registry pins an official record count, report `success` only for an
exact match; otherwise report `partial` and state the expected and parsed
counts. Result limits are applied only after all venue-year attempts finish.

## Semantic recall

Literal keyword matching is only one candidate-generation lane. For each user
request, retain the original query and add three to five meaning-preserving
variants covering:

- alternate technical terminology and acronyms;
- mechanism or behavior descriptions;
- older terminology or application-specific phrasing.

Run all variants against the same venue-year scope, merge manifestations before
the result cap, and record the variants in `query_variants`. Then screen titles
and abstracts against explicit semantic inclusion criteria. Query variants are
recall aids, not evidence of relevance; reject semantic drift during screening.
When an abstract is missing and the title is insufficient, label the record
uncertain instead of treating it as irrelevant.
