"""Main navigation, declared as data.

Each module appends its own entry when its URLs are registered. Keeping the
navbar out of the template means every task can render base.html with only the
URL names that already exist.
"""

# (url_name, Spanish label, emphasised)
NAV_ITEMS = []


def register(url_name, label, emphasised=False):
    """Add a module to the navigation bar, ignoring duplicate registration."""
    entry = (url_name, label, emphasised)
    if entry not in NAV_ITEMS:
        NAV_ITEMS.append(entry)
