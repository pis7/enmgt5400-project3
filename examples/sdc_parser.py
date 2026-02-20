"""SDC (Synopsys Design Constraints) parser for ASIC timing constraint files.

This module parses Tcl-based SDC files produced by synthesis and place-and-route
tools (Synopsys Design Compiler, Cadence Genus, etc.) into structured Python data
models.  Unsupported or unrecognised commands are stored verbatim in
``SDCConstraintSet.raw_commands`` for downstream inspection.

CLI example::

    python sdc_parser.py --input top.sdc --format summary --verbose
    python sdc_parser.py --input top.sdc --format json --output constraints.json --strict

Representative SDC syntax::

    create_clock -name clk_sys -period 10.0 -waveform {0 5} [get_ports clk]
    set_input_delay  -clock clk_sys -max 2.5 [get_ports {data_in[*]}]
    set_output_delay -clock clk_sys -max 3.0 [get_ports out_valid]
    set_false_path   -from [get_clocks clk_a] -to [get_clocks clk_b]
    set_multicycle_path 2 -setup -from [get_pins u_core/q] -to [get_pins u_reg/d]

Example parsed output::

    SDCConstraintSet(clocks=1, io_delays=2, exceptions=2, raw_commands=2)
    ClockConstraint(name='clk_sys', period=10.0ns, waveform=[0.0, 5.0], source='clk')
    IODelay(pin='data_in[*]', clock='clk_sys', delay_value=2.5ns, type='input', -max)
    TimingException(type='false_path', from=['clk_a'], to=['clk_b'])
    TimingException(type='multicycle_path', from=['u_core/q'], to=['u_reg/d'], value=2)
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable, Iterator

__all__ = [
    "ClockConstraint",
    "IODelay",
    "TimingException",
    "SDCConstraintSet",
    "ParseError",
    "SDCParser",
]

logger = logging.getLogger(__name__)


# ─── Data Models ──────────────────────────────────────────────────────────────


@dataclass
class ClockConstraint:
    """A single clock definition from a ``create_clock`` command.

    Attributes:
        name: Clock identifier referenced by other SDC commands.
        period: Clock period in nanoseconds; must be positive.
        waveform: ``[rise_edge_ns, fall_edge_ns]`` within one period.
        source: Port or pin name on which the clock is defined.
    """

    name: str
    period: float
    waveform: list[float]
    source: str

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError(
                f"Clock '{self.name}': period must be > 0, got {self.period}"
            )
        if self.waveform and len(self.waveform) != 2:
            raise ValueError(
                f"Clock '{self.name}': waveform must have exactly 2 edges, "
                f"got {self.waveform}"
            )

    def __repr__(self) -> str:
        return (
            f"ClockConstraint(name={self.name!r}, period={self.period}ns, "
            f"waveform={self.waveform}, source={self.source!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "period_ns": self.period,
            "waveform": self.waveform,
            "source": self.source,
        }


@dataclass
class IODelay:
    """An input or output delay constraint.

    Covers ``set_input_delay`` and ``set_output_delay`` commands.

    Attributes:
        pin: Port or pin name the delay applies to.
        clock: Reference clock name.
        delay_value: Delay magnitude in nanoseconds.
        delay_type: ``"input"`` or ``"output"``.
        min_delay: ``True`` when the ``-min`` flag was present.
        max_delay: ``True`` when the ``-max`` flag was present.
    """

    pin: str
    clock: str
    delay_value: float
    delay_type: str
    min_delay: bool
    max_delay: bool

    def __post_init__(self) -> None:
        if self.delay_type not in {"input", "output"}:
            raise ValueError(
                f"delay_type must be 'input' or 'output', got {self.delay_type!r}"
            )

    def __repr__(self) -> str:
        bound = "-max" if self.max_delay else ("-min" if self.min_delay else "")
        suffix = f", {bound}" if bound else ""
        return (
            f"IODelay(pin={self.pin!r}, clock={self.clock!r}, "
            f"delay_value={self.delay_value}ns, type={self.delay_type!r}{suffix})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "pin": self.pin,
            "clock": self.clock,
            "delay_value_ns": self.delay_value,
            "delay_type": self.delay_type,
            "min_delay": self.min_delay,
            "max_delay": self.max_delay,
        }


@dataclass
class TimingException:
    """A timing path exception.

    Covers ``set_false_path``, ``set_multicycle_path``, ``set_max_delay``,
    and ``set_min_delay``.

    Attributes:
        exception_type: One of ``"false_path"``, ``"multicycle_path"``,
            ``"max_delay"``, or ``"min_delay"``.
        from_list: Source endpoint names (clocks, pins, or ports).
        to_list: Destination endpoint names.
        value: Cycle count for multicycle paths; delay in ns for max/min
            delay constraints; ``None`` for false paths.
    """

    exception_type: str
    from_list: list[str] = field(default_factory=list)
    to_list: list[str] = field(default_factory=list)
    value: float | int | None = None

    _VALID_TYPES: frozenset[str] = field(
        default=frozenset({"false_path", "multicycle_path", "max_delay", "min_delay"}),
        init=False,
        repr=False,
        compare=False,
    )

    def __post_init__(self) -> None:
        valid = {"false_path", "multicycle_path", "max_delay", "min_delay"}
        if self.exception_type not in valid:
            raise ValueError(
                f"exception_type must be one of {sorted(valid)}, "
                f"got {self.exception_type!r}"
            )

    def __repr__(self) -> str:
        val_str = f", value={self.value}" if self.value is not None else ""
        return (
            f"TimingException(type={self.exception_type!r}, "
            f"from={self.from_list!r}, to={self.to_list!r}{val_str})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "exception_type": self.exception_type,
            "from_list": self.from_list,
            "to_list": self.to_list,
            "value": self.value,
        }


@dataclass
class SDCConstraintSet:
    """Top-level container for all constraints parsed from an SDC file.

    Attributes:
        clocks: Clock definitions from ``create_clock``.
        io_delays: Input and output delay constraints.
        exceptions: Timing path exceptions (false paths, multicycle, etc.).
        raw_commands: Verbatim command strings for unrecognised commands.
    """

    clocks: list[ClockConstraint] = field(default_factory=list)
    io_delays: list[IODelay] = field(default_factory=list)
    exceptions: list[TimingException] = field(default_factory=list)
    raw_commands: list[str] = field(default_factory=list)

    def __repr__(self) -> str:
        return (
            f"SDCConstraintSet(clocks={len(self.clocks)}, "
            f"io_delays={len(self.io_delays)}, "
            f"exceptions={len(self.exceptions)}, "
            f"raw_commands={len(self.raw_commands)})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "clocks": [c.to_dict() for c in self.clocks],
            "io_delays": [d.to_dict() for d in self.io_delays],
            "exceptions": [e.to_dict() for e in self.exceptions],
            "raw_commands": self.raw_commands,
        }


# ─── Exception ────────────────────────────────────────────────────────────────


class ParseError(Exception):
    """Raised when a malformed SDC command is encountered in strict mode.

    Attributes:
        line_num: 1-based line number in the source file.
        line_text: Raw text of the offending command.
        message: Human-readable description of the problem.
    """

    def __init__(self, line_num: int, line_text: str, message: str) -> None:
        self.line_num = line_num
        self.line_text = line_text
        self.message = message
        super().__init__(f"Line {line_num}: {message} — {line_text!r}")


# ─── Module-level regex ────────────────────────────────────────────────────────

# Matches common Tcl object-collection commands used in SDC constraints.
_TCL_COLLECTION_RE = re.compile(
    r"^\[\s*(?:get_ports|get_pins|get_nets|get_cells|get_clocks|get_lib_cells)"
    r"\s+(.*?)\s*\]$",
    re.DOTALL,
)


# ─── Parser ───────────────────────────────────────────────────────────────────


class SDCParser:
    """Parser for Synopsys Design Constraints (SDC) files.

    Recognises ``create_clock``, ``set_input_delay``, ``set_output_delay``,
    ``set_false_path``, ``set_multicycle_path``, ``set_max_delay``, and
    ``set_min_delay``.  All other commands are stored verbatim in
    ``SDCConstraintSet.raw_commands``.

    Backslash line continuation and inline ``#`` comments are handled
    transparently during preprocessing.  The parser reads input incrementally
    (line by line) to support large EDA-generated SDC files.

    Args:
        strict: When ``True``, raises :class:`ParseError` on the first
            malformed command.  When ``False`` (default), logs a warning
            and continues parsing.
    """

    _IO_DELAY_CMDS: frozenset[str] = frozenset(
        {"set_input_delay", "set_output_delay"}
    )
    _EXCEPTION_CMDS: frozenset[str] = frozenset(
        {"set_false_path", "set_multicycle_path", "set_max_delay", "set_min_delay"}
    )
    _EXCEPTION_TYPE_MAP: dict[str, str] = {
        "set_false_path": "false_path",
        "set_multicycle_path": "multicycle_path",
        "set_max_delay": "max_delay",
        "set_min_delay": "min_delay",
    }

    def __init__(self, strict: bool = False) -> None:
        self.strict = strict

    # ── Public API ─────────────────────────────────────────────────────────

    def parse_file(self, path: Path) -> SDCConstraintSet:
        path = Path(path)
        logger.debug("Parsing SDC file: %s", path)
        with path.open(encoding="utf-8", errors="replace") as fh:
            return self._parse_from_iter(enumerate(fh, start=1))

    def parse_string(self, content: str) -> SDCConstraintSet:
        lines = content.splitlines(keepends=True)
        return self._parse_from_iter(enumerate(lines, start=1))

    # ── Preprocessing ──────────────────────────────────────────────────────

    def _parse_from_iter(
        self, numbered_lines: Iterable[tuple[int, str]]
    ) -> SDCConstraintSet:
        result = SDCConstraintSet()
        for line_num, command in self._iter_commands(numbered_lines):
            logger.debug("Line %d: %s", line_num, command[:80])
            self._dispatch_command(line_num, command, result)
        return result

    def _iter_commands(
        self, numbered_lines: Iterable[tuple[int, str]]
    ) -> Iterator[tuple[int, str]]:
        pending = ""
        start_line = 1
        for line_num, raw in numbered_lines:
            line = raw.rstrip("\r\n")
            if not pending:
                start_line = line_num
            if line.rstrip().endswith("\\"):
                pending += line.rstrip()[:-1] + " "
                continue
            full = self._strip_comment(pending + line).strip()
            pending = ""
            if full:
                yield start_line, full
        if pending.strip():
            full = self._strip_comment(pending).strip()
            if full:
                yield start_line, full

    @staticmethod
    def _strip_comment(line: str) -> str:
        depth_bracket = depth_brace = 0
        in_string = False
        for idx, ch in enumerate(line):
            if ch == '"' and not in_string:
                in_string = True
            elif ch == '"' and in_string:
                in_string = False
            elif not in_string:
                if ch == "[":
                    depth_bracket += 1
                elif ch == "]":
                    depth_bracket = max(0, depth_bracket - 1)
                elif ch == "{":
                    depth_brace += 1
                elif ch == "}":
                    depth_brace = max(0, depth_brace - 1)
                elif ch == "#" and depth_bracket == 0 and depth_brace == 0:
                    return line[:idx]
        return line

    # ── Tokenisation ───────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(command: str) -> list[str]:
        tokens: list[str] = []
        i, n = 0, len(command)
        while i < n:
            ch = command[i]
            if ch.isspace():
                i += 1
                continue
            if ch == "[":
                depth, start = 0, i
                while i < n:
                    if command[i] == "[":
                        depth += 1
                    elif command[i] == "]":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                tokens.append(command[start:i])
            elif ch == "{":
                depth, start = 0, i
                while i < n:
                    if command[i] == "{":
                        depth += 1
                    elif command[i] == "}":
                        depth -= 1
                        if depth == 0:
                            i += 1
                            break
                    i += 1
                tokens.append(command[start:i])
            elif ch == '"':
                start = i
                i += 1
                while i < n:
                    if command[i] == "\\" and i + 1 < n:
                        i += 2
                    elif command[i] == '"':
                        i += 1
                        break
                    else:
                        i += 1
                tokens.append(command[start:i])
            else:
                start = i
                while i < n and not command[i].isspace() and command[i] not in '[{"':
                    i += 1
                tokens.append(command[start:i])
        return [t for t in tokens if t]

    # ── Tcl collection helpers ─────────────────────────────────────────────

    def _extract_names(self, token: str) -> list[str]:
        token = token.strip()
        m = _TCL_COLLECTION_RE.match(token)
        if m:
            return self._split_tcl_list(m.group(1).strip())
        if token.startswith("{") and token.endswith("}"):
            return self._split_tcl_list(token[1:-1])
        if token.startswith('"') and token.endswith('"'):
            return [token[1:-1]]
        return [token] if token else []

    @staticmethod
    def _split_tcl_list(s: str) -> list[str]:
        items: list[str] = []
        current: list[str] = []
        depth = 0
        for ch in s.strip():
            if ch == "{":
                depth += 1
                current.append(ch)
            elif ch == "}":
                depth -= 1
                current.append(ch)
            elif ch.isspace() and depth == 0:
                if current:
                    items.append("".join(current).strip("{}"))
                    current = []
            else:
                current.append(ch)
        if current:
            items.append("".join(current).strip("{}"))
        return [item for item in items if item]

    # ── Error handling ─────────────────────────────────────────────────────

    def _handle_error(self, line_num: int, line_text: str, message: str) -> None:
        if self.strict:
            raise ParseError(line_num, line_text, message)
        logger.warning("Line %d: %s — skipping: %r", line_num, message, line_text[:120])

    # ── Command dispatch ───────────────────────────────────────────────────

    def _dispatch_command(
        self, line_num: int, command: str, result: SDCConstraintSet
    ) -> None:
        tokens = self._tokenize(command)
        if not tokens:
            return
        cmd = tokens[0]
        if cmd == "create_clock":
            clock = self._parse_create_clock(tokens, line_num, command)
            if clock is not None:
                result.clocks.append(clock)
        elif cmd in self._IO_DELAY_CMDS:
            result.io_delays.extend(
                self._parse_io_delay(tokens, line_num, command)
            )
        elif cmd in self._EXCEPTION_CMDS:
            exc = self._parse_timing_exception(tokens, line_num, command)
            if exc is not None:
                result.exceptions.append(exc)
        else:
            logger.debug(
                "Line %d: unrecognised command %r — storing verbatim", line_num, cmd
            )
            result.raw_commands.append(command)

    # ── Command parsers ────────────────────────────────────────────────────

    def _parse_create_clock(
        self, tokens: list[str], line_num: int, raw: str
    ) -> ClockConstraint | None:
        name: str | None = None
        period: float | None = None
        waveform: list[float] = []
        source: str | None = None
        i = 1
        while i < len(tokens):
            tok = tokens[i]
            if tok == "-name" and i + 1 < len(tokens):
                name = tokens[i + 1].strip('"')
                i += 2
            elif tok == "-period" and i + 1 < len(tokens):
                try:
                    period = float(tokens[i + 1])
                except ValueError:
                    self._handle_error(line_num, raw, f"Invalid -period: {tokens[i+1]!r}")
                    return None
                i += 2
            elif tok == "-waveform" and i + 1 < len(tokens):
                waveform = self._parse_float_list(tokens[i + 1], line_num, raw)
                i += 2
            elif tok.startswith("-"):
                i += 2 if i + 1 < len(tokens) and not tokens[i + 1].startswith("-") else 1
            else:
                names = self._extract_names(tok)
                if names:
                    source = names[0]
                i += 1
        if period is None:
            self._handle_error(line_num, raw, "create_clock missing required -period")
            return None
        if name is None:
            name = source or "unnamed_clock"
        if not waveform:
            waveform = [0.0, period / 2.0]
        try:
            return ClockConstraint(
                name=name, period=period, waveform=waveform, source=source or ""
            )
        except ValueError as exc:
            self._handle_error(line_num, raw, str(exc))
            return None

    def _parse_io_delay(
        self, tokens: list[str], line_num: int, raw: str
    ) -> list[IODelay]:
        delay_type = "input" if tokens[0] == "set_input_delay" else "output"
        clock = ""
        delay_value: float | None = None
        is_min = is_max = False
        pins: list[str] = []
        # Flags that consume no value argument
        _bool_flags = {
            "-add_delay", "-network_latency_included",
            "-source_latency_included", "-rise", "-fall",
            "-level_sensitive", "-edge_triggered",
        }
        i = 1
        while i < len(tokens):
            tok = tokens[i]
            if tok == "-clock" and i + 1 < len(tokens):
                names = self._extract_names(tokens[i + 1])
                clock = names[0] if names else ""
                i += 2
            elif tok == "-max":
                is_max = True
                i += 1
            elif tok == "-min":
                is_min = True
                i += 1
            elif tok in _bool_flags:
                i += 1
            elif tok == "-reference_pin":
                i += 2
            elif tok.startswith("[") or tok.startswith("{"):
                pins.extend(self._extract_names(tok))
                i += 1
            elif tok.startswith("-"):
                i += 2
            else:
                try:
                    delay_value = float(tok)
                except ValueError:
                    pins.extend(self._extract_names(tok))
                i += 1
        if delay_value is None:
            self._handle_error(line_num, raw, f"{tokens[0]} missing delay value")
            return []
        results: list[IODelay] = []
        for pin in pins:
            try:
                results.append(
                    IODelay(
                        pin=pin,
                        clock=clock,
                        delay_value=delay_value,
                        delay_type=delay_type,
                        min_delay=is_min,
                        max_delay=is_max,
                    )
                )
            except ValueError as exc:
                self._handle_error(line_num, raw, str(exc))
        return results

    def _parse_timing_exception(
        self, tokens: list[str], line_num: int, raw: str
    ) -> TimingException | None:
        exception_type = self._EXCEPTION_TYPE_MAP[tokens[0]]
        from_list: list[str] = []
        to_list: list[str] = []
        value: float | int | None = None
        _bool_flags = {"-setup", "-hold", "-rise", "-fall", "-datapath_only"}
        i = 1
        while i < len(tokens):
            tok = tokens[i]
            if tok == "-from" and i + 1 < len(tokens):
                from_list.extend(self._extract_names(tokens[i + 1]))
                i += 2
            elif tok == "-to" and i + 1 < len(tokens):
                to_list.extend(self._extract_names(tokens[i + 1]))
                i += 2
            elif tok == "-through" and i + 1 < len(tokens):
                i += 2  # through-points are not modelled; skip
            elif tok in _bool_flags:
                i += 1
            elif tok.startswith("-"):
                i += 2
            else:
                try:
                    raw_val = float(tok)
                    value = int(raw_val) if raw_val == int(raw_val) else raw_val
                except ValueError:
                    self._handle_error(line_num, raw, f"Unexpected token: {tok!r}")
                    return None
                i += 1
        try:
            return TimingException(
                exception_type=exception_type,
                from_list=from_list,
                to_list=to_list,
                value=value,
            )
        except ValueError as exc:
            self._handle_error(line_num, raw, str(exc))
            return None

    # ── Float-list helper ──────────────────────────────────────────────────

    def _parse_float_list(
        self, token: str, line_num: int, raw: str
    ) -> list[float]:
        token = token.strip().strip("{}")
        parts = token.replace(",", " ").split()
        result: list[float] = []
        for part in parts:
            try:
                result.append(float(part))
            except ValueError:
                self._handle_error(line_num, raw, f"Non-numeric value in float list: {part!r}")
                return []
        return result


# ─── Summary helper ───────────────────────────────────────────────────────────


def _build_summary(cs: SDCConstraintSet) -> str:
    lines = [
        "=== SDC Constraint Summary ===",
        f"  Clocks              : {len(cs.clocks)}",
        f"  IO Delays           : {len(cs.io_delays)}",
        f"  Timing Exceptions   : {len(cs.exceptions)}",
        f"  Unrecognised Cmds   : {len(cs.raw_commands)}",
    ]
    if cs.clocks:
        lines.append("\nClocks:")
        for c in cs.clocks:
            freq_mhz = 1000.0 / c.period if c.period else 0.0
            lines.append(f"  {c}  [{freq_mhz:.1f} MHz]")
    if cs.io_delays:
        lines.append("\nIO Delays:")
        for d in cs.io_delays:
            lines.append(f"  {d}")
    if cs.exceptions:
        lines.append("\nTiming Exceptions:")
        for e in cs.exceptions:
            lines.append(f"  {e}")
    if cs.raw_commands:
        lines.append("\nUnrecognised Commands:")
        for cmd in cs.raw_commands:
            lines.append(f"  {cmd[:100]}")
    return "\n".join(lines)


# ─── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="Parse an SDC timing constraints file and emit JSON or a summary.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python sdc_parser.py -i design.sdc --format summary\n"
            "  python sdc_parser.py -i design.sdc --format json -o out.json\n"
        ),
    )
    ap.add_argument(
        "-i", "--input", required=True, type=Path, metavar="FILE",
        help="Input SDC file path.",
    )
    ap.add_argument(
        "-o", "--output", type=Path, default=None, metavar="FILE",
        help="Output file path (default: stdout).",
    )
    ap.add_argument(
        "--format", choices=["json", "summary"], default="summary",
        help="Output format (default: summary).",
    )
    ap.add_argument(
        "--strict", action="store_true",
        help="Raise ParseError on the first malformed command instead of warning.",
    )
    ap.add_argument(
        "-v", "--verbose", action="store_true",
        help="Enable DEBUG-level logging.",
    )
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.WARNING,
        format="%(levelname)s %(name)s: %(message)s",
    )

    try:
        parser = SDCParser(strict=args.strict)
        constraint_set = parser.parse_file(args.input)
    except FileNotFoundError:
        logger.error("Input file not found: %s", args.input)
        sys.exit(1)
    except ParseError as exc:
        logger.error("Parse error: %s", exc)
        sys.exit(2)

    if args.format == "json":
        output = json.dumps(constraint_set.to_dict(), indent=2)
    else:
        output = _build_summary(constraint_set)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        logger.info("Written to %s", args.output)
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
