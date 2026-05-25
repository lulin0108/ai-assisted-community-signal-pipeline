"""SQLite persistence for pipeline runs."""

from pathlib import Path
from contextlib import closing
import json
import sqlite3
from typing import Any

from models import CollectionState


def save_run_to_sqlite(
    db_path: Path,
    run_id: str,
    analysis: dict[str, Any],
    collector_diagnostics: dict[str, Any],
    raw_items: list[dict[str, Any]],
    prepared_items: list[dict[str, Any]],
    excluded_items: list[dict[str, Any]],
    relevance_excluded_items: list[dict[str, Any]],
    processing_batches: list[dict[str, Any]] | None = None,
) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
            _save_run(connection, run_id, analysis)
            _save_collector_diagnostics(connection, run_id, collector_diagnostics)
            _save_collection_pages(connection, run_id, collector_diagnostics)
            _save_collection_states(connection, run_id, collector_diagnostics)
            _save_raw_items(connection, run_id, raw_items)
            _save_prepared_items(connection, run_id, prepared_items)
            _save_excluded_items(connection, run_id, excluded_items)
            _save_relevance_excluded_items(connection, run_id, relevance_excluded_items)
            _save_processing_batches(connection, run_id, processing_batches or [])
            _save_evidence_rows(connection, run_id, analysis["evidence_rows"])
            _save_category_summaries(connection, run_id, analysis["category_summaries"])


def list_runs(db_path: Path, limit: int = 20, offset: int = 0) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
                run_id,
                generated_at_utc,
                venture_category,
                total_items_analyzed,
                evidence_rows,
                demo_fallback_items
            from runs
            order by generated_at_utc desc
            limit ? offset ?
            """,
            (limit, offset),
        ).fetchall()
    return [dict(row) for row in rows]


def get_run_summary(db_path: Path, run_id: str) -> dict[str, Any] | None:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            select
                run_id,
                generated_at_utc,
                project_title,
                venture_category,
                community_queries_json,
                stackexchange_site,
                stackexchange_queries_json,
                max_discussion_items,
                max_review_items,
                request_timeout,
                processing_batch_size,
                collection_policy_json,
                debug_save_raw,
                raw_items_file,
                resume_from_run_id,
                total_items_analyzed,
                evidence_rows,
                demo_fallback_items
            from runs
            where run_id = ?
            """,
            (run_id,),
        ).fetchone()
        if row is None:
            return None
        diagnostics = connection.execute(
            """
            select source_key, diagnostics_json
            from collector_diagnostics
            where run_id = ?
            order by source_key
            """,
            (run_id,),
        ).fetchall()
        summaries = connection.execute(
            """
            select category, summary_json
            from category_summaries
            where run_id = ?
            order by category
            """,
            (run_id,),
        ).fetchall()

    summary = dict(row)
    summary["debug_save_raw"] = bool(summary["debug_save_raw"])
    summary["collection_policy"] = _from_json(summary.pop("collection_policy_json"))
    summary["community_queries"] = _from_json(summary.pop("community_queries_json"))
    summary["stackexchange_queries"] = _from_json(summary.pop("stackexchange_queries_json"))
    summary["collector_diagnostics"] = {
        diagnostic["source_key"]: _from_json(diagnostic["diagnostics_json"])
        for diagnostic in diagnostics
    }
    summary["category_summaries"] = {
        category_summary["category"]: _from_json(category_summary["summary_json"])
        for category_summary in summaries
    }
    return summary


def get_evidence_rows(
    db_path: Path,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
    category: str | None = None,
) -> list[dict[str, Any]]:
    query = """
        select row_json
        from evidence_rows
        where run_id = ?
    """
    params: list[Any] = [run_id]
    if category:
        query += " and category = ?"
        params.append(category)
    query += " order by signal_relevance_score desc, id asc limit ? offset ?"
    params.extend([limit, offset])

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        rows = connection.execute(query, params).fetchall()
    return [_from_json(row[0]) for row in rows]


