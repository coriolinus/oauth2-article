
INSTALLED_APPS = [
    # include your own set of  applications here,
    # but at least these must be included:
    'rest_framework',
    'rest_framework.authtoken',  # if you use the same token auth system as the example
    'social_django',  # python social auth
]

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.TokenAuthentication',
    ),
}

# Authentication backends
# https://docs.djangoproject.com/en/1.10/ref/settings/#authentication-backends
# Here, we add two social authentication methods _above_ the default ModelBackend.
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)

# Set up social auth keys from the environment
# Why does this application need them, if the frontend is handling the entire
# OAuth2 process and we're just grabbing data from the social APIs using the
# access tokens? They're necessary for Python Social Auth to work properly,
# even if the application doesn't participate in the OAuth2 process.
for key in ['GOOGLE_OAUTH2_KEY',
            'GOOGLE_OAUTH2_SECRET',
            'FACEBOOK_KEY',
            'FACEBOOK_SECRET']:
    exec("SOCIAL_AUTH_{key} = os.environ.get('{key}', '')".format(key=key))

# We need to set at least the following scopes, to ensure that we can read
# basic profile details and email addresses.
# NB: These scopes are never actually used on the backend; things will work
# just fine if you omit these settings from the backend. However, the
# _frontend_ needs to be sure to send at least these scopes in order for the
# tokens to have enough permissions to get the user model updates / matching
# working properly.
SOCIAL_AUTH_FACEBOOK_SCOPE = ['email']
SOCIAL_AUTH_GOOGLE_OAUTH2_SCOPE = ['email', 'profile']

# config per http://psa.matiasaguirre.net/docs/configuration/django.html#django-admin
SOCIAL_AUTH_ADMIN_USER_SEARCH_FIELDS = ['username', 'first_name', 'email']

# If this is not set, PSA constructs a plausible username from the first portion of the
# user email, plus some random disambiguation characters if necessary.
SOCIAL_AUTH_USERNAME_IS_FULL_EMAIL = True

# define a custom social auth pipeline.
# The key thing here is to include email association. Both FB and Google
# only return validated user emails, so email validation is safe.
#
# Don't do this if you wish to use an OAuth2 provider which doesn't
# validate email addresses, as that opens up an attack vector.
# An attacker targeting one of your users might create an account with
# the OAuth2 provider, falsely claiming your user's email address as
# their own. Without validation, that provider can't know otherwise.
# They can then gain access to your user's account by logging in via
# that OAuth2 provider.
#
# See here for more details:
# http://psa.matiasaguirre.net/docs/use_cases.html#associate-users-by-email
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'social_core.pipeline.user.get_username',
    'social_core.pipeline.social_auth.associate_by_email',  # <- this line not included by default
    'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)
