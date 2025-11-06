#!/usr/bin/env python3
"""Check LangSmith tracing status from database and environment."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.operations import get_app_setting
from src.database.schema import create_database
import os

# Ensure database exists
create_database()

# Check database
db_value = get_app_setting('LANGCHAIN_TRACING_V2', default=None)
env_value = os.getenv('LANGCHAIN_TRACING_V2', 'not set')
api_key = os.getenv('LANGCHAIN_API_KEY', 'not set')

print('=' * 60)
print('LangSmith Tracing Status')
print('=' * 60)
print(f'Database Setting: {db_value if db_value else "not set"}')
print(f'Environment Variable: {env_value}')
print(f'API Key: {"SET" if api_key != "not set" else "NOT SET"}')

# Determine current status
if db_value:
    enabled = db_value.lower() in ('true', '1', 'yes', 'on')
    print(f'\nCurrent Status: {"ENABLED" if enabled else "DISABLED"} (from database)')
elif env_value != 'not set':
    enabled = env_value.lower() in ('true', '1', 'yes', 'on')
    print(f'\nCurrent Status: {"ENABLED" if enabled else "DISABLED"} (from environment)')
else:
    print('\nCurrent Status: DISABLED (default)')

print('=' * 60)

