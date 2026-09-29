import streamlit as st
import os
import csv
import time
import shutil
from pathlib import Path
from google import genai
from google.genai.errors import ClientError

# =====================================================
# STREAMLIT UI CONFIGURATION
# =====================================================
st.set_page_config(page_title="Literary Chapter Translator", page_icon="📚", layout="centered")

st.title("📚 Chinese-to-Russian Literary Chapter Translator")
st.write("Upload your glossary, text chapter files, enter your Gemini API Key, select your footnote preference, and translate everything into natural, publication-ready Russian prose.")

# =====================================================
# SIDEBAR / CONFIGURATION INPUTS
# =====================================================
st.sidebar.header("Configuration")
api_key_input = st.sidebar.text_input("Gemini API Key", type="password", placeholder="AIzaSy...")
model_input = st.sidebar.text_input("Gemini Model Name", value="gemini-3-flash-preview")
max_chars = st.sidebar.slider("Chunk Size (Chars)", 1000, 5000, 2500, step=500)

# Footnote mode selector choice
footnote_mode = st.sidebar.radio(
    "Footnote Mode",
    ["No Footnotes", "Up to 2 Footnotes"]
)

# =====================================================
# FILE UPLOADERS
# =====================================================
st.subheader("1. Upload Glossary (Optional)")
uploaded_glossary = st.file_uploader("Upload glossary.csv (must contain Chinese, Russian columns)", type=["csv"])

st.subheader("2. Upload Chapter Text Files")
uploaded_files = st.file_uploader("Upload .txt chapter files", type=["txt"], accept_multiple_files=True)

