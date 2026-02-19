"""
Verilog gate-level netlist utilities.

Provides functions for analyzing post-synthesis Verilog netlists:
cell instance counting, fanout analysis, and hierarchy traversal.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from collections import Counter


@dataclass
class PortConnection:
    port_name: str
    net_name: str


@dataclass
class CellInstance:
    instance_name: str
    cell_type: str
    connections: list[PortConnection] = field(default_factory=list)


@dataclass
class Wire:
    name: str
    width: int = 1


@dataclass
class Module:
    name: str
    ports: list[str] = field(default_factory=list)
    wires: list[Wire] = field(default_factory=list)
    instances: list[CellInstance] = field(default_factory=list)


def parse_netlist(filepath):
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Netlist not found: {filepath}")

    content = path.read_text()
    modules = []
    current_module = None

    # strip block comments
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)
    # strip line comments
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)

    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # module declaration
        mod_match = re.match(r"module\s+(\S+)\s*\(([^)]*)\)\s*;", line)
        if mod_match:
            name = mod_match.group(1)
            port_str = mod_match.group(2)
            ports = [p.strip() for p in port_str.split(",") if p.strip()]
            current_module = Module(name=name, ports=ports)
            i += 1
            continue

        # handle escaped identifiers in module name
        mod_esc_match = re.match(r"module\s+(\\[^\s]+)\s+\(([^)]*)\)\s*;", line)
        if mod_esc_match:
            name = mod_esc_match.group(1)
            port_str = mod_esc_match.group(2)
            ports = [p.strip() for p in port_str.split(",") if p.strip()]
            current_module = Module(name=name, ports=ports)
            i += 1
            continue

        if line == "endmodule" and current_module:
            modules.append(current_module)
            current_module = None
            i += 1
            continue

        if current_module is None:
            i += 1
            continue

        # wire declarations
        wire_match = re.match(r"wire\s+(?:\[(\d+):(\d+)\]\s+)?(\S+)\s*;", line)
        if wire_match:
            hi = int(wire_match.group(1)) if wire_match.group(1) else 0
            lo = int(wire_match.group(2)) if wire_match.group(2) else 0
            width = abs(hi - lo) + 1
            current_module.wires.append(Wire(name=wire_match.group(3), width=width))
            i += 1
            continue

        # cell instantiation with named port connections
        # may span multiple lines, so collect until we see ");'
        inst_match = re.match(r"(\S+)\s+(\S+)\s*\(", line)
        if inst_match and not line.startswith(("input", "output", "inout", "wire", "assign", "reg")):
            cell_type = inst_match.group(1)
            inst_name = inst_match.group(2)

            # gather full instantiation (may be multi-line)
            full_inst = line
            while ");" not in full_inst and i < len(lines) - 1:
                i += 1
                full_inst += " " + lines[i].strip()

            # parse port connections: .port(net)
            conn_matches = re.findall(r"\.(\w+)\s*\(([^)]*)\)", full_inst)
            connections = []
            for port, net in conn_matches:
                connections.append(PortConnection(port_name=port, net_name=net.strip()))

            inst = CellInstance(
                instance_name=inst_name,
                cell_type=cell_type,
                connections=connections,
            )
            current_module.instances.append(inst)

        i += 1

    return modules


def count_cells(modules):
    counts = Counter()
    for mod in modules:
        for inst in mod.instances:
            counts[inst.cell_type] += 1
    return dict(counts.most_common())


def compute_fanout(modules):
    net_drivers = {}
    net_loads = {}

    for mod in modules:
        for inst in mod.instances:
            for conn in inst.connections:
                net = conn.net_name
                # rough heuristic: Y, Z, Q, ZN, QN are outputs
                if conn.port_name in ("Y", "Z", "Q", "ZN", "QN", "S", "CO", "SO"):
                    net_drivers[net] = (inst.instance_name, inst.cell_type)
                else:
                    if net not in net_loads:
                        net_loads[net] = []
                    net_loads[net].append((inst.instance_name, conn.port_name))

    fanout_map = {}
    for net, driver in net_drivers.items():
        loads = net_loads.get(net, [])
        fanout_map[net] = {
            "driver": driver,
            "fanout": len(loads),
            "loads": loads,
        }

    return fanout_map


def find_high_fanout_nets(modules, threshold=16):
    fanout_map = compute_fanout(modules)
    flagged = []
    for net, info in fanout_map.items():
        if info["fanout"] > threshold:
            flagged.append({
                "net": net,
                "driver_instance": info["driver"][0],
                "driver_cell": info["driver"][1],
                "fanout": info["fanout"],
            })
    return sorted(flagged, key=lambda x: x["fanout"], reverse=True)


def get_cell_area_estimate(modules, cell_areas=None):
    if cell_areas is None:
        # default rough estimates in gate equivalents
        cell_areas = {
            "INVX1": 1, "INVX2": 1.5, "INVX4": 2,
            "NAND2X1": 2, "NAND2X2": 2.5, "NAND3X1": 3,
            "NOR2X1": 2, "NOR2X2": 2.5, "NOR3X1": 3,
            "AND2X1": 2.5, "OR2X1": 2.5,
            "AOI21X1": 3, "OAI21X1": 3,
            "DFFX1": 6, "DFFX2": 8,
            "MUX2X1": 4, "BUFX1": 1, "BUFX2": 1.5,
        }

    total = 0.0
    by_type = {}
    for mod in modules:
        for inst in mod.instances:
            area = cell_areas.get(inst.cell_type, 3.0)
            total += area
            if inst.cell_type not in by_type:
                by_type[inst.cell_type] = {"count": 0, "area": 0.0}
            by_type[inst.cell_type]["count"] += 1
            by_type[inst.cell_type]["area"] += area

    return {"total_area_ge": total, "by_cell_type": by_type}


def print_netlist_summary(filepath):
    modules = parse_netlist(filepath)

    for mod in modules:
        print(f"Module: {mod.name}")
        print(f"  Ports: {len(mod.ports)}")
        print(f"  Wires: {len(mod.wires)}")
        print(f"  Instances: {len(mod.instances)}")

        cells = count_cells([mod])
        print("  Cell distribution:")
        for cell_type, cnt in cells.items():
            print(f"    {cell_type}: {cnt}")

        high_fo = find_high_fanout_nets([mod])
        if high_fo:
            print(f"  High fanout nets (>{16}):")
            for net_info in high_fo[:5]:
                print(f"    {net_info['net']}: fanout={net_info['fanout']} "
                      f"(driven by {net_info['driver_cell']} {net_info['driver_instance']})")

        area = get_cell_area_estimate([mod])
        print(f"  Estimated area: {area['total_area_ge']:.0f} gate equivalents")
        print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python netlist_utils.py <netlist.v>")
        sys.exit(1)
    print_netlist_summary(sys.argv[1])
