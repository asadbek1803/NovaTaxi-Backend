from rest_framework import serializers


class AdminUserSerializer(serializers.Serializer):
    pass


class AdminDriverApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'reject'])
    reason = serializers.CharField(required=False, default='')
