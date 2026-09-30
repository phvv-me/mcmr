use super::cursor::Cursor;
use super::delimiter::BRACE;
use std::collections::{BTreeMap, BTreeSet};

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
    "Leftarrow",
    "Rightarrow",
    "approx",
    "big",
    "binom",
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
    "equiv",
    "exists",
    "forall",
    "frac",
    "ge",
    "geq",
    "gets",
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
    "lceil",
    "lfloor",
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
    "ne",
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
    "rceil",
    "rfloor",
    "right",
    "rightarrow",
    "setminus",
    "sim",
    "simeq",
    "sqrt",
    "star",
    "subset",
    "subseteq",
    "substack",
    "sum",
    "text",
    "textstyle",
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
    "begin",
    "end",
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

/// Font and accent are part of a symbol's identity, not merely source decoration.
const STYLED: &[&str] = &[
    "bar",
    "boldsymbol",
    "hat",
    "mathbb",
    "mathbf",
    "mathcal",
    "mathfrak",
    "mathit",
    "mathsf",
    "overline",
    "tilde",
    "vec",
    "widehat",
    "widetilde",
];

/// The relations that read as a definition when a symbol stands alone on their left.
const DEFINING: &[&str] = &[":=", "\\coloneqq", "\\equiv", "\\triangleq", "="];

/// Expand declared symbol aliases only; never execute TeX or recursively expand a cycle.
pub fn expanded(math: &str, aliases: &BTreeMap<String, String>) -> String {
    expand_aliases(math, aliases, &mut Vec::new())
}

fn expand_aliases(
    math: &str,
    aliases: &BTreeMap<String, String>,
    active: &mut Vec<String>,
) -> String {
    let mut cursor = Cursor::new(math);
    let mut output = String::new();
    while let Some(character) = cursor.bump() {
        if character != '\\' {
            output.push(character);
            continue;
        }
        let name = cursor.take_while(|character| character.is_ascii_alphabetic());
        if let Some(replacement) = aliases.get(&name).filter(|_| !active.contains(&name)) {
            active.push(name.clone());
            output.push_str(&expand_aliases(replacement, aliases, active));
            active.pop();
        } else {
            output.push('\\');
            output.push_str(&name);
        }
    }
    output
}

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
            let mut script = String::new();
            let mut powers = Vec::new();
            loop {
                while characters
                    .get(index)
                    .is_some_and(|character| character.is_whitespace())
                {
                    index += 1;
                }
                if characters.get(index) == Some(&'_') {
                    (script, index) = read_subscript(&characters, index);
                } else if characters.get(index) == Some(&'^') {
                    let start = index + 1;
                    let end = if characters.get(start) == Some(&'{') {
                        skip_group(&characters, start)
                    } else if start < characters.len() {
                        read_symbol(&characters, start).1
                    } else {
                        start
                    };
                    let power: String = characters[start..end].iter().collect();
                    let power = power
                        .strip_prefix('{')
                        .and_then(|body| body.strip_suffix('}'))
                        .unwrap_or(&power);
                    if !matches!(power, "\\mathsf{T}" | "\\mathrm{T}" | "\\top") {
                        powers.extend(named(power));
                    }
                    index = end;
                } else {
                    break;
                }
            }
            found.push(format!("{base}{script}"));
            found.extend(powers);
        }
    }
    found
}

/// A literal one-letter component index can be renamed by an explicit local binder.
pub fn indexed(name: &str) -> Option<(&str, &str)> {
    let (base, index) = name.rsplit_once('_')?;
    let index = index
        .strip_prefix('{')
        .and_then(|index| index.strip_suffix('}'))
        .unwrap_or(index);
    (index.len() == 1
        && index
            .chars()
            .all(|character| character.is_ascii_alphabetic()))
    .then_some((base, index))
}

/// A literal component list identifies its named endpoints, not arbitrary expressions.
pub fn listed(math: &str) -> Vec<String> {
    let Some((left, right)) = ["\\ldots", "\\cdots", "\\dots"]
        .iter()
        .find_map(|dots| math.split_once(dots))
    else {
        return Vec::new();
    };
    let left = named(left)
        .into_iter()
        .rev()
        .find(|name| name.contains('_'));
    let right = named(right).into_iter().find(|name| name.contains('_'));
    let (Some(left), Some(right)) = (left, right) else {
        return Vec::new();
    };
    if left.rsplit_once('_').map(|(base, _)| base) != right.rsplit_once('_').map(|(base, _)| base)
    {
        return Vec::new();
    }
    vec![left, right]
}

/// A standard infix operator is the middle subject of a literal two-operand expression.
pub fn infix(math: &str) -> Option<String> {
    let names = named(math);
    let [_, operator, _] = names.as_slice() else {
        return None;
    };
    matches!(
        operator.as_str(),
        "\\oplus" | "\\ominus" | "\\otimes" | "\\odot" | "\\oslash" | "\\boxplus" | "\\boxtimes"
    )
    .then(|| operator.clone())
}

