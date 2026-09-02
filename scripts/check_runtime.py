import os
from pathlib import Path
from importlib.metadata import PackageNotFoundError, version

from dotenv import load_dotenv

EXPECTED = "0.1.0"
ROOT = Path(__file__).parents[1]
REQUIRED_EXPORTS = [
    "get_fund_detail",
    "get_fund_daily",
    "get_fund_daily_post",
]

load_dotenv(ROOT / ".env", override=False)


def candidate_roots() -> list[Path]:
    raw = os.environ.get("PARQUET_ROOT_CANDIDATES", "")
    items = [os.environ.get("PARQUET_ROOT_PATH", "").strip()]
    items.extend(part.strip() for part in raw.split(",") if part.strip())
    seen: set[str] = set()
    out: list[Path] = []
    for item in items:
        if not item:
            continue
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(Path(item))
    return out


def has_required_dirs(path: Path) -> bool:
    return all((path / name).exists() for name in ["fund_basic", "fund_daily"])


def pick_root() -> Path | None:
    for path in candidate_roots():
        try:
            if has_required_dirs(path):
                return path
        except OSError:
            continue
    return None

try:
    installed = version("panda_data")
except PackageNotFoundError:
    raise SystemExit("panda_data is not installed; obtain and install the authorized 0.1.0 SDK first")

if installed != EXPECTED:
    raise SystemExit(f"panda_data version mismatch: expected {EXPECTED}, got {installed}")

import panda_data

missing = [name for name in REQUIRED_EXPORTS if not hasattr(panda_data, name)]
if missing:
    raise SystemExit(f"Missing ETF exports: {', '.join(missing)}")

parquet_path = pick_root()
if parquet_path is None:
    tried = ", ".join(str(p) for p in candidate_roots()) or "<not configured>"
    raise SystemExit(f"No accessible parquet root with fund_basic/fund_daily found. Tried: {tried}")

print(f"panda_data {installed} ready; module={panda_data.__file__}")
print("PARQUET_ROOT_PATH is configured and accessible")
