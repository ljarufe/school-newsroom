"""Public result contracts for smart-paste normalization.

The public façade in :mod:`apps.news.smart_paste` re-exports these types so
callers keep their established import path.
"""

from collections import Counter
from dataclasses import dataclass, field


@dataclass(frozen=True)
class NormalizedBlock:
    block_type: str
    value: str | dict[str, object]
    kind: str

    def as_dict(self) -> dict[str, object]:
        return {"type": self.block_type, "value": self.value}


@dataclass
class NormalizedPaste:
    blocks: list[NormalizedBlock]
    source: str
    warnings: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, object]:
        counts = Counter(block.kind for block in self.blocks)
        return {
            "blocks": [block.as_dict() for block in self.blocks],
            "source": self.source,
            "summary": {
                "total": len(self.blocks),
                "paragraphs": counts["paragraph"],
                "headings": counts["heading"],
                "lists": counts["list"],
                "quotes": counts["quote"],
                "dividers": counts["divider"],
                "tables": counts["table"],
            },
            "warnings": self.warnings,
        }
