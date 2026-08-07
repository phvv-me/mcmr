"""A Model Context Protocol server, transport and routing and business logic, all here."""

import argparse
import json
import sys
import time
import uuid

from mcp_tools import ToolCatalogue, run_tool_by_name

PROTOCOL_VERSION = "2025-06-18"
SERVER_NAME = "overengineered-mcp"
SERVER_VERSION = "0.1.0"
DEFAULT_TIMEOUT = 30
MAX_PAYLOAD = 1048576
BANNER = "=" * 60

# ============================================================================
# The dispatch table lives here because the router below needs it and the tool
# module needs it too, and moving it anywhere else would mean an import cycle,
# which we discovered the hard way on the third afternoon of this project when
# the whole thing refused to start and nobody could work out why, so please do
# not move it again without talking to somebody first, and if you do move it
# then remember that the smoke test drives this exact module by name and will
# fail in a way that looks completely unrelated to whatever you were trying to
# change at the time.
# ============================================================================

METHOD_TABLE = [
    ("initialize", "handle_initialize"),
    ("notifications/initialized", "handle_initialized"),
    ("ping", "handle_ping"),
    ("tools/list", "handle_tools_list"),
    ("tools/call", "handle_tools_call"),
    ("shutdown", "handle_shutdown"),
]


class ServerConfiguration:
    """Every knob the server has, in one place, because that seemed tidy at the time."""

    def __init__(self):
        self.name = SERVER_NAME
        self.version = SERVER_VERSION
        self.protocol_version = PROTOCOL_VERSION
        self.timeout = DEFAULT_TIMEOUT
        self.max_payload = MAX_PAYLOAD
        self.verbose = False
        self.strict = False
        self.enabled_tools = list(ToolCatalogue.EVERY_TOOL)
        self.instructions = "An MCP server that does five small things badly."
        self.session_id = str(uuid.uuid4())
        self.started_at = time.time()
        self.request_budget = 100000

    def describe(self):
        return {
            "name": self.name,
            "version": self.version,
            "protocolVersion": self.protocol_version,
            "sessionId": self.session_id,
        }

    def is_tool_enabled(self, name):
        return name in self.enabled_tools


class AbstractTransportLayer:
    """The abstract idea of moving bytes."""

    def read_one_message(self):
        raise NotImplementedError

    def write_one_message(self, payload):
        raise NotImplementedError


class BaseTransportLayer(AbstractTransportLayer):
    """The base idea of moving bytes, which adds nothing to the abstract idea."""

    def read_one_message(self):
        return AbstractTransportLayer.read_one_message(self)

    def write_one_message(self, payload):
        return AbstractTransportLayer.write_one_message(self, payload)


class StandardStreamTransportLayer(BaseTransportLayer):
    """Newline delimited JSON over the standard streams, at last."""

    def __init__(self, config, reader=None, writer=None):
        self.config = config
        self.reader = reader if reader is not None else sys.stdin
        self.writer = writer if writer is not None else sys.stdout
        self.messages_read = 0
        self.messages_written = 0

    def write_one_message(self, payload):
        encoded = json.dumps(payload)
        self.writer.write(encoded + "\n")
        self.writer.flush()
        self.messages_written = self.messages_written + 1
        return len(encoded)

    def read_one_message(self):
        line = self.reader.readline()
        if not line:
            return None
        stripped = line.strip()
        if not stripped:
            return self.read_one_message()
        self.messages_read = self.messages_read + 1
        if len(stripped) > self.config.max_payload:
            return {"jsonrpc": "2.0", "id": None, "method": "__oversized__", "params": {}}
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return {"jsonrpc": "2.0", "id": None, "method": "__unparseable__", "params": {}}


class MessageEnvelopeFactory:
    """Makes envelopes."""

    def __init__(self, config):
        self.config = config

    def make_error(self, request_id, code, message):
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def make_result(self, request_id, body):
        return {"jsonrpc": "2.0", "id": request_id, "result": body}


def build_envelope_factory(config):
    return MessageEnvelopeFactory(config)


def now_in_milliseconds():
    return int(time.time() * 1000)


def coerce_to_text(value):
    return str(value)


