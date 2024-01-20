from  configparser import  ConfigParser
import requests
import random
from cache import Cache
from input_object import InputObject


HEADER={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}


#--------Loading the CONFIG files---------------------------
config=ConfigParser()
config.read("config.ini")

SUBREDDIT_LIST = config["Reddit"]["subreddits"].split(",")
SEARCH_LIMIT = config["Reddit"]["search_limit"]
SORT=config["Reddit"]["sort_posts"]
FETCH_LATEST = eval(config["Reddit"]["fetch_latest_post"])

CHANNEL_NAME=config["Telegram"]["channel_name"]
CHANNEL_LINK=config["Telegram"]["channel_link"]
INCLUDE_TITLE=eval(config["Telegram"]["include_title"])
LINK_TO_POST=eval(config["Telegram"]["link_to_post"])
SIGN_MESSAGES=eval(config["Telegram"]["sign_messages"])
ONLY_IMAGES=eval(config["Telegram"]["only_images"])


PHOTO_FILE_TYPES = ["jpg", "jpeg", "png", "webp"]
ANIMATION_FILE_TYPES = ["gif", "gifv", "mp4"]


REDDIT_URL = "https://www.reddit.com/r/"
REDDIT_PARAMETER = {"limit": SEARCH_LIMIT}


class RedditHandler:
    """
    Class that handles extracting and filtering of media from fetched json file.
    """
    def __init__(self):
        self.retries = 0
        self.current_index = 0

    def get_reddit_json(self, retry:bool=False):
        """
        Retrieves the entire json containing a list of  posts.

        Args:
            retry(bool): True if the method is being called after failing to fetch a post. Default False.

        Returns:
            int: HTTP response code.204 on no new Content Available.
        """


        if self.retries >10:
            return 204

        if retry:
            self.retries+=1
        else:
            self.retries=0

        # Gets a subreddit from a list of subreddits
        self.currrent_subreddit = random.choice(SUBREDDIT_LIST)

        request_url = REDDIT_URL + self.currrent_subreddit+f"/{SORT}/" + ".json"


        try:
            reddit_response = requests.get(request_url, params=REDDIT_PARAMETER,headers=HEADER)
            reddit_response.raise_for_status()

        except:
            print("too many requests")
            return 429 #Too many requests

        else:
            reddit_response_json = reddit_response.json()

        try:
            self.reddit_json = reddit_response_json["data"]["children"]
            self.reddit_json_length=len(self.reddit_json)
        except:
            if len(SUBREDDIT_LIST)==1:
                return 204
            else:
                return self.get_reddit_json(retry=True)
        else:
            return self.get_post_json() #Return the post json

    def get_post_json(self,retry:bool=False):
        """
        Extracts a json element containing the post data from the main json.
        
        Args:
            retry(bool): True if the method is being called after failing to fetch a post. Default False.

        Returns:
            bool|tuple: A tuple containing the post type,media url or media object and caption. False on fail
            

        """

        # ------------for reddit---------------

        if FETCH_LATEST:  # Only look for the most recent post in the specified time.
            if not retry:
                self.index = 0
            else:
                self.index+=1

        else:  # Look for a random post from the search limit
            self.index = random.randint(0, self.reddit_json_length)

        while self.current_index == self.index and not FETCH_LATEST:
            self.index = random.randint(0, self.reddit_json_length)
        self.current_index = self.index


        try:
            self.post_json=self.reddit_json[self.index]["data"]
        except IndexError:
            if len (SUBREDDIT_LIST)==1: #If single sub reddit return
                return 204
            else:
                return self.get_reddit_json(retry=True)

        self.post_id = self.post_json["id"]

        # ----CHECK IF POSTS ARE BEING REPEATED-------------------------------
        if Cache.is_a_repost(subreddit=self.currrent_subreddit,post_id= self.post_id) == True:  #True means posted before.
            if FETCH_LATEST:
                return self.get_post_json(retry=True)
            else:
                return self.get_post_json()


        else:  # PostId has not been posted before
            try:
                is_removed=False
                is_removed = self.post_json["removed_by_category"]
            except:
                pass
            else:
                if is_removed:  # post has been removed by someone. Filtering out spam.
                    Cache.save_post_id(self.currrent_subreddit,self.post_id)
                    return 404

            try: #Check if the post is a pinned post
                is_stickied=self.post_json["stickied"]
            except:
                pass
            else:
                if is_stickied:
                    Cache.save_post_id(self.currrent_subreddit, self.post_id)
                    return 404

            current_permalink = self.post_json["permalink"]
            current_reddit_url = f'www.reddit.com{current_permalink}'

            current_title = self.post_json["title"]
            current_subreddit = self.post_json["subreddit"]

            post_title=""

#----------Post Caption and Signature-------------------------------
            if INCLUDE_TITLE:
                post_title = post_title+current_title+"\n"

            if LINK_TO_POST:
                hyperlink=f'<a href="{current_reddit_url}">r/{current_subreddit}</a>\n\n'
                post_title=post_title+hyperlink

            if SIGN_MESSAGES:
                post_signature=f'<a href="{CHANNEL_LINK}">-{CHANNEL_NAME}</a>'
                post_title = post_title+post_signature