/// A vector spelled through its own coordinate tuple introduces the listed coordinate names.
pub fn tuple_components(math: &str) -> Vec<String> {
    let Some((vector, tuple)) = math.split_once('=') else {
        return Vec::new();
    };
    let Some(vector) = literal_component(vector) else {
        return Vec::new();
    };
    let Some(base) = vector
        .strip_prefix("\\mathbf{")
        .and_then(|name| name.strip_suffix('}'))
    else {
        return Vec::new();
    };
    let Some(tuple) = tuple
        .trim()
        .strip_prefix('(')
        .and_then(|tuple| tuple.strip_suffix(')'))
    else {
        return Vec::new();
    };
    tuple
        .split(',')
        .map(str::trim)
        .filter(|part| !matches!(*part, "\\ldots" | "\\cdots" | "\\dots"))
        .map(literal_component)
        .collect::<Option<Vec<_>>>()
        .unwrap_or_default()
        .into_iter()
        .filter(|name| name.rsplit_once('_').is_some_and(|(name, _)| name == base))
        .collect()
}

/// Read one bare symbol with its optional subscript, rejecting products and sums.
fn literal_component(text: &str) -> Option<String> {
    let characters: Vec<char> = text.trim().chars().collect();
    if characters.is_empty() {
        return None;
    }
    let (base, after) = read_symbol(&characters, 0);
    let (script, after) = read_subscript(&characters, after);
    (after == characters.len())
        .then(|| base.map(|base| format!("{base}{script}")))
        .flatten()
}

/// A numerical vector declaration identifies its entry family without stripping other fonts.
pub fn vectors(math: &str) -> Vec<String> {
    let Some((left, domain)) = math.split_once("\\in") else {
        return Vec::new();
    };
    let domain = domain.trim_start();
    if !["\\mathbb{R}^", "\\mathbb R^", "\\mathbb{C}^", "\\mathbb C^"]
        .iter()
        .any(|prefix| domain.starts_with(prefix))
        || left.chars().any(|character| {
            !character.is_alphabetic()
                && !character.is_whitespace()
                && !",{}\\".contains(character)
        })
    {
        return Vec::new();
    }
    named(left)
        .into_iter()
        .filter(|name| name.starts_with("\\mathbf{") && name.ends_with('}'))
        .collect()
}

/// Explicit numerical lower bounds justify only that endpoint of a declared component family.
pub fn lower_components(math: &str) -> Vec<(String, String)> {
    let mut found = Vec::new();
    let mut cursor = Cursor::new(math);
    while let Some(character) = cursor.bump() {
        if character != '\\' {
            continue;
        }
        let name = cursor.take_while(|character| character.is_ascii_alphabetic());
        drop(cursor.take_while(char::is_whitespace));
        if !matches!(name.as_str(), "sum" | "prod") || !cursor.eat("_") {
            continue;
        }
        let Some(head) = BRACE.read(&mut cursor) else {
            continue;
        };
        let Some((index, lower)) = head.split_once('=') else {
            continue;
        };
        let index = index.trim();
        let lower = lower.trim();
        if index.len() != 1
            || !index.chars().all(char::is_alphabetic)
            || lower.is_empty()
            || !lower.chars().all(|digit| digit.is_ascii_digit())
        {
            continue;
        }
        drop(cursor.take_while(char::is_whitespace));
        if cursor.eat("^") && BRACE.read(&mut cursor).is_none() {
            let _ = cursor.bump();
        }
        drop(cursor.take_while(char::is_whitespace));
        let characters: Vec<char> = cursor.rest().chars().collect();
        if characters.is_empty() {
            continue;
        }
        let (Some(base), after) = read_symbol(&characters, 0) else {
            continue;
        };
        let (script, _) = read_subscript(&characters, after);
        let component = format!("{base}{script}");
        if indexed(&component).is_some_and(|(_, used)| used == index) {
            let endpoint = named(&format!("{base}_{{{lower}}}"));
            found.extend(endpoint.into_iter().map(|name| (component.clone(), name)));
        }
    }
    found
}

