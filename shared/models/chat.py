import uuid

from django.db import models


class ChatThread(models.Model):
    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    ride = models.OneToOneField('shared.Ride', on_delete=models.CASCADE, related_name='chat_thread')
    driver = models.ForeignKey('shared.Driver', on_delete=models.CASCADE, related_name='chat_threads')
    passenger = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='chat_threads')
    last_message = models.TextField(blank=True, default='')
    last_message_time = models.DateTimeField(null=True, blank=True)
    unread_count = models.IntegerField(default=0)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_threads'
        ordering = ['-last_message_time']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'thr_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Thread {self.id}'


class ChatMessage(models.Model):
    id = models.CharField(max_length=20, primary_key=True, default='', editable=False)
    thread = models.ForeignKey(ChatThread, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey('api_user.User', on_delete=models.CASCADE, related_name='sent_messages')
    text = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        ordering = ['created_at']

    def save(self, *args, **kwargs):
        if not self.id:
            self.id = f'msg_{uuid.uuid4().hex[:12]}'
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.id}: {self.text[:50]}'
