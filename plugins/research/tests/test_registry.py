from ai_paper_search.registry import VenueRegistry


def test_core_mas_does_not_silently_include_nlp_secondary():
    registry = VenueRegistry.load()
    selected = registry.selected([2024], include_nlp=False)
    names = {venue.name for venue, _year, _source in selected}
    assert names == {"NeurIPS", "ICML", "ICLR", "AAAI", "IJCAI", "AAMAS"}


def test_nlp_profile_includes_findings():
    registry = VenueRegistry.load()
    selected = registry.selected([2024], include_nlp=True)
    names = {venue.name for venue, _year, _source in selected}
    assert {"ACL", "EMNLP", "ACL Findings", "EMNLP Findings"} <= names
