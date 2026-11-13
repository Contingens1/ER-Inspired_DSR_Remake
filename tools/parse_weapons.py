import xml.etree.ElementTree as ET
import json
import glob
import os

# 1. Szukanie pliku XML rozpakowanego przez WitchyBND
files = glob.glob('work/er/**/EquipParamWeapon*.xml', recursive=True)
if not files:
    files = glob.glob('work/**/EquipParamWeapon*.xml', recursive=True)

if not files:
    print("BŁĄD: Nie znaleziono pliku EquipParamWeapon.xml w folderze work/")
    exit(1)

xml_file = files[0]
print(f"Parsowanie pliku: {xml_file}")

# 2. Odczyt XML i wyciąganie danych
tree = ET.parse(xml_file)
root = tree.getroot()
data = []

for row in root.findall('.//row'):
    row_id = row.attrib.get('id')
    row_name = row.attrib.get('name', '')
    
    sa_durability = None
    sa_break_point = None
    
    for field in row.findall('field'):
        name = field.attrib.get('name')
        if name == 'saDurability':
            sa_durability = field.attrib.get('value')
        elif name == 'saBreakPoint':
            sa_break_point = field.attrib.get('value')
            
    data.append({
        'id': row_id,
        'name': row_name,
        'saDurability': sa_durability,
        'saBreakPoint': sa_break_point
    })

# 3. Zapis do JSON
os.makedirs('work', exist_ok=True)
output_file = 'work/er_weapons_parsed.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"SUKCES: Wyciągnięto {len(data)} broni do {output_file}")