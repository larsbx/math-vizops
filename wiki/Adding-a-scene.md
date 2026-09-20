# Adding a scene

Four small edits and a test. The shape is deliberately boring: everything a
new scene needs is data, except the transcription.

## 1. Check the artifact declares its own vocabulary

A drawable artifact names its classes and its edge kinds in the file itself
(`provenance_classes` / `edge_types`, `[[taxonomy]]`, …). If it does not, add
that declaration upstream first. Pulling the class list into vizops would make
this repository the authority on a vocabulary it does not own — the thing the
whole design refuses.

## 2. Write the adapter

In `vizops/adapters.py`, a function `bytes, Provenance, str -> Figure`:

```python
def my_format(raw: bytes, provenance: Provenance, title: str) -> Figure:
    data = json.loads(raw.decode("utf-8"))
    if data.get("format") != MY_FORMAT:
        raise AdapterError(f"format is {data.get('format')!r}, expected {MY_FORMAT!r}")
    return Figure(
        title=data.get("title") or title,
        provenance=provenance,
        terms=tuple(Term(id=c["id"], name=c["name"]) for c in data["classes"]),
        kinds=tuple(data["edge_types"]),
        nodes=tuple(Node(id=n["id"], label=n["name"], term=n["class"], badge=n["status"]) for n in data["nodes"]),
        edges=tuple(Edge(source=e["from"], target=e["to"], kind=e["type"]) for e in data["edges"]),
    )
```

Transcribe fields; compute nothing. Then register it in `ADAPTERS`.

`Figure` does the rest of the checking: undeclared classes, dangling edges,
undeclared edge kinds, duplicates, self-loops. You do not re-check those.

## 3. Name it in `vizops/sources.toml`

```toml
[[scene]]
id = "my-scene"
title = "What it is"
repo = "larsbx/some-repository"
path = "docs/the-artifact.json"
adapter = "my_format"
scene = "MyScene"
note = "Where the artifact comes from, and what generates it."
```

## 4. Add the scene class

```python
class MyScene(FigureScene):
    source_id = "my-scene"
```

That is the whole class. `FigureScene` asks `vizops.bridge.figure_for` for the
figure and draws it; there is no field for a scene to compute.

## 5. Tests and surfaces

```sh
python -m vizops --sources ..          # it reads and lays out
python -m vizops --write               # scene table and gallery pick it up
pytest -q                              # test_estate covers the new artifact automatically
```

`tests/test_estate.py` and `tests/test_scenes.py` are parametrised over the
manifest, so a new entry is covered the moment it is declared. Add negative
controls for your adapter in `tests/test_adapters.py`: an artifact of the
wrong declared format, and one whose vocabulary does not cover its own nodes.
A check with only positive controls is not a check.
