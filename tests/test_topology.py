import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "ensp_topology", ROOT / "scripts" / "ensp_topology.py"
)
ensp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ensp)


SAMPLE_XML = """<?xml version="1.0" encoding="UNICODE"?>
<topo>
  <devices>
    <dev id="R1-ID" name="R1" model="AR1220" com_port="2001">
      <slot number="slot17" isMainBoard="1">
        <interface sztype="Ethernet" interfacename="Ethernet" count="2" />
        <interface sztype="Ethernet" interfacename="GE" count="2" />
      </slot>
    </dev>
    <dev id="SW2-ID" name="LSW2" model="S5700" com_port="2002">
      <slot number="slot17" isMainBoard="1">
        <interface sztype="Ethernet" interfacename="GE" count="2" />
      </slot>
    </dev>
    <dev id="SW10-ID" name="LSW10" model="S5700" com_port="2003">
      <slot number="slot17" isMainBoard="1">
        <interface sztype="Ethernet" interfacename="GE" count="1" />
      </slot>
    </dev>
  </devices>
  <lines>
    <line srcDeviceID="R1-ID" destDeviceID="SW2-ID">
      <interfacePair lineName="Copper" srcIndex="2" tarIndex="1" />
    </line>
    <line srcDeviceID="SW2-ID" destDeviceID="SW10-ID">
      <interfacePair lineName="Copper" srcIndex="0" tarIndex="0" />
    </line>
  </lines>
</topo>
"""


def parse_sample():
    text = SAMPLE_XML.replace(' encoding="UNICODE"', "")
    return ensp.parse_topology(ensp.ET.fromstring(text))


