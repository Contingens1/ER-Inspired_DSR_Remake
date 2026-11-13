import json
import os

input_file = 'work/er_weapons_parsed.json'
output_file = 'work/ds_stance_params.json'

if not os.path.exists(input_file):
    print(f"BŁĄD: Brak pliku {input_file}")
    exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    weapons = json.load(f)

result = []

for w in weapons:
    w_id = w.get('id')
    name = w.get('name', '')
    
    # Pobieranie wartości saDurability / saBreakPoint z ER
    try:
        durability = float(w.get('saDurability') or 0)
    except ValueError:
        durability = 0.0

    # Wzór matematyczny przeliczenia ER -> DS Posture Break:
    # W Elden Ring saDurability definiuje odporność / bazowe obrażenia postury.
    # Wzór przeskalowania: DS_Posture_Damage = Base_Durability * 1.25 (z zaokrągleniem do wartości całk.)
    ds_posture_damage = round(durability * 1.25, 2)
    
    result.append({
        'id': w_id,
        'name': name,
        'er_saDurability': durability,
        'ds_posture_damage': ds_posture_damage
    })

os.makedirs('work', exist_ok=True)
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(result, f, indent=2, ensure_ascii=False)

print(f"SUKCES: Przeliczono Posture Damage dla {len(result)} broni. Wynik zapisano w {output_file}.")