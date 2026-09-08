# Manuscript formatting and parser contract

The source is not the rendered document. A manuscript check must distinguish layout, executable
markup, mathematics, and prose before measuring any of them. A clean parser pass does not certify
a proof, an empirical claim, or the PDF's reading order.

## Linear exposition

Introduce an object before citing its number. This includes definitions, statements, equations,
figures, tables, algorithms, sections, and chapters. A different reference command does not make
unread material available. Put introductory prose before an object when helpful, but put its
numbered discussion afterward. Do not hide a prerequisite in an appendix or a later definition.

ALL-MANU0001 checks the assembled source order, including imported files. Its defaults cover all
these labeled objects and do not exempt `autoref` or `nameref`. Explicit `proofref` navigation may
point forward only when the resolved target is a proof, not a prerequisite. ALL-MANU0006 checks for a missing
text reference; it no longer requires a float to be announced by a forward reference. PDF review
must check actual float placement separately.

A later proof can name an earlier statement in its heading. ALL-MANU0004 recognizes that explicit
association and source attribution for a cited known result. Attribution is recorded separately
from a proof. The check does not certify that an argument or citation proves the claim.

## Notation ontology

Choose one notation convention per mathematical role and record it in the manuscript's symbol
index. Group that index by related concepts, not alphabetical order alone.

| Role | Convention for the accumulation-forests report |
| --- | --- |
| Number domains | Blackboard letters with explicit bounds; `\mathbb N=\{0,1,\ldots\}`, with `p\ge2` stated separately |
| Vectors and matrices | Bold letters (`\mathbf`), distinct from scalar entries |
| Graphs, trees, circuits | Calligraphic letters, such as `\mathcal{G}`, `\mathcal{T}`, `\mathcal{C}` |
| Node, leaf, and other sets | `\mathcal{N}`, `\mathcal{L}`, `\mathcal{W}` |
| Nodes, coordinates, and scalars | Ordinary italic letters |
| Named operators | Short upright names such as `\lca`; omit only inputs fixed by context |
| Tree-dependent reduction | `\Sigma_{\mathcal T_v}^{\mathbb F_\oplus}` with structure below and accumulator format above |
| Component indices | Adjacent indices without commas; retain commas between function arguments |
| Computed values | Precision superscript for sums; hats for other computed outputs; stars for ideal operands; no tildes |

These choices are a project style, not universal mathematical truth. Standard number domains use
blackboard letters; vectors and matrices use bold letters. The glossary and context still matter. A font alone cannot prove an
expression's type. The report's ancestor map is the node-valued `\lca_{\mathcal{T}}(i,j)`;
whether it deserves a separate definition depends on reuse and clarity, not a lint threshold.
Keep sums explicit. Einstein's implicit summation convention would hide which contributions a
reduction combines, so it is inappropriate for this report's accumulation-order arguments.

Only unify integer bounds after checking their meaning. For example, `\mathbb{Z}_{\ge2}` and
`\mathbb{Z}_{>1}` agree, but `\mathbb{R}_{\ge2}` and `\mathbb{R}_{>1}` do not. Renaming a graph's
node set must not rename an unrelated matrix dimension. Do not autofix either transformation from
raw text alone.

The report uses `\Sigma` for an exact sum and `(\Sigma)_{\mathbb F}` for its once-rounded
value, omitting inputs fixed by context. A structure subscript specifies the tree or subtree.
The computed sum is `\Sigma_{\mathcal T}^{\mathbb F_\oplus}`, without a hat. Its superscript
names the accumulator format; a separate outer conversion specifies the final store.
Tree and format still do not determine the intermediate arithmetic policy.

