"""
core/middleware.py
"""
from django.utils.deprecation import MiddlewareMixin


class BlurHashMiddleware(MiddlewareMixin):
    """Placeholder middleware — reserves the hook for future blurhash
    image processing. Currently a no-op so the pipeline is ready."""

    def process_request(self, request):
        return None
