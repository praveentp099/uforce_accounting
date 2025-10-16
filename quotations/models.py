from django.db import models
from django.conf import settings

class Quotation(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('revised', 'Revised'),
    )
    title = models.CharField(max_length=255)
    client_name = models.CharField(max_length=200)
    file = models.FileField(upload_to='quotations/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title