def get_collection_pages(db_path: Path, run_id: str) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
                source,
                query,
                page_number,
                request_url,
                request_params_json,
                raw_count,
                item_count,
                has_more,
                page_json
            from collection_pages
            where run_id = ?
            order by source, query, page_number
            """,
            (run_id,),
        ).fetchall()
    pages = []
    for row in rows:
        page = dict(row)
        page["request_params"] = _from_json(page.pop("request_params_json"))
        page["has_more"] = bool(page["has_more"])
        page["page"] = _from_json(page.pop("page_json"))
        pages.append(page)
    return pages


def get_collection_states(db_path: Path, run_id: str) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
                source,
                query,
                page_count,
                last_page_number,
                next_page_number,
                total_raw_count,
                total_item_count,
                completed,
                state_json
            from collection_states
            where run_id = ?
            order by source, query
            """,
            (run_id,),
        ).fetchall()
    states = []
    for row in rows:
        state = dict(row)
        state["completed"] = bool(state["completed"])
        state["state"] = _from_json(state.pop("state_json"))
        states.append(state)
    return states


def get_resume_start_pages(db_path: Path, run_id: str, source: str) -> dict[str, int]:
    states = get_collection_states(db_path, run_id)
    return {
        state["query"]: state["next_page_number"]
        for state in states
        if state["source"] == source and not state["completed"]
    }


def get_resume_lineage_run_ids(db_path: Path, run_id: str) -> list[str]:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        rows = connection.execute(
            """
            select run_id, resume_from_run_id
            from runs
            """
        ).fetchall()

    parent_by_run = {row[0]: row[1] for row in rows}
    lineage = []
    current = run_id
    while current and current in parent_by_run and current not in lineage:
        lineage.append(current)
        current = parent_by_run[current]
    return lineage


def get_run_chain_summary(db_path: Path, run_id: str) -> dict[str, Any] | None:
    run_ids = get_resume_lineage_run_ids(db_path, run_id)
    if not run_ids:
        return None

    placeholders = _placeholders(run_ids)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            f"""
            select
                run_id,
                generated_at_utc,
                venture_category,
                resume_from_run_id,
                total_items_analyzed,
                evidence_rows,
                demo_fallback_items
            from runs
            where run_id in ({placeholders})
            """,
            run_ids,
        ).fetchall()
        row_by_run_id = {row["run_id"]: dict(row) for row in rows}
        ordered_runs = [row_by_run_id[item] for item in run_ids if item in row_by_run_id]
        raw_item_count = _count_rows(connection, "raw_items", run_ids)
        summary = {
            "run_id": run_id,
            "latest_run_id": ordered_runs[0]["run_id"],
            "root_run_id": ordered_runs[-1]["run_id"],
            "run_ids": [row["run_id"] for row in ordered_runs],
            "run_count": len(ordered_runs),
            "generated_at_utc_start": ordered_runs[-1]["generated_at_utc"],
            "generated_at_utc_end": ordered_runs[0]["generated_at_utc"],
            "venture_categories": sorted({row["venture_category"] for row in ordered_runs}),
            "resume_links": {
                row["run_id"]: row["resume_from_run_id"]
                for row in ordered_runs
                if row["resume_from_run_id"]
            },
            "run_volume": {
                "total_items_analyzed": sum(row["total_items_analyzed"] for row in ordered_runs),
                "evidence_rows": sum(row["evidence_rows"] for row in ordered_runs),
                "demo_fallback_items": sum(row["demo_fallback_items"] for row in ordered_runs),
            },
            "storage_counts": {
                "raw_items": raw_item_count,
                "unique_raw_items": _count_distinct_raw_items(connection, run_ids),
                "prepared_items": _count_rows(connection, "prepared_items", run_ids),
                "excluded_items": _count_rows(connection, "excluded_items", run_ids),
                "relevance_excluded_items": _count_rows(connection, "relevance_excluded_items", run_ids),
                "evidence_rows": _count_rows(connection, "evidence_rows", run_ids),
                "collection_pages": _count_rows(connection, "collection_pages", run_ids),
                "processing_batches": _count_rows(connection, "processing_batches", run_ids),
                "model_artifacts": _count_rows(connection, "model_artifacts", run_ids),
            },
            "processing_batches_by_status": _group_counts(connection, "processing_batches", "status", run_ids),
            "model_artifacts_by_type": _group_counts(connection, "model_artifacts", "artifact_type", run_ids),
            "collection_states": {
                "completed": _count_collection_states(connection, run_ids, completed=True),
                "open": _count_collection_states(connection, run_ids, completed=False),
            },
        }
    return summary


