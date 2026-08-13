'''Structural diff between two Teeworlds/DDNet map versions.

Adapted from the mapdiff module of https://github.com/murpii/ddnet-discord-testing-bot
(extensions/map_testing/mapdiff/diff.py); see DIFF.md there for the model, the
algorithm and the data shapes. Changes for this project: python 3.9 compatibility,
the discord-bot async wrapper is dropped and a plain-text summary was added.

Requires the twmap and numpy packages.
'''

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import twmap

log = logging.getLogger(__name__)

LAYERS = ("Game", "Front", "Tele", "Switch", "Speedup", "Tune")
MAX_LAYER_LINES = 12


@dataclass
class LayerChange:
    group: int
    index: int
    kind: str
    name: str
    added: int = 0
    removed: int = 0
    modified: int = 0
    bbox: tuple[int, int, int, int] | None = None
    note: str | None = None

    @property
    def total(self) -> int:
        return self.added + self.removed + self.modified

    @property
    def is_physics(self) -> bool:
        return self.kind in LAYERS

    def label(self) -> str:
        base = f"{self.kind} \"{self.name}\"" if self.name else self.kind
        return base if self.is_physics or self.name else f"{base} (g{self.group}/l{self.index})"


@dataclass
class ChangeMasks:
    """The three per-cell change grids, accumulated across the layers of one category."""
    added: "np.ndarray"
    removed: "np.ndarray"
    modified: "np.ndarray"

    @classmethod
    def zeros(cls, shape) -> "ChangeMasks":
        return cls(*(np.zeros(shape, dtype=bool) for _ in range(3)))

    def merge(self, added, removed, modified) -> None:
        self.added |= added
        self.removed |= removed
        self.modified |= modified

    def any(self) -> bool:
        return bool(self.added.any() or self.removed.any() or self.modified.any())


@dataclass
class MapDiffResult:
    layer_changes: list[LayerChange] = field(default_factory=list)
    added_layers: list[str] = field(default_factory=list)
    removed_layers: list[str] = field(default_factory=list)
    quad_changes: list[tuple[str, int]] = field(default_factory=list)
    added_images: list[str] = field(default_factory=list)
    removed_images: list[str] = field(default_factory=list)
    info_changes: list[str] = field(default_factory=list)
    dimension_change: str | None = None
    error: str | None = None
    width: int | None = None
    height: int | None = None

    mask_added: "np.ndarray | None" = None
    mask_removed: "np.ndarray | None" = None
    mask_modified: "np.ndarray | None" = None

    @property
    def has_changes(self) -> bool:
        return bool(
            self.layer_changes or self.added_layers or self.removed_layers
            or self.quad_changes or self.added_images or self.removed_images
            or self.info_changes or self.dimension_change
        )

    def union_mask(self) -> "np.ndarray | None":
        union = None
        for mask in (self.mask_added, self.mask_removed, self.mask_modified):
            if mask is not None:
                union = mask if union is None else (union | mask)
        return union

    def change_clusters(self, max_clusters: int = 4, bin_size: int = 20):
        union = self.union_mask()
        if union is None or not union.any():
            return [], 0

        occupied = occupied_bins(union, bin_size)
        bin_groups = connected_bin_groups(occupied)

        clusters = []
        for group in bin_groups:
            cells = cells_in_bins(union, group, bin_size)
            ys, xs = np.nonzero(cells)
            bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            clusters.append((cells, bbox, int(cells.sum())))

        clusters.sort(key=lambda c: c[2], reverse=True)

        out = []
        for cells, bbox, _ in clusters[:max_clusters]:
            out.append((
                self.mask_added & cells if self.mask_added is not None else None,
                self.mask_removed & cells if self.mask_removed is not None else None,
                self.mask_modified & cells if self.mask_modified is not None else None,
                bbox,
            ))
        return out, len(clusters)

    def summary_lines(self) -> list[str]:
        '''Plain-text summary of the changes, one item per line.'''
        if self.error:
            return [self.error]
        if not self.has_changes:
            return ['No structural changes detected.']

        lines = []
        if self.dimension_change:
            lines.append(f"Map resized: {self.dimension_change}")

        physics = sorted((lc for lc in self.layer_changes if lc.is_physics),
                         key=lambda lc: lc.total, reverse=True)
        design = sorted((lc for lc in self.layer_changes if not lc.is_physics),
                        key=lambda lc: lc.total, reverse=True)
        shown = (physics + design)[:MAX_LAYER_LINES]
        for lc in shown:
            lines.append(format_layer_plain(lc))
        hidden = len(self.layer_changes) - len(shown)
        if hidden > 0:
            lines.append(f"…and {hidden} more changed layer(s)")

        for label, delta in self.quad_changes:
            lines.append(f"Quads ({label}): {'+' if delta > 0 else ''}{delta}")
        if self.added_layers:
            lines.append(f"Layers added: {', '.join(self.added_layers)}")
        if self.removed_layers:
            lines.append(f"Layers removed: {', '.join(self.removed_layers)}")
        if self.added_images:
            lines.append(f"Images +: {', '.join(self.added_images)}")
        if self.removed_images:
            lines.append(f"Images −: {', '.join(self.removed_images)}")
        for change in self.info_changes:
            lines.append(f"Info {change}")
        return lines


