# Minecraft-рендер «четыре стадии настроения»

Ремейк мультяшного арта (четыре фигуры: от поникшей к сияющей) в Blender со скином **4ered1t**.

| Вариант | Файл |
|---|---|
| Сияние (ближе всего к оригиналу) | `renders/glow.png` |
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
