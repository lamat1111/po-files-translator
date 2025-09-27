#!/usr/bin/env python3
"""
PO File Translator
Translates .po (gettext) files using OpenAI GPT models with batch processing
"""

import os
import sys
import json
import argparse
import logging
import re
from pathlib import Path
from time import sleep
from datetime import datetime
import glob

# Load environment variables
try:
    from dotenv import load_dotenv
    # Try to load .env from script directory first, then default behavior
    local_env = Path(__file__).parent / ".env"
    if local_env.exists():
        load_dotenv(local_env)
        print(f"📝 Loaded .env from: {local_env}")
    else:
        load_dotenv()  # Try default behavior
except ImportError:
    print("Installing python-dotenv...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-dotenv"])
    from dotenv import load_dotenv
    # Try to load .env from script directory first, then default behavior
    local_env = Path(__file__).parent / ".env"
    if local_env.exists():
        load_dotenv(local_env)
        print(f"📝 Loaded .env from: {local_env}")
    else:
        load_dotenv()  # Try default behavior

try:
    import polib
    import openai
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "polib", "openai"])
    import polib
    import openai

def cleanup_old_logs():
    """Keep only the 3 most recent log files"""
    SCRIPT_DIR = Path(__file__).parent
    LOG_DIR = SCRIPT_DIR / "logs"

    if not LOG_DIR.exists():
        LOG_DIR.mkdir(exist_ok=True)
        return

    # Find all log files matching the pattern
    log_files = list(LOG_DIR.glob("*.log"))

    if len(log_files) <= 3:
        return

    # Sort by modification time (newest first)
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)

    # Remove all but the 3 most recent
    for old_log in log_files[3:]:
        try:
            old_log.unlink()
            print(f"🗑️  Removed old log file: {old_log.name}")
        except Exception as e:
            print(f"⚠️  Could not remove old log file {old_log.name}: {e}")

