from contextlib import contextmanager
import json
import re
from urllib.parse import urlparse, parse_qs

from rest_framework.test import APITestCase

# This is the responses library mentioned in the article, which
# provides RequestsMock
import responses

from requests.exceptions import HTTPError
from requests.models import Response
from social_core.backends import facebook, google

from core.models import User
import core.tests.fixtures as fixtures

SOCIAL_URL = "/api/2.0/social/{}/"  # Customize for your own endpoint URL scheme


class TryToken:  # using the python3 idiom
    """
    Mixin class to provide a simple means of attempting access via a token.
    """

    def try_token(self, token):
        return self.post(
            SOCIAL_URL.format(self.provider),
            data={'access_token': token},
        )


class TestInvalidProvider(TryToken, APITestCase):
    """
    Test that PSA is correctly limiting login attempts to social auth providers
    which we have specifically enabled.
    """
    # obviously, if we support yahoo logins in the future,
    # we'll have to change this.
    provider = 'yahoo'

    def test_only_allowed_backends_work(self):
        """
        Ensure that backends not configured don't work.
        """
        # create an otherwise-valid request
        for token in USER_INFO:
            with self.subTest(token=token):
                resp = self.try_token(token)

                self.assertEqual(resp.status_code, 404)

USER_INFO = {
    'user_1': {
        'id': '00001',
        'name': 'Foo Bar',
        'email': 'foo@bar.com',
    },
    'user_2': {
        'id': '00002',
        'name': 'Pooh Bear',
        'email': 'winnie@100acre.net',
    },
}


def respond_to(request):
    """
    Generate a response according to whether the provided access_token
    is a key in USER_INFO.

    If so, return that user and a success code; otherwise, 401 (like Google).
    """

    token = parse_qs(urlparse(request.url).query)['access_token'][0]
    status = 200
    try:
        body = USER_INFO[token]
    except KeyError:
        # invalid token
        body = {'errors': 'Invalid Token'}
        status = 401
    return (status, {}, json.dumps(body))


@contextmanager
def mocked(endpoint):
    """
    Context manager which mocks out the appropriate foreign endpoint.

    Because the response depends on the particular request--we're mocking a
    dynamic endpoint, not a static page--we provide a callback here instead
    of a static string of response content.
    """
    with responses.RequestsMock() as rsps:
        rsps.add_callback(responses.GET, endpoint,
                          callback=respond_to,
                          content_type='application/json',
                          match_querystring=True,
                          )
        yield rsps


class SocialAuthTests(TryToken):
    """
    Social auth tests.

    Note that this isn't actually a descendent of APITestCase, which it would need to be
    to run directly. Instead, we have to create subclasses which mix in this,
    TestFacebook, TestGoogle, etc., with APITestCase, so that setup gets run appropriately.
    """

    def test_new_user_creation(self):
        "Ensure that we can correctly create a new user for someone with a valid token."
        for token, data in USER_INFO.items():
            with self.subTest(token=token), mocked(self.mock_url):
                resp = self.try_token(token)

                # request must return success
                self.assertEqual(self.status_head(resp), 2)

                # request must return a token of our own
                self.assertIn('token', resp.data)

                # new token must not be the same as what we submitted
                self.assertNotEqual(resp.data['token'], token)

                # user must appear in our database
                self.assertEqual(User.objects.filter(email=data['email']).count(), 1)

                # username must be set to full email address
                user_model = User.objects.get(email=data['email'])
                self.assertEqual(user_model.username, user_model.email)

    def test_existing_user_login(self):
        "Ensure that users with existing accounts and a valid social token can log in."
        for token, data in USER_INFO.items():
            # create the users in the DB
            # we could use a separate class with fixtures for this, but for now,
            # let's just do it here. we can always refactor later.
            User.objects.create_user(data['email'], email=data['email'],
                                     first_name=data['name'], last_name='')

            with self.subTest(token=token), mocked(self.mock_url):
                resp = self.try_token(token)

                # request must return success
                self.assertEqual(self.status_head(resp), 2)

                # request must return a token of our own
                self.assertIn('token', resp.data)

                # new token must not be the same as what we submitted
                self.assertNotEqual(resp.data['token'], token)

                # user must appear in our database only once
                # we don't want to duplicate the users here
                self.assertEqual(User.objects.filter(email=data['email']).count(), 1)

                # user should have their name updated per the social values
                user = User.objects.get(email=data['email'])
                self.assertEqual(user.get_full_name(), data['name'])

    def test_invalid_social_token(self):
        "Ensure that users who present an invalid social token are not granted access"
        # back up our existing user set
        usernames = {u.username for u in User.objects.all()}

        token = 'invalid_token'  # anything that's not a key in USER_INFO
        resp = self.try_token(token)

        # request must return failure
        self.assertEqual(self.status_head(resp), 4)

        # request must not return a token of our own
        self.assertNotIn('token', resp.data)

        # the database must not have any new users
        new_usernames = {u.username for u in User.objects.all()}
        self.assertEqual(usernames, new_usernames)

# This is a regular expression string designed to capture an arbitrary number
# of arbitary query strings from the end of an URL.
QUERY_STRINGS_RE = '\?([\w-]+(=[\w-]*)?(&[\w-]+(=[\w-]*)?)*)?$'


class TestFacebook(SocialAuthTests, APITestCase):
    "Actually run tests for Facebook"
    provider = 'facebook'
    # got lucky; the URL the library uses is a publicly-accessible variable.
    base_url = facebook.FacebookOAuth2.USER_DATA_URL.replace('.', r'\.')
    mock_url = re.compile(
        # match arbitrary key-value query strings at the end
        base_url + QUERY_STRINGS_RE
    )


class TestGoogle(SocialAuthTests, APITestCase):
    "Actually run tests for Google"
    provider = 'google-oauth2'
    # less lucky here:
    # Taken from https://github.com/python-social-auth/social-core/blob/master/social_core/backends/google.py#L70
    # Naturally, if this changes in the PSA library, we'll have to change it here.
    # This is why you pin your libraries, folks.
    base_url = 'https://www.googleapis.com/plus/v1/people/me'.replace('.', r'\.')
    mock_url = re.compile(
        # match arbitrary key-value query strings at the end
        base_url + QUERY_STRINGS_RE
    )
