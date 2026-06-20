"""Cognee sponsor layer: graph + semantic memory ON TOP of the SQLite source of truth.

Additive and optional. If cognee is missing or unconfigured, OffBabel still works fully via
memory.py. This layer is the shot at the Cognee prize (PRD 9): a literal picture of the
learner's memory graph + a semantic query that plain key-value cannot do.

OFFLINE CONFIG (set on the Mac AFTER caching, BEFORE first import). Easiest is a .env, or export:
    LLM_PROVIDER=ollama
    LLM_MODEL=llama3.1:8b
    LLM_ENDPOINT=http://localhost:11434/v1
    LLM_API_KEY=ollama                       # non-empty (works around cognee issue #807)
    STRUCTURED_OUTPUT_FRAMEWORK=BAML         # robust JSON from small local models
    BAML_LLM_PROVIDER=ollama
    BAML_LLM_MODEL=llama3.1:8b
    BAML_LLM_ENDPOINT=http://localhost:11434/v1
    BAML_LLM_API_KEY=ollama
    EMBEDDING_PROVIDER=fastembed
    EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
    EMBEDDING_DIMENSIONS=384
Pre-pull the Ollama model and let fastembed cache its ONNX weights on wifi, then test offline.

Run a self-contained demo (on the Mac, once configured):
    python -m offbabel.cognee_memory
"""
import asyncio

from . import srs

DATASET = "offbabel_learner"


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
    """Push the current struggle data into Cognee and build the graph. Idempotent enough for a demo."""
    import cognee

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
        print("cognee not installed. SQLite memory still works; this layer is the sponsor bonus.")
        return
    # seed a little data if the db is empty so the demo has something to show
    srs.init()
    if not [it for it in srs.all_items() if it["miss_count"] > 0]:
        srs.record_result("speak", "greetings", "A1", "tener", False)
        srs.record_result("speak", "greetings", "A1", "tener", False)
        srs.record_result("speak", "ordering_food", "A2", "estar", False)
        srs.record_result("sign", "L1_vowels", "L1_vowels", "O", False)
    n = await sync_from_sqlite()
    print(f"synced {n} items into cognee")
    answer = await insight(
        "What kinds of things does this learner struggle with most, and what should they review next?"
    )
    print("INSIGHT:", answer)
    try:
        visualize("graph.html")
        print("wrote graph.html")
    except Exception as e:  # noqa: BLE001
        print("visualize skipped:", e)


if __name__ == "__main__":
    asyncio.run(_demo())
