import os
import json
import argparse
import polib
import openai
from pathlib import Path
from time import sleep
import re
import logging

from dotenv import load_dotenv
load_dotenv()

# 📝 Setup logging
SCRIPT_DIR = Path(__file__).parent
LOG_PATH = SCRIPT_DIR / "translate.log"

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

# 🔐 API Key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    logging.critical("❌ OPENAI_API_KEY not set. Please check your .env file.")
    raise ValueError("OPENAI_API_KEY not set.")

# 📁 Project path
project_dir_raw = os.getenv("PROJECT_DIR")
if not project_dir_raw:
    logging.critical("❌ PROJECT_DIR not set. Please check your .env file.")
    raise ValueError("PROJECT_DIR not set.")

PROJECT_DIR = Path(project_dir_raw).resolve()
if not PROJECT_DIR.exists():
    logging.critical(f"❌ PROJECT_DIR does not exist: {PROJECT_DIR}")
    raise FileNotFoundError(f"PROJECT_DIR does not exist: {PROJECT_DIR}")

logging.info(f"📁 Using project directory: {PROJECT_DIR}")

# 📁 Paths
PROMPT_PATH_CREATIVE = PROJECT_DIR / "src/i18n/LLM-prompt-creative.txt"
PROMPT_PATH = PROJECT_DIR / "src/i18n/LLM-prompt.txt"
PO_ROOT_DIR = PROJECT_DIR / "src/i18n"

# ⚙️ Settings
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.2 # increase if you ned more creative translations
BATCH_SIZE = 30 # how many strings sent to the LLM
SLEEP_SECONDS = 1


def clean_line(line):
    return re.sub(r'^"+|"+$', '', line).strip()

def translate_batch(entries, lang_code, prompt_base, temperature):
    lines = [f'"{e.msgid}"' for e in entries]
    joined_lines = "\n".join(lines)

    full_prompt = f"""{prompt_base}

Translate these strings to language code: `{lang_code}`

Strings to translate:
{joined_lines}
"""
    try:
        print(f"→ Translating batch ({len(entries)} strings)...")
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": full_prompt}],
            temperature=temperature
        )
        content = response.choices[0].message.content.strip()
        translations = [clean_line(line) for line in content.split("\n") if line.strip()]

        if len(translations) != len(entries):
            error_msg = f"Mismatch: expected {len(entries)} translations, got {len(translations)}"
            logging.error(error_msg)
            raise ValueError(f"❌ {error_msg}\n\nPrompt sent:\n{joined_lines}\n\nResponse:\n{content}")

        return translations

    except Exception as e:
        logging.exception("💥 Error during translation batch")
        return ["" for _ in entries]

def process_po_file(po_path, lang_code, is_creative, custom_prompt):
    print(f"\nTranslating '{lang_code}'")
    try:
        po = polib.pofile(str(po_path))
    except Exception as e:
        logging.error(f"❌ Failed to load .po file: {po_path}")
        raise

    entries = [e for e in po if not e.msgstr.strip() and e.msgid.strip()]
    print(f"✏️  {len(entries)} entries to translate")

    for i in range(0, len(entries), BATCH_SIZE):
        batch_number = (i // BATCH_SIZE) + 1
        print(f"\nBatch {batch_number}")
        batch = entries[i:i + BATCH_SIZE]
        temperature = 0.8 if is_creative else TEMPERATURE
        translations = translate_batch(batch, lang_code, custom_prompt, temperature)
        for entry, translation in zip(batch, translations):
            entry.msgstr = translation
        sleep(SLEEP_SECONDS)

    # Paths
    backup_path = po_path.with_suffix(".po.bak")
    try:
        if backup_path.exists():
            backup_path.unlink()  # Remove existing .bak if present

        po_path.rename(backup_path)
        print(f"Original file backed up as: {backup_path.name}")

        po.save(str(po_path))
        print(f"✅ Translated file saved as: {po_path.name}")

    except Exception as e:
        logging.error(f"❌ Failed to backup or save .po file: {po_path}")
        raise

def find_available_languages():
    if not PO_ROOT_DIR.exists():
        logging.critical(f"❌ PO_ROOT_DIR does not exist: {PO_ROOT_DIR}")
        raise FileNotFoundError(f"PO_ROOT_DIR not found: {PO_ROOT_DIR}")

    langs = [
        subdir.name for subdir in PO_ROOT_DIR.iterdir()
        if (subdir / "messages.po").exists()
    ]
    return sorted(langs)

def main():
    parser = argparse.ArgumentParser(description="Translate .po files using GPT")
    parser.add_argument("--langs", type=str, required=True,
                        help="Comma-separated list of language codes (e.g. it,es) or 'all'")
    parser.add_argument("--creative", action="store_true", help="Use creative prompt and higher temperature")
    args = parser.parse_args()

    # 🧠 Load prompt and dictionary
    try:
        prompt_path = PROMPT_PATH_CREATIVE if args.creative else PROMPT_PATH
        custom_prompt = prompt_path.read_text(encoding="utf-8")
    except Exception as e:
        logging.critical(f"❌ Failed to read prompt file: {prompt_path}")
        raise


    logging.info("🛠️  Starting translation script...")
    available_langs = find_available_languages()
    logging.info(f"🌐 Available languages: {', '.join(available_langs)}")

    if args.langs == "all":
        langs_to_translate = available_langs
    else:
        langs_to_translate = args.langs.split(",")
        for lang in langs_to_translate:
            if lang not in available_langs:
                logging.error(f"❌ No messages.po found for language: {lang}")
                raise FileNotFoundError(f"No messages.po found for language: {lang}")

    for lang in langs_to_translate:
        po_path = PO_ROOT_DIR / lang / "messages.po"
        process_po_file(po_path, lang, args.creative, custom_prompt)

    logging.info("🎉 Translation complete.")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.critical("🚫 Script terminated due to an error.")
        raise