Structural sets use subscripts such as `\mathcal N_{\mathcal T}`; `\mathcal L(v)` maps a
node to descendant leaves. Keep exponent `e(x)` distinct from its anchor `e_*`; errors use
epsilon or delta. Quantizer maps `Q_E,Q_D` give `(x)_Q=\alpha Q_D(Q_E(x))` with explicit scale.
A Jacobian `\mathrm D f(\mathbf x)` identifies both the map and evaluation point.
These are manuscript choices, not hard-coded parser rules or permission for automatic renaming.

Definition references use Def. or Defs., while displayed definition titles remain complete.
Do not use paragraph environments outside related work. The report-owned `STYLE.md` is the
current source for these editorial choices; shared tooling must not hard-code its chosen symbols.

## What deterministic tooling can establish

- Preserve font and accent identity: `A`, `\mathbb{A}`, and `\widehat{A}` are distinct spellings.
- Canonicalize equivalent source spellings, such as `\mathcal N` and `\mathcal{N}`.
- Expand declared symbol aliases without evaluating TeX, and recognize declared text wrappers.
- Keep `DeclareMathOperator` declarations as operators, never as products of their name's letters.
- Resolve labels and source reading order, including explicitly declared heading aliases.
- Separate paragraphs, proof blocks, description items, table rows, algorithm statements, and
  bibliography entries before computing prose lengths. A provenance comment must not erase the
  blank line after it.
- Preserve a displayed equation's terminal punctuation in the narrative projection while leaving
  its formula tokens out of prose measurements.
- Exclude TeX command implementations, layout arguments, environment delimiters, and text-mode
  annotations from scientific-symbol inventories.
- Read notation entries in both tabular and description-list layouts, and recognize an inline
  equality or a marked term immediately followed by its symbol as an introduction.
- Read each top-level assignment in aligned displays, preserve standard bar accents, and retain
  explicit definitions in captions without treating every caption symbol as a declaration.
- Count symbols explicitly named in an entry's explanatory text as index coverage. Nested
  subsections stay inside the index until the next heading at the index's own level or above.

The current parser implements these structural improvements. The ontology table is a review
contract, not a claim that semantic type checking or every suggested formatting rule is already
implemented. Existing length limits and scientific checks are not disabled.

Safe future autofixes need source ranges and a declared project convention. Bracing an unbraced
font argument is syntax-preserving. Changing a mathematical domain, renaming all `N` symbols, or
moving a theorem is not. Any disagreement with a rule should be raised with the author rather than
hidden by suppressions or a relaxed threshold.

## Scope and declared meaning

ALL-MANU0009 compares explicit role phrases, not the number of introduction sites. Case, spacing,
and a leading article are normalized. Repeating `reduction depth` does not change its meaning.
Giving the same symbol the roles `reduction depth` and `kernel matrix` remains a finding, even
within one section. The obsolete section-count threshold was removed; it had no callers.

A bare equality is not evidence of a changed meaning. An explicit role is attached to the span's
leading mathematical subject, not every symbol in its domain, arguments, or right-hand side.
This prevents a decoder signature from redefining its domain as a decoder. Multiple subjects in
one span and arbitrary descriptive grammar need further support.

The LaTeX scanner recognizes literal sum/product bounds, simple quantifiers, simple set-builder
heads, and parameters on the left of a function-defining equality. Introduction sites in proofs,
theorems, lemmas, propositions, and corollaries are treated as local. First-use and index-coverage
checks use free occurrences; unused-index checks retain all occurrences. A local declaration does
not introduce an unrelated later global use.

A proof that explicitly names its statement inherits that statement's local declarations.
Inside an explicit binder, a one-letter component index may specialize an inherited local
family or an earlier global declaration of that same indexed family. A bare unbound variant
still counts as a free occurrence. This does not make every indexed spelling equivalent to its base. These are bounded
approximations, not full binding/export semantics. Complex dependent binders, macro-generated
scopes, Typst mathematical binders, and arbitrary semantic equivalence remain unsupported.
Different phrases can express the same role; such findings require author review, not automatic
renaming. All introduction sites remain available as facts.

