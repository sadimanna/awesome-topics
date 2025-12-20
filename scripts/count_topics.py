import json
import re
from pathlib import Path

TOPICS_DIR = Path("./../docs/_topics")
OUTPUT_JSON = Path("./../data/topic_counts.json")

TR_PATTERN = re.compile(r"<tr>\s*<td>", re.IGNORECASE)


def extract_title(md_path: Path) -> str:
    """
    Prefer YAML front-matter title if present.
    Fallback to filename.
    """
    text = md_path.read_text(encoding="utf-8")

    # YAML front matter
    match = re.search(r"^---\s*(.*?)\s*---", text, re.DOTALL)
    if match:
        yaml_block = match.group(1)
        title_match = re.search(r"title:\s*(.+)", yaml_block)
        if title_match:
            return title_match.group(1).strip()

    # Fallback
    return md_path.stem.replace("-", " ").title()


def count_papers(md_path: Path) -> int:
    """
    Count number of papers by counting table rows (<tr><td>).
    """
    text = md_path.read_text(encoding="utf-8")
    return len(TR_PATTERN.findall(text))


def main():
    topic_counts = {}

    for md_file in sorted(TOPICS_DIR.glob("*.md")):
        topic_name = extract_title(md_file)
        paper_count = count_papers(md_file)
        topic_counts[topic_name] = paper_count

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(topic_counts, indent=2),
        encoding="utf-8"
    )

    print(f"Topics tracked: {len(topic_counts)}")
    print(f"Saved counts to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
