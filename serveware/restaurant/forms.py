from django import forms

from accounts.models import Restaurant
from restaurant.models import MenuItem, Table


class RestaurantProfileForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = [
            'restaurant_name',
            'restaurant_address',
            'restaurant_landmark',
            'restaurant_pincode',
            'phone',
            'email',
            'gst_number',
        ]
        widgets = {
            'restaurant_address': forms.Textarea(attrs={'rows': 3}),
        }


class TableForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_number', 'seats']
        widgets = {
            'table_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Table Number'}),
            'seats': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter Number of Seats'}),
        }
        labels = {
            'table_number': 'Table Number',
            'seats': 'Number of Seats',
        }

    def clean_table_number(self):
        table_number = self.cleaned_data.get('table_number')
        if not table_number or not table_number.strip():
            raise forms.ValidationError("Table number cannot be empty or only spaces.")
        return table_number


class TableEditForm(forms.ModelForm):
    class Meta:
        model = Table
        fields = ['table_number', 'seats', 'is_occupied']


class MenuItemForm(forms.ModelForm):
    class Meta:
        model = MenuItem
        fields = [
            'name', 'description', 'price', 'image', 'category',
            'is_spicy', 'is_popular', 'is_jain_option', 'is_vegan',
            'is_non_veg', 'is_pure_veg', 'is_chefs_special', 'is_soup', 'is_available'
        ]

    custom_category = forms.CharField(max_length=50, required=False, label='Custom Category')

    def clean_category(self):
        category = self.cleaned_data.get('category')
        custom_category = self.cleaned_data.get('custom_category')
        if custom_category:
            category = custom_category
        return category
