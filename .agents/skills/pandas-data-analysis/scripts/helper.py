#!/usr/bin/env python3
import json
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout, format="%(message)s")
logging.getLogger(__name__).info(
    json.dumps({"skill": "pandas-data-analysis"}, indent=2)
)
