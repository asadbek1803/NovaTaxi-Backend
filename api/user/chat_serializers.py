from rest_framework import serializers

from shared.models import ChatMessage, ChatThread


class ChatMessageSerializer(serializers.ModelSerializer):
    time = serializers.DateTimeField(source='created_at', format='%Y-%m-%dT%H:%M:%SZ')
    time_label = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    class Meta:
        model = ChatMessage
        fields = ['id', 'text', 'time', 'time_label', 'is_mine', 'is_read']

    def get_time_label(self, obj):
        return obj.created_at.strftime('%H:%M') if obj.created_at else ''

    def get_is_mine(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return obj.sender_id == request.user.id
        return False


class ChatThreadSerializer(serializers.ModelSerializer):
    driver_name = serializers.CharField(source='driver.name', read_only=True, default='')
    car_model = serializers.CharField(source='driver.car_model', read_only=True, default='')
    time_label = serializers.SerializerMethodField()

    class Meta:
        model = ChatThread
        fields = ['id', 'driver_id', 'driver_name', 'car_model', 'last_message',
                  'last_message_time', 'time_label', 'unread_count', 'is_online', 'ride_id']
        read_only_fields = ['id', 'ride_id']

    def get_time_label(self, obj):
        if obj.last_message_time:
            return obj.last_message_time.strftime('%H:%M')
        return ''


class SendMessageSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=1000)
