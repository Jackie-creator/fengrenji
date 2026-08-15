"""Tests for the offline package build.

The bundle is what actually ships, so its shape is a contract with the frontend:
`src/dictionary.ts` reads these exact keys.
"""

import json
import sqlite3
from pathlib import Path

import pytest

from ruassist.build import build_bundle, write_json, write_sqlite
from ruassist.index import FormIndex
from ruassist.lexicon import load_dir
from ruassist.stress import STRESS, search_key

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bundle():
    lexicon, issues = load_dir(ROOT / "data" / "lexicon")
    assert not issues
    return build_bundle(lexicon, FormIndex.build(lexicon))


class TestBundleShape:
    def test_stats_match_contents(self, bundle):
        assert bundle["stats"]["entries"] == len(bundle["entries"])
        assert bundle["stats"]["forms"] == len(bundle["forms"])

    def test_every_entry_has_the_keys_the_frontend_reads(self, bundle):
        for entry in bundle["entries"]:
            assert {"i", "l", "s", "p", "sen", "f"} <= entry.keys()
            assert entry["sen"] and all(s["zh"] for s in entry["sen"])

    def test_entry_ids_are_dense_and_ordered(self, bundle):
        """The frontend indexes entries by position, so ids must be 0..n-1."""
        assert [e["i"] for e in bundle["entries"]] == list(range(len(bundle["entries"])))

    def test_form_keys_are_search_keys(self, bundle):
        """Lookup normalises the query; the index must be normalised to match."""
        for form in bundle["forms"]:
            assert form == search_key(form)
            assert STRESS not in form

    def test_form_ids_all_resolve(self, bundle):
        valid = {e["i"] for e in bundle["entries"]}
        for ids in bundle["forms"].values():
            assert set(ids) <= valid

    def test_display_forms_keep_their_stress(self, bundle):
        """Search keys drop stress; the forms shown to the learner must not."""
        stressed = [
            text
            for entry in bundle["entries"]
            for text in entry["f"].values()
            if len(text) > 3
        ]
        marked = [t for t in stressed if STRESS in t or "ё" in t]
        assert len(marked) > len(stressed) * 0.8

    def test_ambiguous_form_maps_to_several_entries(self, bundle):
        assert len(bundle["forms"]["стали"]) >= 2


class TestArtefacts:
    def test_json_round_trips(self, bundle, tmp_path):
        artefact = write_json(bundle, tmp_path / "d.json")
        assert artefact.bytes_written > 0
        reloaded = json.loads((tmp_path / "d.json").read_text(encoding="utf-8"))
        assert reloaded["stats"] == bundle["stats"]

    def test_sqlite_is_queryable(self, bundle, tmp_path):
        write_sqlite(bundle, tmp_path / "d.db")
        connection = sqlite3.connect(tmp_path / "d.db")
        (count,) = connection.execute("SELECT COUNT(*) FROM entries").fetchone()
        assert count == len(bundle["entries"])
        rows = connection.execute(
            "SELECT e.lemma FROM forms f JOIN entries e ON e.id = f.entry_id"
            " WHERE f.form = ?",
            ("стали",),
        ).fetchall()
        assert {r[0] for r in rows} == {"стать", "сталь"}
        connection.close()

    def test_bundle_stays_small_enough_to_cache(self, bundle, tmp_path):
        """A phone has to hold this; a regression here shows up before shipping."""
        artefact = write_json(bundle, tmp_path / "d.json")
        per_entry = artefact.bytes_written / len(bundle["entries"])
        assert per_entry < 2500, f"{per_entry:.0f} bytes/entry is too fat"
