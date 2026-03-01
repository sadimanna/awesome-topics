from loguru import logger
from fire import Fire
from utils import (
    get_msg, init, get_dblp_items, request_data,
    write_venue_yaml, extract_arxiv_query_terms, build_arxiv_query,
    get_arxiv_items, build_public_index, normalize_title, extract_arxiv_id
)
import yaml
from pathlib import Path
import os
import datetime

class Scaffold:
    def __init__(self):
        # Define base paths relative to this file
        self.root_dir = Path(__file__).resolve().parent.parent
        self.configs_dir = self.root_dir / "_configs"
        self.data_out_dir = self.root_dir / "_data"
        self.data_out_dir.mkdir(exist_ok=True)

    def topic_to_title(self, topic_name: str) -> str:
        """
        Convert topic slug to human-readable title.
        federatedml -> Federated ML
        gradient-inversion-attacks -> Gradient Inversion Attacks
        """
        return " ".join(
            word.upper() if word.isupper() else word.capitalize()
            for word in topic_name.replace("-", " ").split()
        )

    def run(
        self,
        env: str = "dev",
        global_cfg_path: str = "./../config.yaml",
        dblp: bool = True,
        arxiv: bool = True,
        no_dblp: bool = False,
        no_arxiv: bool = False,
    ):
        # Initialize global settings (logging, etc)
        global_cfg = init(cfg_path=global_cfg_path)
        # print(global_cfg)
        # {'cache_path': PosixPath('../cached'), 'dblp': {'topics': ['federate%20venue%3AICML%3A'], 'url': 'https://dblp.org/search/publ/api?q={}&format=json&h=1000'}}
        
        # 1. Iterate through every yaml in _configs
        config_files = list(self.configs_dir.glob("*.yaml"))
        # print(config_files)
        if not config_files:
            logger.warning(f"No config files found in {self.configs_dir}")
            return

        if no_dblp:
            dblp = False
        if no_arxiv:
            arxiv = False

        if not dblp and not arxiv:
            logger.warning("Both dblp and arxiv are disabled; nothing to do.")
            return

        # Load cache for DBLP to avoid duplicates across runs
        if dblp:
            cache_path = global_cfg["cache_path"] / "dblp_cache.yaml"
            dblp_cache = yaml.safe_load(open(cache_path, "r")) if cache_path.exists() else {}
        else:
            cache_path = None
            dblp_cache = {}
        # print(dblp_cache is None)

        # Load cache for arXiv to avoid duplicates across runs
        if arxiv:
            arxiv_cache_path = global_cfg["cache_path"] / "arxiv_cache.yaml"
            arxiv_cache = yaml.safe_load(open(arxiv_cache_path, "r")) if arxiv_cache_path.exists() else {}
        else:
            arxiv_cache_path = None
            arxiv_cache = {}

        # Build an index of existing public data to filter duplicates
        public_index = build_public_index(self.data_out_dir) if arxiv else None

        arxiv_cfg = global_cfg.get("arxiv", {}) if arxiv else {}
        arxiv_page_size = int(arxiv_cfg.get("max_results", 50)) if arxiv else 0
        arxiv_cache_empty = not bool(arxiv_cache)
        arxiv_since_date = None
        if arxiv and not arxiv_cache_empty:
            arxiv_since_date = datetime.date.today() - datetime.timedelta(days=7)
        
        aggregated_msg = ""
        total_flag = False

        for c_file in config_files:
            temp_topic_name = self.topic_to_title(c_file.stem)
            logger.info(f"Processing topic config: {temp_topic_name}")
            
            with open(c_file, 'r') as f:
                topic_cfg = yaml.safe_load(f)
            
            # Target output file in _data/ (e.g., federated.yaml)
            target_yaml_path = self.data_out_dir / c_file.name
            
            # The URL template from global config
            dblp_url_template = global_cfg["dblp"]["url"] if dblp else None
            topics = topic_cfg.get("dblp", {}).get("topics", [])
            # print(topics)

            topic_new_items_found = False

            if dblp:
                for topic_query in topics:
                    # Request data
                    dblp_data = request_data(dblp_url_template.format(topic_query))
                    if dblp_data is None:
                        continue

                    items = get_dblp_items(dblp_data)

                    # Filter against cache
                    cached_items = dblp_cache.get(topic_query, [])
                    new_items = [item for item in items if item not in cached_items]
                    # new_items = cached_items

                    if len(new_items) > 0:
                        topic_new_items_found = True
                        total_flag = True

                        # Update local cache object
                        if topic_query not in dblp_cache:
                            dblp_cache[topic_query] = []
                        dblp_cache[topic_query].extend(new_items)

                        # Generate messages for Github/Logs
                        aggregated_msg += get_msg(new_items, topic_query, temp_topic_name, aggregated=True)

                    # Write to the specific YAML file in _data/
                    write_venue_yaml(new_items, target_yaml_path)
                    logger.info(f"Added {len(new_items)} items to {target_yaml_path.name}")
                    if env == "dev":
                        titles = [item.get("title", "").strip() for item in new_items if item.get("title")]
                        if titles:
                            logger.info(
                                f"DBLP new papers for {temp_topic_name} ({topic_query}): "
                                + "; ".join(titles)
                            )

                        # Update public index with DBLP items
                        if public_index is not None:
                            for item in new_items:
                                title_key = (normalize_title(item.get("title", "")), str(item.get("year", "")))
                                if title_key[0]:
                                    public_index["title_year"].add(title_key)
                                link = item.get("ee") or item.get("url") or ""
                                arxiv_id = extract_arxiv_id(link)
                                if arxiv_id:
                                    public_index["arxiv_ids"].add(arxiv_id)

            # ---- arXiv integration (derived from DBLP topics) ----
            if arxiv:
                arxiv_terms = extract_arxiv_query_terms(topics)
                if arxiv_terms:
                    for term in arxiv_terms:
                        arxiv_query = build_arxiv_query(term)
                        arxiv_items = get_arxiv_items(
                            arxiv_query,
                            max_results=arxiv_page_size,
                            since_date=arxiv_since_date,
                        )
                        if not arxiv_items:
                            continue

                        cached_ids = set(arxiv_cache.get(arxiv_query, []))
                        new_items = []
                        new_ids = []

                        for item in arxiv_items:
                            arxiv_id = item.get("arxiv_id")
                            if not arxiv_id or arxiv_id in cached_ids:
                                continue

                            title_key = (normalize_title(item.get("title", "")), str(item.get("year", "")))
                            in_public_by_title = title_key in public_index["title_year"]
                            in_public_by_arxiv = arxiv_id in public_index["arxiv_ids"]
                            is_published = bool(item.get("doi") or item.get("journal_ref"))

                            # Include if unpublished OR not already listed (dedupe by arXiv id)
                            if is_published:
                                if in_public_by_title or in_public_by_arxiv:
                                    continue
                            else:
                                if in_public_by_arxiv:
                                    continue

                            new_items.append(item)
                            new_ids.append(arxiv_id)

                        if new_items:
                            topic_new_items_found = True
                            total_flag = True

                            if arxiv_query not in arxiv_cache:
                                arxiv_cache[arxiv_query] = []
                            arxiv_cache[arxiv_query].extend(new_ids)

                            # Append a brief message for CI/CD output
                            aggregated_msg += f"# {temp_topic_name} - New arXiv papers\n\n"
                            aggregated_msg += f"## {term}\n\n"
                            aggregated_msg += f"Explore {len(new_items)} new arXiv papers for {term}.\n\n"

                        write_venue_yaml(new_items, target_yaml_path)
                        logger.info(f"Added {len(new_items)} arXiv items to {target_yaml_path.name}")
                        if env == "dev":
                            titles = [item.get("title", "").strip() for item in new_items if item.get("title")]
                            if titles:
                                logger.info(
                                    f"arXiv new papers for {temp_topic_name} ({term}): "
                                    + "; ".join(titles)
                                )

                            # Update public index with new arXiv items
                            for item in new_items:
                                title_key = (normalize_title(item.get("title", "")), str(item.get("year", "")))
                                if title_key[0]:
                                    public_index["title_year"].add(title_key)
                                arxiv_id = item.get("arxiv_id")
                                if arxiv_id:
                                    public_index["arxiv_ids"].add(arxiv_id)

        # 2. Save updated cache
        if dblp and cache_path is not None:
            with open(cache_path, "w") as f:
                yaml.safe_dump(dblp_cache, f, sort_keys=False, indent=2)
        if arxiv and arxiv_cache_path is not None:
            with open(arxiv_cache_path, "w") as f:
                yaml.safe_dump(arxiv_cache, f, sort_keys=False, indent=2)

        # 3. Handle CI/CD Output
        if env == "prod" and total_flag:
            env_file = os.getenv("GITHUB_ENV")
            if env_file:
                with open(env_file, "a") as f:
                    # Clip if necessary and write to Github Env
                    output_msg = aggregated_msg[:4000] + "..." if len(aggregated_msg) > 4096 else aggregated_msg
                    f.write(f"MSG<<EOF\n{output_msg}\nEOF\n")

if __name__ == "__main__":
    Fire(Scaffold)
