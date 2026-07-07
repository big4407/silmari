from pathlib import Path

p = Path("requirements.txt")
raw = p.read_bytes()
if raw.startswith(b"\xff\xfe"):
    text = raw.decode("utf-16")
elif raw.startswith(b"\xef\xbb\xbf"):
    text = raw.decode("utf-8-sig")
else:
    text = raw.decode("utf-8")

replacement = (
    "# torchreid: install separately from git (not on PyPI as 1.4.0)\n"
    '# pip install --no-build-isolation "git+https://github.com/KaiyangZhou/deep-person-reid.git@f8cd150fdf77e8d9e1ed143b7f308c2c609ded50"'
)
if "torchreid==1.4.0" in text:
    text = text.replace("torchreid==1.4.0", replacement)
elif "torchreid: install separately" not in text:
    raise SystemExit("torchreid line not found")

p.write_text(text, encoding="utf-8")
print("OK", len(text.splitlines()), "lines, utf-8")
