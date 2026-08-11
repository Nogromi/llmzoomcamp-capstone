import streamlit as st


def main() -> None:
    st.set_page_config(
        page_title="DLMM Position Lab",
        page_icon="🧪",
    )

    st.title("DLMM Position Lab")

    st.write(
        "Explore Meteora DLMM pools using RAG, "
        "live pool data, and LLM explanations."
    )


if __name__ == "__main__":
    main()