#------------Checking the type of post fetched--------------------

            if not ONLY_IMAGES:

                # ---------------------Photo Post----------------------
                if self.is_photo_post() == True:  # check if post is single photo
                    current_url = self.post_json["url_overridden_by_dest"]
                    return ("photo", current_url, post_title)

                # ------------------------Gallery Post------------------------------
                elif self.is_gallery_post() == True:  # checks if post is gallery type
                    gallery_photo_list = []
                    animation_list = []
                    first_run = True
                    for link in self.gallery_url_list["photo"]:
                        current_url = link
                        current_type = "photo"


                        reddit_media_group_object = InputObject(media=current_url,
                                                                type=current_type,
                                                                caption=post_title,
                                                                subreddit=current_subreddit,
                                                                reddit_url=current_reddit_url)


                        dict_obj = (reddit_media_group_object.__dict__)  # Object to dictionary

                        if not first_run:  # Delete caption of all other photos and keep only one.
                            del dict_obj["caption"]
                        first_run = False
                        gallery_photo_list.append(dict_obj)  # save dict to list

                    for link in self.gallery_url_list["animation"]:
                        animation_list.append(link)

                    # post_title=f"{current_title}\n- r/{current_subreddit}"
                    photo_list = gallery_photo_list  # json this later in the main.py
                    return ("gallery", photo_list, animation_list, post_title)

                # ------------------------Animation Post------------------------------
                elif self.is_animation_post() == True:
                    current_type = "animation"
                    current_url = self.post_json["url_overridden_by_dest"]

                    return ("animation", current_url, post_title)

                # ------------------------Video Post------------------------------
                elif self.is_video_post() == True:
                    video_url = self.post_json["url_overridden_by_dest"]
                    video_id = video_url.rsplit("/", 1)[1]  # Extracting the id from the url v.reddit.it/video_id
                    # extracting video size from a stored thumbnail.
                    video_height = self.post_json["preview"]["images"][0]["source"][
                        "height"]  # height is to be used in the url.
                    video_width = self.post_json["preview"]["images"][0]["source"]["width"]
                    return ("video", video_id, video_height, post_title)

                # ------------------------Gfycat Post------------------------------
                elif self.is_gfycat_post() == True:

                    # Gfycat ids are case-sensitive and this is the only location its stored with proper case.
                    preview_url = self.post_json["secure_media"]["oembed"]["thumbnail_url"]

                    after_slash = preview_url.split("/")[-1]
                    after_dash = after_slash.split("-")[-2]

                    gfycat_id = after_dash  # extracting the id

                    return ("gfycat", gfycat_id, post_title)

                # ------------------------Unsupported Post------------------------------
                else:
                    return 404

            else:#Post photo only
                # ---------------------Photo Post----------------------
                if self.is_photo_post() == True:  # check if post is single photo
                    current_url = self.post_json["url_overridden_by_dest"]
                    return ("photo", current_url, post_title)
                else:
                    return  False


                    # ----------Check post Type----------------------

    def is_photo_post(self):
        """
        Checks if the extracted post json block represents a photo post.

        Returns:
            bool:
        """
        try:
            override_url = self.post_json["url_overridden_by_dest"]
        except KeyError:
            return False
        else:
            try:
                url_ext = (override_url.rsplit(".", 1)[1])
                if url_ext in PHOTO_FILE_TYPES:
                    return True
            except:
                return False
        return False

    def is_gallery_post(self):
        """
        Checks if the extracted json block represents a gallery post.

        Returns:
            bool:

        """
        self.gallery_url_list = []  # change self later
        iteration = 0
        media_data = {"photo": [], "animation": []}

        try:
            if self.post_json["is_gallery"] == True:
                pass
        except KeyError:
            return False
        else:
            if self.post_json["is_gallery"] == True:

                if self.post_json["media_metadata"] != None:

                    for item in self.post_json["media_metadata"]:
                        # since telegram only accepts max-10 posts as group media.
                        if self.post_json["media_metadata"][item]["status"] == "valid" and iteration <= 8:
                            post_type = (self.post_json["media_metadata"][item]["e"])

                            if post_type == "Image":
                                raw_url = (self.post_json["media_metadata"][item]["s"]["u"])
                                url = raw_url.replace("amp;", "")
                                media_data["photo"].append(url)

                            elif post_type == "AnimatedImage":
                                url = (self.post_json["media_metadata"][item]["s"]["gif"])
                                media_data["animation"].append(url)

                            iteration += 1
                    self.gallery_url_list = media_data

                    return True

                else:
                    pass
            else:
                Cache.save_post_id(self.currrent_subreddit, self.post_id)
                return False

    def is_animation_post(self):
        """
        Checks if the extracted json block represents an animation(gif) post.

        Returns:
            bool:

        """
        try:
            override_url = self.post_json["url_overridden_by_dest"]
        except KeyError:
            return False
        else:
            try:
                url_ext = (override_url.rsplit(".", 1)[1])
            except:
                return False
            else:
                if url_ext in ANIMATION_FILE_TYPES:
                    return True

        return False

    def is_video_post(self):
        """
        Checks if the extracted json block represents an internal video post.

        Returns:
             bool:

        """
        try:
            post_hint = self.post_json["post_hint"]
            is_video = self.post_json["is_video"]
            secure_media = self.post_json["secure_media"]

        except KeyError:
            return False
        else:
            if post_hint == "hosted:video" and is_video == True:
                return True
        return False

    def is_gfycat_post(self):
        """
        Checks if the extracted json block represents an embedded gyfcat post.

        Returns:
                bool:

        """

        try:
            post_hint = self.post_json["post_hint"]
        except KeyError:
            return False
        else:
            if post_hint == "rich:video":
                if self.post_json["media"]["type"] == "gfycat.com":
                    return True
            return False