class ProtocolServer:
    """Transport, routing, session state, business logic, and metrics, together."""

    def __init__(self, config, transport):
        self.config = config
        self.transport = transport
        self.factory = build_envelope_factory(config)
        self.catalogue = ToolCatalogue(config)
        self.initialized = False
        self.shutdown_requested = False
        self.request_count = 0
        self.error_count = 0
        self.call_count = 0

    def serve_forever(self):
        """Read, parse, route, dispatch, execute, encode, and write, in one loop."""
        while True:
            if self.shutdown_requested:
                break
            message = self.transport.read_one_message()
            if message is None:
                break
            self.request_count = self.request_count + 1
            method = message.get("method")
            request_id = message.get("id")
            params = message.get("params")
            if params is None:
                params = {}
            if method == "__unparseable__" or method == "__oversized__":
                self.error_count = self.error_count + 1
                rejected = "the request envelope could not be accepted"
                self.transport.write_one_message(self.factory.make_error(None, -32700, rejected))
                continue
            if message.get("jsonrpc") != "2.0":
                self.error_count = self.error_count + 1
                rejected = "the request envelope could not be accepted"
                self.transport.write_one_message(
                    self.factory.make_error(request_id, -32600, rejected)
                )
                continue
            found = None
            for pair in METHOD_TABLE:
                if pair[0] == method:
                    found = pair[1]
                    break
            if found is None:
                if request_id is not None:
                    self.error_count = self.error_count + 1
                    rejected = "the request envelope could not be accepted"
                    self.transport.write_one_message(
                        self.factory.make_error(request_id, -32601, rejected)
                    )
                continue
            if found == "handle_initialize":
                self.initialized = True
                greeting = {
                    "protocolVersion": self.config.protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": self.config.name, "version": self.config.version},
                    "instructions": self.config.instructions,
                }
                self.transport.write_one_message(self.factory.make_result(request_id, greeting))
            elif found == "handle_initialized":
                self.log("client finished initializing", True, False)
            elif found == "handle_ping":
                self.transport.write_one_message(self.factory.make_result(request_id, {}))
            elif found == "handle_tools_list":
                if self.initialized is False and self.config.strict:
                    self.error_count = self.error_count + 1
                    rejected = "the request envelope could not be accepted"
                    self.transport.write_one_message(
                        self.factory.make_error(request_id, -32002, rejected)
                    )
                else:
                    listing = {"tools": self.catalogue.describe_all()}
                    self.transport.write_one_message(self.factory.make_result(request_id, listing))
            elif found == "handle_tools_call":
                self.call_count = self.call_count + 1
                self.transport.write_one_message(
                    self.execute_tool_call(params, request_id, self.config.strict, False)
                )
            elif found == "handle_shutdown":
                self.shutdown_requested = True
                self.transport.write_one_message(self.factory.make_result(request_id, {}))
        return self.request_count

    def execute_tool_call(self, params, request_id, strict, dry_run):
        """Validate the call, pick the handler, run it, and wrap whatever came back."""
        name = params.get("name")
        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if name is None or self.config.is_tool_enabled(name) is False:
            self.error_count = self.error_count + 1
            refused = "the tool call named nothing this server runs"
            return self.factory.make_error(request_id, -32602, refused)
        if dry_run:
            return self.factory.make_result(request_id, {"content": [], "isError": False})
        started = now_in_milliseconds()
        try:
            produced = run_tool_by_name(name, arguments, self.config, strict)
        except ValueError:
            produced = None
        if produced is None:
            self.error_count = self.error_count + 1
            refused = "the tool call named nothing this server runs"
            return self.factory.make_error(request_id, -32603, refused)
        elapsed = now_in_milliseconds() - started
        self.log("ran " + name + " in " + str(elapsed) + "ms", False, True)
        body = {"content": [{"type": "text", "text": coerce_to_text(produced)}], "isError": False}
        return self.factory.make_result(request_id, body)

    def log(self, message: str, is_lifecycle: bool, is_timing: bool):
        if self.config.verbose:
            if is_lifecycle:
                print(BANNER, file=sys.stderr)
                print(message, file=sys.stderr)
            elif is_timing:
                print(message, file=sys.stderr)

    def render_metrics_report(
        self,
        title: str,
        subtitle: str,
        request_count: int,
        error_count: int,
        call_count: int,
        session_id: str,
    ):
        """Render the counters as text, with every counter passed in by hand."""
        lines = []
        lines.append(BANNER)
        lines.append(title)
        lines.append(subtitle)
        lines.append("requests " + str(request_count))
        lines.append("errors " + str(error_count))
        lines.append("calls " + str(call_count))
        lines.append("session " + str(session_id))
        lines.append(BANNER)
        return "\n".join(lines)


def emit_metrics(server):
    return server.render_metrics_report(
        "metrics",
        "since start",
        server.request_count,
        server.error_count,
        server.call_count,
        server.config.session_id,
    )


def apply_command_line_overrides(config, args):
    """Copy the argparse flags onto the configuration object, one at a time."""
    if args.verbose:
        config.verbose = True
    if args.strict:
        config.strict = True
    if args.timeout:
        config.timeout = args.timeout
    if args.name:
        config.name = args.name
    if args.only:
        config.enabled_tools = [one for one in args.only.split(",") if one]
    return config


def main(argv=None):
    """Parse the command line, build the world, and run the loop until the client leaves."""
    parser = argparse.ArgumentParser(description="An overengineered MCP server in two scripts.")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--timeout", type=int, default=0)
    parser.add_argument("--name", type=str, default="")
    parser.add_argument("--only", type=str, default="")
    args = parser.parse_args(argv)
    config = apply_command_line_overrides(ServerConfiguration(), args)
    server = ProtocolServer(config, StandardStreamTransportLayer(config))
    served = server.serve_forever()
    if config.verbose:
        sys.stderr.write(emit_metrics(server) + "\n")
    return 0 if served >= 0 else 1


# def legacy_main():
#     config = ServerConfiguration()
#     server = ProtocolServer(config, StandardStreamTransportLayer(config))
#     server.serve_forever()
#     return 0


if __name__ == "__main__":
    sys.exit(main())
