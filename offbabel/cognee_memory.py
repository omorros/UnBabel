"""Cognee layer: graph + semantic memory ON TOP of the SQLite source of truth.

Additive and optional. If cognee is missing or unconfigured, OffBabel still works fully via
srs.py/memory.py. This is the shot at the Cognee prize: a literal picture of the learner's
memory graph + a semantic query that plain key-value storage cannot answer.

This module SELF-CONFIGURES for fully-offline use (local Ollama LLM + in-process fastembed
embeddings). You do not need a .env. Override any default with env vars if you want.

RUN IT (on the demo machine, e.g. the Mac):
    brew install ollama && ollama serve &           # local LLM (Linux/Win: install Ollama)
    ollama pull llama3.1:8b                          # the cognify model (or set OFFBABEL_COGNEE_MODEL)
    pip install "cognee[fastembed]"
    python -m offbabel.cognee_memory                 # builds the graph + writes graph.html
Pull the model + let fastembed cache its weights on wifi once, then it runs offline.
"""
import asyncio
import os

DATASET = "offbabel_learner"


def configure():
    """Set Cognee to run fully local/offline. Called at import, before cognee is loaded.
    Everything is os.environ.setdefault, so real env vars still win."""
    model = os.environ.get("OFFBABEL_COGNEE_MODEL", "llama3.1:8b")
    endpoint = os.environ.get("OFFBABEL_OLLAMA", "http://localhost:11434/v1")
    defaults = {
        # LLM for cognify + search -> local Ollama
        "LLM_PROVIDER": "ollama",
        "LLM_MODEL": model,
        "LLM_ENDPOINT": endpoint,
        "LLM_API_KEY": "ollama",  # must be non-empty (cognee issue #807)
        # robust structured output from local models
        "STRUCTURED_OUTPUT_FRAMEWORK": "BAML",
        "BAML_LLM_PROVIDER": "ollama",
        "BAML_LLM_MODEL": model,
        "BAML_LLM_ENDPOINT": endpoint,
        "BAML_LLM_API_KEY": "ollama",
        # embeddings in-process, no server, no OpenAI
        "EMBEDDING_PROVIDER": "fastembed",
        "EMBEDDING_MODEL": "sentence-transformers/all-MiniLM-L6-v2",
        "EMBEDDING_DIMENSIONS": "384",
    }
    for k, v in defaults.items():
        os.environ.setdefault(k, v)


configure()  # before any cognee import below


def available():
    try:
        import cognee  # noqa: F401
        return True
    except Exception:  # noqa: BLE001
        return False


def _to_sentence(it):
    """One struggle item -> a short natural-language fact for the graph to reason over."""
    val = it["prompt"]
    miss = it["miss_count"]
    if it["mode"] == "sign":
        return f"The learner practised the BSL fingerspelling sign '{val}' and missed it {miss} times."
    return (
        f"In a {it['scenario']} ({it['level']}) lesson, the learner struggled with "
        f"'{val}', missing it {miss} times."
    )


async def sync_from_sqlite():
    """Push the current struggle data into Cognee and build the graph."""
    import cognee
    from . import srs

    items = [it for it in srs.all_items() if it["miss_count"] > 0]
    if not items:
        return 0
    for it in items:
        await cognee.add(_to_sentence(it), dataset_name=DATASET)
    await cognee.cognify([DATASET])
    return len(items)


async def insight(query_text):
    """Semantic / graph answer over the learner's memory (the Cognee 'wow' query)."""
    import cognee

    return await cognee.search(
        query_text=query_text,
        query_type=cognee.SearchType.GRAPH_COMPLETION,
    )


def visualize(path="graph.html"):
    """Write a browsable picture of the learner's memory graph. Great for the live pitch."""
    import cognee

    return cognee.visualize_graph(path)


async def _demo():
    if not available():
        print("cognee not installed (pip install 'cognee[fastembed]'). SQLite memory still works.")
        return
    from . import srs

    srs.init()
    if not [it for it in srs.all_items() if it["miss_count"] > 0]:
        # seed a little data so the graph has something to show
        srs.record_result("speak", "greetings", "A1", "tener", False)
        srs.record_result("speak", "greetings", "A1", "tener", False)
        srs.record_result("speak", "ordering_food", "A2", "estar", False)
        srs.record_result("sign", "letters_abgw", "letters_abgw", "G", False)
    try:
        n = await sync_from_sqlite()
        print(f"synced {n} struggle items into Cognee")
    except Exception as e:  # noqa: BLE001
        print("cognify failed (is Ollama running with the model pulled?):", e)
        return
    try:
        answer = await insight(
            "What kinds of things does this learner struggle with most, and what to review next?"
        )
        print("INSIGHT:", answer)
    except Exception as e:  # noqa: BLE001
        print("search failed:", e)
    try:
        visualize("graph.html")
        print("wrote graph.html (open it to see the learner's memory graph)")
    except Exception as e:  # noqa: BLE001
        print("visualize skipped:", e)


if __name__ == "__main__":
    asyncio.run(_demo())
