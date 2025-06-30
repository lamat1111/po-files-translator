# 🧠 GPT Translator for Quorum `.po` Files

This script translates `.po` files using OpenAI's GPT models, with context-aware batches and custom prompts. It's designed for localizing the [Quorum UI](https://github.com/QuilibriumNetwork/quorum-desktop) with consistent, high-quality translations.

## 🔧 Setup

1. Clone this repo or copy the script into your `quorum-desktop` folder.

2. Create a `.env` file in the **same folder as the script**, with the following variables:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxx
PROJECT_DIR=/absolute/path/to/quorum-desktop
```

3. Install the required Python packages:

```
pip install openai polib python-dotenv
```

4. Make sure the following files exist in the Quorum repo:

- `src/i18n/LLM-prompt.txt` and `src/i18n/LLM-prompt-creative.txt` → custom prompts for tone, style, and translation instructions
- `.po` files inside language subfolders like: `src/i18n/it/messages.po`, `src/i18n/es/messages.po`, etc.

## 🚀 Usage

Translate specific languages:

```
python translate.py --langs it,es
```

Translate all available `.po` files:

```
python translate.py --langs all
```


### 🎨 Creative Languages

Some languages (like `en-PI` for Pirate English) benefit from a more creative tone. To enable this, add the `--creative` flag:

```
python translate.py --langs en-PI --creative
```

This will modify the translation prompt to encourage more expressive or poetic output, ideal for artistic or experimental localizations. 

**IMPORTANT: you have to edit the file `src\i18n\LLM-prompt-creative.txt` in your local Quorum repo with specific instructions for the creative language you want to use.**

## 📝 Output

Translated `.po` files are saved as:

```
src/i18n/<lang>/messages.translated.po
```

They remain in the same directory as the originals.

## ⚙️ Configuration

You can adjust the following settings directly in the script:

- `MODEL` → OpenAI model to use (`gpt-4o`, `gpt-4`, etc.)
- `BATCH_SIZE` → Number of strings to send per request
- `SLEEP_SECONDS` → Delay between GPT calls

## 🛡️ Error Handling

The script includes:

- Validation for missing API keys or invalid project paths
- Logging to `translate-po-files.log`
- Clear error messages in the terminal for missing files or mismatched responses

---

Built for Quorum, but flexible enough to use in any GPT-powered translation pipeline.
