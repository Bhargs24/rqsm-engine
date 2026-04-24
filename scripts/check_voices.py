import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app.tts.service import _voice_for_role

print("Testing persona_index-based voice assignment:")
for i in range(4):
    v = _voice_for_role("British Colonial Official", i)
    print(f"  index={i}: {v['name']} ({v['language_code']})")

print()
v0 = _voice_for_role("British Colonial Official", 0)
v1 = _voice_for_role("Indian Independence Advocate", 1)
print("Debate pair test:")
print(f"  index=0 (British Colonial Official)  -> {v0['name']} ({v0['language_code']})")
print(f"  index=1 (Indian Independence Advocate) -> {v1['name']} ({v1['language_code']})")
print(f"  Distinct voices: {v0['name'] != v1['name']}")
