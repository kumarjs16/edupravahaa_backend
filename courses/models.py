from django.db import models
from django.conf import settings
from django.utils.text import slugify
from django.core.exceptions import ValidationError

class Course(models.Model):
    """
    Pre-defined courses that teachers can schedule classes for.
    These are created by admins, not teachers.
    """
    SLOT_CHOICES = (
        ('morning', 'Morning'),
        ('afternoon', 'Afternoon'),
        ('evening', 'Evening'),
    )
    
    LEVEL_CHOICES = (
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    )
    
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    description = models.TextField()
    category = models.CharField(max_length=100)
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='beginner')
    thumbnail = models.ImageField(upload_to='course_thumbnails/', blank=True, null=True)
    duration_hours = models.IntegerField(help_text="Total course duration in hours", default=30)
    base_price = models.DecimalField(max_digits=10, decimal_places=2)
    advantages = models.JSONField(default=list, help_text="List of course advantages/features")
    
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'courses'
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['slug']),
        ]
        
    def __str__(self):
        return f"{self.name} ({self.category})"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)