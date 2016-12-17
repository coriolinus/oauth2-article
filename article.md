# How to integrate OAuth2 into your Django/DRF backend without going insane

We've all been there: you've been working on the API backend, and you're happy with how it's going. You've recently completed the minimal viable product, the tests are all passing, and you're looking forward to implementing some new features. Then the boss sends you an email: "By the way, we need to let people log in via Facebook and Google; they shouldn't have to create an account just for a little site like ours."

```shell
$ pip search oauth | wc -l
278
$ pip search oauth | grep -i django | wc -l
53
```

The bad news is that `pip` knows about 278 packages which deal with oauth, 53 of which specifically mention django. It's a week's work just to research the options in any depth, let alone start writing code. It might happen that you're not familiar with OAuth2 at all; I wasn't, when this situation first happened to me. So what are you supposed to do?

The good news is that OAuth2 has emerged as the industry standard for social and third-party authentication, so you can focus on understanding and implementing that standard. Let's get going, then.

## A quick overview of the OAuth2 flow

OAuth2 was designed from the beginning as a web authentication protocol. This is not quite the same as if it had been designed as a _net_ authentication protocol; it assumes that tools like HTML rendering and browser redirects are available to you. This is obviously something of a hindrance for a JSON-based API, but we can work around that. First, let's go through the process as if we were writing a traditional, server-side website.

### The server-side OAuth2 flow

The first step in the process happens outside the application flow entirely: the project owner has to register your application with each OAuth2 provider with whom logins should be supported. During this registration, they provide the OAuth2 provider with a **callback URI**, at which your application will be available to receive requests. In exchange, they receive a **client key** and **client secret**. These tokens are exchanged during the authentication process to validate the login requests.

> The below image currently hotlinks to an image I found on imgur, but for the article proper we should probably create our own.

