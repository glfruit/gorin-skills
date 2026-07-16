#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict


@dataclass
class Route:
    mode: str
    target_skill: str
    rationale: str
    notes: list[str]


MODE_TABLE = {
    "cover": Route(
        mode="cover",
        target_skill="baoyu-cover-image",
        rationale="Article or post cover requests map best to the dedicated cover-image workflow.",
        notes=["Best for single hero images.", "Use when the user mentions 封面, cover, hero image."],
    ),
    "infographic": Route(
        mode="infographic",
        target_skill="baoyu-infographic",
        rationale="High-density visual explanation requests map to the infographic workflow.",
        notes=["Best for 信息图, visual summary, dense explainers.", "Prefer portrait when the user wants a card-like vertical layout."],
    ),
    "multi-card": Route(
        mode="multi-card",
        target_skill="baoyu-xhs-images",
        rationale="Carousel or multi-panel social-card requests map to the XHS image series workflow.",
        notes=["Best for 多图卡片, carousel, 小红书图组.", "Good default when one long card would be too dense."],
    ),
    "comic": Route(
        mode="comic",
        target_skill="baoyu-comic",
        rationale="Narrative, manga, or educational-comic requests need storyboard + image generation.",
        notes=["Best for 漫画, comic, manga, storyboard-style explanation."],
    ),
    "whiteboard": Route(
        mode="whiteboard",
        target_skill="baoyu-image-gen",
        rationale="Whiteboard or sketchnote requests currently need a prompt-driven image workflow rather than a dedicated renderer.",
        notes=["Include whiteboard / hand-drawn / arrows / labels in the prompt.", "Use aspect ratio based on the user's target surface."],
    ),
    "long-card": Route(
        mode="long-card",
        target_skill="baoyu-infographic",
        rationale="Long reading cards are closest to portrait infographic layouts in the current OpenClaw stack.",
        notes=["Prefer portrait aspect.", "Use dense-modules or bento-grid style recommendations when helpful."],
    ),
    "generic-image": Route(
        mode="generic-image",
        target_skill="baoyu-image-gen",
        rationale="When the user just wants a visual artifact without a stronger structural signal, fall back to generic image generation.",
        notes=["Ask one clarifying question only if the output shape is still ambiguous."],
    ),
}


def infer_mode(text: str, explicit: str | None) -> str:
    if explicit:
        key = explicit.strip().lower()
        aliases = {
            "-l": "long-card",
            "-i": "infographic",
            "-m": "multi-card",
            "-c": "comic",
            "-w": "whiteboard",
            "card": "long-card",
            "long": "long-card",
            "poster": "multi-card",
        }
        return aliases.get(key, key)

    t = text.lower()
    if any(k in t for k in ["封面", "cover", "hero image"]):
        return "cover"
    if any(k in t for k in ["漫画", "comic", "manga"]):
        return "comic"
    if any(k in t for k in ["白板", "whiteboard", "sketchnote", "视觉笔记"]):
        return "whiteboard"
    if any(k in t for k in ["多卡", "多图", "carousel", "小红书", "xhs"]):
        return "multi-card"
    if any(k in t for k in ["信息图", "infographic", "visual summary", "可视化"]):
        return "infographic"
    if any(k in t for k in ["长图", "卡片", "做成图", "做成卡片", "reading card"]):
        return "long-card"
    return "generic-image"


def main() -> int:
    parser = argparse.ArgumentParser(description="Route a visual-card request to the best existing OpenClaw skill.")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--mode", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    mode = infer_mode(args.text, args.mode)
    route = MODE_TABLE.get(mode, MODE_TABLE["generic-image"])

    if args.json:
        print(json.dumps(asdict(route), ensure_ascii=False, indent=2))
    else:
        print(f"mode: {route.mode}")
        print(f"target_skill: {route.target_skill}")
        print(f"rationale: {route.rationale}")
        for note in route.notes:
            print(f"- {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
