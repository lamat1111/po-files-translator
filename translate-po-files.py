import os
import json
import argparse
import polib
import openai
from pathlib import Path
from time import sleep
import re
import logging

# 📝 Setup logging
SCRIPT_DIR = Path(__file__).parent
LOG_PATH = SCRIPT_DIR / "translate-po-files.log"

# File handler: logs everything
file_handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_formatter = logging.Formatter("%(asctime)s — %(levelname)s — %(message)s")
file_handler.setFormatter(file_formatter)

# Console handler: only show errors and critical issues
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.ERROR)
console_formatter = logging.Formatter("⚠️  %(levelname)s — %(message)s")
console_handler.setFormatter(console_formatter)

logging.basicConfig(
    level=logging.INFO,
    handlers=[file_handler, console_handler]
)


def clean_line(line):
    return re.sub(r'^"+|"+$', '', line).strip()

# 🔐 API Key
openai.api_key = "sk-..."

# 📁 Paths
PROJECT_DIR = Path("...")  # path to local quorum-desktop folder
PROMPT_PATH = PROJECT_DIR / "src/i18n/LLM-prompt.txt"
DICT_PATH = PROJECT_DIR / "src/i18n/dictionary-base.json"
PO_ROOT_DIR = PROJECT_DIR / "src/i18n"

# ⚙️ Settings
MODEL = "gpt-4o"
BATCH_SIZE = 50
SLEEP_SECONDS = 1

# 🧠 Load prompt and dictionary
custom_prompt = PROMPT_PATH.read_text(encoding="utf-8")

# Dictionary not used atm
# dictionary = json.load(DICT_PATH.open("r", encoding="utf-8")) 

def translate_batch(entries, lang_code, prompt_base):
    lines = [f'"{e.msgid}"' for e in entries]
    joined_lines = "\n".join(lines)

    full_prompt = f"""{prompt_base}

Translate these strings to language code: `{lang_code}`

Strings to translate:
{joined_lines}
"""
    try:
        logging.info(f"Sending batch of {len(entries)} entries to GPT for lang: {lang_code}")
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()
        translations = [clean_line(line) for line in content.split("\n") if line.strip()]

        if len(translations) != len(entries):
            error_msg = f"Mismatch: expected {len(entries)} translations, got {len(translations)}"
            logging.error(error_msg)
            raise ValueError(f"❌ {error_msg}\n\nPrompt sent:\n{joined_lines}\n\nResponse:\n{content}")

        return translations

    except Exception as e:
        logging.exception("Error during translation batch")
        return ["" for _ in entries]

def process_po_file(po_path, lang_code):
    logging.info(f"Starting translation for {lang_code} — {po_path}")
    po = polib.pofile(str(po_path))
    entries = [e for e in po if not e.msgstr.strip() and e.msgid.strip()]
    logging.info(f"{len(entries)} entries to translate in {lang_code}")

    for i in range(0, len(entries), BATCH_SIZE):
        batch = entries[i:i + BATCH_SIZE]
        translations = translate_batch(batch, lang_code, custom_prompt)
        for entry, translation in zip(batch, translations):
            entry.msgstr = translation
        sleep(SLEEP_SECONDS)

    output_path = po_path.with_name("messages.translated.po")
    po.save(str(output_path))
    logging.info(f"✅ Saved: {output_path}")

def find_available_languages():
    return sorted([
        subdir.name for subdir in PO_ROOT_DIR.iterdir()
        if (subdir / "messages.po").exists()
    ])

def main():
    parser = argparse.ArgumentParser(description="Translate .po files using GPT")
    parser.add_argument("--langs", type=str, required=True,
                        help="Comma-separated list of language codes (e.g. it,es) or 'all'")
    args = parser.parse_args()

    logging.info("Starting translation script")
    available_langs = find_available_languages()
    logging.info(f"🌐 Available languages: {', '.join(available_langs)}")

    if args.langs == "all":
        langs_to_translate = available_langs
    else:
        langs_to_translate = args.langs.split(",")
        for lang in langs_to_translate:
            if lang not in available_langs:
                logging.error(f"No messages.po found for language: {lang}")
                raise FileNotFoundError(f"❌ No messages.po found for language: {lang}")

    for lang in langs_to_translate:
        po_path = PO_ROOT_DIR / lang / "messages.po"
        process_po_file(po_path, lang)

    logging.info("🎉 Translation complete.")

if __name__ == "__main__":
    main()
