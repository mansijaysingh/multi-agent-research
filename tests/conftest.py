import os

# Tests never call real APIs; also make sure they never send traces.
# conftest.py runs before the test files import the agents, and load_dotenv()
# doesn't overwrite a variable that's already set, so this wins over .env.
os.environ["LANGSMITH_TRACING"] = "false"
