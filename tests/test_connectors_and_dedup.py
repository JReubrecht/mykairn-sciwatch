"""
Tests des parseurs multi-sources (PubMed XML, OpenAlex Inverted Index, RSS) et du moteur de dédoublonnage.
"""

from __future__ import annotations

import unittest

from mykairn_sciwatch.connectors.aggregator import deduplicate_publications
from mykairn_sciwatch.connectors.base import normalize_doi, normalize_title_key
from mykairn_sciwatch.connectors.crossref_rss import CrossrefRssConnector
from mykairn_sciwatch.connectors.openalex import parse_openalex_work, reconstruct_abstract
from mykairn_sciwatch.connectors.pubmed import parse_pubmed_xml
from mykairn_sciwatch.models import RawPublication


SAMPLE_PUBMED_XML = """<?xml version="1.0" ?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>38123456</PMID>
      <Article>
        <Journal>
          <Title>Sports Medicine</Title>
          <JournalIssue>
            <PubDate><Year>2025</Year><Month>Mar</Month><Day>15</Day></PubDate>
          </JournalIssue>
        </Journal>
        <ArticleTitle>Training Intensity Distribution and Pacing in Recreational and Elite Trail Runners: A Systematic Review and Meta-Analysis.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Trail running requires specific uphill and downhill adaptations.</AbstractText>
          <AbstractText Label="METHODS">We included n = 420 trail runners across 18 studies (PRISMA).</AbstractText>
          <AbstractText Label="CONCLUSIONS">Polarized and pyramidal training load significantly improved performance (p &lt; 0.01).</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Millet</LastName><Initials>GP</Initials></Author>
          <Author><LastName>Giovanelli</LastName><Initials>N</Initials></Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Meta-Analysis</PublicationType>
          <PublicationType>Systematic Review</PublicationType>
        </PublicationTypeList>
      </Article>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Running</DescriptorName></MeshHeading>
        <MeshHeading><DescriptorName>Physical Endurance</DescriptorName></MeshHeading>
      </MeshHeadingList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">38123456</ArticleId>
        <ArticleId IdType="doi">10.1007/s40279-025-01999-x</ArticleId>
        <ArticleId IdType="pmc">PMC1099999</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


class TestConnectorsAndDedup(unittest.TestCase):
    def test_normalize_doi_and_title(self) -> None:
        self.assertEqual(
            normalize_doi("https://doi.org/10.1007/S40279-025-01999-X"),
            "10.1007/s40279-025-01999-x",
        )
        self.assertIsNone(normalize_doi("invalid_doi"))
        self.assertEqual(
            normalize_title_key("Trail-Running: A Meta-Analysis!"),
            normalize_title_key("trail running a meta analysis"),
        )

    def test_parse_pubmed_xml(self) -> None:
        pubs = parse_pubmed_xml(SAMPLE_PUBMED_XML, query_matched="trail running")
        self.assertEqual(len(pubs), 1)
        p = pubs[0]
        self.assertEqual(p.pmid, "38123456")
        self.assertEqual(p.doi, "10.1007/s40279-025-01999-x")
        self.assertEqual(p.publication_date, "2025-03-15")
        self.assertTrue(p.is_open_access)
        self.assertIn("Meta-Analysis", p.raw_publication_types)
        self.assertIn("n = 420", p.abstract)

    def test_reconstruct_openalex_abstract_and_work(self) -> None:
        inv = {"Trail": [0], "running": [1], "improves": [2], "durability.": [3]}
        self.assertEqual(reconstruct_abstract(inv), "Trail running improves durability.")

        work = {
            "id": "https://openalex.org/W12345",
            "doi": "https://doi.org/10.1007/s40279-025-01999-x",
            "title": "Training Intensity Distribution and Pacing in Recreational and Elite Trail Runners",
            "publication_date": "2025-03-15",
            "publication_year": 2025,
            "cited_by_count": 64,
            "abstract_inverted_index": inv,
            "primary_location": {"source": {"display_name": "Sports Medicine"}},
            "open_access": {"is_oa": True, "oa_url": "https://example.org/paper.pdf"},
        }
        parsed = parse_openalex_work(work)
        self.assertIsNotNone(parsed)
        assert parsed is not None
        self.assertEqual(parsed.citation_count, 64)
        self.assertEqual(parsed.doi, "10.1007/s40279-025-01999-x")

    def test_multi_source_deduplication_merges_metadata(self) -> None:
        pm_pub = parse_pubmed_xml(SAMPLE_PUBMED_XML)[0]
        oa_pub = RawPublication(
            source="openalex",
            external_id="openalex:W12345",
            title=pm_pub.title,
            abstract="Short abstract",
            journal="Sports Medicine",
            publication_date="2025-03-15",
            publication_year=2025,
            doi="10.1007/s40279-025-01999-x",
            citation_count=78,
            concepts=["Biomechanics", "Endurance"],
        )
        s2_pub = RawPublication(
            source="semantic_scholar",
            external_id="s2:999",
            title=pm_pub.title,
            abstract="",
            publication_year=2025,
            doi="10.1007/s40279-025-01999-x",
            citation_count=72,
            influential_citation_count=12,
        )
        merged = deduplicate_publications([pm_pub, oa_pub, s2_pub])
        self.assertEqual(len(merged), 1)
        rec = merged[0]
        self.assertEqual(set(rec.sources), {"pubmed", "openalex", "semantic_scholar"})
        self.assertEqual(rec.raw.citation_count, 78)
        self.assertEqual(rec.raw.influential_citation_count, 12)
        self.assertIn("Running", rec.raw.mesh_terms)
        self.assertIn("Biomechanics", rec.raw.concepts)

    def test_parse_rss_xml(self) -> None:
        rss_xml = """<?xml version="1.0" encoding="UTF-8" ?>
        <rss version="2.0"><channel>
          <item>
            <title>Downhill Running Biomechanics and Muscle Damage</title>
            <link>https://doi.org/10.1123/ijspp.2025-0100</link>
            <description>Eccentric load and poles usage in trail runners.</description>
          </item>
        </channel></rss>"""
        items = CrossrefRssConnector.parse_rss_xml(rss_xml, journal_fallback="IJSPP")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].doi, "10.1123/ijspp.2025-0100")


if __name__ == "__main__":
    unittest.main()
