import re
from app.services.shortener import generate_slug

def test_slug_length():
    slug = generate_slug()
    assert len(slug) == 7

def test_slug_is_alphanumeric():
    slug = generate_slug()
    assert re.match(r"^[A-Za-z0-9]+$", slug)

def test_slugs_are_unique():
    assert generate_slug() != generate_slug()