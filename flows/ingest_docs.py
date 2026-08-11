from prefect import flow, task


@task
def load_documents() -> list[str]:
    return [
        "DLMM documentation placeholder",
    ]


@task
def process_documents(documents: list[str]) -> None:
    for document in documents:
        print(document)


@flow(name="meteora-docs-ingestion")
def ingest_docs() -> None:
    documents = load_documents()
    process_documents(documents)


if __name__ == "__main__":
    ingest_docs()