Introduction cues ignore internal math placeholders and retain a coordinated declaration across
`and` or `or`, as in `Let A ... and B ...`. Explicit sentence-leading assumptions and literal
`use ... for ...` names are recognized. Typed noun phrases are read from their own sentence.
A tuple assignment introduces its simple component heads; an arbitrary expression on the left
does not. These additions do not infer the meaning of a product such as `\delta\mathbf y`.

When an index entry explicitly says “A format subscript is used,” its listed symbol also covers
observed variants carrying a blackboard-domain subscript. The negative sentence “No format
subscript is used” supplies no such coverage. The parser retains the index entry's source and
meaning; it does not drop subscripts throughout the document or infer an unstated convention.

Inside a statement, literal operand lists introduced as primitive parameters, quantified lists,
or explicit `use ... for ...` bindings remain local through that statement. Numerical vector
declarations such as `\mathbf a\in\mathbb R^m` supply the scalar entry family `a_j` locally.
Different fonts and expressions such as `\mathbf a+\mathbf b\in\mathbb R^m` do not establish
that declaration. A reduction starting with `\sum_{k=0}^{p-1}d_k` records its literal lower
endpoint `d_0` when `d_k` is declared in the same statement. It does not invent `d_9`, infer
an undeclared family, or resolve an arbitrary index range. Uses after the statement remain free.
An explicit `For i,j\in[K]` clause also binds those simple indices through its statement, so a
previously declared indexed family can be used at either index. A mathematical expression on
the left of membership is not treated as a list of bound names.

A literal tuple such as `\mathbf x=(x_0,\ldots,x_{m-1})` introduces its named coordinates.
A weighted tuple or one using another vector's coordinate names does not. An index row pairing a
bold vector with its matching scalar entries explicitly covers simple one-letter and one-digit
component indices. Merely listing a subscripted scalar, or listing entries of a different vector,
does not declare that family convention. This is index coverage, not a proof of index bounds.

An explicit `denotes` or `means` declaration identifies the operator in a standard infix expression,
not its first operand. An arbitrary scalar product or equality does not supply that declaration.
A sentence- or clause-leading definition verb remains an introduction across a longer intervening
noun phrase, including `For ... , define the two trajectories by ...`.
Opening a math environment preserves that introduction. Unrelated statement, table, and paragraph
boundaries still end it; inline and displayed equations must receive the same prose context.

Finite-family selection remains a limit: knowing `T_1,T_2` and later `s\in\{1,2\}` does not
automatically establish `T_s` across scopes. That needs domain-bearing bindings, including checks
for an undeclared member, a wrong selector domain, and use after the scope ends. The report now
introduces `T_s` directly and distinguishes execution indices from rooted-subtree indices in its
existing tree entry. The parser does not infer that mathematical distinction from the font alone.

Quantitative evidence uses assembled sentences and retains whether a number came from a formula.
An algorithmic radix is not an empirical benchmark measurement. An aggregate ratio needs its
statistic defined; the median of paired ratios cannot be reconstructed from two separate medians.
Literal ratio definitions and linked evidence tables are recognized, but their scientific
correctness still needs review. Citation locators belong to the associated sentence, not a distant
measurement that happens to follow the citation.

## Limits and Typst

