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
