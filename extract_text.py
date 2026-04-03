import requests
from bs4 import BeautifulSoup
import json
from urllib.parse import urljoin

url = "https://www.kubeflow.org/docs/started/introduction/"
response = requests.get(url)

if response.status_code != 200:
    raise Exception(f"Failed to fetch page: {response.status_code}")

soup = BeautifulSoup(response.text, "html.parser")

main = soup.find("article") or soup.find("main") or soup.body
title = soup.title.string.strip() if soup.title else "No Title"


def extract_heading_text(tag):
    a = tag.find("a")
    if a:
        return a.get_text(" ", strip=True)
    return tag.get_text(" ", strip=True)


def is_valid_code_block(code_text):
    if len(code_text) < 15:
        return False
    if code_text.count("/") == 1 and len(code_text.split()) == 1:
        return False
    return True


def normalize_youtube(url):
    if "youtube.com/embed/" in url:
        return url.replace("embed/", "watch?v=")
    return url


sections = []
current_section = None
seen_code_blocks = set()

current_hierarchy = {
    "h1": None,
    "h2": None,
    "h3": None
}

for tag in main.descendants:

    if not hasattr(tag, "name"):
        continue

    # ---- HEADINGS ----
    if tag.name in ["h1", "h2", "h3"]:
        heading_text = extract_heading_text(tag)

        if not heading_text:
            continue

        if "kubeflow community" in heading_text.lower():
            if current_section and current_section["content"].strip():
                sections.append(current_section)
            break

        if current_section and current_section["content"].strip():
            sections.append(current_section)

        current_hierarchy[tag.name] = heading_text

        if tag.name == "h1":
            current_hierarchy["h2"] = None
            current_hierarchy["h3"] = None
        elif tag.name == "h2":
            current_hierarchy["h3"] = None

        current_section = {
            "heading": heading_text,
            "level": tag.name,
            "parent": current_hierarchy.get("h1") if tag.name != "h1" else None,
            "content": ""
        }

    # ---- TEXT ----
    elif tag.name in ["p", "li"]:
        text = tag.get_text(" ", strip=True)

        if not text:
            continue

        if "kubeflow community" in text.lower():
            if current_section and current_section["content"].strip():
                sections.append(current_section)
            break

        if current_section:
            current_section["content"] += text + "\n"

    # ---- CODE BLOCKS ----
    elif tag.name in ["pre", "code"]:
        code_text = tag.get_text("\n", strip=True)

        if (
            code_text
            and current_section
            and is_valid_code_block(code_text)
            and code_text not in seen_code_blocks
        ):
            current_section["content"] += f"\n```{code_text}```\n"
            seen_code_blocks.add(code_text)

    # ---- TABLES ----
    elif tag.name == "table":
        rows = []

        for tr in tag.find_all("tr"):
            cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
            if cols:
                rows.append(" | ".join(cols))

        if rows and current_section:
            table_text = "\n".join(rows)
            current_section["content"] += f"\n[TABLE]\n{table_text}\n[/TABLE]\n"

    # ---- IMAGES ----
    elif tag.name == "img":
        src = tag.get("src")
        alt = tag.get("alt", "").strip()

        if src and current_section:
            full_url = urljoin(url, src)
            current_section["content"] += f"\n[IMAGE]\nalt: {alt}\nurl: {full_url}\n[/IMAGE]\n"

    # ---- VIDEOS (IFRAME) ----
    elif tag.name == "iframe":
        src = tag.get("src")

        if src and current_section:
            if "youtube.com" in src or "youtu.be" in src:
                video_url = normalize_youtube(src)
                current_section["content"] += f"\n[VIDEO]\nurl: {video_url}\n[/VIDEO]\n"


# Final append
if current_section and current_section["content"].strip():
    sections.append(current_section)


# ---- SECTION DEDUPLICATION ----
unique_sections = []
seen_sections = set()

for sec in sections:
    key = (
        sec["heading"].strip().lower(),
        sec["content"].strip()
    )

    if key not in seen_sections:
        seen_sections.add(key)
        unique_sections.append(sec)


data = {
    "url": url,
    "title": title,
    "sections": unique_sections
}

# ---- EXTRACTED FILE ----
with open("sw_extract.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Structured extraction complete.")