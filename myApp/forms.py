from django import forms


INQUIRY_CHOICES = [
    ('general', 'General questions & support'),
    ('partners', 'Healthcare providers & partners'),
    ('privacy', 'Privacy & legal'),
    ('other', 'Something else'),
]


class ContactForm(forms.Form):
    name = forms.CharField(
        label='Full name',
        max_length=120,
        widget=forms.TextInput(attrs={
            'placeholder': 'First and last name',
            'autocomplete': 'name',
        }),
    )
    email = forms.EmailField(
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'name@email.com',
            'autocomplete': 'email',
        }),
    )
    inquiry_type = forms.ChoiceField(
        label='What can we help with?',
        choices=INQUIRY_CHOICES,
        widget=forms.Select(),
    )
    organization = forms.CharField(
        label='Organization (optional)',
        max_length=160,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Your clinic or organization',
            'autocomplete': 'organization',
        }),
    )
    message = forms.CharField(
        label='Message',
        min_length=20,
        max_length=4000,
        widget=forms.Textarea(attrs={
            'placeholder': 'Share your question, idea, or how we can help…',
            'rows': 5,
        }),
    )
    # Honeypot — hidden from users; bots often fill it.
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Unable to send your message.')
        return ''
