"""Regression tests for the current heuristic baseline pipeline."""

from pathlib import Path
from contextlib import closing, redirect_stdout
from types import SimpleNamespace
import io
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from analyzers.venture_signal_analyzer import analyze_venture_signals
from config import DEFAULT_VENTURE_CATEGORY, PipelineConfig
import collectors.source1_collector as source1_collector
import collectors.source2_collector as source2_collector
from collectors.source1_collector import _map_hn_hit
from collectors.source2_collector import _map_stackoverflow_question
from exporters.csv_exporter import export_csv_outputs
from exporters.html_exporter import export_html_report
from exporters.markdown_exporter import export_markdown_report
from evaluate_clusters import (
    evaluation_rows,
    evaluate_cluster_artifacts,
    render_backend_comparison,
    render_threshold_sweep,
    run_backend_comparison,
    run_evaluation,
    run_threshold_sweep,
    threshold_sweep_rows,
    write_threshold_sweep_csv,
)
from export_cluster_review import build_label_template, build_review_rows, write_review_csv
from inspect_runs import main as inspect_runs_main
from main import _load_raw_items, _local_file_diagnostics
from main import _dedupe_resume_raw_items
from models import (
    AnalysisResult,
    CollectionState,
    CollectorDiagnostics,
    EvidenceRow,
    FilteringSummary,
    PreparedItem,
    RawItem,
    RelevanceSummary,
    RunMetadata,
    VolumeSummary,
)
from processors.batch_pipeline import process_evidence_batches
from processors.embeddings import build_embedding_provider
from processors.model_artifacts import build_classification_artifacts, build_cluster_artifacts, build_embedding_artifacts
from processors.prepare_items import prepare_items
from processors.text_cleaner import clean_text, excerpt
from processors.text_quality_filter import filter_quality_items
from storage.sqlite_store import (
    get_collection_pages,
    get_collection_states,
    get_embedding_artifacts,
    get_evidence_rows,
    get_model_artifacts,
    get_processing_batches,
    get_raw_item_source_keys,
    get_cluster_artifacts,
    get_run_chain_embedding_artifacts,
    get_run_chain_evidence_rows,
    get_run_chain_cluster_artifacts,
    get_run_chain_model_artifacts,
    get_run_chain_summary,
    get_resume_lineage_run_ids,
    get_resume_start_pages,
    get_run_summary,
    list_runs,
    save_model_artifacts,
    save_run_to_sqlite,
)


class TextCleanerTests(unittest.TestCase):
    def test_clean_text_removes_html_and_normalizes_entities(self) -> None:
        text = clean_text("<p>CRM&nbsp;workflow &amp; invoicing</p><p>setup pain</p>")

        self.assertEqual(text, "CRM workflow & invoicing setup pain")

    def test_excerpt_truncates_cleaned_text(self) -> None:
        text = excerpt("<p>small business workflow integration pain</p>", max_chars=20)

        self.assertEqual(text, "small business wo...")