# =====================================================
# SYSTEM PROMPT BUILDER (DYNAMIC BASED ON MODE)
# =====================================================
def get_system_prompt(glossary_text, mode):
    if mode == "No Footnotes":
        return f"""You are a professional literary translator.

Translate the following Chinese text into natural, fluent Russian.

Glossary (mandatory, exact usage):
{glossary_text}

IMPORTANT CONTEXT:
This is a fragment extracted from a larger work.
Do NOT attempt to continue, complete, or resolve it.

CRITICAL RULES:
- Translate ONLY the provided text.
- Do NOT add, continue, or invent any content.
- Stop EXACTLY where the source text stops.
- Preserve paragraph structure.
- Output ONLY the Russian translation.

STYLE AND DIALOGUE:
- Format all dialogue according to Russian punctuation rules:
  each spoken line must begin with an em dash (—), not quotation marks.
- Preserve tone, pacing, and emotional nuance.
- Group Subjects: Avoid "A, B, and C—all did X." Use "A, B, and C did X."
- It is mandatory to use the letter "ё" in all words where it is required according to the rules of the Russian language. Erroneous use of "е" instead of "ё" is unacceptable.
- Swearing and offensive language are strictly prohibited.
- Conditional Structures: Avoid the participial construction "Знай [subject], сделал бы" (e.g., Знай он правду, он бы пришел). Instead, use the standard conditional: "Если бы [subject] знал(а/и/о), то..." (e.g., Если бы он знал правду, он бы пришёл).

IDIOMS AND PROVERBS:
- Chinese idioms, chengyu, and proverbs MUST be replaced with Russian equivalents.
- Preserve their literal imagery in Russian.

FORMS OF ADDRESS & TITLES (CRITICAL)
- Transliterate the following chinese titles and forms of address into russian phonetics using the palladius system, retaining the original sounds rather than translating the meanings: гунян, ван-е, ланцзюнь, фужэнь, момо, сяонянцзы, нян (мать), де (отец), лаофужэнь, а-нян, а-де, гэгэ, цзецзе, мэймэй, диди, and гунцзы. Do not replace them with russian semantic equivalents (e.g. «господин», «князь», «госпожа», «барышня»).
- When used with a name, these specific transliterated titles must be placed after the name and separated by a hyphen.
- All the other chinese titles and forms of address, including gugu, must be translated into russian. For example, gugu should be translated as тётя.
- Do NOT apply any special formatting (no bold, italics, quotation marks, or capitalization, no * symbol).
- Do NOT keep Latin transliteration or any Chinese characters in the output.
- Preserve honorific structure and hierarchy exactly as in the source text.
- Use one consistent transliteration for each title throughout the fragment.
- The words “матушка”, “батюшка”, “барышня”, “вдовствующая императрица”, “папа”, “князь”, “госпожа”, “рыцарь”, “перекантоваться”, “богатырь” must never be used; use appropriate Chinese transliteration if the original uses a form of address.
- Avoid the words “вспыхнуло”, “карета”, “ларец”, “экипаж”. Use more descriptive or varied alternatives.
- Personal pronouns: translate nin (您) strictly as вы and ni (你) strictly as ты. Do not confuse or swap these pronouns during translation.

Do NOT summarize, censor, or explain anything outside footnotes.
"""
    else:  # Up to 2 Footnotes
        return f"""You are a professional literary translator.

Translate the following Chinese text into natural, fluent Russian.

Glossary (mandatory, exact usage):
{glossary_text}

IMPORTANT CONTEXT:
This is a fragment extracted from a larger work.
Do NOT attempt to continue, complete, or resolve it.

CRITICAL RULES:
- Translate ONLY the provided text.
- Do NOT add, continue, or invent any content.
- Stop EXACTLY where the source text stops.
- Preserve paragraph structure.
- Output ONLY the Russian translation.

STYLE AND DIALOGUE:
- Format all dialogue according to Russian punctuation rules:
  each spoken line must begin with an em dash (—), not quotation marks.
- Preserve tone, pacing, and emotional nuance.
- Group Subjects: Avoid "A, B, and C—all did X." Use "A, B, and C did X."
- Swearing and offensive language are strictly prohibited.
- Conditional Structures: Avoid the participial construction "Знай [subject], сделал бы" (e.g., Знай он правду, он бы пришел). Instead, use the standard conditional: "Если бы [subject] знал(а/и/о), то..." (e.g., Если бы он знал правду, он бы пришёл).

IDIOMS AND PROVERBS:
- Chinese idioms, chengyu, and proverbs must NOT be replaced with Russian equivalents. 
- Preserve their literal imagery in Russian. 
- When translating or writing text in Russian that includes specialized terms, idioms, or Chinese idioms (chengyu), add numbered footnote references directly in the main text (e.g., ¹, ²) wherever clarification is needed. At the end of the text, provide the corresponding footnotes using this exact format:
[Superscript Number] [Russian translation/term] ([Original Chinese], [pinyin]) — [Explanation in Russian].
- Footnotes must be concise and informative. You can include a maximum of two footnotes per text.

FORMS OF ADDRESS & TITLES (CRITICAL)
- Transliterate the following chinese titles and forms of address into russian phonetics using the palladius system, retaining the original sounds rather than translating the meanings: гунян, ван-е, ланцзюнь, фужэнь, момо, сяонянцзы, нян (мать), де (отец), лаофужэнь, а-нян, а-де, гэгэ, цзецзе, мэймэй, диди, and гунцзы. Do not replace them with russian semantic equivalents (e.g. «господин», «князь», «госпожа», «барышня»).
- When used with a name, these specific transliterated titles must be placed after the name and separated by a hyphen.
- All the other chinese titles and forms of address, including gugu, must be translated into russian. For example, gugu should be translated as тётя.
- Do NOT apply any special formatting (no bold, italics, quotation marks, or capitalization, no * symbol).
- Do NOT keep Latin transliteration in the output.
- Preserve honorific structure and hierarchy exactly as in the source text.
- Use one consistent transliteration for each title throughout the fragment.
- The words “матушка”, “батюшка”, “барышня”, “вдовствующая императрица”, “папа”, “князь”, “госпожа”, “рыцарь”, “перекантоваться”, “богатырь”, “магический”, “колдун”, “маг” must never be used; use appropriate Chinese transliteration if the original uses a form of address.
- Avoid the words “вспыхнуло”, “карета”, “ларец”, “экипаж”. Use more descriptive or varied alternatives.
- Personal pronouns: translate nin (您) strictly as вы and ni (你) strictly as ты. Do not confuse or swap these pronouns during translation.

Do NOT summarize, censor, or explain anything outside footnotes.
"""

