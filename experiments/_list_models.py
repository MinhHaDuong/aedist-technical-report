#!/usr/bin/env python3
"""List model short names for Makefile consumption.

Usage:
    python3 _list_models.py models.yaml --set census_cloud --experiments experiments.toml
    python3 _list_models.py models.yaml --set census_cloud --experiments experiments.toml --format full
    python3 _list_models.py models.yaml --set census_local --experiments experiments.toml --format padme-short
"""

import argparse
import sys
import tomllib

import yaml


def short_name(model_id: str) -> str:
    """Extract short name from model ID (strip provider prefix, replace colons)."""
    return model_id.split("/")[-1].replace(":", "-")


def main():
    parser = argparse.ArgumentParser(description="List model names for Makefile targets")
    parser.add_argument("models", help="Path to models.yaml")
    parser.add_argument("--set", required=True, dest="model_set", help="Model set name")
    parser.add_argument("--experiments", default="experiments.toml", help="Path to experiments.toml")
    parser.add_argument(
        "--format",
        choices=["short", "full", "padme-short"],
        default="short",
        help="Output format: short (provider stripped), full (model ID), padme-short (colon→dash)",
    )
    args = parser.parse_args()

    with open(args.models) as f:
        models = yaml.safe_load(f)

    with open(args.experiments, "rb") as f:
        experiments = tomllib.load(f)

    model_set = experiments.get("sets", {}).get(args.model_set)
    if not model_set:
        print(f"Error: set '{args.model_set}' not found in {args.experiments}", file=sys.stderr)
        sys.exit(1)

    set_ids = set(model_set["model_ids"])
    selected = [m for m in models if m["id"] in set_ids]

    if args.format == "full":
        names = [m["id"] for m in selected]
    elif args.format == "padme-short":
        names = [m["id"].replace(":", "-") for m in selected]
    else:
        names = [short_name(m["id"]) for m in selected]

    print(" ".join(names))


if __name__ == "__main__":
    main()
