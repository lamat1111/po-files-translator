import os
import json
import argparse
import polib
import openai
from pathlib import Path
from time import sleep

    
import re

def clean_line(line):
    # Remove outer quotes only, and trim whitespace
    return re.sub(r'^"+|"+$', '', line).strip()


# 🔐 API Key
openai.api_key = "sk-..."

# 📁 Paths
PROJECT_DIR = Path("...") #path to local quorum-desktop folder
PROMPT_PATH = PROJECT_DIR / "src/i18n/LLM-prompt.txt" #contains the prompt specific for Quorum translations
DICT_PATH = PROJECT_DIR / "src/i18n/dictionary-base.json" #contains the dictionary specific for Quorum translations
PO_ROOT_DIR = PROJECT_DIR / "src/i18n"

# ⚙️ Settings
MODEL = "gpt-4o" #chnage model here
BATCH_SIZE = 50 #lower if necessary
SLEEP_SECONDS = 1

# 🧠 Load prompt and dictionary
custom_prompt = PROMPT_PATH.read_text(encoding="utf-8")
dictionary = json.load(DICT_PATH.open("r", encoding="utf-8"))

# 📤 Send a batch to GPT
def translate_batch(entries, lang_code, prompt_base):
    lines = [f'"{e.msgid}"' for e in entries]
    joined_lines = "\n".join(lines)

    full_prompt = f"""{prompt_base}


Translate these strings to language code: `{lang_code}`

Strings to translate:
{joined_lines}
"""
    try:
        print("⏳ Translating...")
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        translations = [clean_line(line) for line in content.split("\n") if line.strip()]
        
        if len(translations) != len(entries):
            raise ValueError(
                f"❌ Mismatch: expected {len(entries)} translations, got {len(translations)}.\n\nPrompt sent:\n{joined_lines}\n\nResponse:\n{content}"
            )

        return translations

    except Exception as e:
        print("⚠️ Error:", e)
        return ["" for _ in entries]  # fallback: empty strings

# 🧩 Process a single .po file
def process_po_file(po_path, lang_code):
    print(f"Translating {lang_code} — {po_path}")

    po = polib.pofile(str(po_path))
    entries = [e for e in po if not e.msgstr.strip() and e.msgid.strip()]
    print(f"{len(entries)} entries to translate")

    for i in range(0, len(entries), BATCH_SIZE):
        batch = entries[i:i + BATCH_SIZE]
        translations = translate_batch(batch, lang_code, custom_prompt)
        for entry, translation in zip(batch, translations):
            entry.msgstr = translation
        sleep(SLEEP_SECONDS)

    output_path = po_path.with_name("messages.translated.po")
    po.save(str(output_path))
    print(f"✅ Saved: {output_path}\n")

# 🔄 Find all available languages (folders with messages.po)
def find_available_languages():
    return sorted([
        subdir.name for subdir in PO_ROOT_DIR.iterdir()
        if (subdir / "messages.po").exists()
    ])

# 🚀 Main CLI Entry
def main():
    parser = argparse.ArgumentParser(description="Translate .po files using GPT")
    parser.add_argument("--langs", type=str, required=True,
                        help="Comma-separated list of language codes (e.g. it,es) or 'all'")
    args = parser.parse_args()

    available_langs = find_available_languages()
    print(f"🌐 Available languages: {', '.join(available_langs)}")

    if args.langs == "all":
        langs_to_translate = available_langs
    else:
        langs_to_translate = args.langs.split(",")
        for lang in langs_to_translate:
            if lang not in available_langs:
                raise FileNotFoundError(f"❌ No messages.po found for language: {lang}")

    for lang in langs_to_translate:
        po_path = PO_ROOT_DIR / lang / "messages.po"
        process_po_file(po_path, lang)

if __name__ == "__main__":
    main()
