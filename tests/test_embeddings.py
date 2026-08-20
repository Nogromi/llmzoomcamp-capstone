from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from dlmm_position_lab.embeddings import embed_texts, embedding_text


def test_embed_texts_batches_and_preserves_response_index_order() -> None:
    client = MagicMock()
    client.embeddings.create.side_effect = [
        SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[2.0, 2.0]),
                SimpleNamespace(index=0, embedding=[1.0, 1.0]),
            ]
        ),
        SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[3.0, 3.0])]),
    ]

    vectors = embed_texts(
        ["one", "two", "three"],
        client=client,
        model="test-model",
        dimensions=2,
        batch_size=2,
    )

    assert vectors == [[1.0, 1.0], [2.0, 2.0], [3.0, 3.0]]
    assert client.embeddings.create.call_count == 2
    client.embeddings.create.assert_any_call(
        input=["one", "two"],
        model="test-model",
        dimensions=2,
        encoding_format="float",
    )


def test_embed_texts_validates_inputs() -> None:
    assert embed_texts([], client=MagicMock()) == []
    with pytest.raises(ValueError, match="input must not be empty"):
        embed_texts(["  "], client=MagicMock())
    with pytest.raises(ValueError, match="batch_size must be positive"):
        embed_texts(["valid"], client=MagicMock(), batch_size=0)


def test_embedding_text_includes_retrieval_metadata() -> None:
    assert embedding_text("DLMM", "Active Bin", "Useful text") == (
        "DLMM\nActive Bin\nUseful text"
    )