def load_glossary_text(csv_path):
    glossary_lines = []
    if not os.path.exists(csv_path):
        return ""
    with open(csv_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        if not reader.fieldnames or not {"Chinese", "Russian"}.issubset(reader.fieldnames):
            return ""
        for row in reader:
            zh = row.get("Chinese", "").strip()
            ru = row.get("Russian", "").strip()
            if zh and ru:
                glossary_lines.append(f"{zh} = {ru}")
    return "\n".join(glossary_lines)

# =====================================================
# TEXT PROCESSING HELPERS
# =====================================================
def chunk_text(text: str, max_chars: int):
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current = ""
    for p in paragraphs:
        if len(current) + len(p) + 2 <= max_chars:
            current += ("\n\n" if current else "") + p
        else:
            if current.strip():
                chunks.append(current)
            current = p
    if current.strip():
        chunks.append(current)
    return chunks

def is_meta_response(text: str) -> bool:
    lower = text.lower()
    return (
        "please provide" in lower
        or "source text" in lower
        or "предоставьте" in lower
        or "исходный текст" in lower
    )

def translate_text(client, model_name, source_text, glossary_text, max_chars, mode, status_text):
    system_prompt = get_system_prompt(glossary_text, mode)
    translated_chunks = []
    chunks = chunk_text(source_text, max_chars)
    
    for i, chunk in enumerate(chunks, 1):
        status_text.text(f"Translating chunk {i} of {len(chunks)}...")
        prompt_content = system_prompt + "\n\nSOURCE TEXT:\n" + chunk
        
        success = False
        delay = 2
        for attempt in range(5):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt_content
                )
                raw = response.text if response else None
                if not raw:
                    translated_chunks.append("")
                    success = True
                    break
                
                text = raw.strip()
                if is_meta_response(text):
                    translated_chunks.append(text)
                    success = True
                    break
                
                translated_chunks.append(text)
                success = True
                break
            except ClientError as e:
                if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                    time.sleep(delay)
                    delay *= 2
                else:
                    raise e
        if not success:
            translated_chunks.append("")
            
    return "\n\n".join(translated_chunks)

# =====================================================
# MAIN EXECUTION BUTTON
# =====================================================
if st.button("Start Translation"):
    if not api_key_input:
        st.error("Please enter your Gemini API Key in the sidebar.")
    elif not uploaded_files:
        st.error("Please upload at least one chapter .txt file.")
    else:
        input_dir = Path("input")
        output_dir = Path("output")
        input_dir.mkdir(exist_ok=True)
        output_dir.mkdir(exist_ok=True)
        
        # Save glossary if uploaded
        glossary_path = input_dir / "glossary.csv"
        if uploaded_glossary:
            with open(glossary_path, "wb") as f:
                f.write(uploaded_glossary.getbuffer())
        
        glossary_text = load_glossary_text(glossary_path)
        
        # Save chapter files
        for file in uploaded_files:
            with open(input_dir / file.name, "wb") as f:
                f.write(file.getbuffer())
                
        try:
            client = genai.Client(api_key=api_key_input)
        except Exception as e:
            st.error(f"Failed to initialize Gemini Client: {e}")
            st.stop()
            
        st.info(f"Starting translation process using mode: **{footnote_mode}**...")
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(".txt")])
        total_files = len(files)
        success_count = 0
        
        for idx, filename in enumerate(files, 1):
            status_text.text(f"Processing file [{idx}/{total_files}]: {filename}")
            file_path = input_dir / filename
            
            with open(file_path, "r", encoding="utf-8") as f:
                source_text = f.read()
                
            try:
                result = translate_text(client, model_input, source_text, glossary_text, max_chars, footnote_mode, status_text)
                out_path = output_dir / filename
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(result)
                success_count += 1
            except Exception as e:
                st.error(f"Error processing {filename}: {e}")
                
            progress_bar.progress(idx / total_files)
            
        status_text.success(f"Successfully translated {success_count} of {total_files} files!")
        
        # Create ZIP for download
        shutil.make_archive("translated_chapters_output", "zip", output_dir)
        
        with open("translated_chapters_output.zip", "rb") as fp:
            st.download_button(
                label="📦 Download Translated Files (ZIP)",
                data=fp,
                file_name="translated_chapters.zip",
                mime="application/zip"
            )
