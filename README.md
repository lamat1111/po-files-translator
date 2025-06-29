# 🧠 GPT Translator for Quorum .po Files

Translate your `.po` files using OpenAI's GPT models. Ideal for localizing Quorum UI with context-aware, consistent translations.

## 🔧 Setup

1. Clone this repo and place the script inside the `quorum-desktop` folder.
2. Install dependencies:

```bash
pip install openai polib
```

3. Set your OpenAI API key:

```python
openai.api_key = "sk-..."
```

4. Make sure the following files exist:
- `src/i18n/LLM-prompt.txt` → custom prompt for translation tone/style
- `src/i18n/dictionary-base.json` → optional base dictionary for terminology
- `.po` files inside `src/i18n/<lang>/messages.po`

## 🚀 Usage

```bash
python translate.py --langs it,es
```

Or to translate all:

```bash
python translate.py --langs all
```

## 📝 Output

Translated files are saved as `messages.translated.po` alongside the original.

## ⚙️ Settings

Adjust model, batch size, and sleep delay at the top of the script.

---

Made for Quorum, but adaptable to any GPT-assisted localization flow.

