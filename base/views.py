from rest_framework.views import APIView

from base.responses import error_response, success_response


class BaseAPIView(APIView):
    def success(self, data=None, message="Success", status=200):
        return success_response(data=data, message=message, status=status)

    def error(self, message="An error occurred", errors=None, status=400):
        return error_response(message=message, errors=errors, status=status)
