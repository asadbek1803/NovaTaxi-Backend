from rest_framework import serializers

from shared.models import PaymentMethod


class PaymentMethodSerializer(serializers.ModelSerializer):
    masked_number = serializers.CharField(read_only=True)
    type_label = serializers.CharField(read_only=True)

    class Meta:
        model = PaymentMethod
        fields = ['id', 'type', 'type_label', 'masked_number', 'holder_name', 'expiry', 'is_default']
        read_only_fields = ['id', 'is_default']


class PaymentMethodCreateSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=PaymentMethod.TYPE_CHOICES)
    card_number = serializers.CharField(max_length=20)
    holder_name = serializers.CharField(max_length=255)
    expiry = serializers.CharField(max_length=5)
