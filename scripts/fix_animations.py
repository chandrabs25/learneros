#!/usr/bin/env python3
"""Fix Three.js BufferGeometry crash in animation HTML files.

The bug: new THREE.BufferGeometry() creates an empty geometry with no position
attribute, then computeLineDistances() tries to access position.count which
is undefined -> crash.

Fix: Initialize with dummy points so the geometry has a valid position attribute.
"""

import os
import re

ANIM_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "animations")

fixed_count = 0

for fname in sorted(os.listdir(ANIM_DIR)):
    if not fname.endswith(".html"):
        continue

    fpath = os.path.join(ANIM_DIR, fname)
    with open(fpath, "r") as f:
        content = f.read()

    if "computeLineDistances" not in content:
        continue

    original = content

    # Fix: new THREE.BufferGeometry() NOT followed by .setFromPoints
    # Replace with initialized geometry so computeLineDistances doesn't crash
    content = re.sub(
        r"new THREE\.BufferGeometry\(\)(?!\.setFromPoints)",
        "new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0,0,0), new THREE.Vector3(0,0,0)])",
        content,
    )

    if content != original:
        with open(fpath, "w") as f:
            f.write(content)
        fixed_count += 1
        print(f"  FIXED: {fname}")

print(f"\nTotal additional files fixed: {fixed_count}")
