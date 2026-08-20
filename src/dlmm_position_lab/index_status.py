"""Print the status of the Meteora documentation index."""

from dlmm_position_lab.indexing import (
    DEFAULT_INDEX_NAME,
    create_client,
    document_count,
)


def main() -> None:
    """Display the configured index name and document count."""
    with create_client() as client:
        count = document_count(client)
    print(f"Index: {DEFAULT_INDEX_NAME}")
    print(f"Documents: {count}")


if __name__ == "__main__":
    main()
