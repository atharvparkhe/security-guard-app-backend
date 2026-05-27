from rest_framework.response import Response


def success_response(data=None, message="Success", status=200):
    return Response(
        {
            "response_type": "SUCCESS",
            "message": message,
            "content": data if data is not None else {},
        },
        status=status,
    )


def error_response(message="An error occurred", errors=None, status=400):
    return Response(
        {
            "response_type": "ERROR",
            "message": message,
            "content": errors if errors is not None else {},
        },
        status=status,
    )
