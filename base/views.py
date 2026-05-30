from rest_framework.views import APIView

from base.pagination import CustomPagination
from base.responses import error_response, success_response


class BaseAPIView(APIView):
    def success(self, data=None, message="Success", status=200):
        return success_response(data=data, message=message, status=status)

    def error(self, message="An error occurred", errors=None, status=400):
        return error_response(message=message, errors=errors, status=status)

    def paginate_list(self, request, items):
        paginator = CustomPagination()
        page = paginator.paginate_queryset(items, request, view=self)
        if page is None:
            return None
        return paginator, page

    def paginated_content(self, request, items, **extra_content):
        paginated = self.paginate_list(request, items)
        if not paginated:
            content = dict(extra_content)
            content["results"] = items
            return content
        paginator, page = paginated
        page_data = paginator.get_paginated_response(page).data
        content = dict(extra_content)
        content["pagination"] = page_data["pagination"]
        content["results"] = page_data["results"]
        return content
