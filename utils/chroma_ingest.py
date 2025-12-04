"""Ingest Foody CSV data into a Chroma vector store with OpenAI embeddings."""

from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    load_dotenv = None


def _row_to_document(row: pd.Series) -> Document:
    """Convert one CSV row to a LangChain Document."""
    text_parts = [
        f"{row.get('name', '')}",
        f"Branch: {row.get('branch_name', '')}" if row.get("branch_name") else "",
        f"Address: {row.get('address', '')}, {row.get('district', '')}, {row.get('city', '')}",
        f"Cuisines: {row.get('cuisines', '')}",
        f"Categories: {row.get('categories', '')}",
        f"Rating: {row.get('avg_rating', '')} ({row.get('total_reviews', '')} reviews)",
        f"Delivery: {row.get('has_delivery', '')}, Booking: {row.get('has_booking', '')}",
    ]
    page_content = "\n".join([part for part in text_parts if part])

    metadata = {
        "name": row.get("name"),
        "branch_name": row.get("branch_name"),
        "address": row.get("address"),
        "district": row.get("district"),
        "city": row.get("city"),
        "avg_rating": row.get("avg_rating"),
        "total_reviews": row.get("total_reviews"),
        "has_delivery": row.get("has_delivery"),
        "has_booking": row.get("has_booking"),
        "delivery_url": row.get("delivery_url"),
        "booking_url": row.get("booking_url"),
        "detail_url": row.get("detail_url"),
        "branch_url": row.get("branch_url"),
        "cuisines": row.get("cuisines"),
        "categories": row.get("categories"),
        "latitude": row.get("latitude"),
        "longitude": row.get("longitude"),
    }
    return Document(page_content=page_content, metadata=metadata)


def load_documents(csv_path: Path | str) -> List[Document]:
    """Read CSV and return a list of Documents."""
    df = pd.read_csv(csv_path)
    df = df.fillna("")
    return [_row_to_document(row) for _, row in df.iterrows()]


def ingest_to_chroma(
    csv_path: Path | str = "data/foody_page1.csv",
    persist_dir: Path | str = "chroma/foody",
    collection_name: str = "foody_restaurants",
):
    """Load CSV, convert to documents, and persist into a Chroma collection."""
    documents = load_documents(csv_path)
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=str(persist_dir),
        collection_name=collection_name,
    )
    vectorstore.persist()
    return vectorstore


if __name__ == "__main__":
    ingest_to_chroma()
    print("Ingested documents into Chroma.")
