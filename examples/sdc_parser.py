"""SDC (Synopsys Design Constraints) parser — example ASIC tool."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field


# ── Data models ───────────────────────────────────────────────────────────────

@dataclass
class ClockConstraint:
    """A clock definition from create_clock."""
    name: str
    period: float   # nanoseconds
    source: str


@dataclass
class IODelay:
    pin: str        # port or pin name
    clock: str
    delay_ns: float
    direction: str  # "input" or "output"


@dataclass
class SDCConstraintSet:
    """All constraints parsed from one SDC file."""
    clocks: list[ClockConstraint] = field(default_factory=list)
    io_delays: list[IODelay] = field(default_factory=list)
    unknown_cmds: list[str] = field(default_factory=list)


class ParseError(Exception):
    def __init__(self, line_num: int, message: str):
        self.line_num = line_num
        super().__init__(f"Line {line_num}: {message}")


# ── Parser ────────────────────────────────────────────────────────────────────

class SDCParser:
    """Parses create_clock, set_input_delay, and set_output_delay commands.

    Args:
        strict: If True, raise ParseError on malformed input instead of skipping.
    """

    def __init__(self, strict=False):
        self.strict = strict

    def parse_file(self, path):
        with open(path, encoding="utf-8") as fh:
            return self.parse_string(fh.read())

    def parse_string(self, content: str) -> SDCConstraintSet:
        result = SDCConstraintSet()
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            # join backslash continuations
            line = lines[i].strip()
            while line.endswith("\\") and i + 1 < len(lines):
                i += 1
                line = line[:-1].rstrip() + " " + lines[i].strip()
            # strip inline comments
            if "#" in line:
                line = line[:line.index("#")].rstrip()
            if line:
                self._parse_line(i + 1, line, result)
            i += 1
        return result

    def _parse_line(self, line_num, line, result):
        tokens = line.split()
        cmd = tokens[0] if tokens else ""
        if cmd == "create_clock":
            clk = self._parse_clock(line_num, line, tokens)
            if clk:
                result.clocks.append(clk)
        elif cmd in ("set_input_delay", "set_output_delay"):
            delay = self._parse_io_delay(line_num, line, tokens)
            if delay:
                result.io_delays.append(delay)
        else:
            result.unknown_cmds.append(line)

    def _parse_clock(self, line_num, raw, tokens):
        name = period = source = None
        i = 1
        while i < len(tokens):
            if tokens[i] == "-name" and i + 1 < len(tokens):
                name = tokens[i + 1].strip('"{}')
                i += 2
            elif tokens[i] == "-period" and i + 1 < len(tokens):
                try:
                    period = float(tokens[i + 1])
                except ValueError:
                    return self._error(line_num, raw, f"bad -period: {tokens[i+1]}")
                i += 2
            elif tokens[i].startswith("["):
                # last [get_ports ...] token is the clock source
                source = tokens[i].strip("[]").split()[-1] if tokens[i] else ""
                i += 1
            else:
                i += 1
        if period is None:
            return self._error(line_num, raw, "create_clock missing -period")
        return ClockConstraint(name=name or source or "clk", period=period, source=source or "")

    def _parse_io_delay(self, line_num, raw, tokens):
        direction = "input" if tokens[0] == "set_input_delay" else "output"
        clock = ""
        delay = None
        pin = ""
        i = 1
        while i < len(tokens):
            if tokens[i] == "-clock" and i + 1 < len(tokens):
                clock = tokens[i + 1].strip("{}")
                i += 2
            elif tokens[i] in ("-max", "-min"):
                i += 1
            elif tokens[i].startswith("["):
                pin = tokens[i].strip("[]").split()[-1]
                i += 1
            elif tokens[i].startswith("-"):
                i += 2
            else:
                try:
                    delay = float(tokens[i])
                except ValueError:
                    pass
                i += 1
        if delay is None:
            return self._error(line_num, raw, f"{tokens[0]} missing delay value")
        return IODelay(pin=pin, clock=clock, delay_ns=delay, direction=direction)

    def _error(self, line_num, raw, msg):
        if self.strict:
            raise ParseError(line_num, msg)
        print(f"WARNING line {line_num}: {msg} — skipping")
        return None


# ── Summary ───────────────────────────────────────────────────────────────────

def print_summary(cs: SDCConstraintSet):
    print(f"Clocks: {len(cs.clocks)}, IO delays: {len(cs.io_delays)}, "
          f"Unknown: {len(cs.unknown_cmds)}")
    for c in cs.clocks:
        mhz = 1000.0 / c.period
        print(f"  clock {c.name!r}: {c.period} ns ({mhz:.1f} MHz) on {c.source!r}")
    for d in cs.io_delays:
        print(f"  {d.direction} delay {d.delay_ns} ns on {d.pin!r} (clock: {d.clock!r})")


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Parse an SDC constraints file.")
    ap.add_argument("-i", "--input", required=True, help="SDC file path")
    ap.add_argument("--strict", action="store_true", help="Raise on malformed input")
    args = ap.parse_args()

    try:
        cs = SDCParser(strict=args.strict).parse_file(args.input)
    except (FileNotFoundError, ParseError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    print_summary(cs)
