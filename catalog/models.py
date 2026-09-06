from django.db import models
from django.utils.text import slugify
from django.conf import settings
from decimal import Decimal


class TCG(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    icon_symbol = models.CharField(max_length=50, default='✦', help_text="Emoji or icon marker")
    accent_color = models.CharField(max_length=20, default='#6342FF', help_text="Brand hex color")
    banner_image = models.URLField(blank=True, default='')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'TCG Universe'
        verbose_name_plural = 'TCG Universes'
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField(blank=True, default='')
    image_url = models.URLField(blank=True, default='')
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    class ProductType(models.TextChoices):
        BOOSTER_BOX = 'BOOSTER_BOX', 'Booster Box'
        BOOSTER_PACK = 'BOOSTER_PACK', 'Booster Pack'
        ELITE_TRAINER_BOX = 'ELITE_TRAINER_BOX', 'Elite Trainer Box'
        COLLECTION_BOX = 'COLLECTION_BOX', 'Collection Box'
        SINGLE_CARD = 'SINGLE_CARD', 'Single Card'
        DECK = 'DECK', 'Starter / Structure Deck'
        ACCESSORIES = 'ACCESSORIES', 'Accessories'
        SLEEVES = 'SLEEVES', 'Card Sleeves'
        DECK_BOXES = 'DECK_BOXES', 'Deck Box'
        BINDERS = 'BINDERS', 'Collector Binder'
        PLAYMATS = 'PLAYMATS', 'Playmat'
        MYSTERY = 'MYSTERY', 'Mystery Product / Drop'
        PRE_ORDER = 'PRE_ORDER', 'Pre-Order Sealed Box'

    class Condition(models.TextChoices):
        SEALED = 'SEALED', 'Factory Sealed / Mint'
        NEAR_MINT = 'NEAR_MINT', 'Near Mint (NM)'
        LIGHTLY_PLAYED = 'LIGHTLY_PLAYED', 'Lightly Played (LP)'
        MODERATELY_PLAYED = 'MODERATELY_PLAYED', 'Moderately Played (MP)'
        GRADED_PSA = 'GRADED_PSA', 'Graded - PSA Gem Mint'
        GRADED_BGS = 'GRADED_BGS', 'Graded - BGS Pristine'
        GRADED_CGC = 'GRADED_CGC', 'Graded - CGC Pristine'

    class Language(models.TextChoices):
        ENGLISH = 'EN', 'English'
        JAPANESE = 'JA', 'Japanese'
        KOREAN = 'KO', 'Korean'
        OTHER = 'OT', 'Other'

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    sku = models.CharField(max_length=50, unique=True)
    tcg = models.ForeignKey(TCG, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')

    price = models.DecimalField(max_digits=10, decimal_places=2)
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    short_description = models.CharField(max_length=300, blank=True, default='')
    description = models.TextField()

    product_type = models.CharField(
        max_length=30,
        choices=ProductType.choices,
        default=ProductType.BOOSTER_BOX
    )
    condition = models.CharField(
        max_length=30,
        choices=Condition.choices,
        default=Condition.SEALED
    )
    language = models.CharField(
        max_length=10,
        choices=Language.choices,
        default=Language.ENGLISH
    )
    edition = models.CharField(max_length=100, blank=True, default='1st Edition / Original Run')
    release_date = models.DateField(null=True, blank=True)

    is_featured = models.BooleanField(default=False)
    is_new = models.BooleanField(default=True)
    is_preorder = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['sku']),
            models.Index(fields=['price']),
            models.Index(fields=['is_active']),
            models.Index(fields=['is_featured']),
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name)
            slug = base_slug
            counter = 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def primary_image(self):
        primary = self.images.filter(is_primary=True).first()
        if primary:
            return primary.get_image_url()
        first = self.images.first()
        if first:
            return first.get_image_url()
        return "https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=800&auto=format&fit=crop&q=80"

    @property
    def discount_percentage(self):
        if self.compare_at_price and self.compare_at_price > self.price:
            discount = ((self.compare_at_price - self.price) / self.compare_at_price) * 100
            return round(discount)
        return 0

    @property
    def current_stock(self):
        if hasattr(self, 'inventory'):
            return self.inventory.stock_quantity
        return 0

    @property
    def is_in_stock(self):
        if self.is_preorder:
            return True
        if hasattr(self, 'inventory'):
            return self.inventory.stock_quantity > 0 or self.inventory.allow_backorders
        return False

    @property
    def stock_status(self):
        if self.is_preorder:
            return 'Pre-Order'
        if hasattr(self, 'inventory'):
            return self.inventory.get_status_display()
        return 'Out of Stock'

    def __str__(self):
        return f"{self.name} [{self.tcg.name}]"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    image_url = models.URLField(max_length=500, blank=True, default='')
    alt_text = models.CharField(max_length=200, blank=True, default='')
    is_primary = models.BooleanField(default=False)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', '-is_primary', 'id']

    def get_image_url(self):
        if self.image:
            return self.image.url
        if self.image_url:
            return self.image_url
        return "https://images.unsplash.com/photo-1613771404784-3a5686aa2be3?w=800&auto=format&fit=crop&q=80"

    def __str__(self):
        return f"Image for {self.product.name}"


class Inventory(models.Model):
    class Status(models.TextChoices):
        IN_STOCK = 'IN_STOCK', 'In Stock'
        LOW_STOCK = 'LOW_STOCK', 'Low Stock'
        OUT_OF_STOCK = 'OUT_OF_STOCK', 'Out of Stock'
        PRE_ORDER = 'PRE_ORDER', 'Pre-Order'

    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name='inventory')
    stock_quantity = models.PositiveIntegerField(default=10)
    low_stock_threshold = models.PositiveIntegerField(default=5)
    allow_backorders = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.IN_STOCK
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = 'Inventories'

    def refresh_status(self):
        if self.product.is_preorder:
            self.status = self.Status.PRE_ORDER
        elif self.stock_quantity == 0:
            self.status = self.Status.OUT_OF_STOCK
        elif self.stock_quantity <= self.low_stock_threshold:
            self.status = self.Status.LOW_STOCK
        else:
            self.status = self.Status.IN_STOCK

    def save(self, *args, **kwargs):
        self.refresh_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} ({self.stock_quantity} available)"


class Promotion(models.Model):
    code = models.CharField(max_length=30, unique=True)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    minimum_spend = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} ({self.discount_percentage}% / ${self.discount_amount})"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveSmallIntegerField(default=5)
    title = models.CharField(max_length=150, blank=True, default='')
    comment = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.user.username} on {self.product.name}"
