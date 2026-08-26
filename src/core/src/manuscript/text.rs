/// Abbreviations whose trailing dot never ends a sentence in mathematical prose.
const ABBREVIATIONS: &[&str] = &[
    "al", "cf", "e.g", "eq", "etc", "fig", "i.e", "no", "resp", "sec", "tab", "thm", "vs",
];

/// Split one run of prose into the sentences a reader hears.
///
/// A naive split on the dot cuts `3.14`, `i.e.` and `Fig. 2` into fragments and turns a document
/// into hundreds of two-word sentences, which would make every length measurement meaningless.
/// The three guards below are the ones that matter for mathematical prose, and each is decided
/// from the characters either side of the dot rather than from a dictionary.
pub fn sentences(text: &str) -> Vec<String> {
    let mut found = Vec::new();
    let mut current = String::new();
    let characters: Vec<char> = text.chars().collect();
    for (index, character) in characters.iter().enumerate() {
        current.push(*character);
        if !matches!(character, '.' | '!' | '?') || !ends_sentence(&characters, index) {
            continue;
        }
        found.push(std::mem::take(&mut current));
    }
    if !current.trim().is_empty() {
        found.push(current);
    }
    found
        .into_iter()
        .filter(|one| !one.trim().is_empty())
        .collect()
}

/// Return the numeric literals one run of text states.
///
/// A number is kept exactly as written, since the whole point of comparing prose against a table
/// is that `0.145584` and `0.145878` are different claims. Separators inside a number travel with
/// it and a trailing sentence dot does not.
pub fn numbers(text: &str) -> Vec<String> {
    let mut found = Vec::new();
    let mut current = String::new();
    for character in text.chars() {
        if character.is_ascii_digit() || (!current.is_empty() && matches!(character, '.' | ',')) {
            current.push(character);
            continue;
        }
        push_number(&mut found, std::mem::take(&mut current));
    }
    push_number(&mut found, current);
    found
}

/// Count the whitespace separated words one run of text holds.
pub fn words(text: &str) -> usize {
    text.split_whitespace().count()
}

/// Whether the dot at one index closes a sentence rather than a number or an abbreviation.
fn ends_sentence(characters: &[char], index: usize) -> bool {
    let previous = index
        .checked_sub(1)
        .and_then(|before| characters.get(before));
    let next = characters.get(index + 1);
    if previous.is_some_and(char::is_ascii_digit) && next.is_some_and(char::is_ascii_digit) {
        return false;
    }
    if next.is_some_and(|following| !following.is_whitespace()) {
        return false;
    }
    !is_abbreviation(&characters[..index])
}

/// Whether the word ending at a dot is one whose dot belongs to the word.
fn is_abbreviation(before: &[char]) -> bool {
    let word: String = before
        .iter()
        .rev()
        .take_while(|character| !character.is_whitespace())
        .collect::<Vec<_>>()
        .into_iter()
        .rev()
        .collect();
    let lowered = word.to_lowercase();
    word.chars().count() == 1 || ABBREVIATIONS.contains(&lowered.as_str())
}

/// Keep one candidate number after removing punctuation that only ended a sentence.
fn push_number(found: &mut Vec<String>, candidate: String) {
    let trimmed = candidate.trim_end_matches(['.', ',']);
    if trimmed.chars().any(|character| character.is_ascii_digit()) {
        found.push(trimmed.to_string());
    }
}
