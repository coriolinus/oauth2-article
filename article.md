# How to integrate OAuth2 into your Django/DRF backend without going insane

We've all been there: you've been working on the API backend, and you're happy with how it's going. You've recently completed the minimal viable product, the tests are all passing, and you're looking forward to implementing some new features. Then the boss sends you an email: "By the way, we need to let people log in via Facebook and Google; they shouldn't have to create an account just for a little site like ours."

```shell
$ pip search oauth | wc -l
278
$ pip search oauth | grep -i django | wc -l
53
```

The bad news is that `pip` knows about 278 packages which deal with oauth, 53 of which specifically mention django. It's a week's work just to research the options in any depth, let alone start writing code. It might happen that you're not familiar with the OAuth2 process at all; I wasn't, when this situation first happened to me. So what are you supposed to do?

The good news is that OAuth2 has emerged as the industry standard for social and third-party authentication, so you can focus on understanding and implementing that standard. Let's get going, then.

## A quick overview of the OAuth2 flow

## Here's a recipe

## That looks like magic. How does it work?

## Why not just roll my own? OAuth2 isn't _that_ hard.