class ConfigTests(unittest.TestCase):
    def test_cli_arguments_override_environment_and_defaults(self) -> None:
        env = {
            "PRODUCT_THEME": "Environment theme",
            "COMMUNITY_QUERIES": "env discussion query",
            "STACKEXCHANGE_QUERIES": "env review query",
            "MAX_DISCUSSION_ITEMS": "10",
            "DEBUG_SAVE_RAW": "true",
        }
        argv = [
            "--theme",
            "CLI theme",
            "--community-queries",
            "cli discussion one;cli discussion two",
            "--stackexchange-queries",
            "cli review one;cli review two",
            "--max-discussion-items",
            "7",
            "--max-review-items",
            "8",
            "--request-timeout",
            "9",
            "--processing-batch-size",
            "2",
            "--embedding-backend",
            "hashing",
            "--embedding-model",
            "ignored-for-hashing",
            "--cluster-similarity-threshold",
            "0.25",
            "--discussion-page-size",
            "25",
            "--discussion-max-pages-per-query",
            "3",
            "--discussion-sort",
            "date",
            "--review-page-size",
            "40",
            "--review-max-pages-per-query",
            "4",
            "--review-sort",
            "creation",
            "--review-order",
            "asc",
            "--resume-from-run-id",
            "previous_run",
            "--no-debug-save-raw",
        ]

        with patch.dict(os.environ, env, clear=True):
            config = PipelineConfig.from_args(argv)

        self.assertEqual(config.product_theme, "CLI theme")
        self.assertEqual(config.community_queries, ["cli discussion one", "cli discussion two"])
        self.assertEqual(config.stackexchange_queries, ["cli review one", "cli review two"])
        self.assertEqual(config.max_discussion_items, 7)
        self.assertEqual(config.max_review_items, 8)
        self.assertEqual(config.request_timeout, 9)
        self.assertEqual(config.processing_batch_size, 2)
        self.assertEqual(config.embedding_backend, "hashing")
        self.assertEqual(config.embedding_model, "ignored-for-hashing")
        self.assertEqual(config.cluster_similarity_threshold, 0.25)
        self.assertEqual(config.discussion_page_size, 25)
        self.assertEqual(config.discussion_max_pages_per_query, 3)
        self.assertEqual(config.discussion_sort, "date")
        self.assertEqual(config.review_page_size, 40)
        self.assertEqual(config.review_max_pages_per_query, 4)
        self.assertEqual(config.review_sort, "creation")
        self.assertEqual(config.review_order, "asc")
        self.assertEqual(config.resume_from_run_id, "previous_run")
        self.assertFalse(config.debug_save_raw)

    def test_config_file_values_override_environment(self) -> None:
        env = {
            "PRODUCT_THEME": "Environment theme",
            "COMMUNITY_QUERIES": "env discussion query",
            "STACKEXCHANGE_QUERIES": "env review query",
            "MAX_DISCUSSION_ITEMS": "10",
        }
        config_data = {
            "theme": "Config theme",
            "community_queries": ["config discussion one", "config discussion two"],
            "stackexchange_queries": ["config review one", "config review two"],
            "max_discussion_items": 11,
            "max_review_items": 12,
            "request_timeout": 13,
            "embedding_backend": "sentence-transformer",
            "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
            "cluster_similarity_threshold": 0.3,
            "enable_discussion_source": False,
            "discussion_page_size": 30,
            "discussion_max_pages_per_query": 2,
            "discussion_sort": "date",
            "review_page_size": 20,
            "review_max_pages_per_query": 3,
            "review_sort": "votes",
            "review_order": "asc",
            "debug_save_raw": False,
            "raw_items_file": "samples/example.json",
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "run_config.json"
            path.write_text(json.dumps(config_data), encoding="utf-8")
            with patch.dict(os.environ, env, clear=True):
                config = PipelineConfig.from_args(["--config", str(path)])

        self.assertEqual(config.product_theme, "Config theme")
        self.assertEqual(config.community_queries, ["config discussion one", "config discussion two"])
        self.assertEqual(config.stackexchange_queries, ["config review one", "config review two"])
        self.assertEqual(config.max_discussion_items, 11)
        self.assertEqual(config.max_review_items, 12)
        self.assertEqual(config.processing_batch_size, 500)
        self.assertEqual(config.embedding_backend, "sentence-transformer")
        self.assertEqual(config.embedding_model, "sentence-transformers/all-MiniLM-L6-v2")
        self.assertEqual(config.cluster_similarity_threshold, 0.3)
        self.assertEqual(config.request_timeout, 13)
        self.assertFalse(config.enable_discussion_source)
        self.assertEqual(config.discussion_page_size, 30)
        self.assertEqual(config.discussion_max_pages_per_query, 2)
        self.assertEqual(config.discussion_sort, "date")
        self.assertEqual(config.review_page_size, 20)
        self.assertEqual(config.review_max_pages_per_query, 3)
        self.assertEqual(config.review_sort, "votes")
        self.assertEqual(config.review_order, "asc")
        self.assertFalse(config.debug_save_raw)
        self.assertEqual(config.raw_items_file, "samples/example.json")

    def test_cli_arguments_override_config_file_values(self) -> None:
        config_data = {
            "theme": "Config theme",
            "community_queries": ["config discussion"],
            "stackexchange_queries": ["config review"],
            "max_review_items": 12,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "run_config.json"
            path.write_text(json.dumps(config_data), encoding="utf-8")
            config = PipelineConfig.from_args(
                [
                    "--config",
                    str(path),
                    "--theme",
                    "CLI theme",
                    "--max-review-items",
                    "3",
                    "--raw-items-file",
                    "samples/cli.json",
                ]
            )

        self.assertEqual(config.product_theme, "CLI theme")
        self.assertEqual(config.community_queries, ["config discussion"])
        self.assertEqual(config.max_review_items, 3)
        self.assertEqual(config.raw_items_file, "samples/cli.json")

    def test_environment_values_still_work_without_cli_arguments(self) -> None:
        env = {
            "PRODUCT_THEME": "Environment theme",
            "COMMUNITY_QUERIES": "env discussion one;env discussion two",
            "STACKEXCHANGE_SITE": "superuser",
            "STACKEXCHANGE_QUERIES": "env review one;env review two",
            "MAX_REVIEW_ITEMS": "12",
            "EMBEDDING_BACKEND": "hashing",
            "CLUSTER_SIMILARITY_THRESHOLD": "0.18",
        }

        with patch.dict(os.environ, env, clear=True):
            config = PipelineConfig.from_args([])

        self.assertEqual(config.product_theme, "Environment theme")
        self.assertEqual(config.community_queries, ["env discussion one", "env discussion two"])
        self.assertEqual(config.stackexchange_site, "superuser")
        self.assertEqual(config.stackexchange_queries, ["env review one", "env review two"])
        self.assertEqual(config.max_review_items, 12)
        self.assertEqual(config.embedding_backend, "hashing")
        self.assertEqual(config.cluster_similarity_threshold, 0.18)

    def test_defaults_are_used_without_cli_or_environment(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = PipelineConfig.from_args([])

        self.assertEqual(config.product_theme, DEFAULT_VENTURE_CATEGORY)
        self.assertEqual(config.stackexchange_site, "stackoverflow")
        self.assertEqual(config.max_discussion_items, 50)
        self.assertEqual(config.processing_batch_size, 500)
        self.assertEqual(config.embedding_backend, "hashing")
        self.assertEqual(config.embedding_model, "")
        self.assertEqual(config.cluster_similarity_threshold, 0.12)
        self.assertTrue(config.enable_discussion_source)
        self.assertTrue(config.enable_review_source)
        self.assertEqual(config.discussion_page_size, 0)
        self.assertEqual(config.discussion_max_pages_per_query, 0)
        self.assertEqual(config.discussion_sort, "relevance")
        self.assertEqual(config.review_page_size, 0)
        self.assertEqual(config.review_max_pages_per_query, 0)
        self.assertEqual(config.review_sort, "activity")
        self.assertEqual(config.review_order, "desc")
        self.assertTrue(config.debug_save_raw)
        self.assertEqual(config.raw_items_file, "")
        self.assertEqual(config.resume_from_run_id, "")


class ModelContractTests(unittest.TestCase):
    def test_raw_item_contract_preserves_collector_shape(self) -> None:
        item = RawItem(
            source_type="discussion",
            source_name="fixture",
            source_id="source-1",
            source_url="https://example.test/source",
            title="Workflow pain",
            author="alice",
            created_at="2026-01-01T00:00:00Z",
            collected_at="2026-01-01T00:01:00Z",
            product_theme="AI operations tools",
            query_theme="small business workflow pain",
            text="Small business workflow setup is hard.",
        ).to_dict()

        self.assertEqual(item["source_type"], "discussion")
        self.assertEqual(item["source_id"], "source-1")
        self.assertEqual(item["text"], "Small business workflow setup is hard.")
        self.assertIn("reviewed_product", item)
        self.assertFalse(item["is_demo_fallback"])

    def test_collector_diagnostics_contract_preserves_source_fields(self) -> None:
        diagnostics = CollectorDiagnostics(
            source="source2_stackoverflow_questions",
            endpoint="https://example.test/api",
            stackexchange_site="stackoverflow",
            stackexchange_query=["crm api integration problem"],
            request_params=[{"q": "crm api integration problem"}],
            expected_response_format="JSON object with items.",
            live_question_count_fetched=2,
            live_items_fetched_count=1,
            fallback_triggered=False,
        ).to_dict()

        self.assertEqual(diagnostics["source"], "source2_stackoverflow_questions")
        self.assertEqual(diagnostics["stackexchange_site"], "stackoverflow")
        self.assertEqual(diagnostics["live_question_count_fetched"], 2)
        self.assertIn("query_used", diagnostics)

    def test_filtering_summary_contract_preserves_report_fields(self) -> None:
        summary = FilteringSummary(
            raw_items_collected=4,
            filtered_out_items=1,
            evidence_candidate_items=3,
            raw_by_source={"discussion": 2, "review": 2},
            kept_by_source={"discussion": 1, "review": 2},
            excluded_by_source={"discussion": 1},
            top_exclusion_reasons={"job_or_careers_language": 1},
        ).to_dict()

        self.assertEqual(summary["raw_items_collected"], 4)
        self.assertEqual(summary["evidence_candidate_items"], 3)
        self.assertEqual(summary["top_exclusion_reasons"]["job_or_careers_language"], 1)
        self.assertIn("kept_by_source", summary)

    def test_collection_state_contract_preserves_resume_fields(self) -> None:
        state = CollectionState(
            source="source1_discussion",
            query="small business workflow pain",
            page_count=2,
            last_page_number=1,
            next_page_number=2,
            total_raw_count=100,
            total_item_count=80,
            completed=False,
        ).to_dict()

        self.assertEqual(state["source"], "source1_discussion")
        self.assertEqual(state["next_page_number"], 2)
        self.assertFalse(state["completed"])

    def test_relevance_summary_contract_preserves_report_fields(self) -> None:
        summary = RelevanceSummary(
            evidence_candidates_after_quality_filter=5,
            evidence_candidates_after_relevance_filter=3,
            relevance_filtered_items=2,
        ).to_dict()

        self.assertEqual(summary["evidence_candidates_after_quality_filter"], 5)
        self.assertEqual(summary["evidence_candidates_after_relevance_filter"], 3)
        self.assertEqual(summary["relevance_filtered_items"], 2)

    def test_analysis_result_contract_preserves_export_shape(self) -> None:
        run_metadata = RunMetadata(
            run_id="run-1",
            generated_at_utc="2026-01-01T00:00:00Z",
            project_title="AI-Assisted Community Signal Pipeline",
            venture_category="AI operations tools",
            community_query="small business workflow pain",
            community_queries=["small business workflow pain"],
            stackexchange_site="stackoverflow",
            stackexchange_query="crm api integration problem",
            stackexchange_queries=["crm api integration problem"],
            max_discussion_items=10,
            max_review_items=10,
            request_timeout=25,
            processing_batch_size=500,
            collection_policy={
                "enable_discussion_source": True,
                "enable_review_source": True,
                "discussion_page_size": 0,
                "discussion_max_pages_per_query": 0,
                "discussion_sort": "relevance",
                "review_page_size": 0,
                "review_max_pages_per_query": 0,
                "review_sort": "activity",
                "review_order": "desc",
            },
            debug_save_raw=False,
            raw_items_file="",
        ).to_dict()
        volume = VolumeSummary(
            total_items_analyzed=1,
            discussion_items=1,
            review_items=0,
            evidence_rows=0,
            demo_fallback_items=0,
        ).to_dict()
        analysis = AnalysisResult(
            run_metadata=run_metadata,
            data_sources=[],
            volume=volume,
            category_summaries={},
            evidence_rows=[],
            uncertainty_notes=[],
            venture_implications=[],
            limitations=[],
            filtering_summary={"raw_items_collected": 1},
            relevance_summary={"relevance_filtered_items": 0},
        ).to_dict()

        self.assertEqual(analysis["run_metadata"]["run_id"], "run-1")
        self.assertEqual(analysis["volume"]["total_items_analyzed"], 1)
        self.assertIn("filtering_summary", analysis)
        self.assertIn("relevance_summary", analysis)

    def test_prepared_item_contract_preserves_expected_keys(self) -> None:
        item = PreparedItem.from_raw(
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "source-1",
                "source_url": "https://example.test/source",
                "author": "alice",
                "created_at": "2026-01-01T00:00:00Z",
                "product_theme": "AI operations tools",
                "query_theme": "crm api integration",
                "rating": "2",
            },
            "review-1",
            "Clean CRM integration text",
            "CRM integration problem",
            {"relevance_score": 7, "relevance_reasons": "business_scope_terms:crm"},
        ).to_dict()

        self.assertEqual(item["item_id"], "review-1")
        self.assertEqual(item["source_id"], "source-1")
        self.assertEqual(item["clean_text"], "Clean CRM integration text")
        self.assertEqual(item["relevance_score"], 7)
        self.assertIn("exclude_for_relevance", item)

    def test_evidence_row_contract_preserves_export_shape(self) -> None:
        row = EvidenceRow(
            run_id="run-1",
            category="adoption_barriers",
            category_title="Adoption barriers",
            matched_terms="setup, integration",
            evidence_excerpt="Setup and integration are hard for our CRM workflow.",
            item_id="review-1",
            source_type="review",
            source_name="fixture",
            source_id="source-1",
            source_url="https://example.test/source",
            title="CRM setup issue",
            created_at="2026-01-01T00:00:00Z",
            rating="2",
            quality_score=3,
            quality_reasons="review_like_experience_statement",
            relevance_score=8,
            signal_relevance_score=12,
            relevance_reasons="business_scope_terms:crm",
            relevance_penalties="",
            is_demo_fallback=False,
            fallback_label="",
            fallback_reason="",
        ).to_dict()

        self.assertEqual(row["category"], "adoption_barriers")
        self.assertEqual(row["signal_relevance_score"], 12)
        self.assertEqual(row["source_id"], "source-1")
        self.assertEqual(row["source_url"], "https://example.test/source")


class QualityFilterTests(unittest.TestCase):
    def test_empty_input_returns_zero_filtering_summary(self) -> None:
        kept, excluded, summary = filter_quality_items([])

        self.assertEqual(kept, [])
        self.assertEqual(excluded, [])
        self.assertEqual(summary["raw_items_collected"], 0)
        self.assertEqual(summary["evidence_candidate_items"], 0)
        self.assertEqual(summary["top_exclusion_reasons"], {})

    def test_keeps_user_like_operational_complaint(self) -> None:
        raw_items = [
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "keep-1",
                "source_url": "https://example.test/keep",
                "title": "Small business workflow pain",
                "text": (
                    "I run a small business and our CRM workflow is scattered across invoicing, "
                    "scheduling, and follow-up. Setup is hard and we still do manual work."
                ),
            }
        ]

        kept, excluded, summary = filter_quality_items(raw_items)

        self.assertEqual(len(kept), 1)
        self.assertEqual(excluded, [])
        self.assertEqual(summary["evidence_candidate_items"], 1)

    def test_excludes_job_and_promotional_text(self) -> None:
        raw_items = [
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "job-1",
                "source_url": "https://example.test/job",
                "title": "Hiring software engineer",
                "text": "We are hiring a full-time software engineer. Apply now for this job.",
            },
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "promo-1",
                "source_url": "https://example.test/promo",
                "title": "All-in-one workflow platform",
                "text": "Our platform helps companies unlock growth. Book a demo and get started.",
            },
        ]

        kept, excluded, summary = filter_quality_items(raw_items)

        self.assertEqual(kept, [])
        self.assertEqual(len(excluded), 2)
        self.assertEqual(summary["filtered_out_items"], 2)
        self.assertIn("job_or_careers_language", summary["top_exclusion_reasons"])
        self.assertIn("promotional_or_landing_copy", summary["top_exclusion_reasons"])


