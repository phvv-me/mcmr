/// Control sequences that shape mathematics rather than name a quantity in it.
///
/// A reader does not look `\frac` up in the notation index, so counting it as a symbol would bury
/// the ones they do look up. The list is deliberately about structure, operators and delimiters,
/// which is what every document shares, and never about one project's own names.
const STRUCTURAL: &[&str] = &[
    "Big",
    "Bigg",
    "Biggl",
    "Biggm",
    "Biggr",
    "Bigl",
    "Bigm",
    "Bigr",
    "Delta",
    "Gamma",
    "Lambda",
    "Leftarrow",
    "Omega",
    "Phi",
    "Pi",
    "Psi",
    "Rightarrow",
    "Sigma",
    "Theta",
    "Upsilon",
    "Xi",
    "approx",
    "big",
    "bigg",
    "bmatrix",
    "bmod",
    "cdot",
    "cdots",
    "circ",
    "colon",
    "coloneqq",
    "cup",
    "cap",
    "dfrac",
    "displaystyle",
    "dots",
    "biggl",
    "biggm",
    "biggr",
    "bigl",
    "bigm",
    "bigr",
    "emptyset",
    "epsilon",
    "equiv",
    "exists",
    "forall",
    "frac",
    "ge",
    "geq",
    "gg",
    "hat",
    "hbox",
    "in",
    "infty",
    "int",
    "iff",
    "implies",
    "int",
    "label",
    "land",
    "langle",
    "ldots",
    "le",
    "left",
    "leftarrow",
    "leq",
    "ll",
    "lor",
    "mapsto",
    "mathbb",
    "mathbf",
    "mathcal",
    "mathfrak",
    "mathit",
    "mathrm",
    "mathsf",
    "max",
    "mid",
    "min",
    "mspace",
    "neg",
    "neq",
    "nonumber",
    "not",
    "notin",
    "operatorname",
    "overline",
    "partial",
    "pmatrix",
    "pm",
    "prod",
    "propto",
    "qquad",
    "quad",
    "rangle",
    "right",
    "rightarrow",
    "setminus",
    "sim",
    "simeq",
    "sqrt",
    "subset",
    "subseteq",
    "substack",
    "sum",
    "text",
    "textrm",
    "tfrac",
    "tilde",
    "times",
    "to",
    "top",
    "underbrace",
    "underline",
    "vdots",
    "vec",
    "widehat",
    "widetilde",
];

/// Operator names a reader reads as a word rather than as a quantity.
const OPERATORS: &[&str] = &[
    "arccos", "arcsin", "arctan", "cos", "cosh", "det", "dim", "exp", "gcd", "inf", "ker", "lim",
    "liminf", "limsup", "ln", "log", "sin", "sinh", "sup", "tan", "tanh",
];

/// Control sequences whose group holds words rather than symbols.
///
/// `\mathrm{fl}` is one operator a reader says out loud, not an `f` beside an `l`, and
/// `\text{exactly}` is a sentence. Reading their letters as symbols would bury every real symbol
/// under the alphabet. A font command that keeps its argument mathematical, such as `\mathcal`
/// or `\mathbf`, is deliberately not here, since its argument is still a symbol.
const TEXTUAL: &[&str] = &[
    "hbox",
    "label",
    "mbox",
    "mathrm",
    "operatorname",
    "text",
    "textbf",
    "textit",
    "textrm",
    "textsc",
    "textup",
];

/// The relations that read as a definition when a symbol stands alone on their left.
const DEFINING: &[&str] = &[":=", "\\coloneqq", "\\equiv", "\\triangleq", "="];

