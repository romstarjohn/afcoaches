import logging

from django.db import transaction
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .registry import Operation, Result, SyncConflict, SyncRejected, get_handler

logger = logging.getLogger(__name__)

MAX_BATCH = 100


class OperationSerializer(serializers.Serializer):
    op_id = serializers.UUIDField()
    entity = serializers.CharField(max_length=64)
    id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=["upsert", "delete"])
    data = serializers.DictField(required=False, default=dict)
    client_updated_at = serializers.DateTimeField()


class PushSerializer(serializers.Serializer):
    operations = OperationSerializer(many=True, allow_empty=False, max_length=MAX_BATCH)


class SyncPushView(APIView):
    """Apply a batch of offline operations. Each operation succeeds or fails on its own.

    Response per operation: ``applied`` (client removes it from its outbox), ``conflict`` or
    ``rejected`` (client keeps it aside and shows it to the user; never retried automatically).
    """

    throttle_scope = "sync"

    def post(self, request):
        payload = PushSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        results = []
        for raw in payload.validated_data["operations"]:
            op = Operation(
                op_id=raw["op_id"],
                entity=raw["entity"],
                record_id=raw["id"],
                action=raw["action"],
                data=raw["data"],
                client_updated_at=raw["client_updated_at"],
            )
            result = self._apply(request.user, op)
            item = {"op_id": str(op.op_id), "status": result.status}
            if result.error:
                item["error"] = result.error
            if result.server_updated_at:
                item["server_updated_at"] = result.server_updated_at.isoformat()
            results.append(item)
        return Response({"results": results})

    @staticmethod
    def _apply(user, op: Operation) -> Result:
        handler = get_handler(op.entity)
        if handler is None:
            return Result("rejected", error="unknown_entity")
        try:
            with transaction.atomic():
                return handler.apply(user, op)
        except SyncRejected as exc:
            return Result("rejected", error=str(exc) or "rejected")
        except SyncConflict as exc:
            return Result("conflict", error=str(exc) or "conflict")
        except Exception:
            # Unexpected server error: do not leak details; client keeps the op and retries later.
            logger.exception("sync handler failed for entity=%s op=%s", op.entity, op.op_id)
            raise
