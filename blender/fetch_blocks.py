"""Скачать текстуры блоков из официального клиента Minecraft (по умолчанию 26.2).

    python3 blender/fetch_blocks.py [версия] [папка]

Текстуры принадлежат Mojang, поэтому в репозиторий не кладутся (blocks/ в .gitignore).
"""
import io
import json
import os
import sys
import urllib.request
import zipfile

NEEDED = ["dark_oak_planks", "red_wool", "polished_blackstone_bricks", "dark_oak_log",
          "glowstone", "shroomlight"]


def main(version="26.2", out="blocks"):
    manifest = json.load(urllib.request.urlopen(
        "https://piston-meta.mojang.com/mc/game/version_manifest_v2.json"))
    url = next(v["url"] for v in manifest["versions"] if v["id"] == version)
    client = json.load(urllib.request.urlopen(url))["downloads"]["client"]["url"]
    jar = zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(client).read()))
    os.makedirs(out, exist_ok=True)
    for name in NEEDED:
        data = jar.read(f"assets/minecraft/textures/block/{name}.png")
        open(os.path.join(out, name + ".png"), "wb").write(data)
    print("ok:", version, "->", out, NEEDED)


if __name__ == "__main__":
    main(*sys.argv[1:3])
