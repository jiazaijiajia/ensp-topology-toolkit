#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Parse an eNSP .topo file into Markdown tables and a Mermaid diagram.

Only the Python standard library is required. Python 3.9 or newer is supported.
"""

import argparse
import html
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def read_topo(path: Path) -> ET.Element:
    """Read eNSP's XML, including files declaring the nonstandard UNICODE encoding."""
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030")

    # ElementTree does not recognize encoding="UNICODE". The declaration is
    # removed after decoding because the actual bytes are already known here.
    text = re.sub(r'encoding\s*=\s*"[^"]*"', "", text, count=1)
    return ET.fromstring(text)


# eNSP numbers switch ports from 1 but router and end-device ports from 0.
# Expansion card ports are appended to the main board's interface list and
# take the card slot number, so the groups a main board owns must be known to
# tell a card port apart from a fixed one.
MAINBOARD_GROUPS = {"AR1220": (("GE", 2), ("Ethernet", 8))}


def first_port_number(model: str) -> int:
    """Return 1 for switch families such as S3700 and 0 for everything else."""
    return 1 if re.match(r"^S\d", model) else 0


def group_prefixes(dev: ET.Element, groups, model: str) -> list[str]:
    """Return the slot prefix ("0/0", "2/0") for each interface group."""
    layout = MAINBOARD_GROUPS.get(model)
    mainboard = len(layout) if layout else len(groups)
    prefixes = ["0/0"] * min(mainboard, len(groups))
    extra = groups[len(prefixes):]
    slots = sorted(
        int(slot.get("id", "0")) + 1
        for slot in dev.findall("slot")
        if slot.get("isMainBoard") == "0"
    )
    if len(extra) != len(slots):
        # Unknown card layout: keep the ports visible without inventing a slot.
        return prefixes + ["?/0"] * len(extra)
    return prefixes + [f"{slot}/0" for slot in slots]


def build_interface_map(dev: ET.Element) -> dict[int, str]:
    """Map eNSP's absolute interface indexes to names such as GE0/0/1 or GE2/0/0."""
    model = dev.get("model", "")
    groups = []
    for slot in dev.findall("slot"):
        for interface in slot.findall("interface"):
            count = int(interface.get("count", "0"))
            if count < 0:
                raise ValueError("interface count cannot be negative")
            groups.append((interface.get("interfacename", "?"), count))

    base = first_port_number(model)
    prefixes = group_prefixes(dev, groups, model)

    result = {}
    absolute = 0
    for (name, count), prefix in zip(groups, prefixes):
        for offset in range(count):
            result[absolute] = f"{name}{prefix}/{offset + base}"
            absolute += 1
    return result


def format_port(interfaces: dict[int, str], index: int) -> str:
    """Keep an unresolved index visible instead of silently guessing a port."""
    return interfaces.get(index, f"#{index}")


def parse_topology(root: ET.Element):
    """Return (devices, links) parsed from a topo root element."""
    devices = []
    by_id = {}
    dev_root = root.find("devices")
    if dev_root is None:
        return [], []

    for dev in dev_root.findall("dev"):
        info = {
            "id": dev.get("id", ""),
            "name": dev.get("name", "?"),
            "model": dev.get("model", "?"),
            "com_port": dev.get("com_port", "0"),
            "interfaces": build_interface_map(dev),
        }
        devices.append(info)
        by_id[info["id"]] = info

    links = []
    line_root = root.find("lines")
    if line_root is None:
        return devices, links

    for line in line_root.findall("line"):
        src_id = line.get("srcDeviceID", "")
        dst_id = line.get("destDeviceID", "")
        src_dev = by_id.get(src_id)
        dst_dev = by_id.get(dst_id)
        pair = line.find("interfacePair")
        broken = src_dev is None or dst_dev is None or pair is None

        src_name = src_dev["name"] if src_dev else f"<未知:{src_id[:8]}>"
        dst_name = dst_dev["name"] if dst_dev else f"<未知:{dst_id[:8]}>"
        if pair is None:
            src_port = dst_port = "?"
            kind = "Copper"
        else:
            src_index = int(pair.get("srcIndex", "0"))
            dst_index = int(pair.get("tarIndex", "0"))
            src_port = format_port(src_dev["interfaces"], src_index) if src_dev else "?"
            dst_port = format_port(dst_dev["interfaces"], dst_index) if dst_dev else "?"
            kind = pair.get("lineName", "Copper")

        links.append({
            "src": src_name,
            "dst": dst_name,
            "src_port": src_port,
            "dst_port": dst_port,
            "kind": kind,
            "broken": broken,
        })

    return devices, links


def natural_key(value: str):
    """Sort LSW2 before LSW10 while retaining ordinary alphabetical ordering."""
    return [int(part) if part.isdigit() else part.casefold()
            for part in re.split(r"(\d+)", value)]


