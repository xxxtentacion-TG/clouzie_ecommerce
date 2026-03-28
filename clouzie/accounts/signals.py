from allauth.socialaccount.signals import social_account_added
from django.dispatch import receiver
import uuid
@receiver(social_account_added)
def save_google_data(request, sociallogin, **kwargs):

    print("Signal is working")
    user = sociallogin.user


    given_name = data.get("given_name")
    family_name = data.get("family_name")

    if given_name and family_name:
        full_name = f"{given_name} {family_name}"
    elif given_name:
        full_name = given_name
    else:
        full_name = user.email.split("@")[0]

    user.username = f"{full_name}_{uuid.uuid4().hex[:4]}"
    user.save()