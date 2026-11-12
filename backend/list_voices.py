import edge_tts
import asyncio

async def main():
    voices = await edge_tts.list_voices()
    print("=== ALL VOICES COUNT:", len(voices))
    
    # Urdu voices
    urdu = [v for v in voices if v['Locale'].startswith('ur')]
    print(f"\n=== URDU VOICES ({len(urdu)}) ===")
    for v in urdu:
        print(f"{v['ShortName']} | {v['Gender']} | {v['Locale']} | {v.get('FriendlyName','')}")
    
    # Hindi voices  
    hindi = [v for v in voices if v['Locale'].startswith('hi')]
    print(f"\n=== HINDI VOICES ({len(hindi)}) ===")
    for v in hindi:
        print(f"{v['ShortName']} | {v['Gender']} | {v['Locale']} | {v.get('FriendlyName','')}")
    
    # All South Asian
    sa = [v for v in voices if any(v['Locale'].startswith(x) for x in ['bn','pa','gu','mr','te','ta','kn','ml','or','si'])]
    print(f"\n=== OTHER SOUTH ASIAN ({len(sa)}) ===")
    for v in sa:
        print(f"{v['ShortName']} | {v['Gender']} | {v['Locale']}")
    
    # Print ALL voices for reference
    print(f"\n=== FULL LIST ALL ({len(voices)}) ===")
    for v in voices:
        print(f"{v['ShortName']} | {v['Gender']} | {v['Locale']}")

asyncio.run(main())

