# Roadmap

MCMR is in its early public releases. The current focus is a dependable deterministic core,
an honest opt-in boundary for model and network work, and integrations that preserve useful policy
history without owning repository state.

## Foundation

- [x] Parse Python, Rust, TypeScript, C, C++, and CUDA repositories
- [x] Expose one typed Polars table per fact family
- [x] Run each selected rule once over shared facts
- [x] Separate deterministic, contextual, and external execution lanes
- [x] Report exact findings through Rich, concise, plain, and JSON formats
- [x] Preview and verify safe source repairs
- [x] Discover installed rule and provider packages through public entry points
- [x] Keep default runs stateless and free of hidden repository artifacts

## First public release

- [x] Finish the public package metadata and publish to PyPI
- [x] Publish the documentation site and set its canonical URLs
- [ ] Keep the deterministic self-scan free of unexplained failures
- [ ] Review every contextual rule against a representative quality sample
- [x] Document expected model cost and request batching for contextual runs
- [ ] Stabilize scan-level path exclusion
- [ ] Add release smoke tests from a clean source archive and wheel
- [ ] Verify installation and the demo on Linux and macOS

## Policy engine

- [ ] Group the wide `CallSite` fact into cohesive typed records while preserving clear rule queries
- [ ] Count literals used directly as call arguments in literal grouping
- [ ] Improve suppression repairs with stable previews and semantic cases
- [ ] Make module move previews propose only cohesive moves into existing sibling modules
- [ ] Expand conservative repairs where the source facts prove one unambiguous outcome

## DataHub integration

- [x] Read schemas, lineage, ownership, tags, and glossary context through GraphQL
- [x] Resolve literal SQL references without guessing ambiguous asset identities
- [x] Publish fact datasets, repository flows, global rules, and run instances
- [x] Record one assertion timeline per rule and governed subject
- [x] Read prior verdicts through `mcmr history`
- [x] Carry contextual model and token provenance into published verdicts
- [x] Close stale per-file verdicts and resolve stabilized incidents
- [ ] Test writeback against the newest supported DataHub Core release
- [ ] Add safe retries and clearer receipts for partially accepted writeback batches
- [ ] Enrich run instances when DataHub supports ownership, glossary, and structured properties on
      that entity type
- [ ] Document compatibility across supported DataHub versions

## Package ecosystem

- [ ] Publish a minimal third-party rule package template
- [ ] Publish a minimal external evidence provider template
- [ ] Add compatibility tests for independently installed plugins
- [ ] Version the fact schema separately from the command line interface

## Release standard

A release is ready when a clean checkout installs through Chefe, all Python and Rust gates pass,
the deterministic self-scan has no unexplained failures, the demo output matches its documentation,
the wheel and source archive install cleanly, and every enabled integration states its network and
write behavior before it runs.
