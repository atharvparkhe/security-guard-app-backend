from django.conf import settings
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPagination(PageNumberPagination):
    page_size = settings.REST_FRAMEWORK.get("PAGE_SIZE", 10)
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response(
            {
                "pagination": {
                    "previous_page": (
                        self.page.previous_page_number()
                        if self.page.has_previous()
                        else None
                    ),
                    "is_previous_page": self.page.has_previous(),
                    "next_page": (
                        self.page.next_page_number() if self.page.has_next() else None
                    ),
                    "is_next_page": self.page.has_next(),
                    "start_index": self.page.start_index(),
                    "end_index": self.page.end_index(),
                    "total_entries": self.page.paginator.count,
                    "total_pages": self.page.paginator.num_pages,
                    "page": self.page.number,
                },
                "results": data,
            }
        )
