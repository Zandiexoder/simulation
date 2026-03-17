from pathlib import Path


def test_env_example_has_qwen35_defaults():
    text = Path('.env.example').read_text()
    assert 'OLLAMA_MODEL_NAMING=qwen3.5:0.8b' in text
    assert 'OLLAMA_MODEL_PEOPLE=qwen3.5:4b' in text
    assert 'OLLAMA_MODEL_GM=qwen3.5:9b' in text
