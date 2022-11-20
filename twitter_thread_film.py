import os

import requests
import tweepy
import shutil
from moviepy.editor import VideoFileClip, concatenate_videoclips

# ID of the first tweet in the thread, the one after /status/ in the URL
TWEET_ID = 1594108188915372034

# Limit of how many clips to download and join
# For default it's super high for the whole movie, but this takes a long time!
LIMIT = 2048

# Enter your keys/secrets as strings in the following fields
# You need to create a Twitter developer app for this
CREDENTIALS = {
    "API_KEY": "YOUR_API_KEY",
    "API_SECRET": "YOUR_API_SECRET",
    "ACCESS_TOKEN": "YOUR_ACCESS_TOKEN",
    "ACCESS_SECRET": "YOUR_ACCESS_SECRET",
}

auth = tweepy.OAuthHandler(CREDENTIALS.get("API_KEY"), CREDENTIALS.get("API_SECRET"))
auth.set_access_token(CREDENTIALS.get("ACCESS_TOKEN"), CREDENTIALS.get("ACCESS_SECRET"))
api = tweepy.API(auth)


def get_all_tweets(tweet):
    # initialize a list to hold all the tweepy Tweets
    all_tweets = []
    # make initial request for most recent tweets (200 is the maximum allowed count)
    new_tweets = api.user_timeline(screen_name=tweet.user.screen_name, count=200)
    all_tweets.extend(new_tweets)
    # save the id of the oldest tweet less one
    oldest = all_tweets[-1].id - 1
    # keep grabbing tweets until there are no tweets left to grab
    while len(new_tweets) > 0 and oldest >= tweet.id:
        # all subsequent requests use the max_id param to prevent duplicates
        new_tweets = api.user_timeline(
            screen_name=tweet.user.screen_name, count=200, max_id=oldest
        )
        # save most recent tweets
        all_tweets.extend(new_tweets)
        # update the id of the oldest tweet less one
        oldest = all_tweets[-1].id - 1
        print(f"...{len(all_tweets)} tweets downloaded so far")
    return [tweet.id for tweet in all_tweets]


def get_all_tweets_for_thread(tweetId, limit=1024):
    thread = []
    res = api.get_status(tweetId, tweet_mode="extended")
    all_until_thread = get_all_tweets(res)
    thread.append(res)
    if all_until_thread[-1] > res.id:
        print("Not able to retrieve tweets so old")
        return thread
    print("Downloaded required tweets")
    start_index = all_until_thread.index(res.id)
    quiet_long = 0
    while start_index != 0 and quiet_long < 25 and len(thread) < limit:
        now_index = start_index - 1
        now_tweet = api.get_status(all_until_thread[now_index], tweet_mode="extended")
        if now_tweet.in_reply_to_status_id == thread[-1].id:
            quiet_long = 0
            thread.append(now_tweet)
        else:
            quiet_long = quiet_long + 1
        start_index = now_index
    return thread


def get_video_urls(tweets):
    if len(tweets) < 1:
        print("No tweets to print")
        return
    video_urls = []
    for tweet in tweets:
        variants = tweet.extended_entities["media"][0]["video_info"]["variants"]
        variants = [
            variant for variant in variants if variant["content_type"] == "video/mp4"
        ]
        variants = sorted(variants, key=lambda v: v["bitrate"], reverse=True)
        video_urls.append(variants[0]["url"])
    return video_urls


def download_video(url, filename):
    print(f"downloading video {url} to {filename}")
    try:
        response = requests.get(url, stream=True)
    except requests.exceptions.RequestException as e:
        print(f"requests error: {e}")
        return

    with open(filename, "wb") as out_file:
        shutil.copyfileobj(response.raw, out_file)
    del response


def concatenate_clips(filenames):
    print("concatenating clips into a single one")
    files = []
    for filename in filenames:
        file = VideoFileClip(filename)
        files.append(file)
    final_clip = concatenate_videoclips(files)
    final_clip.write_videofile("movie/movie.mp4")


if __name__ == "__main__":
    thread_tweets = get_all_tweets_for_thread(TWEET_ID, LIMIT)
    urls = get_video_urls(thread_tweets)

    if not os.path.exists("movie"):
        os.makedirs("movie")

    idx = 1
    filenames = []
    for url in urls:
        filename = f"movie/clip_{idx}.mp4"
        download_video(url, filename)
        filenames.append(filename)
        idx = idx + 1
    print("Downloaded clips")
    concatenate_clips(filenames)
