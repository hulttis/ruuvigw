# coding=utf-8
# -------------------------------------------------------------------------------
# Name:        logger_config.py
# Purpose:     logger configuration file (json) reader
# Copyright:   (c) 2019 TK
# Licence:     MIT
# -------------------------------------------------------------------------------
import os
import json
import logging.config

def logger_config(
    default_path='logging.json',
    default_level=logging.INFO,
    env_key='LOG_CFG'
):
    """Setup logging configuration
    """

    path = default_path
    value = os.getenv(env_key, None)
    if value:
        path = value
    if os.path.exists(path):
        with open(path, 'rt') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)