![](https://i.stack.imgur.com/SCJZO.png)

The flow begins when your application generates a page which includes a button like "Log in with Facebook" or "Sign in with Google+". Fundamentally, these are nothing but simple links, which points to a URL like `https://oauth2provider.com/auth?response_type=code&client_id=CLIENT_KEY&redirect_uri=CALLBACK_URI&scope=profile&scope=email`.

Let's unpack that a little. You've provided your client key and redirect URI, but no secrets. In exchange, you've told the server that you'd like an authentication code in response, and access to both the 'profile' and 'email' scopes. These scopes define the permissions you request from the user, and limit the extent of the provider's API for which the access token you will receive will be valid.

Upon receipt, the OAuth2 provider verifies that the callback URI and client key match each other before proceeding. If they do, the flow diverges briefly depending on the user's session tokens; if the user isn't currently logged in to that service, they'll be prompted to do so first. Once they're logged in, the user is presented with a dialog requesting permission to allow your application to log in.

> We definitely need to re-create this image, but it's pretty much exactly what we want. To match our example here, it should say "The app **Example** by Toptal Blog would like the ability to access your basic profile information and email address."

![](https://aaronparecki.com/2012/07/29/2/oauth-authorization-prompt.png)

Assuming the user approves, the OAUth2 server then redirects them back to the callback URI that you provided, including an **authorization code** in the query parameters: `GET https://api.yourapp.com/oauth2/callback/?code=AUTH_CODE`. This is a fast-expiring, single-use token; immediately upon its receipt, your server should turn around and make another request to the OAuth2 provider, including both the auth code and your client secret: `POST https://oauth2provider.com/token/?grant_type=authorization_code&code=AUTH_CODE&redirect_uri=CALLBACK_URI&client_id=CLIENT_KEY&client_secret=CLIENT_SECRET`.

This request provides both your client key and your client secret, alongside the authorization code, and your callback URI. If everything matches up, the server returns an **access token**, with which you can make calls to that provider while authenticated as the user. As the request is generated directly from your server to the OAuth2 server over a TLS-secured connection, your client secret is never revealed to the client or to any attacker.

Once you've received the access token from the server, your server then redirects the user's browser once more to the landing page for just-logged-in users. It's common to retain the access token in the user's session, so that the server can make calls to the given social provider whenever necessary.

There are more details which we could go into: for example, Google will include a **refresh token** with which you can extend the life of your access token, while Facebook simply provides an endpoint at which you can exchange the short-lived access token they give by default for something longer-lived; these details don't matter to us, though, because we're not going to use this flow.

This flow is cumbersome for a REST API: while you could have the frontend client generate the initial login page, have the backend provide a callback URL, you'll eventually run into a problem: you want to redirect the user to the frontend's landing page once you've received the access token, and there's no clear, RESTful way to do so. Luckily, there's another OAuth2 flow available, which works much better in this case.

### The client-side OAuth2 flow

In this flow, the frontend becomes responsible for handling the entire OAuth2 process. It generally resembles the server-side flow, with an important exception: frontends live on machines that users control, so cannot be entrusted with the client secret. The solution is to simply eliminate that entire step of the process.

The first step, as in the server-side flow, is registering the application. In this case, the project owner will still register the application, but as a web application; the OAuth2 provider will still provide a **client key**, but may not provide any client secret.

The frontend provides the user with a social login button as before, and as before, this directs to a webpage the OAuth2 provider controls, requesting permission for our application to access certain aspects of the user's profile. The link looks a little different this time: `https://oauth2provider.com/auth?response_type=token&client_id=CLIENT_KEY&redirect_uri=CALLBACK_URI&scope=profile&scope=email`. Note that the `response_type` this time is now `token`.

> This should be the same image we created before

![](https://aaronparecki.com/2012/07/29/2/oauth-authorization-prompt.png)

So what about the redirect url? The frontend actually temporarily runs a server capable of accepting HTTP requests on the user's device; the redirect URL is of the form `http://localhost:7862/callback/?token=TOKEN`. Because the OAuth2 server returns a HTTP redirect after the user has accepted, and this redirect is processed by the browser on the user's device, this address is interpreted correctly, giving the frontend access to the token.

From this point, the frontend can directly call the OAuth2 provider's API using the token, but they don't really want that; they want authenticated access to your API! However, the backend is excluded from the OAuth2 process using this flow, so all it needs to provide is an endpoint at which the frontend can exchange a social provider's access token for a token which grants access to your API.

This flow may seem complicated for the frontend, and it is, if you require the frontend team to develop everything on their own. However, both [Facebook](https://developers.facebook.com/docs/facebook-login/web/login-button) and [Google](https://developers.google.com/identity/sign-in/web/sign-in) provide libraries which enable the frontend to include login buttons which handle the entire process with a minimum of configuration.

### Diagram Time

> Please have a designer make this diagram pretty

```text
.        SERVER FLOW                             CLIENT FLOW

+-----------------------------+         +-----------------------------+
| Page presents login button  |         | Frontend presents login     |
| to user                     |         | button to user              |
+-----------------------------+         +-----------------------------+
               |                                       |
+-----------------------------+         +-----------------------------+
| Button click redirects to   |         | Button click redirects to   |
| social auth server          |         | social auth server          |
+-----------------------------+         +-----------------------------+
               |                                       |               
               |                        +-----------------------------+
               |                        | Frontend starts up a short- |
               |                        | lived web server which      |
               |                        | accepts requests at the     |
               |                        | callback uri.               |
               |                        +-----------------------------+
               |                                       |
+-----------------------------+         +-----------------------------+
| OAuth2 provider validates   |         | OAuth2 provider validates   |
| request; redirects user to  |         | request; redirects user to  |
| server-side                 |         | frontend                    |
| callback url, including an  |         | callback url, including an  |
| authorization code          |         | access token                |
+-----------------------------+         +-----------------------------+
               |                                       |
+-----------------------------+         +-----------------------------+
| Server makes REST request   |         | Frontend makes REST request |
| to OAuth2 provider,         |         | to your backend, exchanging |
| exchanging authorization    |         | provider access token for   |
| code for access token       |         | an access token which works |
+-----------------------------+         | on your API                 |
               |                        +-----------------------------+
               |                                       |
+-----------------------------+         +-----------------------------+
| Backend makes calls to      |         | Frontend makes calls to     |
| OAuth2 provider as          |         | your API; backend calls     |
| necessary                   |         | OAuth2 provider as          |
+-----------------------------+         | necessary                   |
                                        +-----------------------------+
```

## Here's a recipe for token exchange on the backend

Under the client flow, the backend is pretty isolated from the OAuth2 process. Unfortunately, that doesn't mean its job is simple. You want at least the following features:

- Send at least one request to the OAuth2 provider just to ensure that the token that the frontend provided was valid, not some arbitrary random string.
- When the token is valid, return a token valid for your API. Otherwise, return an informative error.
- If this is a new user, create a `User` model for them and populate it appropriately.
- If this is a user for whom a `User` model already exists, match them by their email address, so they gain access to the correct account instead of creating a new one for the social login.
- Update the user's profile details according to what they've provided on social media.

So here's the magic: how to get all that working on the backend in two dozen lines of code. This depends on the [Python Social Auth](https://github.com/python-social-auth) library, so you'll need to include both `social-auth-core` and `social-auth-app-django` in your `requirements.txt`. You'll also need to configure the library as documented [here](http://psa.matiasaguirre.net/docs/configuration/django.html). Note that this excludes some exception handling for clarity. Full code for this example can be found [here](http://gist.github.com/put the gist with the source files here).

> Don't forget to update the link above once we have a gist with the source.

```python
@api_view(http_method_names=['POST'])
@permission_classes([AllowAny])
@psa()
def exchange_token(request, backend):
    serializer = SocialSerializer(data=request.data)

    if serializer.is_valid(raise_exception=True):
        user = request.backend.do_auth(serializer.validated_data['access_token'])

        if user:
            if user.is_active:
                token, _ = Token.objects.get_or_create(user=user)
                return Response({'token': token.key})
            else:
                return Response(
                    {'errors': {'non_field_errors': 'This user account is inactive'}},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {'errors': {'token': 'Invalid token'}},
                status=status.HTTP_400_BAD_REQUEST,
            )
```

There's just a little more that needs to go in your settings, and then you're all set:

```python
AUTHENTICATION_BACKENDS = (
    'social_core.backends.google.GoogleOAuth2',
    'social_core.backends.facebook.FacebookOAuth2',
    'django.contrib.auth.backends.ModelBackend',
)
for key in ['GOOGLE_OAUTH2_KEY',
            'GOOGLE_OAUTH2_SECRET',
            'FACEBOOK_KEY',
            'FACEBOOK_SECRET']:
    exec("SOCIAL_AUTH_{key} = os.environ.get('{key}')".format(key=key))
SOCIAL_AUTH_PIPELINE = (
  'social_core.pipeline.social_auth.social_details',
  'social_core.pipeline.social_auth.social_uid',
  'social_core.pipeline.social_auth.auth_allowed',
  'social_core.pipeline.social_auth.social_user',
  'social_core.pipeline.user.get_username',
  'social_core.pipeline.social_auth.associate_by_email',
  'social_core.pipeline.user.create_user',
  'social_core.pipeline.social_auth.associate_user',
  'social_core.pipeline.social_auth.load_extra_data',
  'social_core.pipeline.user.user_details',
)
```

Add a mapping to this function in your `urls.py`, and you're all set!

## That looks a lot like magic. How does it work?

## Why not just roll my own?
