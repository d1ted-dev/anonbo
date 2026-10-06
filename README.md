# Minecraft-рендер «четыре стадии настроения»

Ремейк мультяшного арта (четыре фигуры: от поникшей к сияющей) в Blender со скином **4ered1t**.

| Вариант | Файл |
|---|---|
| **Финал: крупный план** | `renders/closeup_final.png` |
| **Финал: шествие** | `renders/march_final.png` |
| Сияние (ранний вариант) | `renders/glow.png` |
| Мультяшный контур (Freestyle) | `renders/cartoon.png` |
| Шествие сбоку, отражающий пол (`--style bright`) | `renders/march.png` |
| Крупный план (`--style bright`) | `renders/closeup.png` |

`renders/raw/` — рендеры до постобработки. Для `--style bright` передайте `bright`
четвёртым аргументом в `post.py`.

## Как перерендерить

```bash
pip install bpy pillow          # Blender 5.0 как python-модуль
python3 blender/scene.py --skin skins/4ered1t.png --model slim \
    --variant glow --out renders/raw/glow.png --meta renders/raw/glow.json
python3 blender/post.py renders/raw/glow.png renders/raw/glow.json renders/glow.png
```

Варианты: `glow`, `cartoon`, `march`, `closeup`. Другой скин — любой PNG 64×64
(`--model classic` для широких рук). Позы, цвета и камеры — в `POSES`, `LOOKS`,
`VARIANTS` в `blender/scene.py`.

### Финальные версии

```bash
for v in closeup march; do
  python3 blender/scene.py --skin skins/4ered1t.png --variant $v --style bright --shell \
      --out renders/raw/${v}_final.png --mask renders/raw/${v}_final_mask.png \
      --mask-prev renders/raw/${v}_final_mprev.png --meta renders/raw/${v}_final.json \
      --samples 128 --res 1920
  python3 blender/post.py renders/raw/${v}_final.png renders/raw/${v}_final.json \
      renders/${v}_final.png bright renders/raw/${v}_final_mask.png holo-skin \
      renders/raw/${v}_final_mprev.png
done
```
