from unittest.mock import MagicMock, patch

import pytest

from dlmm_position_lab.indexing import (
    EMBEDDING_MAPPING,
    INDEX_MAPPINGS,
    build_index_actions,
    document_count,
    ensure_index,
    index_documents,
)
from dlmm_position_lab.ingestion import DocumentationChunk


def make_chunk(identifier: str = "chunk-1") -> DocumentationChunk:
    return DocumentationChunk(
        id=identifier,
        title="DLMM",
        section="Bins",
        url="https://docs.meteora.ag/core-products/dlmm/what-is-dlmm",
        text="DLMM liquidity is distributed across discrete price bins.",
    )


def test_ensure_index_creates_expected_mapping_when_missing() -> None:
    client = MagicMock()
    client.indices.exists.return_value = False

    assert ensure_index(client) is True
    client.indices.create.assert_called_once_with(
        index="meteora_docs",
        mappings=INDEX_MAPPINGS,
        settings={"number_of_shards": 1, "number_of_replicas": 0},
    )


def test_ensure_index_is_idempotent() -> None:
    client = MagicMock()
    client.indices.exists.return_value = True

    assert ensure_index(client) is False
    client.indices.create.assert_not_called()
    client.indices.put_mapping.assert_called_once_with(
        index="meteora_docs", properties={"embedding": EMBEDDING_MAPPING}
    )


def test_actions_use_stable_id_and_complete_source() -> None:
    chunk = make_chunk()

    assert build_index_actions([chunk]) == [
        {
            "_op_type": "index",
            "_index": "meteora_docs",
            "_id": "chunk-1",
            "_source": {
                "id": "chunk-1",
                "title": "DLMM",
                "section": "Bins",
                "url": chunk.url,
                "text": chunk.text,
            },
        }
    ]


def test_actions_include_matching_embeddings() -> None:
    actions = build_index_actions([make_chunk()], embeddings=[[0.1, 0.2]])

    assert actions[0]["_source"]["embedding"] == [0.1, 0.2]
    with pytest.raises(ValueError, match="same length"):
        build_index_actions([make_chunk()], embeddings=[])


@patch("dlmm_position_lab.indexing.bulk", return_value=(1, []))
def test_index_documents_uses_bulk_upsert(mock_bulk: MagicMock) -> None:
    client = MagicMock()
    client.indices.exists.return_value = True

    assert index_documents(client, [make_chunk()]) == 1
    actions = mock_bulk.call_args.args[1]
    assert actions[0]["_op_type"] == "index"
    assert actions[0]["_id"] == "chunk-1"
    assert mock_bulk.call_args.kwargs["refresh"] == "wait_for"


def test_document_count_handles_missing_and_existing_index() -> None:
    client = MagicMock()
    client.indices.exists.side_effect = [False, True]
    client.count.return_value = {"count": 87}

    assert document_count(client) == 0
    assert document_count(client) == 87
