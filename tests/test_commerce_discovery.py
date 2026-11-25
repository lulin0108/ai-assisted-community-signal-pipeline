import unittest
from unittest.mock import patch

from commerce.discovery import DiscoveryError, build_queries, discover, normalize_result
from commerce.server import validate_request


def row(url, title="A listing", description=""):
    return {"url": url, "title": title, "description": description}


class CommerceDiscoveryTests(unittest.TestCase):
    def test_chinese_query_expansion_keeps_original_context(self):
        queries = build_queries("想找适合小空间的宠物喂食区防溅商品")
        self.assertIn("pet feeding station splash guard", queries[0]["query"])
        self.assertIn("小空间", queries[-1]["query"])
        self.assertEqual(len(queries), 4)
        self.assertEqual(len(build_queries("pet bowl")), 3)

    def test_classifies_product_and_review_links_and_strips_markup(self):
        product = normalize_result(row("https://www.amazon.com/a-title/dp/B000ABC123?tag=x", "<b>Pet bowl</b>"))
        review = normalize_result(row("https://www.chewy.com/pet-bowl/product-reviews/51"))
        self.assertEqual(product["kind"], "product")
        self.assertEqual(product["title"], "Pet bowl")
        self.assertEqual(product["url"], "https://amazon.com/dp/B000ABC123")
        self.assertEqual(review["kind"], "feedback")
        self.assertIsNone(normalize_result(row("https://old.reddit.com/r/pets")))
        self.assertIsNone(normalize_result(row("javascript:alert(1)")))

    @patch("commerce.discovery.fetch_results")
    def test_aggregates_leads_without_inflating_pain_counts(self, fetch):
        fetch.side_effect = [
            [row("https://www.store.example/products/bowl?utm_source=x")],
            [row("https://reviews.example/reviews/bowl", description="I bought one. It is hard to clean but has no leaks.")],
            [row("https://store.example/products/bowl"), row("https://blog.example/roundup", "10 best bowls")],
        ]
        result = discover("pet bowl", "US", "secret")
        self.assertEqual(result["state"], "ok")
        self.assertEqual(len(result["groups"]["product"]), 1)
        self.assertEqual(len(result["groups"]["reference"]), 1)
        self.assertEqual(result["themes"], [{"id": "cleanup", "urls": ["https://reviews.example/reviews/bowl"]}])
        self.assertEqual(len(result["searches"]), 3)
        self.assertNotIn("secret", repr(result))

    @patch("commerce.discovery.fetch_results")
    def test_keeps_partial_results_and_stops_after_quota(self, fetch):
        fetch.side_effect = [DiscoveryError("timeout"), [row("https://shop.example/products/item")], DiscoveryError("quota")]
        result = discover("宠物喂食", "CA", "test")
        self.assertEqual(result["state"], "partial")
        self.assertEqual(len(result["groups"]["product"]), 1)
        self.assertEqual(fetch.call_count, 3)
        self.assertEqual(result["searches"][-1]["error"], "quota")

    @patch("commerce.discovery.fetch_results", return_value=[])
    def test_no_results_are_reported_as_empty(self, _fetch):
        result = discover("pet bowl", "GB", "test")
        self.assertEqual(result["state"], "empty")
        self.assertFalse(result["themes"])

    def test_request_validation(self):
        self.assertEqual(validate_request({"scene": " pet feeding ", "market": "US"}), ("pet feeding", "US", ""))
        for payload in [[], {"scene": "", "market": "US"}, {"scene": "pet bowl", "market": ["US"]}]:
            with self.assertRaises(ValueError):
                validate_request(payload)


if __name__ == "__main__":
    unittest.main()
