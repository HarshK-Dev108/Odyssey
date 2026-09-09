from app.data.travel_data import TRAVEL_OPTIONS


class TourismRetriever:
    """Small deterministic retriever for static catalog knowledge.

    Live MongoDB/API data remains authoritative for prices and availability;
    this retriever only serves descriptive fallback knowledge.
    """

    def __init__(self, documents=None):
        self.documents = documents or self._build_documents()

    @staticmethod
    def _build_documents():
        documents = []
        for destination, options in TRAVEL_OPTIONS.items():
            for option in options:
                documents.append({
                    "destination": destination,
                    "title": option.get("name", "Travel option"),
                    "text": (
                        f"{option.get('name', 'Travel option')} is a "
                        f"{option.get('type', 'travel')} option in {destination}. "
                        f"Interests: {', '.join(option.get('interests', []))}."
                    ),
                })
        return documents

    def search(self, query: str, destination: str | None = None, limit: int = 5):
        terms = {term.casefold() for term in query.split() if term.strip()}
        destination_key = destination.casefold() if destination else None
        scored = []
        for document in self.documents:
            if destination_key and document["destination"].casefold() != destination_key:
                continue
            haystack = f"{document['title']} {document['text']}".casefold()
            score = sum(term in haystack for term in terms)
            if score:
                scored.append((score, document))
        scored.sort(key=lambda item: (-item[0], item[1]["title"]))
        return [document for _, document in scored[:limit]]