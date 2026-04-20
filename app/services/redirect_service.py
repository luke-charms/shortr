class RedirectService:
    def __init__(self, repo, cache):
        self.repo = repo
        self.cache = cache

    async def get_original_url(self, slug: str) -> str:
        # 1. Try cache
        cached = await self.cache.get_url(slug)
        if cached:
            return cached

        # 2. DB lookup
        link = await self.repo.get_by_slug(slug)
        if not link:
            return None

        # 3. Store in cache
        await self.cache.set_url(slug, link.original_url)

        return link.original_url