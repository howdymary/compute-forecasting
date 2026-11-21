"""Create original procedural PBR maps without changing reference assets."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'web/desk/assets/visual-motion-v22'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(22001)
    size = 512
    noise = rng.normal(size=(size, size))
    stripe = rng.normal(size=(size, 1))
    brushed = np.clip(150 + 13 * stripe + 3 * noise, 0, 255).astype('uint8')
    polymer = np.clip(188 + 7 * noise, 0, 255).astype('uint8')
    paper = np.clip(223 + 9 * noise, 0, 255).astype('uint8')
    for name, values in [('brushed-roughness', brushed), ('polymer-roughness', polymer), ('paper-roughness', paper)]:
        Image.fromarray(values).save(OUT / (name + '.png'))
    height = (noise + 2 * stripe) * .3
    y, x = np.gradient(height)
    vectors = np.stack([-x * .018, -y * .018, np.ones_like(x)], axis=-1)
    vectors /= np.linalg.norm(vectors, axis=-1, keepdims=True)
    Image.fromarray(np.clip((vectors + 1) * 127.5, 0, 255).astype('uint8')).save(OUT / 'brushed-normal.png')
    (OUT / 'TEXTURE-LICENSE.txt').write_text('Original procedural textures generated for MOCHI V22. Copyright 2026 Mary Liu. Released under CC0 1.0. No external image inputs.\n')
    print(json.dumps({'maps': 4, 'seed': 22001, 'size': size}))


if __name__ == '__main__':
    main()