/// Return the symbols one math span names, each spelled the way the reader meets it.
///
/// A symbol is a control sequence the lists above do not claim, or a single letter, and the
/// subscript immediately after it travels with it. Keeping the subscript is what separates
/// `m_i` from `m_e`, which is the granularity a notation index is actually written at and
/// therefore the only granularity at which its completeness can be checked.
pub fn named(math: &str) -> Vec<String> {
    let characters: Vec<char> = math.chars().collect();
    let mut found = Vec::new();
    let mut index = 0usize;
    while index < characters.len() {
        let (symbol, next) = read_symbol(&characters, index);
        index = next;
        if let Some(base) = symbol {
            let (script, after) = read_subscript(&characters, index);
            index = after;
            found.push(format!("{base}{script}"));
        }
    }
    found
}

/// Return the symbol a display defines, when it defines exactly one.
///
/// A display whose left side is a single symbol and whose relation is an equality is the shape
/// every definition is written in, so that symbol is the one being introduced. Anything more
/// elaborate on the left is an equation about symbols the reader already has.
pub fn defined(math: &str) -> Option<String> {
    let body = math.split("\\\\").next().unwrap_or(math);
    let relation = DEFINING
        .iter()
        .filter_map(|token| body.find(token).map(|at| (at, *token)))
        .min_by_key(|(at, _)| *at)?;
    let left = &body[..relation.0];
    let symbols = named(left);
    match symbols.len() == 1 && named(left).first().is_some_and(|one| !one.is_empty()) {
        true => symbols.into_iter().next(),
        false => None,
    }
}

/// Whether one control sequence names a quantity rather than shaping the mathematics around it.
fn is_quantity(name: &str) -> bool {
    !name.is_empty() && !STRUCTURAL.contains(&name) && !OPERATORS.contains(&name)
}

/// Read whatever symbol starts at one index, returning it and where reading stopped.
fn read_symbol(characters: &[char], index: usize) -> (Option<String>, usize) {
    match characters[index] {
        '\\' => read_control(characters, index),
        letter if letter.is_ascii_alphabetic() => (Some(letter.to_string()), index + 1),
        _ => (None, index + 1),
    }
}

/// Read one control sequence, keeping it only when it names a quantity.
fn read_control(characters: &[char], index: usize) -> (Option<String>, usize) {
    let mut end = index + 1;
    while characters.get(end).is_some_and(char::is_ascii_alphabetic) {
        end += 1;
    }
    let name: String = characters[index + 1..end].iter().collect();
    if TEXTUAL.contains(&name.as_str()) {
        return (None, skip_group(characters, end));
    }
    match is_quantity(&name) {
        true => (Some(format!("\\{name}")), end),
        false => (None, end.max(index + 1)),
    }
}

/// Skip the balanced group a text-mode command takes, when one follows it.
fn skip_group(characters: &[char], index: usize) -> usize {
    if characters.get(index) != Some(&'{') {
        return index;
    }
    let mut end = index + 1;
    let mut depth = 1usize;
    while end < characters.len() && depth > 0 {
        depth = match characters[end] {
            '{' => depth + 1,
            '}' => depth - 1,
            _ => depth,
        };
        end += 1;
    }
    end
}

/// Read the subscript attached to a symbol, which is part of how the reader spells it.
fn read_subscript(characters: &[char], index: usize) -> (String, usize) {
    if characters.get(index) != Some(&'_') {
        return (String::new(), index);
    }
    if characters.get(index + 1) == Some(&'\\') {
        let mut end = index + 2;
        while characters.get(end).is_some_and(char::is_ascii_alphabetic) {
            end += 1;
        }
        let script: String = characters[index + 1..end].iter().collect();
        return (format!("_{script}"), end);
    }
    if characters.get(index + 1) != Some(&'{') {
        let script: String = characters[index + 1..].iter().take(1).collect();
        return (format!("_{script}"), index + 2);
    }
    let mut end = index + 2;
    let mut depth = 1usize;
    while end < characters.len() && depth > 0 {
        depth = match characters[end] {
            '{' => depth + 1,
            '}' => depth - 1,
            _ => depth,
        };
        end += 1;
    }
    let script: String = characters[index + 2..end.saturating_sub(1)]
        .iter()
        .collect();
    (format!("_{{{script}}}"), end)
}
