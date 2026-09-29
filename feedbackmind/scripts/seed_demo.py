"""
FeedbackMind — one-command perfect demo state.
    python scripts/seed_demo.py            fills whatever is missing
    python scripts/seed_demo.py --fresh    wipes local state markers first
Chain: dataset? -> ingest -> digests 1-8 (PM correction injected after wk 2)
For a 100% pristine memory bank: delete bank 'feedbackmind' in the cloud UI once, then --fresh.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))          # so `core` imports work from anywhere

from core import digest, ingest        # noqa: E402  (path fix must come first)

DATA = ROOT / "data"


def main(fresh=False):
    if fresh:
        for f in ("ingest_state.json", "digests.json", "digest_state.json"):
            p = DATA / f
            if p.exists():
                p.unlink()
                print(f"removed local state: {f}")

    if not (DATA / "feedback.csv").exists():
        print("== generating dataset ==")
        import runpy
        runpy.run_path(str(ROOT / "scripts" / "generate_data.py"),
                       run_name="__main__")

    if not (DATA / "ingest_state.json").exists():
        print("== ingesting into Hindsight ==")
        ingest.ingest()
    else:
        print("ingest already done - skipping (use --fresh to redo)")

    print("== digest timeline + learning loop ==")
    digest.seed()
    print("\n🎬 Demo state ready. Launch:  streamlit run app.py")


if __name__ == "__main__":
    try:
        main(fresh="--fresh" in sys.argv)
    finally:
        from core import memory
        memory.client().close()