# Setup logging with enhanced features
def setup_logging(script_dir):
    LOG_DIR = script_dir / "logs"
    LOG_DIR.mkdir(exist_ok=True)

    # Create log file with current date-time
    current_time = datetime.now().strftime("%d-%m-%Y_%H-%M-%S")
    log_path = LOG_DIR / f"{current_time}.log"

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s — %(levelname)s — %(message)s")
    file_handler.setFormatter(file_formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(levelname)s — %(message)s")
    console_handler.setFormatter(console_formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

    # Clean up old logs after creating new one
    cleanup_old_logs()

# Initialize logging automatically
SCRIPT_DIR = Path(__file__).parent
setup_logging(SCRIPT_DIR)

# Settings
MODEL = "gpt-4o-mini"
TEMPERATURE = 0.2
BATCH_SIZE = 30
SLEEP_SECONDS = 1

# Default locale to skip
DEFAULT_LOCALE = os.getenv("DEFAULT_LOCALE", "en")

def clean_line(line):
    """Clean up LLM response line by removing unwanted quotes and whitespace"""
    line = line.strip()
    line = re.sub(r'^"+|"+$', '', line)
    return line.strip()

def validate_translation(original, translation):
    """Basic validation to catch common issues"""
    if not translation:
        return False
    
    if translation.count('"') % 2 != 0:
        logging.warning(f"Unmatched quotes in translation: {translation}")
        return False
        
    if '\\' in translation:
        logging.warning(f"Backslash found in translation: {translation}")
        return False
        
    return True

def translate_batch(entries, lang_code, prompt_base, temperature):
    # Replace newlines with placeholder to avoid LLM confusion
    newline_placeholder = "|||NEWLINE|||"
    # Handle consecutive newlines explicitly (common in multiline strings)
    lines = []
    for entry in entries:
        processed = entry.msgid.replace('\n\n', f'{newline_placeholder}{newline_placeholder}').replace('\n', newline_placeholder)
        lines.append(processed)
    separator = "|||ENTRY_SEPARATOR|||"
    joined_lines = separator.join(lines)

    full_prompt = f"""{prompt_base}

Translate these strings to language code: `{lang_code}`

Each string is separated by {separator}. The placeholder {newline_placeholder} represents a line break - preserve it as {newline_placeholder} in your translations.
Return translations in the same order, one per line (no separators needed).

Strings to translate:
{joined_lines}
"""
    try:
        print(f"→ Translating batch ({len(entries)} strings)...")
        logging.info(f"🌐 Translating batch for language: {lang_code}")

        # Try modern API first, fallback to legacy if needed
        try:
            client = openai.OpenAI()
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=temperature
            )
        except AttributeError:
            # Fallback to legacy API
            response = openai.ChatCompletion.create(
                model=MODEL,
                messages=[{"role": "user", "content": full_prompt}],
                temperature=temperature
            )
        content = response.choices[0].message.content.strip()

        # Handle both line-based and separator-based responses
        if separator in content:
            # LLM returned with separators - split on separator
            translations = [clean_line(part.strip()) for part in content.split(separator) if part.strip()]
        else:
            # LLM returned line-based - split on newlines
            translations = [clean_line(line) for line in content.split("\n") if line.strip()]

        if len(translations) != len(entries):
            error_msg = f"Mismatch: expected {len(entries)} translations, got {len(translations)}"
            logging.error(f"❌ Translation failed for {lang_code}: {error_msg}")
            raise ValueError(f"❌ {error_msg}\n\nPrompt sent:\n{joined_lines}\n\nResponse:\n{content}")

        # Validate translations and restore newlines
        validated_translations = []
        for i, (entry, translation) in enumerate(zip(entries, translations)):
            # Restore newlines in translation
            restored_translation = translation.replace(newline_placeholder, '\n')
            if validate_translation(entry.msgid, restored_translation):
                validated_translations.append(restored_translation)
            else:
                logging.warning(f"Invalid translation for '{entry.msgid}': '{restored_translation}' - keeping original")
                validated_translations.append(entry.msgid)  # Fallback to original

        logging.info(f"✅ Successfully translated batch for {lang_code} ({len(entries)} strings)")
        return validated_translations

    except Exception as e:
        logging.error(f"❌ Translation batch failed for {lang_code}: {str(e)}")
        logging.exception("💥 Detailed error during translation batch")
        return ["" for _ in entries]

def process_po_file(po_path, lang_code, is_creative, custom_prompt):
    print(f"\n🔄 Processing '{lang_code}' at {po_path}")
    try:
        po = polib.pofile(str(po_path))
    except Exception as e:
        logging.error(f"❌ Failed to load .po file: {po_path}")
        raise

    entries = [e for e in po if not e.msgstr.strip() and e.msgid.strip()]
    print(f"✏️  Found {len(entries)} entries to translate")

    if not entries:
        print("⚪ No entries to translate. All entries are already translated.")
        return

    for i in range(0, len(entries), BATCH_SIZE):
        batch_number = (i // BATCH_SIZE) + 1
        print(f"\n📦 Processing batch {batch_number}/{((len(entries) - 1) // BATCH_SIZE) + 1}")
        batch = entries[i:i + BATCH_SIZE]
        temperature = 0.8 if is_creative else TEMPERATURE
        translations = translate_batch(batch, lang_code, custom_prompt, temperature)
        for entry, translation in zip(batch, translations):
            entry.msgstr = translation
        sleep(SLEEP_SECONDS)

    backup_path = po_path.with_suffix(".po.bak")
    try:
        if backup_path.exists():
            backup_path.unlink()

        po_path.rename(backup_path)
        print(f"📦 Original file backed up as: {backup_path.name}")

        po.save(str(po_path))
        print(f"✅ Translated file saved as: {po_path.name}")

    except Exception as e:
        logging.error(f"❌ Failed to backup or save .po file: {po_path}")
        raise

def find_po_files(input_dir):
    """Find all .po files in input directory"""
    po_files = list(input_dir.glob("*.po"))
    return po_files

def find_available_languages(po_root_dir):
    """Find available language directories with messages.po files"""
    logging.info(f"🔍 Scanning for languages in: {po_root_dir}")
    
    if not po_root_dir.exists():
        logging.critical(f"❌ PO_ROOT_DIR does not exist: {po_root_dir}")
        raise FileNotFoundError(f"PO_ROOT_DIR not found: {po_root_dir}")

    # List all subdirectories first for debugging
    all_dirs = [subdir.name for subdir in po_root_dir.iterdir() if subdir.is_dir()]
    logging.info(f"📂 Found directories: {all_dirs}")

    # Folders to skip - both the DEFAULT_LOCALE and literal "defaultLocale"
    folders_to_skip = {DEFAULT_LOCALE, "defaultLocale"}
    logging.info(f"🚫 Will skip folders: {folders_to_skip}")
    
    langs = []
    for subdir in po_root_dir.iterdir():
        if subdir.is_dir():
            messages_po = subdir / "messages.po"
            if messages_po.exists():
                if subdir.name not in folders_to_skip:
                    langs.append(subdir.name)
                    logging.info(f"✅ Found valid language: {subdir.name}")
                else:
                    logging.info(f"⏭️  Skipping: {subdir.name}")
            else:
                logging.info(f"❌ No messages.po in: {subdir.name}")
    
    return sorted(langs)

def process_project_mode():
    """Process .po files using PROJECT_DIR"""
    project_dir_raw = os.getenv("PROJECT_DIR")
    if not project_dir_raw:
        print("❌ PROJECT_DIR not set in .env file")
        return False

    po_root_dir = Path(project_dir_raw).resolve()
    if not po_root_dir.exists():
        print(f"❌ PROJECT_DIR does not exist: {po_root_dir}")
        return False

    logging.info(f"📁 Using PROJECT_DIR: {po_root_dir}")
    
    available_langs = find_available_languages(po_root_dir)
    
    if not available_langs:
        print(f"⚠️  No valid language directories found in {po_root_dir}")
        return False
    
    print(f"\n🌐 Available languages: {', '.join(available_langs)}")
    print(f"🚫 Skipping default locale: {DEFAULT_LOCALE}")
    
    # Get target languages
    lang_input = input("\nEnter language codes to translate (comma-separated) or 'all': ").strip().lower()
    if not lang_input:
        print("Language selection is required")
        return False
    
    if lang_input == 'all':
        langs_to_translate = available_langs
    else:
        langs_to_translate = [lang.strip() for lang in lang_input.split(",")]
        # Validate languages exist
        for lang in langs_to_translate:
            if lang not in available_langs:
                print(f"❌ Language '{lang}' not found in available languages")
                return False
    
    # Ask for creative mode
    creative_input = input("Use creative translation mode? (y/N): ").strip().lower()
    is_creative = creative_input == 'y'
    
    print(f"\n🎯 Will translate: {', '.join(langs_to_translate)}")
    print(f"Creative mode: {'Yes' if is_creative else 'No'}")
    
    # Load prompt from file
    script_dir = Path(__file__).parent
    try:
        prompt_path = script_dir / ("LLM-prompt-creative.txt" if is_creative else "LLM-prompt.txt")
        logging.info(f"📄 Loading prompt from: {prompt_path}")
        custom_prompt = prompt_path.read_text(encoding="utf-8")
        print(f"✅ Using custom prompt: {prompt_path.name}")
    except Exception as e:
        logging.warning(f"Failed to read prompt file: {e}")
        # Fallback to default prompt
        custom_prompt = """You are a professional translator. Translate the given strings accurately while preserving:
- Technical terms and placeholders (like %s, {variable}, etc.)
- HTML tags and formatting
- The original meaning and tone
- Context and cultural appropriateness

Provide only the translated strings, one per line, in the same order as the input."""
        print("⚠️  Using fallback default prompt")
    
    # Process each language
    for lang in langs_to_translate:
        po_path = po_root_dir / lang / "messages.po"
        try:
            process_po_file(po_path, lang, is_creative, custom_prompt)
        except Exception as e:
            logging.error(f"Failed to process {lang}: {e}")
            continue
    
    return True

def main():
    script_dir = Path(__file__).parent
    
    print("PO File Translator")
    print("=" * 18)
    print("Translates .po (gettext) files using OpenAI GPT models")
    print()
    
    # Check for API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        logging.critical("❌ OPENAI_API_KEY not found in environment variables")
        print("Please add your OpenAI API key to the .env file")
        return
    
    openai.api_key = openai_key
    print("✅ OpenAI API configured")
    
    # Check if PROJECT_DIR is configured for project mode
    project_dir_raw = os.getenv("PROJECT_DIR")
    project_mode_available = False
    
    if project_dir_raw:
        project_dir = Path(project_dir_raw).resolve()
        if project_dir.exists():
            project_mode_available = True
            print(f"✅ Project mode available: {project_dir}")
        else:
            print(f"⚠️  PROJECT_DIR in .env exists but path not found: {project_dir}")
    
    # Choose mode
    if project_mode_available:
        print("\nSelect translation mode:")
        print("1. Input/Output folders (classic mode)")
        print("2. Project mode (automatic repository processing)")
        
        while True:
            choice = input("Enter choice (1 or 2): ").strip()
            if choice in ['1', '2']:
                break
            print("Please enter 1 or 2")
        
        if choice == '2':
            print(f"\n🚀 Using project mode")
            success = process_project_mode()
            if success:
                print(f"\n🎉 Translation completed!")
                logging.info("Translation process complete.")
            return
    
    # Classic input/output mode
    print("\n📁 Using input/output folder mode")
    input_dir = script_dir / "input"
    output_dir = script_dir / "output"
    
    # Create directories
    input_dir.mkdir(exist_ok=True)
    output_dir.mkdir(exist_ok=True)
    
    # Find .po files
    po_files = find_po_files(input_dir)
    
    if not po_files:
        print(f"⚠️  No .po files found in {input_dir}")
        print("Please add .po files to the input folder and try again.")
        return
    
    print(f"Found {len(po_files)} .po file(s) to translate")
    
    # Get target language
    lang_code = input("Enter target language code (e.g., it, es, fr): ").strip().lower()
    if not lang_code:
        print("Language code is required")
        return
    
    # Ask for creative mode
    creative_input = input("Use creative translation mode? (y/N): ").strip().lower()
    is_creative = creative_input == 'y'
    
    print(f"Target language: {lang_code}")
    print(f"Creative mode: {'Yes' if is_creative else 'No'}")
    print()
    
    # Default prompt for translation
    default_prompt = """You are a professional translator. Translate the given strings accurately while preserving:
- Technical terms and placeholders (like %s, {variable}, etc.)
- HTML tags and formatting
- The original meaning and tone
- Context and cultural appropriateness

Provide only the translated strings, one per line, in the same order as the input."""
    
    # Process each .po file
    for po_file in po_files:
        try:
            print(f"\n📄 Processing: {po_file.name}")
            
            # Copy to output directory for processing
            output_file = output_dir / po_file.name
            
            # Read and copy file content
            with open(po_file, 'r', encoding='utf-8') as src:
                with open(output_file, 'w', encoding='utf-8') as dst:
                    dst.write(src.read())
            
            # Process the copied file
            process_po_file(output_file, lang_code, is_creative, default_prompt)
            
        except Exception as e:
            logging.error(f"Failed to process {po_file.name}: {e}")
            continue
    
    print(f"\n🎉 Translation completed!")
    print(f"📂 Translated files saved in: {output_dir}")
    logging.info("Translation process complete.")

if __name__ == "__main__":
    main()