from django import forms
from django.contrib.auth.forms import UserCreationForm
from accounts.models import CustomUser, Restaurant, Customer
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'email')


# Restaurant Sign-Up Form
class RestaurantSignUpForm(UserCreationForm):
    restaurant_name = forms.CharField(max_length=255, label="Restaurant Name")
    restaurant_address = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), label="Address")
    restaurant_landmark = forms.CharField(max_length=255, required=False, label="Landmark")
    restaurant_pincode = forms.CharField(max_length=6, label="Pincode")
    phone = forms.CharField(max_length=10, label="Phone Number")
    email = forms.EmailField(label="Email Address")
    gst_number = forms.CharField(max_length=20, required=False, label="GST Number")

    class Meta:
        model = CustomUser
        fields = ('username', 'password1', 'password2', 'email')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'restaurant' 
        if commit:
            user.save()
            Restaurant.objects.create(
                restaurant_admin=user,
                restaurant_name=self.cleaned_data.get('restaurant_name'),
                restaurant_address=self.cleaned_data.get('restaurant_address'),
                restaurant_landmark=self.cleaned_data.get('restaurant_landmark'),
                restaurant_pincode=self.cleaned_data.get('restaurant_pincode'),
                phone=self.cleaned_data.get('phone'),
                email=self.cleaned_data.get('email'),
                gst_number=self.cleaned_data.get('gst_number'),
            )
        return user

class CustomerRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email Address", widget=forms.EmailInput(attrs={'placeholder': 'Enter your email address'}))
    phone = forms.CharField(max_length=10, required=True, label="Phone Number", widget=forms.TextInput(attrs={'placeholder': 'Enter 10-digit phone number'}))
    dob = forms.DateField(required=False, label="Date of Birth", widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = CustomUser
        fields = ['username', 'email', 'password1', 'password2', 'phone', 'dob']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.user_type = 'customer'
        if commit:
            user.save()
            Customer.objects.create(user=user, phone=self.cleaned_data['phone'], dob=self.cleaned_data['dob'])
        return user



# Sign-in Form for CustomUser
class CustomUserSignInForm(AuthenticationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'password')

# Sign-in Form for Restaurant
class RestaurantSignInForm(AuthenticationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'password')

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        if user and user.user_type != 'restaurant':
            raise forms.ValidationError("This account is not registered as a Restaurant.")
        return cleaned_data
    
# Sign-in Form for Customer
class CustomerSignInForm(AuthenticationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'password')

    def clean(self):
        cleaned_data = super().clean()
        user = self.get_user()
        if user and user.user_type != 'customer':
            raise forms.ValidationError("This account is not registered as a Customer.")
        return cleaned_data


class PasswordResetEmailForm(forms.Form):
    email = forms.EmailField(
        max_length=254, 
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your registered email address'}),
        label="Email"
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not CustomUser.objects.filter(email=email).exists():
            raise ValidationError("There is no account associated with this email.")
        return email

class SetNewPasswordForm(forms.Form):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter new password'}),
        label="New Password",
    )
    confirm_new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm new password'}),
        label="Confirm New Password",
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)  
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        new_password = cleaned_data.get('new_password')
        confirm_new_password = cleaned_data.get('confirm_new_password')

        if new_password != confirm_new_password:
            raise ValidationError("Passwords do not match.")
        return cleaned_data


class OTPForm(forms.Form):
    otp = forms.CharField(
        max_length=6, 
        widget=forms.TextInput(attrs={'placeholder': 'Enter the OTP'}),
        label="One-Time Password"
    )

    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        return otp
