from django import template

register = template.Library()

@register.simple_tag
def average_score(submissions):
    scores = [float(s.final_score) for s in submissions if s.final_score is not None]
    if not scores:
        return '—'
    return f"{sum(scores)/len(scores):.1f}"

@register.simple_tag
def best_score(submissions):
    scores = [float(s.final_score) for s in submissions if s.final_score is not None]
    if not scores:
        return '—'
    return f"{max(scores):.1f}"

@register.filter
def get_item(dictionary, key):
    """Allows dict[key] lookups in templates."""
    return dictionary.get(key)
