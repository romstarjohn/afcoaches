from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """Hands the SPA a CSRF token for unsafe requests.

    Same-origin only (no CORS configured), so other sites cannot read the token. The cookie itself
    stays HttpOnly; the SPA sends the token back in the X-CSRFToken header.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class MeSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()


class MeView(APIView):
    """Current user. 403 when not logged in (session auth). Login/logout endpoints: backlog 000002."""

    def get(self, request):
        return Response(MeSerializer(request.user).data)
