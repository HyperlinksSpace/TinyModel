#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

from huggingface_hub import create_repo, upload_folder


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Publish one TinyOrbit artifact folder to Hugging Face."
    )
    parser.add_argument("--namespace", required=True, help="HF user/org namespace")
    parser.add_argument("--name", required=True, help="HF repository name")
    parser.add_argument(
        "--repo-type",
        required=True,
        choices=["model", "dataset", "space"],
        help="HF repository type",
    )
    parser.add_argument("--source-dir", required=True, help="Local folder to upload")
    parser.add_argument("--token", required=False, help="HF token")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = Path(args.source_dir)
    if not source_dir.exists() or not source_dir.is_dir():
        raise FileNotFoundError(f"Source directory not found: {source_dir}")

    token = args.token or os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError("Missing Hugging Face token. Set HF_TOKEN.")

    repo_id = f"{args.namespace}/{args.name}"

    create_repo(
        repo_id=repo_id,
        repo_type=args.repo_type,
        token=token,
        exist_ok=True,
    )

    upload_folder(
        folder_path=str(source_dir),
        repo_id=repo_id,
        repo_type=args.repo_type,
        token=token,
        commit_message=f"Deploy {args.name} from GitHub Actions",
        ignore_patterns=[".gitkeep"],
    )

    print(json.dumps({"repo_id": repo_id, "repo_type": args.repo_type}))


if __name__ == "__main__":
    main()