The Typst frontend uses the official `typst-syntax` crate, not a regular-expression substitute.
Literal headings, labels, references, equations, included files, prose, lists, and selected
literal-content layout wrappers emit the same structural facts as LaTeX. Mathematical identifiers
are read through Typst's syntax tree, with names such as `alpha` and styling such as `bb(A)` kept
intact. Definitions inside unused `#let` bindings are not manuscript prose. The architecture and
AST contracts are documented by [Typst](https://github.com/typst/typst/blob/main/docs/dev/architecture.md)
and its [syntax crate](https://docs.rs/typst-syntax/0.15.1/typst_syntax/).

This is a literal-document frontend, not a Typst interpreter. Runtime-generated content, show
rules, arbitrary function calls, and unresolved includes stop the scan with a source-located
diagnostic. They do not produce an empty passing verdict. Generated theorem packages, figures,
tables, and bibliography semantics need a later extension with evidence from their evaluated
structure. A static rule pass also does not replace the compiler: for example, a valid reference
label still needs numbering enabled to compile in Typst.

The same contract applies to both frontends: preserve semantic spelling, record source order,
separate rendered blocks, and expose unsupported constructs. Dynamic macro expansion, imported
package behavior, compiled layout, symbol meaning, and proof validity require additional evidence.

First-use and index-coverage rules still depend on explicit syntactic introduction cues. They do
not resolve arbitrary parameterized macros or every indexed family. A prose definition can
therefore be reported as missing. These findings need source review; they are not proof that the
notation is undefined. Do not collapse all indexed symbols merely to silence them.

## One local lint entry

From the workspace root, `mainboard run lint-files <files...>` invokes pre-commit once. The shared
quality hook groups files by their nearest project or manuscript owner. Ruff (including its
pyupgrade rules), Vulture, Lizard, MCMR, Pyrefly, and ty run where applicable; existing file-hygiene,
formatting, spelling, and dependency-audit hooks remain enabled. CUDA headers retain coverage.
Safe repairs are limited to supplied files. Manuscript source is not automatically rewritten.
Type checks and structural checks can inspect the whole owner, so existing neighboring defects
can fail a staged-file run. Normal project owners are checked independently.

There is one explicit unfinished boundary: a workspace-owned file such as `mainboard.toml` has
no narrower MCMR analysis scope. The hook returns a failure rather than scanning sibling projects.
Applicable changed-file checks still run. The missing seam is analysis-path selection through
`Judgment`, `TableExecution`, both analysis-session bindings, `Request`, and native `Scope`.
The latter already coordinates source, history, and route discovery. A proper implementation must
also label partial coverage and prevent repository-wide reachability claims from a file subset.
`repair_paths` restricts edits, not analysis; it cannot provide that boundary.

`pre-commit run --all-files` uses the current repository's tracked files. It does not recurse into
Git submodules. Use explicit submodule file paths with `mainboard run lint-files` when checking
those projects; the report acceptance below used that form. Neither root lint nor one changed-file
run is a claim that every submodule has been checked.
The root formatting task likewise feeds Ruff the NUL-delimited Git-tracked Python file list,
rather than recursing through `ruff .` into submodules or untracked files.

`mcmr prose <manuscript-directory>` exports the shared parser's narrative projection. It preserves
paragraph breaks and display punctuation, without formula tokens, table cells, algorithms,
bibliography entries, or source-marker lines. The manuscript branch of the hook sends that
projection to Vale and proselint. Running those tools directly on TeX is not an equivalent check.

The wrapper uses one class per file, as requested. `Quality` lives beside its CLI functions;
`Changes` and `Result` have their own modules. This also meets the independent module-count limit.
The author approved expected `queue.Empty` waiting as control flow on September 8. The rule now
requires source-resolved queue retrieval rather than accepting any exception named `Empty`.
The watcher normalizes its first queue timeout into an empty batch inside `Changes.batch`; its
outer loop no longer catches exceptions around the whole batching operation. Unrelated failures
still propagate. Unresolved wrapper calls are not exempted by the rule.
Cross-tool repair compatibility is not guaranteed: ALL-STRI0001 merged a fragmented diagnostic
into a long literal that Ruff rejected. The final Ruff pass caught it; shortening the diagnostic
resolved this occurrence without an exemption. General layout-aware repair remains open.

## Validation record: September 8, 2026

The current manuscript-only snapshot is September 8 at 15:27 JST, on the editor's revised
source. The installed command reports zero findings, with all fifteen rules assessed. Earlier
snapshots had ten findings at report commit `88bd3de` and nineteen after the notation rewrite.
Both the manuscript and parser changed afterward; these counts do not measure parser accuracy.

The accumulation-forests report is the real integration workload. The local native extension was
rebuilt without a release. Existing focused Rust and Python manuscript checks exercise the shared
facts and rules: thirteen native checks and nineteen Python checks pass. Ruff and Clippy pass on the
changed code. Whole-table, algorithm, and adjacent-proof paragraph artifacts were reproduced
before repair. The first source-order pass also exposed genuine forward dependencies; these are
reported to the manuscript editor rather than treated as parser exceptions.

A two-file Typst document with numbered headings, a labeled equation, backward references, an
unused heading-producing binding, and a notation list was compiled and analyzed through the
installed local extension. Its manuscript pass produced three nonempty fact families and no
findings. A runtime show rule is rejected as unresolved in the focused native check.
The installed command rejects the show-rule control with a source-located diagnostic and exit
status 2, without a traceback. These are miniature integration fixtures, not a production Typst
paper. No project Typst manuscript was available for validation.

Installed-command controls confirm that an identical role restated in another section and local
function parameters produce no role-collision finding. A reduction-depth/kernel-matrix conflict
within one section produces exactly one finding, with both role phrases in the message.

The final installed manuscript pass has zero findings. All fifteen manuscript rules execute,
with no skipped or unassessed rules:

| Finding family | Count | Interpretation |
| --- | ---: | --- |
| First-use introductions | 0 | Explicit declarations, local components, and displayed introductions are recognized |
| Index coverage | 0 | Vector/entry families and the editor's explicit tree/implementation roles are covered |
| Unused index entries | 0 | The glossary matches the body |
| All other manuscript rules | 0 | Order, proof links, floats, prose shape, role collisions, ratios, and citation locators pass |

The final source no longer needs the compound linear-prediction variable. It defines both the
reference and implemented trajectories, states the binary infix notation explicitly, and names
the execution-indexed tree directly. These were editorial and mathematical changes, not parser
exceptions. Component families and local bindings close the other cases without equating arbitrary
subscripts. Finite selector domains and ambiguous perturbation prefixes remain unsupported in
general, even though this manuscript no longer triggers those limits.

This follow-up repaired scoped component bindings, literal coordinate tuples, declared lower
endpoints, vector/entry index coverage, infix declaration heads, and the introduction cue across
clause and displayed-math boundaries. The controls retain unbound and out-of-scope variants,
undeclared families, wrong fonts, weighted tuples, and negative index conventions.
The previous 13:23 JST snapshot had 27 findings; a later edited-source snapshot had 29. Those
historical counts are superseded, not a controlled accuracy comparison.

The parser's scope and family obligations are not exhaustively discharged. A zero count is not
semantic certification of the document. No threshold was raised for this parser work and no
finding was suppressed.
The scope/meaning policy changed with the author's approval, and the report was edited
concurrently, so the finding reduction is not a controlled parser-accuracy benchmark. The
separately requested class-field default remains 64 for ALL-CLAS0004.

The earlier paper-file invocation of `mainboard run lint-files` completed at the ten-finding
manuscript snapshot. Its official prose export, Vale, and proselint each exited zero. Owner-wide
MCMR reported eighty findings: ten manuscript findings plus seventy figure-source policies.
That broader pass executed 204 of 226 applicable/catalog rules and recorded 22 skipped rules.
It was not rerun for the 15:27 manuscript-only snapshot, so its count is historical. The dependency audit
independently reports NLTK 3.10.3 advisory `PYSEC-2026-3740`, with no fixed version listed, and
cannot audit several editable or nightly packages. This records tool output, not an independent
security assessment. No dependency exemption was added.

The normal-owner runtime-hook invocation executes Ruff, Vulture, Lizard, MCMR, Pyrefly, and ty.
Eight existing hook checks pass. The current MCMR pass records 14 findings, with 223 of 226 rules
executed and three skipped. Class count, module count, owner complexity, watcher nesting, and the
document phase's condition count pass. The prior count of 17 included two repeated queue-handler
findings and watcher nesting; the approved waiting behavior and smaller outer loop close those.
The wrapper grew from 304 to 454 lines across three files; it is a functional consolidation, not a
demonstrated reduction in wrapper size. Replacing the existing polling loop with Watchdog's
debouncer is not automatically simpler: its callback holds the condition lock, so long lint work
would block event delivery without another coordination layer.

The remaining hook findings are:

| Rule | Count | Reported issue |
| --- | ---: | --- |
| ALL-ENCA0001 | 2 | Tests call or capture the protected checker method |
| ALL-REAC0001 | 2 | Imported `Changes` and `Result` are not reached by the extracted graph |
| PY-COLL0004 | 2 | Immutable sets constructed from set literals |
| PY-EXCE0002 | 1 | Existing bounded process/watcher exception regions |
| PY-IMPO0004 | 3 | Test relative imports classified beyond the scanned package |
| PY-MODU0002 | 1 | Existing empty package initializer |
| PY-TEST0004 | 1 | Existing pytest strictness configuration |
| PY-TEST0005 | 1 | Existing pytest import mode |
| PY-TYPE0003 | 1 | Python declaration in the hook's type-checker-only project file |

No numeric limit was relaxed. In particular, a runtime-successful relative import and a static graph's
failure to resolve it are different observations; the latter still needs a package-boundary repair.
The nested test fake was replaced with pytest's monkeypatch, leaving one test support class.

Acceptance logs are `/tmp/mcmr-sept8-final-installed.log`,
`/tmp/mcmr-sept8-paper-precommit.log`, `/tmp/quality-three-module-precommit.log`, and
`/tmp/quality-root-boundary.log`. The latter explicitly fails without a workspace scan. Native
controls, Python manuscript controls, and hook controls are recorded separately in
`/tmp/mcmr-sept8-final-controls.log`, `/tmp/mcmr-sept8-final-python.log`, and
`/tmp/quality-three-module-tests.log`. The prior complete hook finding list is
`/tmp/quality-three-module-policy.log`.

The approved queue follow-up is recorded in `/tmp/mcmr-queue-precommit.log` and
`/tmp/mcmr-queue-owner-final.log`. All non-MCMR source-quality checks pass. MCMR retains the
14 findings above, while its targeted `ALL-ERRO0001` pass records zero findings. The preserved
dependency audit still fails independently on the NLTK advisory. This is not a clean full gate.
The real idle watch exits successfully, and the eight existing hook controls pass. Another
38 focused error-rule and oracle controls pass, along with the native try-region control,
Clippy, Ruff, and targeted Pyrefly checks. The package catalog check has 11 passes and one failure
from punctuation in seven existing manuscript-rule docstrings; the queue rule is no longer in
that failure. No unrelated rule was disabled.

The queue rule reads two additional primitive fields from the existing Python AST pass. A sole
protected call can resolve through an imported constructor or a parameter annotation. Exception
identity must resolve through an absolute import. Rebinding, conditional imports, unavailable
source-order bindings, mixed catches, and compound calls remain unresolved or flagged. The
analysis does not infer exception effects across methods, prove runtime receiver types, or model
arbitrary dynamic module replacement. Returning an empty batch removes the watcher's need for
such intermethod inference without hiding other failures.

On September 8 the author authorized retaining the reviewed work on the development branch,
without a release or a merge into `main`. The manuscript and queue checks passed 55 focused
Python cases before that commit. The previously separate repair-path and 64-field-limit changes
were then reviewed in place; their 31 focused cases passed. These checks do not establish a clean
whole-package gate. The local `dev` branch includes the four existing non-main commits by a
fast-forward, preserving their history. The parent committed the root lint integration separately
as `968eaeef` and the two-file watcher simplification as `9f9dab13`.
