from scripts.prepare_logo_prompts import parse_source_folder


def test_prepare_logo_prompts_handles_source_heading_variants(tmp_path):
    source = tmp_path / "logos"
    source.mkdir()
    (source / "1_2.md").write_text(
        "\n".join(
            [
                "# CATEGORY 3 - Negative-space logos",
                "## N01 - Missing core",
                "Prompt:",
                "Design the first mark.",
                "## N02 - Evidence gap",
                "Prompt: Design the second mark.",
                "# Category 4 — Inside/container logos",
                "## C01 — Kernel in a vault",
                "**Prompt:**",
                "Design the third mark.",
                "# Category 5 — Negative-space logos",
                "## 61. AI kernel inside a shell",
                "Design the fourth mark.",
                "# Category 15 — Knowledge logos",
                "### 15.01 — Source ledger",
                "Prompt: Design the fifth mark.",
            ]
        ),
        encoding="utf-8",
    )

    prompts = parse_source_folder(source)

    assert [prompt.generation_id for prompt in prompts] == [
        "cat03_p001",
        "cat03_p002",
        "cat04_p001",
        "cat05_p001",
        "cat15_p001",
    ]
    assert [prompt.source_label for prompt in prompts] == ["N01", "N02", "C01", "61.", "15.01"]
    assert {prompt.source_path for prompt in prompts} == {"1_2.md"}
    assert prompts[0].prompt == "Design the first mark."
    assert prompts[2].prompt == "Design the third mark."
