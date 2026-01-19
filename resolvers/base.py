# resolvers/base.py
class BaseResolver:
    domains = []

    def can_resolve(self, url):
        return any(d in url for d in self.domains)

    def resolve(self, url):
        raise NotImplementedError