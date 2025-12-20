import json
import re
from pathlib import Path

TOPICS_DIR = Path("topics")
OUTPUT_JSON = Path("data/topic_counts.json")

def count_papers_in_markdown(md_path: Path) -> int:
    """
    Counts papers in a markdown file.
    Assumes one paper per markdown list item or table row.
    """
    text = md_path.read_text(encoding="utf-8")

    # Count markdown list items (ignore nested lists)
    list_items = re.findall(r"^\s*-\s+\[?.+", text, flags=re.MULTILINE)

    # Count table rows (ignore header + separator)
    table_rows = []
    in_table = False
    for line in text.splitlines():
        if line.strip().startswith("|"):
            if not in_table:
                in_table = True
                continue
            table_rows.append(line)
        else:
            in_table = False

    # Heuristic: choose the dominant format
    return max(len(list_items), max(len(table_rows) - 1, 0))


def prettify_topic_name(filename: str) -> str:
    """
    Convert 'federated-learning.md' → 'Federated Learning'
    """
    return filename.replace(".md", "").replace("-", " ").title()


def main():
    topic_counts = {}

    for md_file in sorted(TOPICS_DIR.glob("*.md")):
        topic_name = prettify_topic_name(md_file.name)
        paper_count = count_papers_in_markdown(md_file)
        topic_counts[topic_name] = paper_count

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_JSON.write_text(
        json.dumps(topic_counts, indent=2),
        encoding="utf-8"
    )

    print(f"Tracked {len(topic_counts)} topics")
    print(f"Saved counts to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
