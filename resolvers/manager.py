from resolvers.blogger import BloggerResolver
from resolvers.googlevideo import GoogleVideoResolver


class ResolverManager:

    def __init__(self):
        self.resolvers = [
            BloggerResolver(),
            GoogleVideoResolver()
        ]

    def resolve(self, player):
        """
        player: dict {
            url: str,
            type: str,
            source: str
        }
        """
        if not isinstance(player, dict):
            return []

        url = player.get("url")
        if not url:
            return []

        for r in self.resolvers:
            if r.can_resolve(url):
                return r.resolve(url)

        return []