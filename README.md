# PO File Translator

Translates .po (gettext) files using OpenAI GPT models with intelligent batch processing and validation.

## Features
- **Dual mode operation**: Input/Output folders OR automatic project repository processing
- **Professional translation**: Uses GPT-4o-mini for high-quality translations
- **Batch processing**: Processes multiple strings at once for efficiency
- **Smart validation**: Checks for common translation issues
- **Automatic backup**: Creates .po.bak files before processing
- **Creative mode**: Optional higher temperature for creative translations
- **Technical preservation**: Maintains placeholders, HTML tags, and formatting
- **Progress tracking**: Detailed logging and progress reporting
- **Multi-language support**: Process specific languages or all available languages

## Setup
1. **Environment Configuration**: Copy `.env.example` to `.env` and configure:
   ```
   OPENAI_API_KEY=your_openai_key_here
   PROJECT_DIR=/path/to/your/project/src/i18n  # Points directly to i18n directory
   DEFAULT_LOCALE=en                           # Optional: locale to skip
   ```

## Usage Modes

### Mode 1: Input/Output Folders (Classic)
1. Place .po files in the `input/` folder
2. Run `python run.py`
3. Select mode 1 when prompted
4. Enter target language code (e.g., it, es, fr)
5. Choose creative mode (optional)
6. Translated files will be saved in `output/` folder

### Mode 2: Project Repository (Automatic)
1. Configure `PROJECT_DIR` in your `.env` file to point directly to your i18n directory
2. Ensure your i18n directory has structure: `LANG/messages.po` (e.g., `es/messages.po`, `fr/messages.po`)
3. Run `python run.py`
4. Select mode 2 when prompted
5. Choose languages to translate (comma-separated or 'all')
6. Files are processed in-place with automatic backup

Example directory structures:
```
PROJECT_DIR=/my-app/src/i18n/
├── en/messages.po
├── es/messages.po
└── fr/messages.po

PROJECT_DIR=/project/locales/
├── ar/messages.po
├── de/messages.po
└── it/messages.po
```

## File Format
Supports standard gettext .po files with entries like:
```
msgid "Hello world"
msgstr ""
```

The tool will translate empty `msgstr` fields while preserving:
- Technical placeholders (%s, {variable}, etc.)
- HTML tags and formatting
- File structure and comments

## API Key
Get your OpenAI API key from [OpenAI Platform](https://platform.openai.com/):
1. Sign up for an account
2. Navigate to API Keys section
3. Create a new API key
4. Add it to your `.env` file

## Requirements
- Python 3.7+ (tested on 3.8-3.12)
- Dependencies (auto-installed if missing):
  - polib
  - openai
  - python-dotenv

## Platform Compatibility
- **Windows**: Use `run.bat` for quick launch or `python run.py`
- **macOS/Linux**: Use `python3 run.py` or `./run.py` (if executable)
- **Cross-platform**: All file paths use pathlib for compatibility

## Settings
- **Model**: GPT-4o-mini (cost-effective, high-quality)
- **Batch size**: 30 strings per request
- **Temperature**: 0.2 (standard) / 0.8 (creative mode)
- **Rate limiting**: 1 second delay between batches

## Output
- Original files are backed up as `.po.bak`
- Translated files maintain original structure
- Detailed logs saved in `logs`