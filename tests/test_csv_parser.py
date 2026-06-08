from app.batch_parser import parse_batch_input


def test_parse_csv_with_header():
    raw = "prompt,other\nhello,1\nworld,2"
    result = parse_batch_input(raw, mode="csv", csv_column="prompt")
    assert result.prompts == ["hello", "world"]
    assert not result.errors


def test_parse_csv_index():
    raw = "hello,1\nworld,2"
    result = parse_batch_input(raw, mode="csv", csv_column="0")
    assert result.prompts == ["hello", "world"]


def test_parse_structured_csv_metadata():
    raw = 'prompt_id,category_id,prompt,notes\nprompt0001,cat01,"Design, with comma",first'
    result = parse_batch_input(raw, mode="csv", csv_column="prompt")
    assert result.prompts == ["Design, with comma"]
    assert result.rows[0].prompt_id == "prompt0001"
    assert result.rows[0].category_id == "cat01"
    assert result.rows[0].source_metadata["notes"] == "first"