def get_run_chain_evidence_rows(
    db_path: Path,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
    category: str | None = None,
) -> list[dict[str, Any]]:
    run_ids = get_resume_lineage_run_ids(db_path, run_id)
    if not run_ids:
        return []

    placeholders = _placeholders(run_ids)
    query = f"""
        select row_json
        from evidence_rows
        where run_id in ({placeholders})
    """
    params: list[Any] = list(run_ids)
    if category:
        query += " and category = ?"
        params.append(category)
    query += " order by signal_relevance_score desc, id asc limit ? offset ?"
    params.extend([limit, offset])

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        rows = connection.execute(query, params).fetchall()
    return [_from_json(row[0]) for row in rows]


def get_run_chain_model_artifacts(
    db_path: Path,
    run_id: str,
    artifact_type: str | None = None,
    batch_index: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    run_ids = get_resume_lineage_run_ids(db_path, run_id)
    if not run_ids:
        return []

    placeholders = _placeholders(run_ids)
    query = f"""
        select
            run_id,
            batch_index,
            item_id,
            source_id,
            artifact_type,
            model_name,
            model_version,
            input_hash,
            created_at,
            artifact_json
        from model_artifacts
        where run_id in ({placeholders})
    """
    params: list[Any] = list(run_ids)
    if artifact_type:
        query += " and artifact_type = ?"
        params.append(artifact_type)
    if batch_index is not None:
        query += " and batch_index = ?"
        params.append(batch_index)
    query += " order by run_id desc, batch_index, item_id, artifact_type, model_name limit ? offset ?"
    params.extend([limit, offset])

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    artifacts = []
    for row in rows:
        artifact = dict(row)
        artifact["artifact"] = _from_json(artifact.pop("artifact_json"))
        artifacts.append(artifact)
    return artifacts


def get_run_chain_cluster_artifacts(
    db_path: Path,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return get_run_chain_model_artifacts(
        db_path,
        run_id,
        artifact_type="evidence_cluster",
        limit=limit,
        offset=offset,
    )


def get_run_chain_embedding_artifacts(
    db_path: Path,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return get_run_chain_model_artifacts(
        db_path,
        run_id,
        artifact_type="embedding",
        limit=limit,
        offset=offset,
    )


def get_raw_item_source_keys(db_path: Path, run_ids: list[str]) -> set[tuple[str, str]]:
    if not run_ids:
        return set()

    placeholders = ", ".join("?" for _ in run_ids)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        rows = connection.execute(
            f"""
            select source_name, source_id
            from raw_items
            where run_id in ({placeholders})
            """,
            run_ids,
        ).fetchall()
    return {(row[0], row[1]) for row in rows}


def get_processing_batches(db_path: Path, run_id: str) -> list[dict[str, Any]]:
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            select
                batch_index,
                status,
                raw_item_start_index,
                raw_item_end_index,
                raw_items,
                quality_candidates,
                quality_excluded,
                relevance_prepared,
                relevance_excluded,
                batch_json
            from processing_batches
            where run_id = ?
            order by batch_index
            """,
            (run_id,),
        ).fetchall()
    batches = []
    for row in rows:
        batch = dict(row)
        batch["batch"] = _from_json(batch.pop("batch_json"))
        batches.append(batch)
    return batches


def save_model_artifacts(db_path: Path, run_id: str, artifacts: list[dict[str, Any]]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
            _save_model_artifacts(connection, run_id, artifacts)


def get_model_artifacts(
    db_path: Path,
    run_id: str,
    artifact_type: str | None = None,
    batch_index: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    query = """
        select
            batch_index,
            item_id,
            source_id,
            artifact_type,
            model_name,
            model_version,
            input_hash,
            created_at,
            artifact_json
        from model_artifacts
        where run_id = ?
    """
    params: list[Any] = [run_id]
    if artifact_type:
        query += " and artifact_type = ?"
        params.append(artifact_type)
    if batch_index is not None:
        query += " and batch_index = ?"
        params.append(batch_index)
    query += " order by batch_index, item_id, artifact_type, model_name limit ? offset ?"
    params.extend([limit, offset])

    with closing(sqlite3.connect(db_path)) as connection:
        with connection:
            _ensure_schema(connection)
        connection.row_factory = sqlite3.Row
        rows = connection.execute(query, params).fetchall()

    artifacts = []
    for row in rows:
        artifact = dict(row)
        artifact["artifact"] = _from_json(artifact.pop("artifact_json"))
        artifacts.append(artifact)
    return artifacts


def get_cluster_artifacts(
    db_path: Path,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return get_model_artifacts(
        db_path,
        run_id,
        artifact_type="evidence_cluster",
        limit=limit,
        offset=offset,
    )


def get_embedding_artifacts(
    db_path: Path,
    run_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict[str, Any]]:
    return get_model_artifacts(
        db_path,
        run_id,
        artifact_type="embedding",
        limit=limit,
        offset=offset,
    )


def _ensure_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        create table if not exists runs (
            run_id text primary key,
            generated_at_utc text not null,
            project_title text not null,
            venture_category text not null,
            community_queries_json text not null,
            stackexchange_site text not null,
            stackexchange_queries_json text not null,
            max_discussion_items integer not null,
            max_review_items integer not null,
            request_timeout integer not null,
            processing_batch_size integer not null default 500,
            collection_policy_json text not null default '{}',
            debug_save_raw integer not null,
            raw_items_file text not null,
            resume_from_run_id text not null default '',
            total_items_analyzed integer not null,
            evidence_rows integer not null,
            demo_fallback_items integer not null,
            analysis_json text not null
        );

        create table if not exists collector_diagnostics (
            run_id text not null,
            source_key text not null,
            diagnostics_json text not null,
            primary key (run_id, source_key)
        );

        create table if not exists raw_items (
            run_id text not null,
            source_type text not null,
            source_name text not null,
            source_id text not null,
            source_url text not null,
            title text not null,
            query_theme text not null,
            created_at text not null,
            collected_at text not null,
            is_demo_fallback integer not null,
            raw_json text not null,
            primary key (run_id, source_name, source_id)
        );

        create table if not exists collection_pages (
            run_id text not null,
            source text not null,
            query text not null,
            page_number integer not null,
            request_url text not null,
            request_params_json text not null,
            raw_count integer not null,
            item_count integer not null,
            has_more integer not null,
            page_json text not null,
            primary key (run_id, source, query, page_number)
        );

        create table if not exists collection_states (
            run_id text not null,
            source text not null,
            query text not null,
            page_count integer not null,
            last_page_number integer not null,
            next_page_number integer not null,
            total_raw_count integer not null,
            total_item_count integer not null,
            completed integer not null,
            state_json text not null,
            primary key (run_id, source, query)
        );

        create table if not exists prepared_items (
            run_id text not null,
            item_id text not null,
            source_type text not null,
            source_id text not null,
            relevance_score integer not null,
            prepared_json text not null,
            primary key (run_id, item_id)
        );

        create table if not exists excluded_items (
            run_id text not null,
            source_index integer not null,
            source_type text not null,
            source_id text not null,
            exclude_reasons text not null,
            excluded_json text not null,
            primary key (run_id, source_index)
        );

        create table if not exists relevance_excluded_items (
            run_id text not null,
            item_id text not null,
            source_type text not null,
            source_id text not null,
            relevance_score integer not null,
            item_json text not null,
            primary key (run_id, item_id)
        );

        create table if not exists processing_batches (
            run_id text not null,
            batch_index integer not null,
            status text not null,
            raw_item_start_index integer not null,
            raw_item_end_index integer not null,
            raw_items integer not null,
            quality_candidates integer not null,
            quality_excluded integer not null,
            relevance_prepared integer not null,
            relevance_excluded integer not null,
            batch_json text not null,
            primary key (run_id, batch_index)
        );

        create table if not exists model_artifacts (
            run_id text not null,
            batch_index integer not null,
            item_id text not null,
            source_id text not null,
            artifact_type text not null,
            model_name text not null,
            model_version text not null,
            input_hash text not null,
            artifact_json text not null,
            created_at text not null,
            primary key (
                run_id,
                batch_index,
                item_id,
                artifact_type,
                model_name,
                model_version,
                input_hash
            )
        );

        create table if not exists evidence_rows (
            id integer primary key autoincrement,
            run_id text not null,
            item_id text not null,
            category text not null,
            source_type text not null,
            source_id text not null,
            signal_relevance_score integer not null,
            row_json text not null
        );

        create table if not exists category_summaries (
            run_id text not null,
            category text not null,
            title text not null,
            evidence_count integer not null,
            summary_json text not null,
            primary key (run_id, category)
        );

        create index if not exists idx_raw_items_run_source on raw_items (run_id, source_type);
        create index if not exists idx_collection_pages_run_source on collection_pages (run_id, source);
        create index if not exists idx_collection_states_run_completed on collection_states (run_id, completed);
        create index if not exists idx_prepared_items_run_score on prepared_items (run_id, relevance_score);
        create index if not exists idx_processing_batches_run_status on processing_batches (run_id, status);
        create index if not exists idx_model_artifacts_run_type on model_artifacts (run_id, artifact_type);
        create index if not exists idx_model_artifacts_run_batch on model_artifacts (run_id, batch_index);
        create index if not exists idx_evidence_rows_run_category on evidence_rows (run_id, category);
        create index if not exists idx_evidence_rows_run_score on evidence_rows (run_id, signal_relevance_score);
        """
    )
    _ensure_column(connection, "runs", "resume_from_run_id", "text not null default ''")
    _ensure_column(connection, "runs", "processing_batch_size", "integer not null default 500")
    _ensure_column(connection, "runs", "collection_policy_json", "text not null default '{}'")


def _save_run(connection: sqlite3.Connection, run_id: str, analysis: dict[str, Any]) -> None:
    meta = analysis["run_metadata"]
    volume = analysis["volume"]
    connection.execute(
        """
        insert or replace into runs (
            run_id,
            generated_at_utc,
            project_title,
            venture_category,
            community_queries_json,
            stackexchange_site,
            stackexchange_queries_json,
            max_discussion_items,
            max_review_items,
            request_timeout,
            processing_batch_size,
            collection_policy_json,
            debug_save_raw,
            raw_items_file,
            resume_from_run_id,
            total_items_analyzed,
            evidence_rows,
            demo_fallback_items,
            analysis_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            meta["generated_at_utc"],
            meta["project_title"],
            meta["venture_category"],
            _to_json(meta["community_queries"]),
            meta["stackexchange_site"],
            _to_json(meta["stackexchange_queries"]),
            meta["max_discussion_items"],
            meta["max_review_items"],
            meta["request_timeout"],
            meta["processing_batch_size"],
            _to_json(meta["collection_policy"]),
            int(meta["debug_save_raw"]),
            meta["raw_items_file"],
            meta.get("resume_from_run_id", ""),
            volume["total_items_analyzed"],
            volume["evidence_rows"],
            volume["demo_fallback_items"],
            _to_json(analysis),
        ),
    )


def _save_collector_diagnostics(connection: sqlite3.Connection, run_id: str, diagnostics: dict[str, Any]) -> None:
    connection.executemany(
        """
        insert or replace into collector_diagnostics (run_id, source_key, diagnostics_json)
        values (?, ?, ?)
        """,
        [
            (run_id, source_key, _to_json(value))
            for source_key, value in diagnostics.items()
            if isinstance(value, dict)
        ],
    )


def _save_collection_pages(connection: sqlite3.Connection, run_id: str, diagnostics: dict[str, Any]) -> None:
    pages = []
    for value in diagnostics.values():
        if isinstance(value, dict):
            pages.extend(value.get("collected_pages", []))

    connection.executemany(
        """
        insert or replace into collection_pages (
            run_id,
            source,
            query,
            page_number,
            request_url,
            request_params_json,
            raw_count,
            item_count,
            has_more,
            page_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                page["source"],
                page["query"],
                page["page_number"],
                page.get("request_url", ""),
                _to_json(page.get("request_params", {})),
                page["raw_count"],
                page["item_count"],
                int(page["has_more"]),
                _to_json(page),
            )
            for page in pages
        ],
    )


def _save_collection_states(connection: sqlite3.Connection, run_id: str, diagnostics: dict[str, Any]) -> None:
    states = _build_collection_states(diagnostics)
    connection.executemany(
        """
        insert or replace into collection_states (
            run_id,
            source,
            query,
            page_count,
            last_page_number,
            next_page_number,
            total_raw_count,
            total_item_count,
            completed,
            state_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                state["source"],
                state["query"],
                state["page_count"],
                state["last_page_number"],
                state["next_page_number"],
                state["total_raw_count"],
                state["total_item_count"],
                int(state["completed"]),
                _to_json(state),
            )
            for state in states
        ],
    )


def _build_collection_states(diagnostics: dict[str, Any]) -> list[dict[str, Any]]:
    grouped = {}
    for value in diagnostics.values():
        if isinstance(value, dict):
            for page in value.get("collected_pages", []):
                key = (page["source"], page["query"])
                grouped.setdefault(key, []).append(page)

    states = []
    for (source, query), pages in grouped.items():
        pages = sorted(pages, key=lambda page: page["page_number"])
        last_page = pages[-1]
        state = CollectionState(
            source=source,
            query=query,
            page_count=len(pages),
            last_page_number=last_page["page_number"],
            next_page_number=last_page["page_number"] + 1,
            total_raw_count=sum(page["raw_count"] for page in pages),
            total_item_count=sum(page["item_count"] for page in pages),
            completed=not last_page["has_more"],
        ).to_dict()
        states.append(state)
    return states


def _save_raw_items(connection: sqlite3.Connection, run_id: str, items: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into raw_items (
            run_id,
            source_type,
            source_name,
            source_id,
            source_url,
            title,
            query_theme,
            created_at,
            collected_at,
            is_demo_fallback,
            raw_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                item.get("source_type", ""),
                item.get("source_name", ""),
                item.get("source_id", ""),
                item.get("source_url", ""),
                item.get("title", ""),
                item.get("query_theme", ""),
                item.get("created_at", ""),
                item.get("collected_at", ""),
                int(item.get("is_demo_fallback", False)),
                _to_json(item),
            )
            for item in items
        ],
    )


def _save_prepared_items(connection: sqlite3.Connection, run_id: str, items: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into prepared_items (
            run_id,
            item_id,
            source_type,
            source_id,
            relevance_score,
            prepared_json
        ) values (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                item["item_id"],
                item["source_type"],
                item["source_id"],
                int(item.get("relevance_score", 0)),
                _to_json(item),
            )
            for item in items
        ],
    )


def _save_excluded_items(connection: sqlite3.Connection, run_id: str, items: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into excluded_items (
            run_id,
            source_index,
            source_type,
            source_id,
            exclude_reasons,
            excluded_json
        ) values (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                item["source_index"],
                item["source_type"],
                item["source_id"],
                item["exclude_reasons"],
                _to_json(item),
            )
            for item in items
        ],
    )


def _save_relevance_excluded_items(connection: sqlite3.Connection, run_id: str, items: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into relevance_excluded_items (
            run_id,
            item_id,
            source_type,
            source_id,
            relevance_score,
            item_json
        ) values (?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                item["item_id"],
                item["source_type"],
                item["source_id"],
                int(item.get("relevance_score", 0)),
                _to_json(item),
            )
            for item in items
        ],
    )


def _save_processing_batches(connection: sqlite3.Connection, run_id: str, batches: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into processing_batches (
            run_id,
            batch_index,
            status,
            raw_item_start_index,
            raw_item_end_index,
            raw_items,
            quality_candidates,
            quality_excluded,
            relevance_prepared,
            relevance_excluded,
            batch_json
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                batch["batch_index"],
                batch["status"],
                batch["raw_item_start_index"],
                batch["raw_item_end_index"],
                batch["raw_items"],
                batch["quality_candidates"],
                batch["quality_excluded"],
                batch["relevance_prepared"],
                batch["relevance_excluded"],
                _to_json(batch),
            )
            for batch in batches
        ],
    )


def _save_model_artifacts(connection: sqlite3.Connection, run_id: str, artifacts: list[dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into model_artifacts (
            run_id,
            batch_index,
            item_id,
            source_id,
            artifact_type,
            model_name,
            model_version,
            input_hash,
            artifact_json,
            created_at
        ) values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                artifact["batch_index"],
                artifact["item_id"],
                artifact["source_id"],
                artifact["artifact_type"],
                artifact["model_name"],
                artifact["model_version"],
                artifact["input_hash"],
                _to_json(artifact["artifact"]),
                artifact["created_at"],
            )
            for artifact in artifacts
        ],
    )


def _save_evidence_rows(connection: sqlite3.Connection, run_id: str, rows: list[dict[str, Any]]) -> None:
    connection.execute("delete from evidence_rows where run_id = ?", (run_id,))
    connection.executemany(
        """
        insert into evidence_rows (
            run_id,
            item_id,
            category,
            source_type,
            source_id,
            signal_relevance_score,
            row_json
        ) values (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                row["item_id"],
                row["category"],
                row["source_type"],
                row.get("source_id", ""),
                int(row.get("signal_relevance_score", 0)),
                _to_json(row),
            )
            for row in rows
        ],
    )


