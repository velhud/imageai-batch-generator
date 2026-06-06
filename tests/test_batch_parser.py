from app.batch_parser import BatchParseResult, parse_batch_input


def test_parse_lines():
    result = parse_batch_input("hello\nworld", mode="lines")
    assert result.prompts == ["hello", "world"]
    assert result.errors == []


def test_parse_numbered():
    data = "1) hello\n2. world\n3 - third"
    result = parse_batch_input(data, mode="numbered")
    assert result.prompts == ["hello", "world", "third"]
    assert not result.errors


def test_parse_json_array_with_field():
    payload = '[{"prompt":"one"}, {"prompt":"two"}]'
    result = parse_batch_input(payload, mode="json_array", prompt_field="prompt")
    assert result.prompts == ["one", "two"]
    assert result.errors == []


def test_parse_json_lines_error():
    payload = '{"prompt":"a"}\nnot json'
    result = parse_batch_input(payload, mode="json_lines", prompt_field="prompt")
    assert result.prompts == ["a"]
    assert result.errors