class RelevancePreparationTests(unittest.TestCase):
    def test_prepare_items_keeps_relevant_items_and_filters_off_topic_items(self) -> None:
        raw_items = [
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "relevant-1",
                "source_url": "https://example.test/relevant",
                "title": "Small business automation setup",
                "text": (
                    "I run a small business and our workflow automation setup is frustrating. "
                    "Our CRM integration fails and we still have manual cleanup."
                ),
            },
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "off-topic-1",
                "source_url": "https://example.test/off-topic",
                "title": "Favorite movie quote",
                "text": "This favorite quote from a film scene is timeless and funny.",
            },
        ]

        prepared, relevance_excluded = prepare_items(raw_items)

        self.assertEqual(len(prepared), 1)
        self.assertEqual(prepared[0]["source_id"], "relevant-1")
        self.assertGreaterEqual(prepared[0]["relevance_score"], 4)
        self.assertEqual(len(relevance_excluded), 1)
        self.assertEqual(relevance_excluded[0]["source_id"], "off-topic-1")


class BatchProcessingTests(unittest.TestCase):
    def test_process_evidence_batches_preserves_global_counts_and_ids(self) -> None:
        raw_items = [
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "relevant-1",
                "source_url": "https://example.test/relevant-1",
                "title": "Small business automation setup",
                "text": (
                    "I run a small business and our workflow automation setup is frustrating. "
                    "Our CRM integration fails and we still have manual cleanup."
                ),
            },
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "job-1",
                "source_url": "https://example.test/job",
                "title": "Hiring software engineer",
                "text": "We are hiring a full-time software engineer. Apply now for this job.",
            },
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "relevant-2",
                "source_url": "https://example.test/relevant-2",
                "title": "CRM API integration problem",
                "text": (
                    "We use a CRM for customers, but the API integration fails during setup. "
                    "Our small team still has to fix customer records manually."
                ),
                "rating": "1",
            },
        ]

        result = process_evidence_batches(raw_items, batch_size=1)

        self.assertEqual(result["filtering_summary"]["raw_items_collected"], 3)
        self.assertEqual(result["filtering_summary"]["filtered_out_items"], 1)
        self.assertEqual(len(result["candidate_items"]), 2)
        self.assertEqual([row["source_index"] for row in result["excluded_items"]], [2])
        self.assertEqual(len(result["batch_summaries"]), 3)
        self.assertEqual(len({item["item_id"] for item in result["prepared_items"]}), len(result["prepared_items"]))
        self.assertEqual(
            result["relevance_summary"]["evidence_candidates_after_quality_filter"],
            len(result["candidate_items"]),
        )


class ModelArtifactProducerTests(unittest.TestCase):
    def test_build_classification_artifacts_from_prepared_items(self) -> None:
        raw_items = [
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "relevant-1",
                "source_url": "https://example.test/relevant-1",
                "title": "Small business automation setup",
                "text": (
                    "I run a small business and our workflow automation setup is frustrating. "
                    "Our CRM integration fails and we still have manual cleanup."
                ),
            },
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "relevant-2",
                "source_url": "https://example.test/relevant-2",
                "title": "CRM API integration problem",
                "text": (
                    "We use a CRM for customers, but the API integration fails during setup. "
                    "Our small team still has to fix customer records manually."
                ),
                "rating": "1",
            },
        ]
        result = process_evidence_batches(raw_items, batch_size=1)

        artifacts = build_classification_artifacts(result["prepared_items"], result["batch_summaries"])

        self.assertEqual(len(artifacts), len(result["prepared_items"]))
        self.assertEqual([artifact["batch_index"] for artifact in artifacts], [1, 2])
        self.assertEqual(artifacts[0]["artifact_type"], "classification")
        self.assertEqual(artifacts[0]["model_name"], "heuristic-signal-classifier")
        self.assertIn("workflow_friction", artifacts[0]["artifact"]["labels"])
        self.assertIn("implementation_feedback", artifacts[1]["artifact"]["labels"])
        self.assertEqual(len(artifacts[0]["input_hash"]), 64)

    def test_build_cluster_artifacts_groups_related_pain_points(self) -> None:
        raw_items = [
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "sync-1",
                "source_url": "https://example.test/sync-1",
                "title": "CRM integration keeps failing",
                "text": (
                    "Our CRM integration fails and customer records do not sync. "
                    "We still do manual cleanup after the automation breaks."
                ),
            },
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "sync-2",
                "source_url": "https://example.test/sync-2",
                "title": "Customer field sync problem",
                "text": (
                    "The API integration misses customer fields and record updates. "
                    "Our small team has to fix records manually."
                ),
                "rating": "1",
            },
        ]
        result = process_evidence_batches(raw_items, batch_size=1)

        artifacts = build_cluster_artifacts(result["prepared_items"], result["batch_summaries"])

        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["artifact_type"], "evidence_cluster")
        self.assertEqual(artifacts[0]["model_name"], "heuristic-evidence-clusterer")
        self.assertEqual(artifacts[0]["model_version"], "v2")
        self.assertEqual(artifacts[0]["artifact"]["cluster_key"], "customer_data_sync_integration")
        self.assertEqual(artifacts[0]["artifact"]["item_count"], 2)
        self.assertEqual(artifacts[0]["artifact"]["member_source_ids"], ["sync-1", "sync-2"])
        self.assertIn("Customer data sync", artifacts[0]["artifact"]["label"])
        self.assertEqual(artifacts[0]["artifact"]["embedding_model"], "hashed-text-embedding@v1")
        self.assertIn("member_similarity_to_representative", artifacts[0]["artifact"])

    def test_build_embedding_artifacts_from_prepared_items(self) -> None:
        raw_items = [
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "embedding-1",
                "source_url": "https://example.test/embedding-1",
                "title": "CRM API integration problem",
                "text": (
                    "Our CRM API integration fails during setup. "
                    "Customer records do not sync and manual cleanup is slow."
                ),
                "rating": "1",
            }
        ]
        result = process_evidence_batches(raw_items, batch_size=1)

        artifacts = build_embedding_artifacts(result["prepared_items"], result["batch_summaries"])

        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0]["artifact_type"], "embedding")
        self.assertEqual(artifacts[0]["model_name"], "hashed-text-embedding")
        self.assertEqual(artifacts[0]["artifact"]["dimensions"], 64)
        self.assertGreater(len(artifacts[0]["artifact"]["nonzero_indices"]), 0)
        self.assertEqual(len(artifacts[0]["artifact"]["nonzero_indices"]), len(artifacts[0]["artifact"]["values"]))
        self.assertIn("crm", artifacts[0]["artifact"]["top_terms"])

    def test_embedding_provider_factory_supports_hashing_backend(self) -> None:
        provider = build_embedding_provider("hashing")
        item = {
            "item_id": "item-1",
            "title": "CRM sync problem",
            "clean_text": "Customer records do not sync after API integration.",
            "relevance_reasons": "",
            "quality_reasons": "",
        }

        payload = provider.payload(item)

        self.assertEqual(provider.artifact_model_name, "hashed-text-embedding")
        self.assertEqual(payload["embedding_type"], "sparse_hashing")
        self.assertEqual(payload["dimensions"], 64)
        self.assertEqual(len(provider.vector(item)), 64)