def _save_category_summaries(connection: sqlite3.Connection, run_id: str, summaries: dict[str, dict[str, Any]]) -> None:
    connection.executemany(
        """
        insert or replace into category_summaries (
            run_id,
            category,
            title,
            evidence_count,
            summary_json
        ) values (?, ?, ?, ?, ?)
        """,
        [
            (
                run_id,
                category,
                summary["title"],
                summary["evidence_count"],
                _to_json(summary),
            )
            for category, summary in summaries.items()
        ],
    )


def _to_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _from_json(value: str) -> Any:
    return json.loads(value)


def _placeholders(values: list[str]) -> str:
    return ", ".join("?" for _ in values)


def _count_rows(connection: sqlite3.Connection, table: str, run_ids: list[str]) -> int:
    placeholders = _placeholders(run_ids)
    row = connection.execute(
        f"select count(*) from {table} where run_id in ({placeholders})",
        run_ids,
    ).fetchone()
    return int(row[0])


def _count_distinct_raw_items(connection: sqlite3.Connection, run_ids: list[str]) -> int:
    placeholders = _placeholders(run_ids)
    row = connection.execute(
        f"""
        select count(*)
        from (
            select distinct source_name, source_id
            from raw_items
            where run_id in ({placeholders})
        )
        """,
        run_ids,
    ).fetchone()
    return int(row[0])


def _group_counts(
    connection: sqlite3.Connection,
    table: str,
    column: str,
    run_ids: list[str],
) -> dict[str, int]:
    placeholders = _placeholders(run_ids)
    rows = connection.execute(
        f"""
        select {column}, count(*)
        from {table}
        where run_id in ({placeholders})
        group by {column}
        order by {column}
        """,
        run_ids,
    ).fetchall()
    return {row[0]: int(row[1]) for row in rows}


def _count_collection_states(connection: sqlite3.Connection, run_ids: list[str], completed: bool) -> int:
    placeholders = _placeholders(run_ids)
    row = connection.execute(
        f"""
        select count(*)
        from collection_states
        where run_id in ({placeholders}) and completed = ?
        """,
        [*run_ids, int(completed)],
    ).fetchone()
    return int(row[0])


def _ensure_column(connection: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = [row[1] for row in connection.execute(f"pragma table_info({table})")]
    if column not in columns:
        connection.execute(f"alter table {table} add column {column} {definition}")
