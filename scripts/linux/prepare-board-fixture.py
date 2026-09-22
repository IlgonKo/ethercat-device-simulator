#!/usr/bin/env python3
"""Add an explicit, word-aligned 0x1C00 to the upstream Board ESI.

KickCAT 43ad3e9 synthesizes SM types at bit 8 instead of bit 16 after
subindex 0. SOEM Complete Access then sees shifted SM types. Keep the
upstream source and PDO entries intact; declare the object in the ESI.
"""
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def prepare(root):
    source = root / 'third_party/KickCAT/examples/slave/lan9252/freedom-k64f/nuttx/freedom-k64f.xml'
    tree = ET.parse(source)
    dictionary = tree.find('.//Device/Profile/Dictionary')
    if dictionary is None:
        raise RuntimeError('Missing Board dictionary')
    if any(o.findtext('Index', '').lower() == '#x1c00' for o in dictionary.findall('Objects/Object')):
        raise RuntimeError('Upstream now defines 0x1C00; review the fixture adaptation')
    datatype = ET.SubElement(dictionary.find('DataTypes'), 'DataType')
    ET.SubElement(datatype, 'Name').text = 'BENCH_DT1C00'
    ET.SubElement(datatype, 'BitSize').text = '48'
    obj = ET.SubElement(dictionary.find('Objects'), 'Object')
    for name, text in [('Index', '#x1C00'), ('Name', 'Sync manager communication types'),
                       ('Type', 'BENCH_DT1C00'), ('BitSize', '48')]:
        ET.SubElement(obj, name).text = text
    info = ET.SubElement(obj, 'Info')
    for subindex, value in enumerate([4, 1, 2, 3, 4]):
        name = 'Count' if subindex == 0 else f'SM{subindex - 1}'
        sub = ET.SubElement(datatype, 'SubItem')
        for key, text in [('SubIdx', str(subindex)), ('Name', name), ('Type', 'USINT'),
                          ('BitSize', '8'), ('BitOffs', str(0 if subindex == 0 else 8 + subindex * 8))]:
            ET.SubElement(sub, key).text = text
        ET.SubElement(ET.SubElement(sub, 'Flags'), 'Access').text = 'ro'
        default = ET.SubElement(info, 'SubItem')
        ET.SubElement(default, 'Name').text = name
        ET.SubElement(ET.SubElement(default, 'Info'), 'DefaultData').text = f'{value:02x}'
    ET.SubElement(ET.SubElement(obj, 'Flags'), 'Access').text = 'ro'
    folder = root / 'build/fixtures'
    folder.mkdir(parents=True, exist_ok=True)
    tree.write(folder / 'board.xml', encoding='utf-8', xml_declaration=True)
    config = folder / 'board.json'
    config.write_text(json.dumps({'esi': 'board.xml', 'device_type': 'Board'}), encoding='utf-8')
    return config


if __name__ == '__main__':
    print(prepare(Path(__file__).resolve().parents[2]))