/// Recognize literal reduction/quantifier binders and parameters of an equation-defined function.
pub fn bound(math: &str) -> BTreeSet<String> {
    let mut bound = BTreeSet::new();
    let mut cursor = Cursor::new(math);
    while let Some(character) = cursor.bump() {
        if character != '\\' {
            continue;
        }
        let name = cursor.take_while(|character| character.is_ascii_alphabetic());
        drop(cursor.take_while(char::is_whitespace));
        if name.is_empty()
            && cursor.eat("{")
            && let Some((head, _)) = cursor.rest().split_once(':')
            && !head.contains("\\}")
            && !head.chars().any(|character| "(=+-*/".contains(character))
        {
            bound.extend(named(head));
        }
        if matches!(name.as_str(), "sum" | "prod" | "bigcup" | "bigcap") && cursor.eat("_") {
            let head = BRACE
                .read(&mut cursor)
                .unwrap_or_else(|| cursor.take_while(|character| character.is_ascii_alphabetic()));
            if !head.contains("\\substack") {
                let head = head.split(['=', ':']).next().unwrap_or_default();
                let head = head.split("\\in").next().unwrap_or_default();
                bound.extend(named(head));
            }
        } else if matches!(name.as_str(), "forall" | "exists") {
            let characters: Vec<char> = cursor.rest().chars().collect();
            let mut index = 0;
            while index < characters.len() {
                let (symbol, after) = read_symbol(&characters, index);
                let Some(symbol) = symbol else { break };
                let (script, after) = read_subscript(&characters, after);
                bound.insert(format!("{symbol}{script}"));
                index = after;
                while characters
                    .get(index)
                    .is_some_and(|character| character.is_whitespace())
                {
                    index += 1;
                }
                if characters.get(index) != Some(&',') {
                    break;
                }
                index += 1;
                while characters
                    .get(index)
                    .is_some_and(|character| character.is_whitespace())
                {
                    index += 1;
                }
            }
        }
    }
    if let Some((left, _)) = math.split_once('=')
        && let Some((function, parameters)) = left.trim().split_once('(')
        && named(function).len() == 1
        && parameters.ends_with(')')
    {
        let parameters = parameters.trim_end_matches(')');
        if parameters
            .chars()
            .all(|character| character.is_alphabetic() || ", \\".contains(character))
        {
            bound.extend(named(parameters));
        }
    }
    bound
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
    let head = left.split_once('(').map_or(left, |(head, _)| head);
    let symbols = named(head);
    (symbols.len() == 1).then(|| symbols[0].clone())
}

/// Read separate top-level assignments, not commas inside function arguments or fractions.
pub fn definitions(math: &str) -> Vec<String> {
    let mut found = Vec::new();
    for row in math.split("\\\\") {
        let mut depth = 0usize;
        let mut start = 0;
        for (at, character) in row.char_indices() {
            match character {
                '{' | '(' | '[' => depth += 1,
                '}' | ')' | ']' => depth = depth.saturating_sub(1),
                ',' if depth == 0 => {
                    found.extend(assignment(&row[start..at]));
                    start = at + 1;
                }
                _ => {}
            }
        }
        found.extend(assignment(&row[start..]));
    }
    found
}

/// A literal tuple assignment introduces each scalar head, not identifiers inside expressions.
fn assignment(math: &str) -> Vec<String> {
    if let Some(symbol) = defined(math) {
        return vec![symbol];
    }
    let Some((left, _)) = math.split_once('=') else {
        return Vec::new();
    };
    let Some((prefix, tuple)) = left.trim().trim_end_matches('&').trim().split_once('(') else {
        return Vec::new();
    };
    let Some(tuple) = tuple.strip_suffix(')').filter(|_| named(prefix).is_empty()) else {
        return Vec::new();
    };
    tuple
        .split(',')
        .map(|component| {
            let symbols = named(component);
            (symbols.len() == 1).then(|| symbols[0].clone())
        })
        .collect::<Option<Vec<_>>>()
        .unwrap_or_default()
}

/// Whether one control sequence names a quantity rather than shaping the mathematics around it.
pub(super) fn is_quantity(name: &str) -> bool {
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
    while characters
        .get(end)
        .is_some_and(|character| character.is_whitespace())
    {
        end += 1;
    }
    if TEXTUAL.contains(&name.as_str()) {
        return (None, skip_group(characters, end));
    }
    if name == "textcolor" || name == "color" {
        return (None, skip_group(characters, end));
    }
    if STYLED.contains(&name.as_str()) && characters.get(end) == Some(&'{') {
        let after = skip_group(characters, end);
        let argument: String = characters[end + 1..after.saturating_sub(1)]
            .iter()
            .collect();
        let quantities = named(&argument);
        let argument = if quantities.len() == 1 {
            quantities[0].clone()
        } else {
            argument.trim().to_string()
        };
        return (Some(format!("\\{name}{{{argument}}}")), after);
    }
    if STYLED.contains(&name.as_str()) && end < characters.len() {
        let (argument, after) = read_symbol(characters, end);
        return (
            argument.map(|argument| format!("\\{name}{{{argument}}}")),
            after,
        );
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
        let (symbol, end) = read_control(characters, index + 1);
        let script = symbol.unwrap_or_else(|| characters[index + 1..end].iter().collect());
        return (format!("_{{{script}}}"), end);
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
    let script: String = characters[index + 2..end.saturating_sub(1).max(index + 2)]
        .iter()
        .collect();
    let quantities = named(&script);
    let script = if quantities.len() == 1 && script.contains('\\') {
        quantities[0].clone()
    } else {
        script.split_whitespace().collect()
    };
    if script.chars().count() == 1 {
        (format!("_{script}"), end)
    } else {
        (format!("_{{{script}}}"), end)
    }
}