class ClusterEvaluationTests(unittest.TestCase):
    def test_build_review_rows_exports_cluster_label_template(self) -> None:
        prepared_items = [
            {
                "item_id": "review-1",
                "source_id": "source-1",
                "source_type": "review",
                "source_name": "fixture",
                "source_url": "https://example.test/1",
                "title": "CRM sync problem",
                "clean_text": "Customer records do not sync after API integration.",
                "relevance_score": 8,
            }
        ]
        cluster_artifacts = [
            {
                "artifact": {
                    "cluster_id": "cluster-customer_data_sync_integration",
                    "cluster_key": "customer_data_sync_integration",
                    "member_item_ids": ["review-1"],
                    "representative_item_ids": ["review-1"],
                    "top_terms": ["crm", "sync"],
                }
            }
        ]

        rows = build_review_rows(cluster_artifacts, prepared_items)
        labels = build_label_template(rows)

        self.assertEqual(rows[0]["source_id"], "source-1")
        self.assertEqual(rows[0]["reviewed_cluster_label"], "customer_data_sync_integration")
        self.assertIn("Customer records", rows[0]["text_excerpt"])
        self.assertEqual(labels, {"source-1": "customer_data_sync_integration"})

    def test_write_review_csv_creates_human_review_file(self) -> None:
        rows = [
            {
                "source_id": "source-1",
                "item_id": "review-1",
                "current_cluster_id": "cluster-sync",
                "current_cluster_key": "customer_data_sync_integration",
                "reviewed_cluster_label": "customer_data_sync_integration",
                "source_type": "review",
                "source_name": "fixture",
                "title": "CRM sync problem",
                "relevance_score": 8,
                "source_url": "https://example.test/1",
                "top_terms": "crm, sync",
                "text_excerpt": "Customer records do not sync.",
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "review.csv"
            write_review_csv(path, rows)
            content = path.read_text(encoding="utf-8")

        self.assertIn("reviewed_cluster_label", content)
        self.assertIn("customer_data_sync_integration", content)

    def test_evaluate_cluster_artifacts_reports_pairwise_metrics(self) -> None:
        cluster_artifacts = [
            {
                "artifact": {
                    "cluster_id": "cluster-sync",
                    "cluster_key": "customer_data_sync_integration",
                    "item_count": 2,
                    "member_source_ids": ["source-1", "source-2"],
                    "representative_source_ids": ["source-1", "source-2"],
                    "top_terms": ["crm", "sync"],
                }
            },
            {
                "artifact": {
                    "cluster_id": "cluster-workflow",
                    "cluster_key": "workflow_automation_reliability",
                    "item_count": 1,
                    "member_source_ids": ["source-3"],
                    "representative_source_ids": ["source-3"],
                    "top_terms": ["workflow"],
                }
            },
        ]
        labels = {
            "source-1": "customer_data_sync_integration",
            "source-2": "customer_data_sync_integration",
            "source-3": "workflow_automation_reliability",
        }

        result = evaluate_cluster_artifacts(cluster_artifacts, labels)

        self.assertEqual(result["labeled_item_count"], 3)
        self.assertEqual(result["pairwise_precision"], 1.0)
        self.assertEqual(result["pairwise_recall"], 1.0)
        self.assertEqual(result["pairwise_f1"], 1.0)

    def test_run_evaluation_uses_sample_review_labels(self) -> None:
        result = run_evaluation(
            raw_items_file=ROOT_DIR / "samples" / "small_business_operations_raw_items.json",
            labels_file=ROOT_DIR / "samples" / "cluster_review_labels.json",
            embedding_backend="hashing",
            embedding_model="",
            cluster_similarity_threshold=0.12,
            processing_batch_size=2,
        )

        self.assertEqual(result["embedding_backend"], "hashing")
        self.assertEqual(result["raw_item_count"], 5)
        self.assertEqual(result["prepared_item_count"], 4)
        self.assertEqual(result["labeled_item_count"], 4)
        self.assertEqual(result["pairwise_recall"], 1.0)

    def test_run_threshold_sweep_compares_cluster_thresholds(self) -> None:
        result = run_threshold_sweep(
            raw_items_file=ROOT_DIR / "samples" / "small_business_operations_raw_items.json",
            labels_file=ROOT_DIR / "samples" / "cluster_review_labels.json",
            embedding_backend="hashing",
            embedding_model="",
            cluster_similarity_thresholds=[0.05, 0.12, 0.2],
            processing_batch_size=2,
        )
        rendered = render_threshold_sweep(result)

        self.assertEqual(result["evaluation_type"], "threshold_sweep")
        self.assertEqual(len(result["results"]), 3)
        self.assertIn(result["best_threshold"], [0.05, 0.12, 0.2])
        self.assertIn("Cluster Threshold Sweep", rendered)
        self.assertIn("threshold=0.12", rendered)

    def test_threshold_sweep_rows_and_csv_export(self) -> None:
        result = run_threshold_sweep(
            raw_items_file=ROOT_DIR / "samples" / "small_business_operations_raw_items.json",
            labels_file=ROOT_DIR / "samples" / "cluster_review_labels.json",
            embedding_backend="hashing",
            embedding_model="",
            cluster_similarity_thresholds=[0.05, 0.12],
            processing_batch_size=2,
        )
        rows = threshold_sweep_rows(result)

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "thresholds.csv"
            write_threshold_sweep_csv(path, result)
            content = path.read_text(encoding="utf-8")

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["embedding_backend"], "hashing")
        self.assertIn("cluster_similarity_threshold", content)
        self.assertIn("pairwise_f1", content)

    def test_run_backend_comparison_flattens_backend_rows(self) -> None:
        result = run_backend_comparison(
            raw_items_file=ROOT_DIR / "samples" / "small_business_operations_raw_items.json",
            labels_file=ROOT_DIR / "samples" / "cluster_review_labels.json",
            backend_specs=[
                {"embedding_backend": "hashing", "embedding_model": ""},
                {"embedding_backend": "hashing", "embedding_model": "hashing-control"},
            ],
            cluster_similarity_thresholds=[0.05, 0.12],
            processing_batch_size=2,
        )
        rendered = render_backend_comparison(result)
        rows = evaluation_rows(result)

        self.assertEqual(result["evaluation_type"], "backend_comparison")
        self.assertEqual(len(result["backend_results"]), 2)
        self.assertEqual(len(rows), 4)
        self.assertIn("Cluster Backend Comparison", rendered)
        self.assertEqual(rows[0]["embedding_backend"], "hashing")


class AnalyzerAndExporterTests(unittest.TestCase):
    def test_empty_analysis_exports_report_files(self) -> None:
        config = _fake_config()
        filtering_summary = FilteringSummary(
            raw_items_collected=0,
            filtered_out_items=0,
            evidence_candidate_items=0,
            raw_by_source={},
            kept_by_source={},
            excluded_by_source={},
            top_exclusion_reasons={},
        ).to_dict()
        relevance_summary = RelevanceSummary(
            evidence_candidates_after_quality_filter=0,
            evidence_candidates_after_relevance_filter=0,
            relevance_filtered_items=0,
        ).to_dict()
        analysis = analyze_venture_signals([], config, "empty_run", filtering_summary, relevance_summary)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            csv_paths = export_csv_outputs(analysis, [], output_dir, "empty_run", [])
            markdown_path = export_markdown_report(analysis, output_dir, "empty_run")
            html_path = export_html_report(analysis, output_dir, "empty_run")

            self.assertTrue(csv_paths["evidence_csv"].exists())
            self.assertTrue(csv_paths["items_csv"].exists())
            self.assertTrue(csv_paths["summary_csv"].exists())
            self.assertTrue(csv_paths["clusters_csv"].exists())
            self.assertEqual(csv_paths["evidence_csv"].read_text(encoding="utf-8"), "")
            self.assertEqual(csv_paths["items_csv"].read_text(encoding="utf-8"), "")
            self.assertEqual(csv_paths["clusters_csv"].read_text(encoding="utf-8"), "")
            self.assertIn("No strong heuristic evidence found", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("No example evidence surfaced", html_path.read_text(encoding="utf-8"))

    def test_analyzer_creates_evidence_rows_without_investment_recommendations(self) -> None:
        config = _fake_config()
        raw_items = [
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "review-1",
                "source_url": "https://example.test/review",
                "title": "CRM API integration problem",
                "text": (
                    "We use a CRM for customers, but the API integration fails during setup. "
                    "Our small team still has to fix customer records manually."
                ),
                "rating": "1",
            }
        ]
        prepared, _ = prepare_items(raw_items)

        analysis = analyze_venture_signals(prepared, config, "test_run")

        self.assertGreater(len(analysis["evidence_rows"]), 0)
        self.assertIn("adoption_barriers", analysis["category_summaries"])
        rendered_text = " ".join(analysis["venture_implications"] + analysis["limitations"]).lower()
        self.assertIn("not an investment recommendation", rendered_text)
        self.assertNotIn("invest now", rendered_text)

    def test_exporters_create_report_files(self) -> None:
        config = _fake_config()
        raw_items = [
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "review-1",
                "source_url": "https://example.test/review",
                "title": "CRM API integration problem",
                "text": (
                    "We use a CRM for customers, but the API integration fails during setup. "
                    "Our small team still has to fix customer records manually."
                ),
                "rating": "1",
            }
        ]
        prepared, _ = prepare_items(raw_items)
        analysis = analyze_venture_signals(prepared, config, "test_run")
        cluster_artifacts = [
            {
                "artifact": {
                    "cluster_id": "customer_data_sync_integration",
                    "cluster_key": "customer_data_sync_integration",
                    "label": "Customer data sync and integration reliability pain",
                    "product_opportunity": "Improve reliable customer-data sync for small teams.",
                    "item_count": 1,
                    "source_mix": {"review": 1},
                    "average_relevance_score": 7.0,
                    "max_relevance_score": 7,
                    "top_terms": ["crm", "integration", "customer"],
                    "representative_item_ids": [prepared[0]["item_id"]],
                    "representative_source_ids": [prepared[0]["source_id"]],
                    "grouping_basis": "pain mechanism candidate buckets plus hashed embedding cosine connected components",
                    "embedding_model": "hashed-text-embedding@v1",
                    "similarity_threshold": 0.12,
                    "evidence_excerpts": [prepared[0]["clean_text"]],
                }
            }
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            csv_paths = export_csv_outputs(analysis, prepared, output_dir, "test_run", [], cluster_artifacts)
            markdown_path = export_markdown_report(analysis, output_dir, "test_run", cluster_artifacts)
            html_path = export_html_report(analysis, output_dir, "test_run", cluster_artifacts)

            self.assertTrue(csv_paths["evidence_csv"].exists())
            self.assertTrue(csv_paths["items_csv"].exists())
            self.assertTrue(csv_paths["summary_csv"].exists())
            self.assertTrue(csv_paths["clusters_csv"].exists())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(html_path.exists())
            self.assertIn("AI-Assisted Community Signal Pipeline", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("Pain Point Clusters", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("Customer data sync", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("<!doctype html>", html_path.read_text(encoding="utf-8"))
            self.assertIn("Customer data sync", html_path.read_text(encoding="utf-8"))
            self.assertIn("Customer data sync", csv_paths["clusters_csv"].read_text(encoding="utf-8"))


class StorageTests(unittest.TestCase):
    def test_save_run_to_sqlite_creates_run_index_and_stage_tables(self) -> None:
        config = _fake_config(debug_save_raw=False)
        raw_items = [
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "review-1",
                "source_url": "https://example.test/review",
                "title": "CRM API integration problem",
                "text": (
                    "We use a CRM for customers, but the API integration fails during setup. "
                    "Our small team still has to fix customer records manually."
                ),
                "rating": "1",
            },
            {
                "source_type": "discussion",
                "source_name": "fixture",
                "source_id": "job-1",
                "source_url": "https://example.test/job",
                "title": "Hiring software engineer",
                "text": "We are hiring a full-time software engineer. Apply now for this job.",
            },
        ]
        candidate_items, excluded_items, filtering_summary = filter_quality_items(raw_items)
        prepared_items, relevance_excluded_items = prepare_items(candidate_items)
        batch_summaries = process_evidence_batches(raw_items, batch_size=1)["batch_summaries"]
        relevance_summary = RelevanceSummary(
            evidence_candidates_after_quality_filter=len(candidate_items),
            evidence_candidates_after_relevance_filter=len(prepared_items),
            relevance_filtered_items=len(relevance_excluded_items),
        ).to_dict()
        analysis = analyze_venture_signals(prepared_items, config, "sqlite_run", filtering_summary, relevance_summary)
        collector_diagnostics = {
            "source1": {
                "source": "source1_discussion",
                "fallback_triggered": False,
                "collected_pages": [
                    {
                        "source": "source1_discussion",
                        "query": "small business workflow pain",
                        "page_number": 0,
                        "request_url": "https://example.test/hn?page=0",
                        "request_params": {},
                        "raw_count": 1,
                        "item_count": 1,
                        "has_more": False,
                    }
                ],
            },
            "source2": {"source": "source2_stackoverflow_questions", "fallback_triggered": False, "collected_pages": []},
            "final_fallback_item_count": 0,
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            save_run_to_sqlite(
                db_path,
                "sqlite_run",
                analysis,
                collector_diagnostics,
                raw_items,
                prepared_items,
                excluded_items,
                relevance_excluded_items,
                batch_summaries,
            )
            with closing(sqlite3.connect(db_path)) as connection:
                run_count = connection.execute("select count(*) from runs").fetchone()[0]
                raw_count = connection.execute("select count(*) from raw_items").fetchone()[0]
                prepared_count = connection.execute("select count(*) from prepared_items").fetchone()[0]
                excluded_count = connection.execute("select count(*) from excluded_items").fetchone()[0]
                page_count = connection.execute("select count(*) from collection_pages").fetchone()[0]
                state_count = connection.execute("select count(*) from collection_states").fetchone()[0]
                batch_count = connection.execute("select count(*) from processing_batches").fetchone()[0]
                evidence_count = connection.execute("select count(*) from evidence_rows").fetchone()[0]
                category_count = connection.execute("select count(*) from category_summaries").fetchone()[0]

        self.assertEqual(run_count, 1)
        self.assertEqual(raw_count, 2)
        self.assertEqual(prepared_count, len(prepared_items))
        self.assertEqual(excluded_count, 1)
        self.assertEqual(page_count, 1)
        self.assertEqual(state_count, 1)
        self.assertEqual(batch_count, 2)
        self.assertEqual(evidence_count, len(analysis["evidence_rows"]))
        self.assertEqual(category_count, len(analysis["category_summaries"]))

    def test_sqlite_query_helpers_return_run_summary_and_evidence_rows(self) -> None:
        config = _fake_config(debug_save_raw=False)
        raw_items = [
            {
                "source_type": "review",
                "source_name": "fixture",
                "source_id": "review-1",
                "source_url": "https://example.test/review",
                "title": "CRM API integration problem",
                "text": (
                    "We use a CRM for customers, but the API integration fails during setup. "
                    "Our small team still has to fix customer records manually."
                ),
                "rating": "1",
            }
        ]
        candidate_items, excluded_items, filtering_summary = filter_quality_items(raw_items)
        prepared_items, relevance_excluded_items = prepare_items(candidate_items)
        relevance_summary = RelevanceSummary(
            evidence_candidates_after_quality_filter=len(candidate_items),
            evidence_candidates_after_relevance_filter=len(prepared_items),
            relevance_filtered_items=len(relevance_excluded_items),
        ).to_dict()
        analysis = analyze_venture_signals(prepared_items, config, "query_run", filtering_summary, relevance_summary)
        collector_diagnostics = {
            "source1": {
                "source": "source1_discussion",
                "fallback_triggered": False,
                "collected_pages": [
                    {
                        "source": "source1_discussion",
                        "query": "small business workflow pain",
                        "page_number": 0,
                        "request_url": "https://example.test/hn?page=0",
                        "request_params": {},
                        "raw_count": 1,
                        "item_count": 1,
                        "has_more": True,
                    },
                    {
                        "source": "source1_discussion",
                        "query": "small business workflow pain",
                        "page_number": 1,
                        "request_url": "https://example.test/hn?page=1",
                        "request_params": {},
                        "raw_count": 1,
                        "item_count": 1,
                        "has_more": False,
                    }
                ],
            },
            "source2": {
                "source": "source2_stackoverflow_questions",
                "fallback_triggered": False,
                "collected_pages": [
                    {
                        "source": "source2_stackoverflow_questions",
                        "query": "crm api integration problem",
                        "page_number": 1,
                        "request_url": "",
                        "request_params": {"page": 1},
                        "raw_count": 1,
                        "item_count": 1,
                        "has_more": True,
                    }
                ],
            },
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            save_run_to_sqlite(
                db_path,
                "query_run",
                analysis,
                collector_diagnostics,
                raw_items,
                prepared_items,
                excluded_items,
                relevance_excluded_items,
            )

            runs = list_runs(db_path)
            summary = get_run_summary(db_path, "query_run")
            evidence_rows = get_evidence_rows(db_path, "query_run", limit=5)
            pages = get_collection_pages(db_path, "query_run")
            states = get_collection_states(db_path, "query_run")
            processing_batches = get_processing_batches(db_path, "query_run")
            source1_resume_pages = get_resume_start_pages(db_path, "query_run", "source1_discussion")
            source2_resume_pages = get_resume_start_pages(db_path, "query_run", "source2_stackoverflow_questions")
            adoption_rows = get_evidence_rows(db_path, "query_run", limit=5, category="adoption_barriers")

        self.assertEqual(runs[0]["run_id"], "query_run")
        self.assertEqual(summary["run_id"], "query_run")
        self.assertEqual(summary["community_queries"], ["small business workflow pain"])
        self.assertIn("source1", summary["collector_diagnostics"])
        self.assertEqual(pages[0]["query"], "small business workflow pain")
        self.assertEqual(pages[0]["item_count"], 1)
        self.assertEqual(states[0]["last_page_number"], 1)
        self.assertEqual(states[0]["next_page_number"], 2)
        self.assertTrue(states[0]["completed"])
        self.assertEqual(states[0]["total_item_count"], 2)
        self.assertEqual(processing_batches, [])
        self.assertEqual(source1_resume_pages, {})
        self.assertEqual(source2_resume_pages, {"crm api integration problem": 2})
        self.assertGreater(len(evidence_rows), 0)
        self.assertTrue(all(row["signal_relevance_score"] >= evidence_rows[-1]["signal_relevance_score"] for row in evidence_rows))
        self.assertTrue(all(row["category"] == "adoption_barriers" for row in adoption_rows))

    def test_sqlite_lineage_helpers_return_resume_chain_and_source_keys(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="root_run", source_id="review-1")
            _save_sample_storage_run(db_path, run_id="child_run", source_id="review-2", resume_from_run_id="root_run")

            lineage = get_resume_lineage_run_ids(db_path, "child_run")
            source_keys = get_raw_item_source_keys(db_path, lineage)

        self.assertEqual(lineage, ["child_run", "root_run"])
        self.assertIn(("fixture", "review-1"), source_keys)
        self.assertIn(("fixture", "review-2"), source_keys)

    def test_run_chain_helpers_aggregate_resumed_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="root_run", source_id="review-1")
            _save_sample_storage_run(db_path, run_id="child_run", source_id="review-2", resume_from_run_id="root_run")
            save_model_artifacts(
                db_path,
                "child_run",
                [
                    {
                        "batch_index": 0,
                        "item_id": "review-2",
                        "source_id": "review-2",
                        "artifact_type": "classification",
                        "model_name": "heuristic-baseline",
                        "model_version": "v1",
                        "input_hash": "hash-2",
                        "artifact": {"label": "adoption_barrier", "score": 0.8},
                        "created_at": "2026-01-01T00:00:00Z",
                    },
                    {
                        "batch_index": 0,
                        "item_id": "review-2",
                        "source_id": "review-2",
                        "artifact_type": "embedding",
                        "model_name": "hashed-text-embedding",
                        "model_version": "v1",
                        "input_hash": "hash-2",
                        "artifact": {
                            "dimensions": 64,
                            "nonzero_indices": [1, 2],
                            "values": [0.7, 0.7],
                            "top_terms": ["crm", "sync"],
                            "token_count": 2,
                        },
                        "created_at": "2026-01-01T00:01:00Z",
                    },
                    {
                        "batch_index": 0,
                        "item_id": "cluster-customer_data_sync_integration",
                        "source_id": "cluster-customer_data_sync_integration",
                        "artifact_type": "evidence_cluster",
                        "model_name": "heuristic-evidence-clusterer",
                        "model_version": "v1",
                        "input_hash": "hash-3",
                        "artifact": {
                            "cluster_id": "cluster-customer_data_sync_integration",
                            "label": "Customer data sync and integration reliability pain",
                            "item_count": 1,
                        },
                        "created_at": "2026-01-01T00:01:00Z",
                    }
                ],
            )

            summary = get_run_chain_summary(db_path, "child_run")
            evidence_rows = get_run_chain_evidence_rows(db_path, "child_run", limit=50)
            artifacts = get_run_chain_model_artifacts(db_path, "child_run", artifact_type="classification")
            cluster_artifacts = get_run_chain_cluster_artifacts(db_path, "child_run")
            embedding_artifacts = get_run_chain_embedding_artifacts(db_path, "child_run")

        self.assertEqual(summary["run_ids"], ["child_run", "root_run"])
        self.assertEqual(summary["run_count"], 2)
        self.assertEqual(summary["root_run_id"], "root_run")
        self.assertEqual(summary["latest_run_id"], "child_run")
        self.assertEqual(summary["storage_counts"]["raw_items"], 2)
        self.assertEqual(summary["storage_counts"]["unique_raw_items"], 2)
        self.assertEqual(summary["storage_counts"]["model_artifacts"], 3)
        self.assertEqual(summary["model_artifacts_by_type"], {"classification": 1, "embedding": 1, "evidence_cluster": 1})
        self.assertGreater(len(evidence_rows), 0)
        self.assertEqual({row["run_id"] for row in evidence_rows}, {"root_run", "child_run"})
        self.assertEqual(artifacts[0]["run_id"], "child_run")
        self.assertEqual(cluster_artifacts[0]["artifact"]["item_count"], 1)
        self.assertEqual(embedding_artifacts[0]["artifact"]["dimensions"], 64)

    def test_model_artifact_helpers_store_and_filter_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="artifact_run", source_id="review-1")
            artifacts = [
                {
                    "batch_index": 1,
                    "item_id": "review-1",
                    "source_id": "review-1",
                    "artifact_type": "classification",
                    "model_name": "heuristic-baseline",
                    "model_version": "v1",
                    "input_hash": "hash-1",
                    "artifact": {"label": "adoption_barrier", "score": 0.8},
                    "created_at": "2026-01-01T00:00:00Z",
                },
                {
                    "batch_index": 2,
                    "item_id": "review-2",
                    "source_id": "review-2",
                    "artifact_type": "embedding",
                    "model_name": "placeholder-embedding",
                    "model_version": "v1",
                    "input_hash": "hash-2",
                    "artifact": {"vector": [0.1, 0.2]},
                    "created_at": "2026-01-01T00:01:00Z",
                },
                {
                    "batch_index": 1,
                    "item_id": "cluster-customer_data_sync_integration",
                    "source_id": "cluster-customer_data_sync_integration",
                    "artifact_type": "evidence_cluster",
                    "model_name": "heuristic-evidence-clusterer",
                    "model_version": "v1",
                    "input_hash": "hash-3",
                    "artifact": {
                        "cluster_id": "cluster-customer_data_sync_integration",
                        "label": "Customer data sync and integration reliability pain",
                        "item_count": 1,
                    },
                    "created_at": "2026-01-01T00:02:00Z",
                },
            ]

            save_model_artifacts(db_path, "artifact_run", artifacts)
            all_artifacts = get_model_artifacts(db_path, "artifact_run")
            classification_artifacts = get_model_artifacts(db_path, "artifact_run", artifact_type="classification")
            batch_two_artifacts = get_model_artifacts(db_path, "artifact_run", batch_index=2)
            cluster_artifacts = get_cluster_artifacts(db_path, "artifact_run")
            embedding_artifacts = get_embedding_artifacts(db_path, "artifact_run")

        self.assertEqual(len(all_artifacts), 3)
        self.assertEqual(classification_artifacts[0]["artifact"]["label"], "adoption_barrier")
        self.assertEqual(batch_two_artifacts[0]["artifact_type"], "embedding")
        self.assertEqual(cluster_artifacts[0]["artifact"]["item_count"], 1)
        self.assertEqual(embedding_artifacts[0]["artifact"]["vector"], [0.1, 0.2])


class ResumeDeduplicationTests(unittest.TestCase):
    def test_dedupes_resume_raw_items_against_parent_lineage(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="parent_run", source_id="review-1")
            config = _fake_config(resume_from_run_id="parent_run", sqlite_path=db_path)
            raw_items = [
                {
                    "source_type": "review",
                    "source_name": "fixture",
                    "source_id": "review-1",
                    "source_url": "https://example.test/review-1",
                    "title": "Duplicate item",
                    "text": "Duplicate CRM setup problem.",
                },
                {
                    "source_type": "review",
                    "source_name": "fixture",
                    "source_id": "review-2",
                    "source_url": "https://example.test/review-2",
                    "title": "New item",
                    "text": "New workflow automation setup problem.",
                },
            ]

            kept_items, duplicate_items = _dedupe_resume_raw_items(config, raw_items)

        self.assertEqual([item["source_id"] for item in kept_items], ["review-2"])
        self.assertEqual([item["source_id"] for item in duplicate_items], ["review-1"])
        self.assertEqual(duplicate_items[0]["duplicate_reason"], "seen_in_resume_chain")


class InspectRunsCliTests(unittest.TestCase):
    def test_inspect_runs_cli_lists_summary_state_and_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path)

            list_output = _capture_inspect_runs(["--db-path", str(db_path), "--list"])
            summary_output = _capture_inspect_runs(["--db-path", str(db_path), "--run-id", "query_run"])
            state_output = _capture_inspect_runs(
                ["--db-path", str(db_path), "--run-id", "query_run", "--collection-state"]
            )
            batch_output = _capture_inspect_runs(["--db-path", str(db_path), "--run-id", "query_run", "--batches"])
            artifact_output = _capture_inspect_runs(["--db-path", str(db_path), "--run-id", "query_run", "--artifacts"])
            evidence_output = _capture_inspect_runs(
                ["--db-path", str(db_path), "--run-id", "query_run", "--evidence", "--limit", "1"]
            )

        self.assertIn("Runs", list_output)
        self.assertIn("query_run", list_output)
        self.assertIn("Run query_run", summary_output)
        self.assertIn("community_queries: small business workflow pain", summary_output)
        self.assertIn("Collection State", state_output)
        self.assertIn("completed=yes", state_output)
        self.assertIn("Processing Batches", batch_output)
        self.assertIn("No processing batch rows", batch_output)
        self.assertIn("Model Artifacts", artifact_output)
        self.assertIn("No model artifact rows", artifact_output)
        self.assertIn("Evidence Rows", evidence_output)
        self.assertIn("adoption_barriers", evidence_output)

    def test_inspect_runs_cli_shows_model_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="artifact_run", source_id="review-1")
            save_model_artifacts(
                db_path,
                "artifact_run",
                [
                    {
                        "batch_index": 1,
                        "item_id": "review-1",
                        "source_id": "review-1",
                        "artifact_type": "classification",
                        "model_name": "heuristic-baseline",
                        "model_version": "v1",
                        "input_hash": "hash-1",
                        "artifact": {"label": "adoption_barrier", "score": 0.8},
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )

            output = _capture_inspect_runs(
                [
                    "--db-path",
                    str(db_path),
                    "--run-id",
                    "artifact_run",
                    "--artifacts",
                    "--artifact-type",
                    "classification",
                ]
            )

        self.assertIn("Model Artifacts", output)
        self.assertIn("heuristic-baseline@v1", output)
        self.assertIn("classification", output)

    def test_inspect_runs_cli_shows_cluster_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="cluster_run", source_id="review-1")
            save_model_artifacts(
                db_path,
                "cluster_run",
                [
                    {
                        "batch_index": 1,
                        "item_id": "cluster-customer_data_sync_integration",
                        "source_id": "cluster-customer_data_sync_integration",
                        "artifact_type": "evidence_cluster",
                        "model_name": "heuristic-evidence-clusterer",
                        "model_version": "v1",
                        "input_hash": "hash-1",
                        "artifact": {
                            "cluster_id": "cluster-customer_data_sync_integration",
                            "label": "Customer data sync and integration reliability pain",
                            "product_opportunity": "Reliable sync and recovery workflows.",
                            "item_count": 1,
                            "average_relevance_score": 8,
                            "top_terms": ["crm", "integration"],
                            "representative_item_ids": ["review-1"],
                        },
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )

            output = _capture_inspect_runs(["--db-path", str(db_path), "--run-id", "cluster_run", "--clusters"])

        self.assertIn("Evidence Clusters", output)
        self.assertIn("Customer data sync", output)
        self.assertIn("representatives: review-1", output)

    def test_inspect_runs_cli_shows_embedding_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="embedding_run", source_id="review-1")
            save_model_artifacts(
                db_path,
                "embedding_run",
                [
                    {
                        "batch_index": 1,
                        "item_id": "review-1",
                        "source_id": "review-1",
                        "artifact_type": "embedding",
                        "model_name": "hashed-text-embedding",
                        "model_version": "v1",
                        "input_hash": "hash-1",
                        "artifact": {
                            "dimensions": 64,
                            "nonzero_indices": [1, 2],
                            "values": [0.7, 0.7],
                            "top_terms": ["crm", "sync"],
                            "token_count": 2,
                        },
                        "created_at": "2026-01-01T00:00:00Z",
                    }
                ],
            )

            output = _capture_inspect_runs(["--db-path", str(db_path), "--run-id", "embedding_run", "--embeddings"])

        self.assertIn("Embedding Artifacts", output)
        self.assertIn("hashed-text-embedding@v1", output)
        self.assertIn("dims=64", output)

    def test_inspect_runs_cli_shows_resume_chain_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "runs.sqlite3"
            _save_sample_storage_run(db_path, run_id="root_run", source_id="review-1")
            _save_sample_storage_run(db_path, run_id="child_run", source_id="review-2", resume_from_run_id="root_run")

            chain_output = _capture_inspect_runs(["--db-path", str(db_path), "--run-id", "child_run", "--chain"])
            evidence_output = _capture_inspect_runs(
                ["--db-path", str(db_path), "--run-id", "child_run", "--chain", "--evidence", "--limit", "2"]
            )

        self.assertIn("Run Chain", chain_output)
        self.assertIn("run_ids: child_run; root_run", chain_output)
        self.assertIn("resume_links:", chain_output)
        self.assertIn("run=child_run", evidence_output)


class CollectorMappingTests(unittest.TestCase):
    def test_hacker_news_collector_fallbacks_on_timeout(self) -> None:
        config = _fake_config(debug_save_raw=False)

        with patch.object(source1_collector, "_fetch_json_with_retries", side_effect=TimeoutError("timeout")):
            items, diagnostics = source1_collector.collect_discussion_items(config)

        self.assertTrue(diagnostics["fallback_triggered"])
        self.assertEqual(diagnostics["failure_type"], "endpoint_unavailable")
        self.assertGreater(len(items), 0)

    def test_hacker_news_collector_does_not_hide_programming_errors(self) -> None:
        config = _fake_config(debug_save_raw=False)

        with patch.object(source1_collector, "_fetch_json_with_retries", side_effect=RuntimeError("bug")):
            with self.assertRaises(RuntimeError):
                source1_collector.collect_discussion_items(config)

    def test_stackexchange_collector_fallbacks_on_timeout(self) -> None:
        config = _fake_config(debug_save_raw=False)

        with patch.object(source2_collector, "_get_json_with_retries", side_effect=requests.Timeout("timeout")):
            items, diagnostics = source2_collector.collect_review_items(config)

        self.assertTrue(diagnostics["fallback_triggered"])
        self.assertEqual(diagnostics["failure_type"], "endpoint_unavailable")
        self.assertGreater(len(items), 0)

    def test_stackexchange_collector_does_not_hide_programming_errors(self) -> None:
        config = _fake_config(debug_save_raw=False)

        with patch.object(source2_collector, "_get_json_with_retries", side_effect=RuntimeError("bug")):
            with self.assertRaises(RuntimeError):
                source2_collector.collect_review_items(config)

    def test_local_raw_items_diagnostics_counts_sources(self) -> None:
        raw_items = [
            {"source_type": "discussion"},
            {"source_type": "review"},
            {"source_type": "review"},
        ]
        config = _fake_config(raw_items_file="samples/sample.json")

        source1, source2 = _local_file_diagnostics(config, raw_items)

        self.assertEqual(source1["endpoint"], "local_file:samples/sample.json")
        self.assertEqual(source1["live_items_fetched_count"], 1)
        self.assertEqual(source2["live_question_count_fetched"], 2)
        self.assertFalse(source1["fallback_triggered"])

    def test_load_raw_items_reads_json_list(self) -> None:
        data = [{"source_type": "discussion", "source_id": "sample-1"}]

        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "raw_items.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            raw_items = _load_raw_items(str(path))

        self.assertEqual(raw_items, data)

    def test_hacker_news_fetch_retries_transient_failures(self) -> None:
        calls = {"count": 0}

        def flaky_fetch(url: str, timeout: int) -> dict:
            calls["count"] += 1
            if calls["count"] < 3:
                raise TimeoutError("temporary timeout")
            return {"hits": []}

        with patch.object(source1_collector, "_fetch_json", side_effect=flaky_fetch), patch.object(source1_collector.time, "sleep"):
            payload = source1_collector._fetch_json_with_retries("https://example.test", 1)

        self.assertEqual(payload, {"hits": []})
        self.assertEqual(calls["count"], 3)

    def test_hacker_news_paginated_interface_fetches_multiple_pages(self) -> None:
        config = _fake_config(max_discussion_items=101)
        payloads = [
            {
                "hits": [
                    {
                        "objectID": "page-0",
                        "story_id": "100",
                        "story_title": "Workflow discussion",
                        "author": "alice",
                        "created_at": "2026-01-01T00:00:00Z",
                        "comment_text": "Small business workflow pain on page zero.",
                    }
                ],
                "nbPages": 2,
            },
            {
                "hits": [
                    {
                        "objectID": "page-1",
                        "story_id": "101",
                        "story_title": "Workflow discussion",
                        "author": "bob",
                        "created_at": "2026-01-01T00:00:00Z",
                        "comment_text": "Small business workflow pain on page one.",
                    }
                ],
                "nbPages": 2,
            },
        ]

        with patch.object(source1_collector, "_fetch_json_with_retries", side_effect=payloads) as fetch:
            pages = list(source1_collector.iter_discussion_pages(config))

        self.assertEqual([page["page_number"] for page in pages], [0, 1])
        self.assertEqual([page["items"][0]["source_id"] for page in pages], ["page-0", "page-1"])
        self.assertIn("page=0", fetch.call_args_list[0].args[0])
        self.assertIn("page=1", fetch.call_args_list[1].args[0])

    def test_hacker_news_paginated_interface_resumes_from_start_page(self) -> None:
        config = _fake_config(max_discussion_items=1)
        payload = {
            "hits": [
                {
                    "objectID": "page-2",
                    "story_id": "102",
                    "story_title": "Workflow discussion",
                    "author": "alice",
                    "created_at": "2026-01-01T00:00:00Z",
                    "comment_text": "Small business workflow pain on resumed page.",
                }
            ],
            "nbPages": 4,
        }

        with patch.object(source1_collector, "_fetch_json_with_retries", return_value=payload) as fetch:
            pages = list(source1_collector.iter_discussion_pages(config, {"small business workflow pain": 2}))

        self.assertEqual([page["page_number"] for page in pages], [2])
        self.assertIn("page=2", fetch.call_args.args[0])

    def test_hacker_news_paginated_interface_uses_collection_policy(self) -> None:
        config = _fake_config(
            max_discussion_items=100,
            discussion_page_size=25,
            discussion_max_pages_per_query=2,
            discussion_sort="date",
        )
        payload = {
            "hits": [
                {
                    "objectID": "page-item",
                    "story_id": "100",
                    "story_title": "Workflow discussion",
                    "author": "alice",
                    "created_at": "2026-01-01T00:00:00Z",
                    "comment_text": "Small business workflow pain.",
                }
            ],
            "nbPages": 3,
        }

        with patch.object(source1_collector, "_fetch_json_with_retries", return_value=payload) as fetch:
            pages = list(source1_collector.iter_discussion_pages(config))

        self.assertEqual([page["page_number"] for page in pages], [0, 1])
        self.assertIn("search_by_date", fetch.call_args_list[0].args[0])
        self.assertIn("hitsPerPage=25", fetch.call_args_list[0].args[0])

    def test_hacker_news_collector_records_page_diagnostics(self) -> None:
        config = _fake_config(max_discussion_items=1, debug_save_raw=False)
        payload = {
            "hits": [
                {
                    "objectID": "page-0",
                    "story_id": "100",
                    "story_title": "Workflow discussion",
                    "author": "alice",
                    "created_at": "2026-01-01T00:00:00Z",
                    "comment_text": "Small business workflow pain on page zero.",
                }
            ],
            "nbPages": 1,
        }

        with patch.object(source1_collector, "_fetch_json_with_retries", return_value=payload):
            items, diagnostics = source1_collector.collect_discussion_items(config)

        self.assertEqual(len(items), 1)
        self.assertEqual(diagnostics["collected_pages"][0]["page_number"], 0)
        self.assertEqual(diagnostics["collected_pages"][0]["raw_count"], 1)
        self.assertEqual(diagnostics["collected_pages"][0]["item_count"], 1)

    def test_stackexchange_paginated_interface_fetches_multiple_pages(self) -> None:
        config = _fake_config(max_review_items=101)
        payloads = [
            {
                "items": [
                    {
                        "question_id": 100,
                        "title": "CRM API integration problem",
                        "body": "<p>Our CRM API setup fails.</p>",
                        "link": "https://stackoverflow.com/questions/100",
                        "owner": {"display_name": "alice"},
                        "tags": ["crm", "api"],
                        "score": 1,
                        "creation_date": 1767225600,
                    }
                ],
                "has_more": True,
            },
            {
                "items": [
                    {
                        "question_id": 101,
                        "title": "Workflow automation integration",
                        "body": "<p>Our workflow automation setup fails.</p>",
                        "link": "https://stackoverflow.com/questions/101",
                        "owner": {"display_name": "bob"},
                        "tags": ["automation"],
                        "score": 2,
                        "creation_date": 1767225600,
                    }
                ],
                "has_more": False,
            },
        ]

        with patch.object(source2_collector, "_get_json_with_retries", side_effect=payloads) as fetch:
            pages = list(source2_collector.iter_review_pages(config))

        self.assertEqual([page["page_number"] for page in pages], [1, 2])
        self.assertEqual([page["items"][0]["source_id"] for page in pages], ["100", "101"])
        self.assertEqual(fetch.call_args_list[0].args[2]["page"], 1)
        self.assertEqual(fetch.call_args_list[1].args[2]["page"], 2)

    def test_stackexchange_paginated_interface_resumes_from_start_page(self) -> None:
        config = _fake_config(max_review_items=1)
        payload = {
            "items": [
                {
                    "question_id": 102,
                    "title": "Workflow automation integration",
                    "body": "<p>Our workflow automation setup still fails.</p>",
                    "link": "https://stackoverflow.com/questions/102",
                    "owner": {"display_name": "alice"},
                    "tags": ["automation"],
                    "score": 1,
                    "creation_date": 1767225600,
                }
            ],
            "has_more": True,
        }

        with patch.object(source2_collector, "_get_json_with_retries", return_value=payload) as fetch:
            pages = list(source2_collector.iter_review_pages(config, {"crm api integration problem": 3}))

        self.assertEqual([page["page_number"] for page in pages], [3])
        self.assertEqual(fetch.call_args.args[2]["page"], 3)

    def test_stackexchange_paginated_interface_uses_collection_policy(self) -> None:
        config = _fake_config(
            max_review_items=100,
            review_page_size=25,
            review_max_pages_per_query=2,
            review_sort="creation",
            review_order="asc",
        )
        payload = {
            "items": [
                {
                    "question_id": 100,
                    "title": "CRM API integration problem",
                    "body": "<p>Our CRM API setup fails.</p>",
                    "link": "https://stackoverflow.com/questions/100",
                    "owner": {"display_name": "alice"},
                    "tags": ["crm", "api"],
                    "score": 1,
                    "creation_date": 1767225600,
                }
            ],
            "has_more": True,
        }

        with patch.object(source2_collector, "_get_json_with_retries", return_value=payload) as fetch:
            pages = list(source2_collector.iter_review_pages(config))

        self.assertEqual([page["page_number"] for page in pages], [1, 2])
        self.assertEqual(fetch.call_args_list[0].args[2]["pagesize"], 25)
        self.assertEqual(fetch.call_args_list[0].args[2]["sort"], "creation")
        self.assertEqual(fetch.call_args_list[0].args[2]["order"], "asc")

    def test_stackexchange_collector_records_page_diagnostics(self) -> None:
        config = _fake_config(max_review_items=1, debug_save_raw=False)
        payload = {
            "items": [
                {
                    "question_id": 100,
                    "title": "CRM API integration problem",
                    "body": "<p>Our CRM API setup fails.</p>",
                    "link": "https://stackoverflow.com/questions/100",
                    "owner": {"display_name": "alice"},
                    "tags": ["crm", "api"],
                    "score": 1,
                    "creation_date": 1767225600,
                }
            ],
            "has_more": False,
        }

        with patch.object(source2_collector, "_get_json_with_retries", return_value=payload):
            items, diagnostics = source2_collector.collect_review_items(config)

        self.assertEqual(len(items), 1)
        self.assertEqual(diagnostics["collected_pages"][0]["page_number"], 1)
        self.assertEqual(diagnostics["collected_pages"][0]["raw_count"], 1)
        self.assertEqual(diagnostics["collected_pages"][0]["item_count"], 1)

    def test_maps_hacker_news_hit_to_raw_item_shape(self) -> None:
        item = _map_hn_hit(
            {
                "objectID": "123",
                "story_id": "456",
                "story_title": "Workflow discussion",
                "author": "alice",
                "created_at": "2026-01-01T00:00:00Z",
                "comment_text": "<p>Small business workflow pain</p>",
            },
            "AI operations tools",
            "small business workflow pain",
        )

        self.assertEqual(item["source_type"], "discussion")
        self.assertEqual(item["source_id"], "123")
        self.assertEqual(item["source_url"], "https://news.ycombinator.com/item?id=456")
        self.assertFalse(item["is_demo_fallback"])

    def test_maps_stackoverflow_question_to_raw_item_shape(self) -> None:
        item = _map_stackoverflow_question(
            {
                "question_id": 789,
                "title": "CRM API integration problem",
                "body": "<p>Our CRM API setup fails for customer sync.</p>",
                "link": "https://stackoverflow.com/questions/789",
                "owner": {"display_name": "bob"},
                "tags": ["crm", "api"],
                "score": 2,
                "creation_date": 1767225600,
            },
            "crm api integration problem",
            _fake_config(),
        )

        self.assertEqual(item["source_type"], "review")
        self.assertEqual(item["source_id"], "789")
        self.assertEqual(item["reviewed_product"], "crm, api")
        self.assertIn("Our CRM API setup fails", item["text"])


def _fake_config(
    raw_items_file: str = "",
    debug_save_raw: bool = True,
    max_discussion_items: int = 50,
    max_review_items: int = 50,
    resume_from_run_id: str = "",
    sqlite_path: Path | None = None,
    processing_batch_size: int = 500,
    enable_discussion_source: bool = True,
    enable_review_source: bool = True,
    discussion_page_size: int = 0,
    discussion_max_pages_per_query: int = 0,
    discussion_sort: str = "relevance",
    review_page_size: int = 0,
    review_max_pages_per_query: int = 0,
    review_sort: str = "activity",
    review_order: str = "desc",
    embedding_backend: str = "hashing",
    embedding_model: str = "",
    cluster_similarity_threshold: float = 0.12,
) -> SimpleNamespace:
    return SimpleNamespace(
        project_title="AI-Assisted Community Signal Pipeline for Early-Stage Venture Evaluation",
        product_theme="AI-enabled tools for small-business operations, lean teams, and one-person companies",
        community_query="small business workflow pain",
        community_queries=["small business workflow pain"],
        stackexchange_site="stackoverflow",
        stackexchange_query="crm api integration problem",
        stackexchange_queries=["crm api integration problem"],
        max_discussion_items=max_discussion_items,
        max_review_items=max_review_items,
        request_timeout=25,
        processing_batch_size=processing_batch_size,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model,
        cluster_similarity_threshold=cluster_similarity_threshold,
        enable_discussion_source=enable_discussion_source,
        enable_review_source=enable_review_source,
        discussion_page_size=discussion_page_size,
        discussion_max_pages_per_query=discussion_max_pages_per_query,
        discussion_sort=discussion_sort,
        review_page_size=review_page_size,
        review_max_pages_per_query=review_max_pages_per_query,
        review_sort=review_sort,
        review_order=review_order,
        debug_save_raw=debug_save_raw,
        raw_items_file=raw_items_file,
        resume_from_run_id=resume_from_run_id,
        raw_dir=ROOT_DIR / "data" / "raw",
        sqlite_path=sqlite_path or ROOT_DIR / "data" / "storage" / "pipeline_runs.sqlite3",
    )


def _save_sample_storage_run(
    db_path: Path,
    run_id: str = "query_run",
    source_id: str = "review-1",
    resume_from_run_id: str = "",
) -> None:
    config = _fake_config(debug_save_raw=False, resume_from_run_id=resume_from_run_id)
    raw_items = [
        {
            "source_type": "review",
            "source_name": "fixture",
            "source_id": source_id,
            "source_url": "https://example.test/review",
            "title": "CRM API integration problem",
            "text": (
                "We use a CRM for customers, but the API integration fails during setup. "
                "Our small team still has to fix customer records manually."
            ),
            "rating": "1",
        }
    ]
    candidate_items, excluded_items, filtering_summary = filter_quality_items(raw_items)
    prepared_items, relevance_excluded_items = prepare_items(candidate_items)
    relevance_summary = RelevanceSummary(
        evidence_candidates_after_quality_filter=len(candidate_items),
        evidence_candidates_after_relevance_filter=len(prepared_items),
        relevance_filtered_items=len(relevance_excluded_items),
    ).to_dict()
    analysis = analyze_venture_signals(prepared_items, config, run_id, filtering_summary, relevance_summary)
    collector_diagnostics = {
        "source1": {
            "source": "source1_discussion",
            "fallback_triggered": False,
            "collected_pages": [
                {
                    "source": "source1_discussion",
                    "query": "small business workflow pain",
                    "page_number": 0,
                    "request_url": "https://example.test/hn?page=0",
                    "request_params": {},
                    "raw_count": 1,
                    "item_count": 1,
                    "has_more": False,
                }
            ],
        },
        "source2": {"source": "source2_stackoverflow_questions", "fallback_triggered": False},
    }
    save_run_to_sqlite(
        db_path,
        run_id,
        analysis,
        collector_diagnostics,
        raw_items,
        prepared_items,
        excluded_items,
        relevance_excluded_items,
    )


def _capture_inspect_runs(argv: list[str]) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        inspect_runs_main(argv)
    return buffer.getvalue()


if __name__ == "__main__":
    unittest.main()
