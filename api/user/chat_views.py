from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from api.utils import success_response
from shared.models import ChatMessage, ChatThread
from .chat_serializers import ChatMessageSerializer, ChatThreadSerializer, SendMessageSerializer


class ThreadListView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        threads = ChatThread.objects.filter(passenger=request.user)
        total_unread = sum(t.unread_count for t in threads)
        return success_response(data={
            'threads': ChatThreadSerializer(threads, many=True).data,
            'total_unread': total_unread,
        })


class ThreadMessagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            thread = ChatThread.objects.get(id=pk, passenger=request.user)
        except ChatThread.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Suhbat topilmadi'}
            }, status=404)

        messages_qs = thread.messages.all()
        total_items = messages_qs.count()

        try:
            page = int(request.query_params.get('page', 1))
        except (ValueError, TypeError):
            page = 1
        try:
            per_page = int(request.query_params.get('limit', 50))
        except (ValueError, TypeError):
            per_page = 50

        total_pages = max(1, -(-total_items // per_page))
        start = (page - 1) * per_page
        page_messages = messages_qs[start:start + per_page]

        thread_data = ChatThreadSerializer(thread).data
        messages_data = ChatMessageSerializer(page_messages, many=True, context={'request': request}).data

        return success_response(data={
            'thread': thread_data,
            'messages': messages_data,
            'pagination': {
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total_items,
            }
        })


class SendMessageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            thread = ChatThread.objects.get(id=pk, passenger=request.user)
        except ChatThread.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Suhbat topilmadi'}
            }, status=404)

        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        msg = ChatMessage.objects.create(
            thread=thread,
            sender=request.user,
            text=serializer.validated_data['text'],
        )

        thread.last_message = msg.text
        thread.last_message_time = timezone.now()
        thread.unread_count += 1
        thread.save()

        return success_response(
            data=ChatMessageSerializer(msg, context={'request': request}).data,
            status_code=201
        )


class MarkReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        try:
            thread = ChatThread.objects.get(id=pk, passenger=request.user)
        except ChatThread.DoesNotExist:
            return Response({
                'success': False,
                'error': {'code': 'NOT_FOUND', 'message': 'Suhbat topilmadi'}
            }, status=404)

        thread.messages.filter(is_read=False).exclude(sender=request.user).update(is_read=True)
        thread.unread_count = 0
        thread.save()

        return success_response(message="Xabarlar o'qilgan deb belgilandi")
