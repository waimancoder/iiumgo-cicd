from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler
import traceback


def custom_exception_handler(exc, context):
    # Call REST framework's default exception handler first,
    # to get the standard error response.
    response = exception_handler(exc, context)

    error_messages = {
        100: "Continue",
        101: "Switching Protocols",
        102: "Processing",
        200: "OK",
        201: "Created",
        202: "Accepted",
        203: "Non-Authoritative Information",
        204: "No Content",
        205: "Reset Content",
        206: "Partial Content",
        207: "Multi-Status",
        208: "Already Reported",
        226: "IM Used",
        300: "Multiple Choices",
        301: "Moved Permanently",
        302: "Found",
        303: "See Other",
        304: "Not Modified",
        305: "Use Proxy",
        307: "Temporary Redirect",
        308: "Permanent Redirect",
        400: "Bad Request",
        401: "Unauthorized",
        402: "Payment Required",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        406: "Not Acceptable",
        407: "Proxy Authentication Required",
        408: "Request Timeout",
        409: "Conflict",
        410: "Gone",
        411: "Length Required",
        412: "Precondition Failed",
        413: "Payload Too Large",
        414: "URI Too Long",
        415: "Unsupported Media Type",
        416: "Range Not Satisfiable",
        417: "Expectation Failed",
        418: "I'm a teapot",
        421: "Misdirected Request",
        422: "Unprocessable Entity",
        423: "Locked",
        424: "Failed Dependency",
        425: "Too Early",
        426: "Upgrade Required",
        428: "Precondition Required",
        429: "Too Many Requests",
        431: "Request Header Fields Too Large",
        451: "Unavailable For Legal Reasons",
        500: "Internal Server Error",
        501: "Not Implemented",
        502: "Bad Gateway",
        503: "Service Unavailable",
        504: "Gateway Timeout",
        505: "HTTP Version Not Supported",
        506: "Variant Also Negotiates",
        507: "Insufficient Storage",
        508: "Loop Detected",
        509: "Bandwidth Limit Exceeded",
        510: "Not Extended",
        511: "Network Authentication Required",
    }

    # Now add the HTTP status code to the response.
    if response is not None:
        response.data.pop("detail", None)
        response.data["success"] = "False"
        response.data["statusCode"] = response.status_code
        response.data["error"] = error_messages.get(response.status_code, "Unknown Error")
        response.data["message"] = str(exc)
        response.data["traceback"] = traceback.format_exc()

    return response


def handle_auth_failed_exception(exc):
    """
    Custom exception handler for AuthenticationFailed exceptions.
    """
    response = Response(
        {
            "success": False,
            "statusCode": status.HTTP_404_NOT_FOUND,
            "error": "Invalid Token" if str(exc) == "Authentication credentials were not provided." else str(exc),
            "message": "Invalid Token" if str(exc) == "Authentication credentials were not provided." else str(exc),
        },
        status=status.HTTP_404_NOT_FOUND,
    )

    return response
