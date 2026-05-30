from django.utils import timezone


def resolve_gate_time(value):
    if value is None:
        return timezone.now()
    if timezone.is_naive(value):
        return timezone.make_aware(value)
    return value
