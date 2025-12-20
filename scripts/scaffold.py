import os
import utils
import shutil
from pathlib import Path
from config import Config

github_user = os.getenv("GH_USER")

class Scaffold:
    def __init__(self):
        self.repo_root = Path(Config.ROOT_PATH)
        # Step 3 Source: awesome-topics/_data/
        self.src_data_dir = self.repo_root / "_data"
        # Step 3 Destination: awesome-topics/docs/_topics/
        self.docs_topics_dir = self.repo_root / "docs" / "_topics"

    def yaml_to_md_topic(self, yaml_file, md_file, topic_name):
        """Generates a standalone Markdown file for a specific topic."""
        data = utils.read_yaml(yaml_file)
        
        md_lines = [f"# {topic_name}", ""]
        
        # Generate Local TOC for the specific topic page
        md_lines.append(utils.generate_toc(data))
        md_lines.append("\n---\n")

        for sec in data.get("section", []):
            venue = sec["title"]
            venue_id = f"venue-{venue.lower()}"
            venue_data = data.get(venue, {})

            md_lines.append(f'## {venue} <a id="{venue_id}"></a>')
            md_lines.append("<details open>")
            md_lines.append(f"<summary>Expand {venue}</summary>\n")

            for year in sorted(venue_data.keys(), reverse=True):
                if not isinstance(venue_data[year], dict):
                    continue
                    
                year_block = venue_data[year]
                year_id = f"{venue.lower()}-{year}"
                md_lines.append(f'### {year} <a id="{year_id}"></a>')
                md_lines.append(utils.yaml_block_to_mdtable(
                    year_block["header"],
                    year_block["body"],
                ))
                md_lines.append("\n")
            md_lines.append("</details>\n")

        utils.write_mdfile(md_file, "\n".join(md_lines))

    def merge_md_yaml(self, yaml_file=None, md_file=None):
        """
        1. Generates topic-wise MD files.
        2. Builds a comprehensive TOC in README.md linking to those files.
        """
        self.docs_topics_dir.mkdir(parents=True, exist_ok=True)
        
        all_topics_summary = []

        if self.src_data_dir.exists():
            for yaml_path in sorted(self.src_data_dir.glob("*.yaml")):
                topic_id = yaml_path.stem
                dest_md = self.docs_topics_dir / f"{topic_id}.md"
                display_title = topic_id.replace("-", " ").title()

                # Generate the standalone .md file
                self.yaml_to_md_topic(yaml_path, dest_md, display_title)
                
                # Load data to build the README TOC
                topic_data = utils.read_yaml(yaml_path)
                all_topics_summary.append({
                    "id": topic_id,
                    "name": display_title,
                    "data": topic_data
                })

        # Update the main README.md
        # print(Config.README_PATH)
        md_file = md_file or Config.README_PATH
        if os.path.exists(md_file):
            self.generate_main_readme_content(all_topics_summary, md_file)

    def generate_main_readme_content(self, topics_list, md_file):
        """Updates the README.md with the nested TOC linking to standalone pages."""
        md_str = utils.read_mdfile(md_file)
        
        toc_lines = ["## Table of Contents", ""]

        base_url = f"https://{github_user}.github.io/awesome-topics"

        for topic in topics_list:
            topic_url = f"{base_url}/{topic['id']}"

            toc_lines.append("<details>")
            toc_lines.append(f"<summary><strong>{topic['name']}</strong></summary>")
            toc_lines.append("")

            for sec in topic["data"].get("section", []):
                venue = sec["title"]

                toc_lines.append("  <details>")
                toc_lines.append(f"  <summary>{venue}</summary>")
                toc_lines.append("")

                venue_data = topic["data"].get(venue, {})
                years = sorted(
                    [y for y in venue_data.keys() if isinstance(venue_data[y], dict)],
                    reverse=True
                )

                for year in years:
                    toc_lines.append(
                        f"  - [{year}]({topic_url}#"
                        f"{venue.lower()}-{year})"
                    )

                toc_lines.append("  </details>")

            toc_lines.append("</details>")
            toc_lines.append("")

        # REPAIR: Using the Config markers properly to avoid ValueError: empty separator 
        start_marker = Config.START_COMMENT.format("TOC") 
        end_marker = Config.END_COMMENT.format("TOC") 
        updated_md = utils.replace_content( md_str, 
                                           "\n".join(toc_lines), 
                                           start_marker, 
                                           end_marker ) 
        
        utils.write_mdfile(md_file, updated_md)
