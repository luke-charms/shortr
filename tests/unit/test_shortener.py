import re
from app.services.shortener import generate_slug
from app.services import shortener

def test_slug_length():
    slug = generate_slug()
    assert len(slug) == 7

def test_slug_is_alphanumeric():
    slug = generate_slug()
    assert re.match(r"^[A-Za-z0-9]+$", slug)

def test_slugs_are_unique():
    assert generate_slug() != generate_slug()

def test_slug_collision_handled(monkeypatch):

    monkeypatch.setattr(shortener, "generate_slug", lambda: "fixedslug")

    slug1 = shortener.generate_slug()
    slug2 = shortener.generate_slug()

    assert slug1 == slug2