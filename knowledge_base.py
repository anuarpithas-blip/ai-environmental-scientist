from pathlib import Path
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


class KnowledgeBase:
    """
    Local environmental knowledge base.

    Uses TF-IDF retrieval with source-aware reranking.

    Supported knowledge:
    - Darukaa.Earth challenge knowledge
    - Environmental reasoning entries
    - Scientific / FAO sources
    - Future research papers, reports and datasets
    """

    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)

        self.documents = []
        self.sources = []
        self.source_types = []

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True
        )

        self.matrix = None

        self.load()

    # ---------------------------------------------------------
    # SOURCE DETECTION
    # ---------------------------------------------------------

    def _detect_source_type(self, source_name, text):

        combined = f"{source_name} {text}".lower()

        if (
            "darukaa.earth" in combined
            or "challenge requirement" in combined
            or "example from the challenge" in combined
        ):
            return "challenge"

        if (
            "food and agriculture organization" in combined
            or "fao" in combined
            or "scientific grounding" in combined
            or "research paper" in combined
            or "research report" in combined
            or "environmental dataset" in combined
        ):
            return "scientific"

        return "knowledge"

    # ---------------------------------------------------------
    # CHUNKING
    # ---------------------------------------------------------

    def _chunk(self, text, source):

        text = (
            text
            .replace("\r\n", "\n")
            .replace("\r", "\n")
            .strip()
        )

        if not text:
            return []

        sections = re.split(
            r"\n(?=[A-Z][A-Z0-9 /↔&(),.:%:-]{3,}\n)",
            text
        )

        chunks = []

        for section in sections:

            section = section.strip()

            if len(section) < 80:
                continue

            words = section.split()

            for i in range(0, len(words), 180):

                part = " ".join(
                    words[i:i + 180]
                ).strip()

                if len(part) >= 80:
                    chunks.append(
                        (part, source)
                    )

        # Fallback
        if not chunks and len(text) >= 80:

            words = text.split()

            for i in range(0, len(words), 180):

                part = " ".join(
                    words[i:i + 180]
                ).strip()

                if len(part) >= 80:
                    chunks.append(
                        (part, source)
                    )

        return chunks

    # ---------------------------------------------------------
    # LOAD KNOWLEDGE
    # ---------------------------------------------------------

    def load(self):

        self.documents = []
        self.sources = []
        self.source_types = []

        if not self.data_dir.exists():
            return

        for path in sorted(
            self.data_dir.rglob("*.txt")
        ):

            try:

                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

            except Exception:

                continue

            source_name = path.name

            source_type = self._detect_source_type(
                source_name,
                text
            )

            chunks = self._chunk(
                text,
                source_name
            )

            for chunk, source in chunks:

                self.documents.append(chunk)
                self.sources.append(source)
                self.source_types.append(
                    source_type
                )

        if self.documents:

            self.matrix = (
                self.vectorizer
                .fit_transform(self.documents)
            )

    # ---------------------------------------------------------
    # ENVIRONMENTAL TERM DETECTION
    # ---------------------------------------------------------

    def _environmental_terms(self, query):

        q = query.lower()

        groups = {

            "soil": [
                "soil",
                "soil organic carbon",
                "organic carbon",
                "organic matter",
                "soil health",
                "soil moisture",
                "soil ph"
            ],

            "water": [
                "rainfall",
                "rain",
                "water",
                "moisture",
                "water availability"
            ],

            "biodiversity": [
                "biodiversity",
                "species",
                "species richness",
                "habitat",
                "habitat diversity"
            ],

            "land": [
                "land use",
                "land cover",
                "crop",
                "monoculture",
                "agriculture",
                "fragmentation"
            ],

            "climate": [
                "temperature",
                "rainfall",
                "climate",
                "semi-arid"
            ],

            "impact": [
                "pollution",
                "deforestation",
                "human impact",
                "agricultural pressure"
            ]
        }

        detected = set()

        for group, terms in groups.items():

            for term in terms:

                if term in q:

                    detected.add(group)
                    break

        return detected

    # ---------------------------------------------------------
    # SOURCE RELEVANCE
    # ---------------------------------------------------------

    def _source_relevance(
        self,
        query,
        document,
        source,
        source_type
    ):

        q = query.lower()
        d = document.lower()

        detected_groups = self._environmental_terms(
            query
        )

        bonus = 0.0

        # -----------------------------------------------------
        # Scientific source bonus
        # -----------------------------------------------------

        if source_type == "scientific":

            # Scientific evidence gets a small priority,
            # but only when it is environmentally relevant.
            relevant = False

            for term in [
                "soil",
                "organic carbon",
                "organic matter",
                "biodiversity",
                "agroforestry",
                "cover crops",
                "water",
                "land use",
                "habitat"
            ]:

                if term in q and term in d:

                    relevant = True
                    break

            if relevant:

                bonus += 0.18

        # -----------------------------------------------------
        # Specific FAO soil/biodiversity source
        # -----------------------------------------------------

        if (
            source == "04_scientific_soil_biodiversity.txt"
            and (
                "soil" in q
                or "organic carbon" in q
                or "biodiversity" in q
                or "agroforestry" in q
                or "wheat" in q
            )
        ):

            bonus += 0.12

        # -----------------------------------------------------
        # Soil relevance
        # -----------------------------------------------------

        if "soil" in detected_groups:

            if any(
                term in d
                for term in [
                    "soil",
                    "organic carbon",
                    "organic matter",
                    "soil health"
                ]
            ):

                bonus += 0.06

        # -----------------------------------------------------
        # Biodiversity relevance
        # -----------------------------------------------------

        if "biodiversity" in detected_groups:

            if any(
                term in d
                for term in [
                    "biodiversity",
                    "species richness",
                    "habitat diversity",
                    "species"
                ]
            ):

                bonus += 0.06

        # -----------------------------------------------------
        # Water relevance
        # -----------------------------------------------------

        if "water" in detected_groups:

            if any(
                term in d
                for term in [
                    "rainfall",
                    "water",
                    "moisture",
                    "water availability"
                ]
            ):

                bonus += 0.05

        # -----------------------------------------------------
        # Land relevance
        # -----------------------------------------------------

        if "land" in detected_groups:

            if any(
                term in d
                for term in [
                    "land use",
                    "land cover",
                    "crop",
                    "monoculture",
                    "habitat",
                    "fragmentation"
                ]
            ):

                bonus += 0.05

        return bonus

    # ---------------------------------------------------------
    # SEARCH
    # ---------------------------------------------------------

    def search(self, query, k=4):

        if (
            not self.documents
            or self.matrix is None
        ):
            return []

        if not query or not query.strip():
            return []

        q_vector = self.vectorizer.transform(
            [query]
        )

        similarity_scores = cosine_similarity(
            q_vector,
            self.matrix
        )[0]

        # -----------------------------------------------------
        # Build candidate pool
        # -----------------------------------------------------

        candidate_count = min(
            max(k * 6, 24),
            len(self.documents)
        )

        indices = (
            similarity_scores
            .argsort()[::-1][:candidate_count]
        )

        candidates = []

        for index in indices:

            base_score = float(
                similarity_scores[index]
            )

            if base_score <= 0:
                continue

            source = self.sources[index]
            source_type = self.source_types[index]
            document = self.documents[index]

            bonus = self._source_relevance(
                query,
                document,
                source,
                source_type
            )

            final_score = base_score + bonus

            candidates.append({

                "index": int(index),

                "text": document,

                "source": source,

                "source_type": source_type,

                "score": final_score,

                "base_score": base_score
            })

        if not candidates:
            return []

        # -----------------------------------------------------
        # Sort by adjusted relevance
        # -----------------------------------------------------

        candidates.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        # -----------------------------------------------------
        # Source-diverse selection
        # -----------------------------------------------------

        selected = []

        used_sources = set()

        for item in candidates:

            if len(selected) >= k:
                break

            source = item["source"]

            if source in used_sources:
                continue

            selected.append(item)

            used_sources.add(source)

        # -----------------------------------------------------
        # Fill remaining slots
        # -----------------------------------------------------

        if len(selected) < k:

            for item in candidates:

                if len(selected) >= k:
                    break

                if item["source"] in {
                    x["source"]
                    for x in selected
                }:
                    continue

                selected.append(item)

        # -----------------------------------------------------
        # Final output
        # -----------------------------------------------------

        selected.sort(
            key=lambda x: x["score"],
            reverse=True
        )

        return [

            {
                "text": item["text"],

                "source": item["source"],

                "source_type": item["source_type"],

                "score": float(
                    item["score"]
                )
            }

            for item in selected
        ]