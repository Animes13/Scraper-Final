# core/detector.py

class BreakDetector:

    @staticmethod
    def empty_list(data):
        return not data or len(data) == 0

    @staticmethod
    def missing_keys(data, keys):
        if not isinstance(data, dict):
            return True

        for k in keys:
            if k not in data or not data[k]:
                return True
        return False

    @staticmethod
    def invalid_episodes(episodes):
        if not episodes:
            return True

        for ep in episodes:
            if "episodio" not in ep and "ep" not in ep:
                return True
        return False

    @staticmethod
    def invalid_url(url):
        if not url:
            return True

        if not isinstance(url, str):
            return True

        return not url.startswith("http")

    @staticmethod
    def should_trigger_ai(context, result):
        """
        context:
            anime_list
            anime_page
            episode_page
        """
        if context == "anime_list":
            return BreakDetector.empty_list(result)

        if context == "anime_page":
            return BreakDetector.invalid_episodes(result)

        if context == "episode_page":
            return BreakDetector.invalid_url(result)

        return False