import re
from app.services.shortener import generate_slug


def test_slug_length():
    assert len(generate_slug()) == 7


def test_slug_default_length_is_7():
    for _ in range(20):
        assert len(generate_slug()) == 7


def test_slug_is_alphanumeric():
    for _ in range(20):
        assert re.match(r"^[A-Za-z0-9]+$", generate_slug())


def test_slugs_are_unique():
    slugs = {generate_slug() for _ in range(100)}
    # With 62^7 possibilities, 100 draws should virtually never collide
    assert len(slugs) > 95


def test_custom_length():
    assert len(generate_slug(length=10)) == 10


def test_slug_contains_no_special_characters():
    slug = generate_slug()
    assert slug == slug.replace("-", "").replace("_", "")