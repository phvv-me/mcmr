"""The five tools this server exposes, plus the catalogue that describes them."""

import json
import re
import sys

MAX_TEXT = 100000
MAX_NUMBERS = 10000
SEPARATOR = "-" * 40

# ============================================================================
# Every handler below follows the same three steps, which are pull the argument
# out of the mapping, decide what to do when it is missing or the wrong shape,
# and then do the one line of work the tool is actually for. The steps were
# copied from the first handler into the second, and from the second into the
# third, and by the fourth nobody was reading them any more, which is roughly
# how the refusal messages ended up written out five separate times even though
# they are supposed to say the same thing to the same client on the same
# failure, and why changing one of them changes nothing anybody can observe.
# ============================================================================


class ToolSchemaBuilder:
    """Builds the schema."""

    def __init__(self, config):
        self.config = config

    def build_number_schema(self, property_name, description):
        return {
            "type": "object",
            "properties": {
                property_name: {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": description,
                }
            },
            "required": [property_name],
        }

    def build_text_schema(self, property_name, description):
        return {
            "type": "object",
            "properties": {property_name: {"type": "string", "description": description}},
            "required": [property_name],
        }


class ToolCatalogue:
    """Describes every tool, and knows which ones are switched off."""

    EVERY_TOOL = ["echo", "sum_numbers", "word_count", "slugify", "statistics"]

    def __init__(self, config):
        self.config = config
        self.builder = ToolSchemaBuilder(config)

    def describe_all(self):
        """Return the tools/list payload, one hand-written entry per enabled tool."""
        out = []
        for n in self.EVERY_TOOL:
            if self.config.is_tool_enabled(n) is False:
                continue
            if n == "echo":
                out.append(self.text_entry("echo", "Return the text it was given."))
            elif n == "sum_numbers":
                out.append(self.number_entry("sum_numbers", "Add every number it was given."))
            elif n == "word_count":
                out.append(self.text_entry("word_count", "Count the words in the text."))
            elif n == "slugify":
                out.append(self.text_entry("slugify", "Turn the text into a slug."))
            elif n == "statistics":
                out.append(self.number_entry("statistics", "Summarise the numbers."))
        return out

    def text_entry(self, name, description):
        return {
            "name": name,
            "description": description,
            "inputSchema": self.builder.build_text_schema("text", "the text"),
        }

    def number_entry(self, name, description):
        return {
            "name": name,
            "description": description,
            "inputSchema": self.builder.build_number_schema("numbers", "the numbers"),
        }


def warn(message):
    print(SEPARATOR, file=sys.stderr)
    print(message, file=sys.stderr)


def read_text_argument(arguments, config, strict):
    if "text" not in arguments:
        refusal = "the argument is missing or the wrong shape for this tool"
        if strict:
            raise ValueError(refusal)
        return ""
    given = arguments["text"]
    if isinstance(given, str) is False:
        refusal = "the argument is missing or the wrong shape for this tool"
        if strict:
            raise ValueError(refusal)
        given = str(given)
    if config.verbose:
        warn("a tool received " + str(len(given)) + " characters")
    return given[0:MAX_TEXT]


def read_number_argument(arguments, config, strict):
    if "numbers" not in arguments:
        refusal = "the argument is missing or the wrong shape for this tool"
        if strict:
            raise ValueError(refusal)
        return []
    given = arguments["numbers"]
    if isinstance(given, list) is False:
        refusal = "the argument is missing or the wrong shape for this tool"
        if strict:
            raise ValueError(refusal)
        given = [given]
    if config.verbose:
        warn("a tool received " + str(len(given)) + " numbers")
    kept = []
    for entry in given[0:MAX_NUMBERS]:
        if isinstance(entry, bool) is False and isinstance(entry, (int, float)):
            kept.append(entry)
    return kept


def run_echo_tool(arguments, config, strict):
    return read_text_argument(arguments, config, strict)


def run_sum_tool(arguments, config, strict):
    total = 0
    for e in read_number_argument(arguments, config, strict):
        total = total + e
    return str(total)


def run_word_count_tool(arguments, config, strict):
    return str(len(read_text_argument(arguments, config, strict).split()))


def run_slugify_tool(arguments, config, strict):
    t = read_text_argument(arguments, config, strict).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t)
    return t.strip("-")


def run_statistics_tool(arguments, config, strict):
    """Sort the numbers, then compute the five summaries this tool reports."""
    d = read_number_argument(arguments, config, strict)
    if len(d) == 0:
        return json.dumps({"count": 0})
    d.sort()
    n = len(d)
    total = 0
    for e in d:
        total = total + e
    mean = total / n
    if n % 2 == 1:
        median = d[n // 2]
    else:
        median = (d[n // 2 - 1] + d[n // 2]) / 2
    spread = 0
    for e in d:
        spread = spread + (e - mean) * (e - mean)
    return json.dumps(
        {
            "count": n,
            "min": d[0],
            "max": d[n - 1],
            "mean": mean,
            "median": median,
            "variance": spread / n,
        }
    )


def run_tool_by_name(name, arguments, config, strict):
    """Pick the one handler this name refers to, and refuse every other name."""
    if name == "echo":
        return run_echo_tool(arguments, config, strict)
    elif name == "sum_numbers":
        return run_sum_tool(arguments, config, strict)
    elif name == "word_count":
        return run_word_count_tool(arguments, config, strict)
    elif name == "slugify":
        return run_slugify_tool(arguments, config, strict)
    elif name == "statistics":
        return run_statistics_tool(arguments, config, strict)
    else:
        return None


# TODO: resources/list and resources/read are still not implemented here.
# FIXME: the JSON-RPC error codes in mcp_server.py were copied from the spec by hand.
