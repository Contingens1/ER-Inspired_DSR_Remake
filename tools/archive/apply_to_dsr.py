import xml.etree.ElementTree as ET
import json
import glob
import os

# Ścieżki
stance_file = r'work/ds_stance_params.json'
dsr_xml_files = glob.glob(r'work/dsr/**/EquipParamWeapon*.xml', recursive=True)

if not os.path.exists(stance_file):
    print(f"BŁĄD: Brak pliku {stance_file}")
    exit(1)

if not dsr_xml_files:
    print("BŁĄD: Nie znaleziono pliku XML DSR w work/dsr/")
    exit(1)

dsr_xml_file = dsr_xml_files[0]
print(f"Modyfikacja pliku DSR XML: {dsr_xml_file}")

with open(stance_file, 'r', encoding='utf-8') as f:
    stance_data = json.load(f)

# Mapa ID DSR -> Posture Damage
stance_map = {}
for item in stance_data:
    raw_id = str(item.get('id', ''))
    val = item.get('ds_posture_damage', 0)
    if not val or val == 0:
        val = 35.0  # Domyślny bazowy przelicznik Poise
        
    if raw_id:
        stance_map[raw_id] = val
        if len(raw_id) >= 7:
            stance_map[raw_id[:6]] = val
            stance_map[raw_id.rstrip('0')] = val

tree = ET.parse(dsr_xml_file)
root = tree.getroot()
updated_count = 0

# Nazwy pól Poise Break w DSR Paramdex
target_fields = ['saDmgRatio', 'saDmgAtkDmg', 'saDurability', 'staminaDmg']

for row in root.findall('.//row'):
    row_id = str(row.attrib.get('id', ''))
    
    # Dopasowanie ID
    matched_val = stance_map.get(row_id) or stance_map.get(row_id[:6]) if len(row_id) >= 6 else None
    
    if matched_val is not None:
        new_val = str(int(float(matched_val)))
        
        # 1. Aktualizacja istniejących pól
        found_field = False
        for field in row.findall('field'):
            if field.attrib.get('name') in target_fields:
                field.attrib['value'] = new_val
                updated_count += 1
                found_field = True
                
        # 2. Jeśli Paramdex nie wypluł domyślnego pola w XML, wstrzykujemy je bezpośrednio
        if not found_field:
            new_field = ET.SubElement(row, 'field')
            new_field.attrib['name'] = 'saDmgRatio'
            new_field.attrib['value'] = new_val
            updated_count += 1

tree.write(dsr_xml_file, encoding='utf-8', xml_declaration=True)
print(f"SUKCES: Zaktualizowano {updated_count} pól w pliku DSR XML!")