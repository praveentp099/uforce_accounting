from django.db import models
from django.conf import settings
from django.urls import reverse

class Quotation(models.Model):
    """
    A parent object to track a single quotation, its status, and its history.
    """
    STATUS_CHOICES = (
        ('pending', 'Pending (Sent)'),
        ('under_review', 'On Table for Approval'),
        ('revised', 'Revised'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    title = models.CharField(max_length=255)
    client_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    status_notes = models.TextField(blank=True, help_text="Internal notes on the quotation's status.")
    
    # This field links to the specific file that was approved.
    approved_file = models.ForeignKey(
        'QuotationFile',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='approved_quotation'
    )
    
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('quotation_detail', kwargs={'pk': self.pk})

    @property
    def revision_count(self):
        """
        Calculates the number of revisions (all files after the first one).
        """
        return max(0, self.files.count() - 1)

class QuotationFile(models.Model):
    """
    A file (original or revision) associated with a Quotation.
    """
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='quotations/')
    caption = models.CharField(max_length=255, blank=True, help_text="e.g., 'Revision 1', 'Original Quote'")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at'] # Order by oldest first

    def __str__(self):
        return f"File for {self.quotation.title} ({self.id})"