def md_cell(value) -> str:
    """Escape text so device names cannot break a Markdown table."""
    return html.escape(str(value)).replace("|", r"\|").replace("\n", " ")


def make_device_table(devices) -> str:
    lines = ["| 设备名 | 型号 | Console 端口 | 接口数 |", "|---|---|---|---|"]
    for device in sorted(devices, key=lambda item: natural_key(item["name"])):
        port = device["com_port"] if device["com_port"] not in ("0", "") else "—"
        lines.append(
            f"| {md_cell(device['name'])} | {md_cell(device['model'])} "
            f"| {md_cell(port)} | {len(device['interfaces'])} |"
        )
    return "\n".join(lines)


def make_link_table(links) -> str:
    lines = [
        "| 源设备 | 源接口 | 目的设备 | 目的接口 | 链路类型 |",
        "|---|---|---|---|---|",
    ]
    for link in links:
        warning = " ⚠️" if link["broken"] else ""
        lines.append(
            f"| {md_cell(link['src'])}{warning} | {md_cell(link['src_port'])} "
            f"| {md_cell(link['dst'])} | {md_cell(link['dst_port'])} "
            f"| {md_cell(link['kind'])} |"
        )
    return "\n".join(lines)


def make_mermaid(devices, links) -> str:
    """Build a Mermaid graph with generated IDs, safe for arbitrary device names."""
    out = ["```mermaid", "graph LR"]
    ordered = sorted(devices, key=lambda item: natural_key(item["name"]))
    node_ids = {device["name"]: f"D{index}" for index, device in enumerate(ordered)}

    for device in ordered:
        node_id = node_ids[device["name"]]
        name = html.escape(device["name"], quote=True)
        model = html.escape(device["model"], quote=True)
        out.append(f'    {node_id}["{name}<br/>{model}"]')

    for link in links:
        if link["broken"] or link["src"] not in node_ids or link["dst"] not in node_ids:
            continue
        label = html.escape(link["src_port"], quote=True).replace("|", "&#124;")
        out.append(f"    {node_ids[link['src']]} ---|{label}| {node_ids[link['dst']]}")

    out.append("```")
    return "\n".join(out)


def make_summary(devices, links) -> str:
    models = {}
    for device in devices:
        models[device["model"]] = models.get(device["model"], 0) + 1
    model_text = "、".join(f"{key} × {value}" for key, value in sorted(models.items()))
    broken = sum(link["broken"] for link in links)
    unknown_ports = sum(
        link["src_port"].startswith("#") or link["dst_port"].startswith("#")
        for link in links
    )
    parts = [
        f"- 设备总数：**{len(devices)}**（{model_text}）",
        f"- 链路总数：**{len(links)}**",
    ]
    if broken:
        parts.append(f"- ⚠️ **{broken}** 条链路缺少端点设备或接口信息")
    if unknown_ports:
        parts.append(f"- ⚠️ **{unknown_ports}** 条链路含未知接口索引，以 `#索引` 标注")
    return "\n".join(parts)


def render_report(title: str, devices, links) -> tuple[str, str]:
    summary = make_summary(devices, links)
    mermaid = make_mermaid(devices, links)
    report = f"""# {title} —— 拓扑分析

{summary}

## 设备清单

{make_device_table(devices)}

## 连线清单

{make_link_table(links)}

## 拓扑示意

{mermaid}
"""
    return report, mermaid


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="解析 eNSP .topo 文件，生成 Markdown 表格和 Mermaid 拓扑图"
    )
    parser.add_argument("topo", help=".topo 文件路径")
    parser.add_argument("-o", "--out", help="输出目录；不填则打印到屏幕")
    args = parser.parse_args(argv)

    path = Path(args.topo)
    if not path.is_file():
        print(f"找不到文件：{path}", file=sys.stderr)
        return 1

    try:
        root = read_topo(path)
        devices, links = parse_topology(root)
    except ET.ParseError as exc:
        print(f"拓扑 XML 解析失败：{exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"无法读取拓扑：{exc}", file=sys.stderr)
        return 2

    if not devices:
        print("拓扑中没有设备。", file=sys.stderr)
        return 3

    report, mermaid = render_report(path.stem, devices, links)
    if args.out:
        outdir = Path(args.out)
        try:
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "topology.md").write_text(report, encoding="utf-8")
            (outdir / "diagram.mmd").write_text(mermaid, encoding="utf-8")
        except OSError as exc:
            print(f"无法写入输出目录：{exc}", file=sys.stderr)
            return 4
        print(f"已生成：{outdir / 'topology.md'}")
        print(f"已生成：{outdir / 'diagram.mmd'}")
        print()
        print(make_summary(devices, links))
    else:
        print(report)
    return 0


if __name__ == "__main__":
    sys.exit(main())
