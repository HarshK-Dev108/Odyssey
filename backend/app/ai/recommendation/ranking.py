def rank_recommendations(recommendations):
    """
    Sort recommendations from highest score to lowest score.
    """

    return sorted(
        recommendations,
        key=lambda item: item.get("score", 0),
        reverse=True
    )