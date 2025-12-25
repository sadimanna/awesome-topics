from loguru import logger
from fire import Fire
from utils import (
    get_msg, init, get_dblp_items, request_data, 
    write_venue_yaml
)
import yaml
from pathlib import Path
import os

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

    def run(self, env: str = "dev", global_cfg_path: str = "./../config.yaml"):
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

        # Load cache for DBLP to avoid duplicates across runs
        cache_path = global_cfg["cache_path"] / "dblp_cache.yaml"
        dblp_cache = yaml.safe_load(open(cache_path, "r")) if cache_path.exists() else {}
        # print(dblp_cache is None)
        
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
            dblp_url_template = global_cfg["dblp"]["url"]
            topics = topic_cfg.get("dblp", {}).get("topics", [])
            # print(topics)

            topic_new_items_found = False

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

        # 2. Save updated cache
        with open(cache_path, "w") as f:
            yaml.safe_dump(dblp_cache, f, sort_keys=False, indent=2)

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