def occupied_bins(union: np.ndarray, bin_size: int) -> np.ndarray:
    h, w = union.shape
    bins_high, bins_wide = h // bin_size + 1, w // bin_size + 1
    occupied = np.zeros((bins_high, bins_wide), dtype=bool)
    ys, xs = np.nonzero(union)
    occupied[ys // bin_size, xs // bin_size] = True
    return occupied


def connected_bin_groups(occupied: np.ndarray) -> list[list[tuple[int, int]]]:
    bins_high, bins_wide = occupied.shape
    seen = np.zeros_like(occupied)
    groups: list[list[tuple[int, int]]] = []

    for start_y, start_x in zip(*np.nonzero(occupied)):
        if seen[start_y, start_x]:
            continue

        seen[start_y, start_x] = True
        queue = deque([(int(start_y), int(start_x))])
        group: list[tuple[int, int]] = []
        while queue:
            by, bx = queue.popleft()
            group.append((by, bx))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = by + dy, bx + dx
                    if (0 <= ny < bins_high and 0 <= nx < bins_wide
                            and occupied[ny, nx] and not seen[ny, nx]):
                        seen[ny, nx] = True
                        queue.append((ny, nx))
        groups.append(group)

    return groups


def cells_in_bins(union: np.ndarray, group: list[tuple[int, int]], bin_size: int) -> np.ndarray:
    selected = np.zeros_like(union)
    for by, bx in group:
        selected[by * bin_size:(by + 1) * bin_size, bx * bin_size:(bx + 1) * bin_size] = True
    selected &= union
    return selected


def format_layer_plain(lc: LayerChange) -> str:
    if lc.note:
        return f"{lc.label()}: {lc.note}"
    parts = []
    if lc.added:
        parts.append(f"+{lc.added}")
    if lc.removed:
        parts.append(f"−{lc.removed}")
    if lc.modified:
        parts.append(f"~{lc.modified}")
    return f"{lc.label()}: {lc.total} tiles ({' / '.join(parts)})"


def layer_desc(group_index: int, layer) -> str:
    name = layer.name
    return f"g{group_index} {layer.kind()} \"{name}\"" if name else f"g{group_index} {layer.kind()}"


class MapDiff:
    @staticmethod
    def diff_bytes(old_bytes: bytes, new_bytes: bytes) -> MapDiffResult:
        result = MapDiffResult()
        try:
            old_map = twmap.Map.from_bytes(old_bytes)
            new_map = twmap.Map.from_bytes(new_bytes)
        except Exception as exc:
            log.warning("MapDiff: couldn't parse a map for diffing: %s", exc)
            result.error = "Couldn't parse one of the map versions for a diff."
            return result

        game = new_map.game_layer()
        if game is not None:
            shape = (game.height(), game.width())
            physics_masks = ChangeMasks.zeros(shape)
            design_masks = ChangeMasks.zeros(shape)
        else:
            physics_masks = design_masks = None

        old_by_pos = {
            (gi, li): ly for gi, g in enumerate(old_map.groups) for li, ly in enumerate(g.layers)
        }
        new_by_pos = {
            (gi, li): ly for gi, g in enumerate(new_map.groups) for li, ly in enumerate(g.layers)
        }

        for (gi, li) in sorted(set(old_by_pos) | set(new_by_pos)):
            old_layer = old_by_pos.get((gi, li))
            new_layer = new_by_pos.get((gi, li))

            if old_layer is None:
                result.added_layers.append(layer_desc(gi, new_layer))
                continue
            if new_layer is None:
                result.removed_layers.append(layer_desc(gi, old_layer))
                continue

            kind = new_layer.kind()
            if old_layer.kind() != kind:
                result.removed_layers.append(layer_desc(gi, old_layer))
                result.added_layers.append(layer_desc(gi, new_layer))
                continue

            if kind == "Quads":
                delta = len(new_layer.quads) - len(old_layer.quads)
                if delta:
                    result.quad_changes.append((layer_desc(gi, new_layer), delta))
                continue
            if kind == "Sounds":
                continue

            added, removed, modified = diff_tile_layer(result, gi, li, old_layer, new_layer)
            if (added is not None and physics_masks is not None
                    and added.shape == physics_masks.added.shape):
                target = physics_masks if kind in LAYERS else design_masks
                target.merge(added, removed, modified)

        chosen = physics_masks if (physics_masks is not None and physics_masks.any()) else design_masks
        if chosen is not None:
            result.mask_added = chosen.added if chosen.added.any() else None
            result.mask_removed = chosen.removed if chosen.removed.any() else None
            result.mask_modified = chosen.modified if chosen.modified.any() else None

        diff_map_level(result, old_map, new_map)
        return result


def diff_tile_layer(result, gi, li, old_layer, new_layer):
    try:
        old_tiles = old_layer.tiles
        new_tiles = new_layer.tiles
    except Exception:
        return None, None, None

    if old_tiles.shape != new_tiles.shape:
        oh, ow = old_tiles.shape[0], old_tiles.shape[1]
        nh, nw = new_tiles.shape[0], new_tiles.shape[1]
        result.layer_changes.append(LayerChange(
            gi, li, new_layer.kind(), new_layer.name,
            note=f"resized {ow}x{oh} -> {nw}x{nh}",
        ))
        return None, None, None

    changed = np.any(old_tiles != new_tiles, axis=2)
    if not changed.any():
        return None, None, None

    old_id = old_tiles[..., 0]
    new_id = new_tiles[..., 0]
    added = changed & (old_id == 0) & (new_id != 0)
    removed = changed & (old_id != 0) & (new_id == 0)
    modified = changed & ~added & ~removed

    ys, xs = np.nonzero(changed)
    bbox = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    result.layer_changes.append(LayerChange(
        gi, li, new_layer.kind(), new_layer.name,
        int(added.sum()), int(removed.sum()), int(modified.sum()), bbox,
    ))
    return added, removed, modified


def diff_map_level(result, old_map, new_map) -> None:
    old_images = {im.name for im in old_map.images}
    new_images = {im.name for im in new_map.images}
    result.added_images = sorted(new_images - old_images)
    result.removed_images = sorted(old_images - new_images)

    for fld in ("author", "version", "credits", "license"):
        old_val = getattr(old_map.info, fld, None)
        new_val = getattr(new_map.info, fld, None)
        if old_val != new_val:
            result.info_changes.append(f"{fld}: \"{old_val}\" -> \"{new_val}\"")

    old_game = old_map.game_layer()
    new_game = new_map.game_layer()
    if new_game is not None:
        result.width, result.height = new_game.width(), new_game.height()
    if old_game is not None and new_game is not None:
        old_dim = (old_game.width(), old_game.height())
        new_dim = (new_game.width(), new_game.height())
        if old_dim != new_dim:
            result.dimension_change = f"{old_dim[0]}x{old_dim[1]} -> {new_dim[0]}x{new_dim[1]}"