class TopologyParsingTests(unittest.TestCase):
    def test_reads_nonstandard_unicode_declaration(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.topo"
            path.write_bytes(SAMPLE_XML.encode("utf-8"))
            root = ensp.read_topo(path)
        self.assertEqual(len(root.find("devices").findall("dev")), 3)

    def test_reads_gb18030_content(self):
        xml = SAMPLE_XML.replace('name="R1"', 'name="核心路由器"')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "gbk.topo"
            path.write_bytes(xml.encode("gb18030"))
            root = ensp.read_topo(path)
        self.assertEqual(root.find("devices/dev").get("name"), "核心路由器")

    def test_parses_device_inventory(self):
        devices, links = parse_sample()
        self.assertEqual(len(devices), 3)
        self.assertEqual(len(links), 2)
        self.assertEqual(devices[0]["interfaces"][0], "Ethernet0/0/0")
        self.assertEqual(devices[0]["interfaces"][2], "GE0/0/0")
        self.assertEqual(devices[0]["interfaces"][3], "GE0/0/1")

    def test_switch_ports_start_at_one(self):
        xml = """<topo><devices>
          <dev id="A" name="LSW1" model="S3700">
            <slot number="slot17" isMainBoard="1">
              <interface sztype="Ethernet" interfacename="Ethernet" count="22" />
              <interface sztype="Ethernet" interfacename="GE" count="2" />
            </slot>
          </dev>
        </devices></topo>"""
        devices, _ = ensp.parse_topology(ensp.ET.fromstring(xml))
        interfaces = devices[0]["interfaces"]
        self.assertEqual(interfaces[0], "Ethernet0/0/1")
        self.assertEqual(interfaces[9], "Ethernet0/0/10")
        self.assertEqual(interfaces[21], "Ethernet0/0/22")
        self.assertEqual(interfaces[22], "GE0/0/1")
        self.assertEqual(interfaces[23], "GE0/0/2")

    def test_expansion_card_port_takes_card_slot(self):
        xml = """<topo><devices>
          <dev id="A" name="AR1" model="AR1220">
            <slot number="slot17" isMainBoard="1">
              <interface sztype="Ethernet" interfacename="GE" count="2" />
              <interface sztype="Ethernet" interfacename="Ethernet" count="8" />
              <interface sztype="Ethernet" interfacename="GE" count="1" />
            </slot>
            <slot isMainBoard="0" id="1" type="6" />
          </dev>
        </devices></topo>"""
        devices, _ = ensp.parse_topology(ensp.ET.fromstring(xml))
        interfaces = devices[0]["interfaces"]
        self.assertEqual(interfaces[0], "GE0/0/0")
        self.assertEqual(interfaces[1], "GE0/0/1")
        self.assertEqual(interfaces[2], "Ethernet0/0/0")
        self.assertEqual(interfaces[10], "GE2/0/0")

    def test_end_device_ports_start_at_one(self):
        xml = """<topo><devices>
          <dev id="A" name="PC1" model="PC">
            <slot number="slot17" isMainBoard="1">
              <interface sztype="Ethernet" interfacename="Ethernet" count="1" />
            </slot>
          </dev>
        </devices></topo>"""
        devices, _ = ensp.parse_topology(ensp.ET.fromstring(xml))
        self.assertEqual(devices[0]["interfaces"][0], "Ethernet0/0/1")

    def test_maps_absolute_link_indexes(self):
        _, links = parse_sample()
        self.assertEqual(links[0]["src_port"], "GE0/0/0")
        self.assertEqual(links[0]["dst_port"], "GE0/0/2")
        self.assertFalse(links[0]["broken"])

    def test_natural_device_sorting(self):
        devices, _ = parse_sample()
        table = ensp.make_device_table(devices)
        self.assertLess(table.index("LSW2"), table.index("LSW10"))

    def test_unknown_endpoint_is_reported(self):
        xml = SAMPLE_XML.replace('destDeviceID="SW10-ID"', 'destDeviceID="MISSING"')
        _, links = ensp.parse_topology(ensp.ET.fromstring(xml))
        broken = [link for link in links if link["broken"]]
        self.assertEqual(len(broken), 1)
        self.assertIn("&lt;未知:MISSING&gt;", ensp.make_link_table(links))
        self.assertIn("1** 条链路", ensp.make_summary([], links))

    def test_missing_interface_pair_is_not_guessed(self):
        xml = SAMPLE_XML.replace(
            '<interfacePair lineName="Copper" srcIndex="2" tarIndex="1" />', ""
        )
        _, links = ensp.parse_topology(ensp.ET.fromstring(xml))
        self.assertTrue(links[0]["broken"])
        self.assertEqual(links[0]["src_port"], "?")

    def test_unknown_interface_index_stays_visible(self):
        xml = SAMPLE_XML.replace('srcIndex="2"', 'srcIndex="99"')
        devices, links = ensp.parse_topology(ensp.ET.fromstring(xml))
        self.assertEqual(links[0]["src_port"], "#99")
        self.assertIn("未知接口索引", ensp.make_summary(devices, links))

    def test_mermaid_uses_safe_generated_ids(self):
        xml = SAMPLE_XML.replace('name="R1"', 'name="R 1&quot;core"')
        devices, links = ensp.parse_topology(ensp.ET.fromstring(xml))
        diagram = ensp.make_mermaid(devices, links)
        self.assertIn('D0["LSW2<br/>S5700"]', diagram)
        self.assertIn("R 1&quot;core", diagram)
        self.assertNotIn('R 1"core["', diagram)

    def test_empty_devices_is_empty_result(self):
        devices, links = ensp.parse_topology(ensp.ET.fromstring("<topo/>"))
        self.assertEqual(devices, [])
        self.assertEqual(links, [])


class CommandLineTests(unittest.TestCase):
    def run_cli(self, arguments):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = ensp.main(arguments)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_cli_writes_both_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "sample.topo"
            output = Path(directory) / "out"
            source.write_bytes(SAMPLE_XML.encode("utf-8"))
            code, _, _ = self.run_cli([str(source), "-o", str(output)])
            self.assertEqual(code, 0)
            self.assertIn("设备总数：**3**", (output / "topology.md").read_text("utf-8"))
            self.assertIn("```mermaid", (output / "diagram.mmd").read_text("utf-8"))

    def test_cli_missing_file(self):
        code, _, error = self.run_cli(["does-not-exist.topo"])
        self.assertEqual(code, 1)
        self.assertIn("找不到文件", error)

    def test_cli_invalid_xml(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "broken.topo"
            source.write_text("not xml", encoding="utf-8")
            code, _, error = self.run_cli([str(source)])
        self.assertEqual(code, 2)
        self.assertIn("XML 解析失败", error)

    def test_cli_without_devices(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "empty.topo"
            source.write_text("<topo/>", encoding="utf-8")
            code, _, error = self.run_cli([str(source)])
        self.assertEqual(code, 3)
        self.assertIn("没有设备", error)


if __name__ == "__main__":
    unittest.main()
