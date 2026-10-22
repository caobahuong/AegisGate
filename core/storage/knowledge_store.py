"""Knowledge Store implementing the Hybrid SQLite + Markdown storage architecture.

Adheres strictly to python_clean_code.md:
- Type annotations 100%
- Proper exception handling
- Separation of DB operations and file I/O
"""

import json
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from core.config import settings
from core.database import KnowledgeChunk, utc_now
from core.exceptions import StorageError


class KnowledgeStore:
    """Manages structural catalog in SQLite and markdown docs on filesystem."""

    def __init__(self, session: Session, docs_dir: Path | None = None) -> None:
        self.session: Session = session
        self.docs_dir: Path = docs_dir or settings.KNOWLEDGE_DOCS_DIR
        self.docs_dir.mkdir(parents=True, exist_ok=True)

    def _read_file_safe(self, filename: str | None) -> str:
        """Safely read text from a markdown doc file."""
        if not filename:
            return ""
        filepath = self.docs_dir / filename
        if not filepath.exists():
            return ""
        try:
            return filepath.read_text(encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Failed to read file {filename}: {exc}") from exc

    def _write_file_safe(self, filename: str, content: str) -> None:
        """Safely write text to a markdown doc file."""
        filepath = self.docs_dir / filename
        try:
            filepath.write_text(content, encoding="utf-8")
        except OSError as exc:
            raise StorageError(f"Failed to write file {filename}: {exc}") from exc

    def save_chunk(
        self,
        chunk: KnowledgeChunk,
        doc_content: str | None = None,
        skills_content: str | None = None,
    ) -> KnowledgeChunk:
        """Save or update a knowledge chunk and its associated markdown files."""
        # Ensure filenames exist if content is provided
        if doc_content is not None:
            doc_file = chunk.doc_file or f"{chunk.id}_doc.md"
            self._write_file_safe(doc_file, doc_content)
            chunk.doc_file = doc_file

        if skills_content is not None:
            skills_file = chunk.skills_file or f"{chunk.id}_skills.md"
            self._write_file_safe(skills_file, skills_content)
            chunk.skills_file = skills_file

        chunk.updated_at = utc_now()
        self.session.add(chunk)
        self.session.commit()
        self.session.refresh(chunk)
        return chunk

    def get_chunk(self, chunk_id: str) -> dict[str, Any] | None:
        """Retrieve chunk with hydrated doc and skill markdown contents."""
        statement = select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
        chunk = self.session.exec(statement).first()
        if not chunk:
            return None

        doc_text = self._read_file_safe(chunk.doc_file)
        skills_text = self._read_file_safe(chunk.skills_file)
        schema_dict: dict[str, Any] = {}
        try:
            schema_dict = json.loads(chunk.catalog_json)
        except json.JSONDecodeError:
            schema_dict = {}

        return {
            "id": chunk.id,
            "target_id": chunk.target_id,
            "partition_key": chunk.partition_key,
            "title": chunk.title,
            "catalog": schema_dict,
            "doc_content": doc_text,
            "skills_content": skills_text,
            "created_at": chunk.created_at.isoformat(),
            "updated_at": chunk.updated_at.isoformat(),
        }

    def list_chunks(self, target_id: str | None = None) -> list[dict[str, Any]]:
        """List all chunks with summary info."""
        statement = select(KnowledgeChunk)
        if target_id:
            statement = statement.where(KnowledgeChunk.target_id == target_id)
        chunks = self.session.exec(statement).all()

        results: list[dict[str, Any]] = []
        for c in chunks:
            schema_dict: dict[str, Any] = {}
            try:
                schema_dict = json.loads(c.catalog_json)
            except json.JSONDecodeError:
                schema_dict = {}

            results.append(
                {
                    "id": c.id,
                    "target_id": c.target_id,
                    "partition_key": c.partition_key,
                    "title": c.title,
                    "catalog": schema_dict,
                    "doc_file": c.doc_file,
                    "skills_file": c.skills_file,
                    "created_at": c.created_at.isoformat(),
                    "updated_at": c.updated_at.isoformat(),
                }
            )
        return results

    def update_docs(
        self,
        chunk_id: str,
        doc_content: str | None = None,
        skills_content: str | None = None,
    ) -> bool:
        """Update markdown contents for a chunk."""
        statement = select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
        chunk = self.session.exec(statement).first()
        if not chunk:
            return False

        if doc_content is not None:
            if not chunk.doc_file:
                chunk.doc_file = f"{chunk.id}_doc.md"
            self._write_file_safe(chunk.doc_file, doc_content)

        if skills_content is not None:
            if not chunk.skills_file:
                chunk.skills_file = f"{chunk.id}_skills.md"
            self._write_file_safe(chunk.skills_file, skills_content)

        chunk.updated_at = utc_now()
        self.session.add(chunk)
        self.session.commit()
        return True

    def delete_chunk(self, chunk_id: str) -> bool:
        """Delete a knowledge chunk and its associated markdown files."""
        statement = select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
        chunk = self.session.exec(statement).first()
        if not chunk:
            return False

        if chunk.doc_file:
            doc_path = self.docs_dir / chunk.doc_file
            if doc_path.exists():
                doc_path.unlink(missing_ok=True)

        if chunk.skills_file:
            skills_path = self.docs_dir / chunk.skills_file
            if skills_path.exists():
                skills_path.unlink(missing_ok=True)

        self.session.delete(chunk)
        self.session.commit()
        return True

    def ingest_plugin_catalog(
        self, target_id: str, catalog_partitions: list[dict[str, Any]]
    ) -> list[KnowledgeChunk]:
        """Standard Ingest Sink for chunked structural catalog pushed from plugins."""
        saved_chunks: list[KnowledgeChunk] = []
        for part in catalog_partitions:
            partition_key = part.get("partition_key", "Default")
            chunk_id = f"{target_id}_{partition_key.lower().replace(' ', '_')}"
            title = part.get("title", f"{partition_key} Subsystem")
            schema_data = part.get("tables", part)
            schema_json = json.dumps(schema_data, indent=2)

            # Check if chunk exists to preserve docs
            statement = select(KnowledgeChunk).where(KnowledgeChunk.id == chunk_id)
            existing = self.session.exec(statement).first()

            if existing:
                existing.title = title
                existing.catalog_json = schema_json
                existing.updated_at = utc_now()
                self.session.add(existing)
                saved_chunks.append(existing)
            else:
                doc_filename = f"{chunk_id}_doc.md"
                skills_filename = f"{chunk_id}_skills.md"
                new_chunk = KnowledgeChunk(
                    id=chunk_id,
                    target_id=target_id,
                    partition_key=partition_key,
                    title=title,
                    catalog_json=schema_json,
                    doc_file=doc_filename,
                    skills_file=skills_filename,
                    created_at=utc_now(),
                    updated_at=utc_now(),
                )
                # Initialize default documentation template
                default_doc = f"# {title} Documentation\n\nOverview of tables and business rules for {partition_key}."
                default_skills = f"# {title} Query Skills\n\nStandard query templates and performance guidelines."
                self._write_file_safe(doc_filename, default_doc)
                self._write_file_safe(skills_filename, default_skills)
                self.session.add(new_chunk)
                saved_chunks.append(new_chunk)

        self.session.commit()
        for chunk in saved_chunks:
            self.session.refresh(chunk)
        return saved_chunks

