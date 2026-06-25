from __future__ import annotations

SUPPORTED_LANGUAGES = {
    'en': 'English',
    'hi': 'Hindi',
    'te': 'Telugu',
    'ta': 'Tamil',
    'bn': 'Bengali',
    'mr': 'Marathi',
    'fr': 'French',
    'de': 'German',
    'es': 'Spanish',
    'ar': 'Arabic',
}

def translate_text(text: str, target_lang: str) -> str:
    if not text or target_lang == 'en':
        return text
    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source='auto', target=target_lang).translate(text)
        return translated or text
    except Exception as e:
        print(f"[Translator] Warning: {e}")
        return text