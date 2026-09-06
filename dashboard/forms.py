from django import forms
from django.contrib.auth import get_user_model
from catalog.models import Product, ProductImage, Inventory, TCG, Category
from orders.models import StoreSettings

User = get_user_model()


class ProductAdminForm(forms.ModelForm):
    stock_quantity = forms.IntegerField(
        min_value=0,
        initial=10,
        required=True,
        label="Stock Quantity",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '0'})
    )
    low_stock_threshold = forms.IntegerField(
        min_value=1,
        initial=5,
        required=True,
        label="Low Stock Alert Threshold",
        widget=forms.NumberInput(attrs={'class': 'form-input', 'min': '1'})
    )
    image_url_1 = forms.URLField(
        required=False,
        label="Primary Image URL",
        widget=forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://images.unsplash.com/...'})
    )
    image_file_1 = forms.ImageField(
        required=False,
        label="Or Upload Primary Image File",
        widget=forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'})
    )
    image_url_2 = forms.URLField(
        required=False,
        label="Secondary Showcase Image URL (optional)",
        widget=forms.URLInput(attrs={'class': 'form-input', 'placeholder': 'https://images.unsplash.com/...'})
    )
    image_file_2 = forms.ImageField(
        required=False,
        label="Or Upload Secondary Image File",
        widget=forms.FileInput(attrs={'class': 'form-input', 'accept': 'image/*'})
    )

    class Meta:
        model = Product
        fields = (
            'name', 'sku', 'tcg', 'category', 'product_type', 'condition', 'language', 'edition',
            'price', 'compare_at_price', 'short_description', 'description',
            'is_featured', 'is_new', 'is_preorder', 'is_active', 'release_date'
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input'}),
            'sku': forms.TextInput(attrs={'class': 'form-input'}),
            'tcg': forms.Select(attrs={'class': 'form-select'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'product_type': forms.Select(attrs={'class': 'form-select'}),
            'condition': forms.Select(attrs={'class': 'form-select'}),
            'language': forms.Select(attrs={'class': 'form-select'}),
            'edition': forms.TextInput(attrs={'class': 'form-input'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'compare_at_price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'short_description': forms.TextInput(attrs={'class': 'form-input'}),
            'description': forms.Textarea(attrs={'class': 'form-textarea', 'rows': 4}),
            'release_date': forms.DateInput(attrs={'class': 'form-input', 'type': 'date'}),
        }


class StaffCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-input'}), required=True)
    first_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input'}), required=True)
    last_name = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-input'}), required=True)
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': 'form-input'}), required=True)

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'role', 'phone')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input'}),
            'role': forms.Select(attrs={'class': 'form-select'}, choices=[(User.Role.STAFF, 'Staff Member'), (User.Role.SUPERADMIN, 'Super Administrator')]),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class StoreSettingsForm(forms.ModelForm):
    class Meta:
        model = StoreSettings
        fields = '__all__'
        widgets = {
            'store_name': forms.TextInput(attrs={'class': 'form-input'}),
            'tagline': forms.TextInput(attrs={'class': 'form-input'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-input'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-input'}),
            'city': forms.TextInput(attrs={'class': 'form-input'}),
            'state': forms.TextInput(attrs={'class': 'form-input'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-input'}),
            'country': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'website': forms.URLInput(attrs={'class': 'form-input'}),
            'tax_id': forms.TextInput(attrs={'class': 'form-input'}),
            'default_tax_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'invoice_prefix': forms.TextInput(attrs={'class': 'form-input'}),
            'free_shipping_threshold': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
            'standard_shipping_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01'}),
        }
